"""Per-file forms: what a taught file can be asked, as dropdowns, and the code that answers.

A file skill (file-skills/<id>/skill.json, written in the Teach workspace) describes a workbook once:
its tabs, what each column means, checks, and the business words of that file ("paid out" means
Approved or Paid). From that, every tab gets a **form**:

  measures   what to count or add up        "Number of claims", "Total amount (Rs)"
  group_by   how to break it down           Status, Category, Employee, Claim date: month
  filters    which rows                     Status in [...], Category in [...], Amount 1000..5000
  date       a date range on a date column  Claim date 26/08/2026 .. 26/10/2026
  presets    named business rules           "Paid out" = Status in [Approved, Paid]
  lookups    columns joined in from another tab (Officer -> Officers tab -> District); "match": "first_name"
             also joins a bare first name ("Meena") to the one person in the other tab with that first name

A form state (the *spec*) is plain JSON. `run()` turns it into one DuckDB query; every id and column
is checked against the skill and every value is quoted, so a spec can never become arbitrary SQL.
The person picks from dropdowns, or a small model fills the same spec from a typed question; either way
the numbers come from code.

Every column the teacher did not describe still gets a sensible default (count rows; sum and average of
number columns; group by category columns and by month/quarter/year of date columns), so a file is
usable as soon as it is recognised.

`contract()` runs before every query: the tabs and headers the skill depends on must still be there and
still parse. A small drift (a new status value, a new column) is reported and the answer still runs; a
real change (a used column missing, dates no longer parsing) stops and asks for re-teaching.
"""
import datetime as dt
import json
import re

from lib import filekit as fk

TAB_KEYS = ("headers", "columns", "normalize", "validations", "summary", "measures", "group_by", "filters",
            "presets", "date_columns", "lookups", "row_noun", "hidden")


# ---------------------------------------------------------------- the skill's tabs
def tabs_of(skill):
    """{tab name: tab spec}. A version-1 skill (one sheet, keys at the top level) becomes one tab."""
    if skill.get("tabs"):
        return skill["tabs"]
    t = {k: skill[k] for k in TAB_KEYS if k in skill}
    return {skill.get("sheet") if skill.get("sheet") not in (None, "csv") else (skill.get("title") or "Data"): t}


def map_tabs(skill, sheets):
    """Skill tab -> (file sheet, overlap). Tabs are matched by their headers, so a renamed tab still maps."""
    out, taken = {}, set()
    for tab, spec in tabs_of(skill).items():
        want = set(spec.get("headers") or [])
        best, score = None, 0.0
        for name, df in sheets.items():
            if name in taken:
                continue
            s = fk._overlap(set(fk.header_set(df)), want) if want else 0.0
            if s > score or (s == score and name == tab):
                best, score = name, s
        out[tab] = (best, round(score, 2))
        if best and score >= 0.5:
            taken.add(best)
    return out


def match_file(sheets):
    """(skill, score, tab map) for a workbook. The score is the mean header overlap over the skill's tabs."""
    best = (None, 0.0, {})
    for s in fk.load_skills():
        tabs = tabs_of(s)
        if not any(t.get("headers") for t in tabs.values()):
            continue
        m = map_tabs(s, sheets)
        score = sum(v[1] for v in m.values()) / len(m)
        if score > best[1]:
            best = (s, round(score, 2), m)
    return best if best[1] >= 0.8 else (None, best[1], best[2])


# ---------------------------------------------------------------- column kinds
def column_kinds(spec, df):
    """slug -> {"kind", "label", ...}: the teacher's description first, the data's shape for the rest."""
    cols, norm = spec.get("columns") or {}, spec.get("normalize") or {}
    out = {}
    for c in df.columns:
        s = fk.slug(c)
        info = dict(cols.get(s) or {})
        kind = (norm.get(s) or {}).get("type") or info.get("type")
        if not kind:
            k = fk.classify(df[c])["kind"]
            kind = {"longtext": "text", "empty": "text"}.get(k, k)
            if k == "category" and (norm.get(s) or {}).get("case"):
                kind = "category"
        if kind in ("email", "phone"):
            kind = "contact"  # searchable, never a breakdown
        out[s] = {"kind": kind, "label": info.get("label") or c, "header": c, "meaning": info.get("meaning", "")}
    return out


# ---------------------------------------------------------------- building tables
def table_name(base, tab, many):
    return f"{base}__{fk.slug(tab)}" if many else base


def _clean_view(con, df, spec, name):
    d = df.copy()
    d.columns = [fk.slug(c) for c in d.columns]
    con.register(name + "_raw", d)
    cols, norm = spec.get("columns") or {}, spec.get("normalize") or {}
    sel = []
    for c in d.columns:
        cs, n = cols.get(c, {}), norm.get(c, {})
        expr = f'NULLIF(TRIM("{c}"), \'\')'
        if n.get("map"):
            cases = " ".join(f"WHEN lower(trim({expr})) = {fk._lit(str(k).strip().lower())} THEN {fk._lit(v)}"
                             for k, v in n["map"].items())
            expr = f"CASE {cases} ELSE {expr} END"
        if n.get("case") == "title":
            expr = (f"array_to_string(list_transform(string_split(lower(regexp_replace({expr}, '\\s+', ' ', 'g')), "
                    f"' '), lambda x: upper(x[1]) || x[2:]), ' ')")
        kind = n.get("type") or cs.get("type")
        if kind == "number":
            expr = f"TRY_CAST(regexp_replace({expr}, '(?i)(rs\\.?|inr|₹|,|\\s)', '', 'g') AS DOUBLE)"
        elif kind == "date":
            fmts = n.get("formats") or cs.get("formats") or [cs.get("format") or "%d/%m/%Y"]
            expr = "COALESCE(" + ", ".join(f"TRY_STRPTIME({expr}, {fk._lit(f)})::DATE" for f in fmts) + ")"
        sel.append(f'{expr} AS "{c}"')
    con.execute(f'CREATE OR REPLACE VIEW "{name}_clean" AS SELECT {", ".join(sel)} FROM "{name}_raw"')


def build(con, path, skill, base):
    """One cleaned view per tab (lookups joined in). Returns {tab: {"table", "sheet", "df", "header_row"}}."""
    sheets, hdr = fk.raw_sheets(path)
    tabs = tabs_of(skill)
    m = map_tabs(skill, sheets)
    many = len(tabs) > 1
    out = {}
    for tab, spec in tabs.items():
        sheet = m[tab][0]
        if sheet is None:
            continue
        name = table_name(base, tab, many)
        _clean_view(con, sheets[sheet], spec, name)
        out[tab] = {"table": name, "sheet": sheet, "df": sheets[sheet], "header_row": hdr[sheet]}
    for tab, spec in tabs.items():
        if tab not in out:
            continue
        name = out[tab]["table"]
        joins, extra = [], []
        for k, lk in enumerate(spec.get("lookups") or []):
            other = out.get(lk.get("tab"))
            if not other:
                continue
            (left, right), = lk["on"].items()
            a = f"l{k}"
            cols = ", ".join(f'any_value("{c}") AS "{c}"' for c in lk["columns"])
            lkey = f'lower(trim(CAST(t."{left}" AS VARCHAR)))'
            rkey = f'lower(trim(CAST("{right}" AS VARCHAR)))'
            joins.append(f'LEFT JOIN (SELECT {rkey} AS _k, {cols} FROM '
                         f'"{other["table"]}_clean" GROUP BY 1) {a} ON {lkey} = {a}._k')
            if lk.get("match") == "first_name":
                # "Meena" -> "Meena Kulkarni", only when one person in the other tab has that first name
                joins.append(f'LEFT JOIN (SELECT split_part({rkey}, \' \', 1) AS _k, {cols} FROM '
                             f'"{other["table"]}_clean" WHERE {rkey} <> \'\' GROUP BY 1 HAVING count(DISTINCT {rkey}) = 1) {a}f '
                             f'ON {a}._k IS NULL AND position(\' \' IN {lkey}) = 0 AND {lkey} = {a}f._k')
                extra += [f'COALESCE({a}."{c}", {a}f."{c}") AS "{lk.get("prefix", "")}{c}"' for c in lk["columns"]]
            else:
                extra += [f'{a}."{c}" AS "{lk.get("prefix", "")}{c}"' for c in lk["columns"]]
        con.execute(f'CREATE OR REPLACE VIEW "{name}" AS SELECT t.*{"".join(", " + e for e in extra)} '
                    f'FROM "{name}_clean" t {" ".join(joins)}')
    return out


def lookup_kinds(skill, tab, built):
    """Kinds of the columns a tab gains from lookups (they take the kind they have in their own tab)."""
    out = {}
    for lk in tabs_of(skill)[tab].get("lookups") or []:
        other = built.get(lk.get("tab"))
        if not other:
            continue
        kinds = column_kinds(tabs_of(skill)[lk["tab"]], other["df"])
        for c in lk["columns"]:
            k = dict(kinds.get(c) or {"kind": "category", "label": c})
            k["label"] = lk.get("labels", {}).get(c) or k["label"]
            out[lk.get("prefix", "") + c] = k
    return out


# ---------------------------------------------------------------- the form
FMT = {"inr": "Rs", "count": "", "number": "", "percent": "%"}


def form(con, skill, tab, built):
    """Everything a form needs for one tab: measures, groupings, filters (with the values in *this* data)."""
    spec = tabs_of(skill)[tab]
    b = built[tab]
    kinds = {**column_kinds(spec, b["df"]), **lookup_kinds(skill, tab, built)}
    hidden = set(spec.get("hidden") or [])
    noun = spec.get("row_noun") or "rows"
    measures = list(spec.get("measures") or [])
    have = {m["id"] for m in measures}
    if "rows" not in have:
        measures.insert(0, {"id": "rows", "label": f"Number of {noun}", "sql": "count(*)", "format": "count"})
    taught_sql = {re.sub(r'[\s"]', "", m.get("sql", "")).lower() for m in measures}
    for c, k in kinds.items():
        if k["kind"] == "number" and c not in hidden:
            for agg, word in (("sum", "Total"), ("avg", "Average")):
                mid = f"{agg}:{c}"
                if mid not in have and f"{agg}({c})" not in taught_sql:
                    measures.append({"id": mid, "label": f"{word} {k['label']}", "sql": f'{agg}("{c}")',
                                     "format": "number", "auto": True})
    groups = list(spec.get("group_by") or [])
    have = {g["id"] for g in groups}
    for c, k in kinds.items():
        if c in hidden:
            continue
        if k["kind"] == "category" and c not in have:
            groups.append({"id": c, "label": k["label"], "sql": f'"{c}"', "auto": True})
        if k["kind"] == "date":
            for part, word in (("month", "month"), ("quarter", "quarter"), ("year", "year")):
                gid = f"{c}:{part}"
                if gid not in have:
                    sql = {"month": f"strftime(\"{c}\", '%Y-%m')", "quarter": f"strftime(\"{c}\", '%Y') || '-Q' || quarter(\"{c}\")",
                           "year": f"CAST(year(\"{c}\") AS VARCHAR)"}[part]
                    groups.append({"id": gid, "label": f"{k['label']}: {word}", "sql": sql, "auto": True})
    for c, k in kinds.items():  # text columns (names) can be grouped too, listed last
        if k["kind"] == "text" and c not in hidden and c not in have:
            groups.append({"id": c, "label": k["label"], "sql": f'"{c}"', "auto": True, "many": True})
    filters = []
    for c, k in kinds.items():
        if c in hidden:
            continue
        f = {"column": c, "label": k["label"], "kind": k["kind"]}
        if k["kind"] == "contact":
            f["kind"] = "contains"
        elif k["kind"] in ("category", "text"):
            vals = con.execute(f'SELECT "{c}", count(*) FROM "{b["table"]}" WHERE "{c}" IS NOT NULL GROUP BY 1 '
                               f'ORDER BY 2 DESC, 1 LIMIT 501').fetchall()
            if k["kind"] == "category" or len(vals) <= 60:
                f["kind"] = "choice"
                f["values"] = sorted(str(v[0]) for v in vals[:500])
            else:
                f["kind"] = "contains"
        elif k["kind"] in ("number", "date"):
            lo, hi = con.execute(f'SELECT min("{c}"), max("{c}") FROM "{b["table"]}"').fetchone()
            f["min"], f["max"] = (str(lo) if lo is not None else None), (str(hi) if hi is not None else None)
            if k["kind"] == "date":
                f["kind"] = "date"
        filters.append(f)
    dates = spec.get("date_columns") or [c for c, k in kinds.items() if k["kind"] == "date"]
    return {"tab": tab, "sheet": b["sheet"], "summary": spec.get("summary", ""), "row_noun": noun,
            "measures": [{k: v for k, v in m.items() if k != "sql"} for m in measures],
            "group_by": [{k: v for k, v in g.items() if k != "sql"} for g in groups],
            "filters": filters, "date_columns": dates,
            "presets": [{k: v for k, v in p.items()} for p in spec.get("presets") or []],
            "_measures": {m["id"]: m for m in measures}, "_groups": {g["id"]: g for g in groups},
            "_kinds": kinds}


def public(f):
    return {k: v for k, v in f.items() if not k.startswith("_")}


# ---------------------------------------------------------------- spec -> SQL
class SpecError(ValueError):
    pass


def _iso(v):
    try:
        return fk._to_iso(v)
    except ValueError as e:
        raise SpecError(str(e))


def _where(f, spec, table_cols):
    filters = {c: x["kind"] for c, x in ((x["column"], x) for x in f["filters"])}
    conds, used = [], []
    wanted = dict(spec.get("filters") or {})
    for pid in ([spec["preset"]] if isinstance(spec.get("preset"), str) else spec.get("preset") or []):
        p = next((p for p in f["presets"] if p["id"] == pid), None)
        if not p:
            raise SpecError(f"No preset '{pid}'. Presets: {[p['id'] for p in f['presets']]}")
        for c, v in (p.get("filters") or {}).items():
            wanted.setdefault(c, v)
        used.append(p.get("label") or pid)
    for c, v in wanted.items():
        if c not in filters:
            raise SpecError(f"Can't filter on '{c}'. Filters: {sorted(filters)}")
        kind = filters[c]
        if kind in ("choice", "contains") and isinstance(v, (str, list)) and not isinstance(v, dict):
            vals = [v] if isinstance(v, str) else v
            if not vals:
                continue
            if kind == "contains":
                conds.append("(" + " OR ".join(f'"{c}" ILIKE {fk._lit("%" + str(x) + "%")}' for x in vals) + ")")
            else:
                conds.append(f'lower(trim(CAST("{c}" AS VARCHAR))) IN ('
                             + ", ".join(fk._lit(str(x).strip().lower()) for x in vals) + ")")
        elif isinstance(v, dict) and ("min" in v or "max" in v or "from" in v or "to" in v or "contains" in v
                                      or "not" in v or "blank" in v):
            if "contains" in v:
                conds.append(f'"{c}" ILIKE {fk._lit("%" + str(v["contains"]) + "%")}')
            if "not" in v:
                vals = [v["not"]] if isinstance(v["not"], str) else v["not"]
                conds.append(f'(lower(trim(CAST("{c}" AS VARCHAR))) NOT IN ('
                             + ", ".join(fk._lit(str(x).strip().lower()) for x in vals) + f') OR "{c}" IS NULL)')
            if "blank" in v:
                conds.append(f'"{c}" IS {"" if v["blank"] else "NOT "}NULL')
            lo, hi = v.get("min", v.get("from")), v.get("max", v.get("to"))
            if kind == "date":
                if lo not in (None, ""):
                    conds.append(f'"{c}" >= DATE {fk._lit(_iso(lo))}')
                if hi not in (None, ""):
                    conds.append(f'"{c}" <= DATE {fk._lit(_iso(hi))}')
            else:
                for x, op in ((lo, ">="), (hi, "<=")):
                    if x not in (None, ""):
                        try:
                            conds.append(f'"{c}" {op} {float(fk.as_number(x) if isinstance(x, str) else x)}')
                        except (TypeError, ValueError):
                            raise SpecError(f"'{x}' is not a number for {c}.")
        else:
            raise SpecError(f"Filter for '{c}' should be a list of values or {{min/max/from/to/contains/not}}.")
    d = dict(spec.get("date") or {})
    if d.get("period"):
        d["from"], d["to"] = period(d["period"])
    if d.get("from") or d.get("to"):
        col = d.get("column") or (f["date_columns"][0] if f["date_columns"] else None)
        if col not in f["date_columns"]:
            raise SpecError(f"No date column '{col}'. Date columns: {f['date_columns']}")
        if d.get("from"):
            conds.append(f'"{col}" >= DATE {fk._lit(_iso_edge(d["from"], False))}')
        if d.get("to"):
            conds.append(f'"{col}" <= DATE {fk._lit(_iso_edge(d["to"], True))}')
    return conds, used


PERIODS = ("this_month", "last_month", "this_quarter", "last_quarter", "this_year", "last_year",
           "this_financial_year", "last_financial_year", "last_7_days", "last_30_days", "last_90_days")


def period(name, today=None):
    """Named period -> (from, to) as ISO dates. Financial years run April to March (India)."""
    t = today or dt.date.today()
    first = t.replace(day=1)
    if name == "this_month":
        a, b = first, t
    elif name == "last_month":
        b = first - dt.timedelta(days=1)
        a = b.replace(day=1)
    elif name in ("this_quarter", "last_quarter"):
        q0 = dt.date(t.year, 3 * ((t.month - 1) // 3) + 1, 1)
        if name == "this_quarter":
            a, b = q0, t
        else:
            b = q0 - dt.timedelta(days=1)
            a = dt.date(b.year, 3 * ((b.month - 1) // 3) + 1, 1)
    elif name == "this_year":
        a, b = dt.date(t.year, 1, 1), t
    elif name == "last_year":
        a, b = dt.date(t.year - 1, 1, 1), dt.date(t.year - 1, 12, 31)
    elif name in ("this_financial_year", "last_financial_year"):
        y = t.year if t.month >= 4 else t.year - 1
        if name == "last_financial_year":
            y -= 1
        a, b = dt.date(y, 4, 1), (t if name == "this_financial_year" else dt.date(y + 1, 3, 31))
    elif name.startswith("last_") and name.endswith("_days") and name[5:-5].isdigit():
        a, b = t - dt.timedelta(days=int(name[5:-5]) - 1), t
    else:
        raise SpecError(f"Unknown period '{name}'. Periods: {', '.join(PERIODS)}")
    return a.isoformat(), b.isoformat()


def _iso_edge(v, end):
    """A date, or a month ('2026-09', 'Sep 2026'): a month means its first day, or its last day for 'to'."""
    v = str(v).strip()
    for fmt in ("%Y-%m", "%m/%Y", "%b %Y", "%B %Y"):
        try:
            d = dt.datetime.strptime(v, fmt).date()
        except ValueError:
            continue
        if end:
            d = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
        return d.isoformat()
    return _iso(v)


def compile_spec(f, table, spec):
    """(sql, total_sql or None, column labels). Raises SpecError for anything not in the form."""
    conds, presets = _where(f, spec, None)
    where = (" WHERE " + " AND ".join(conds)) if conds else ""
    measures = spec.get("measures") or []
    groups = spec.get("group_by") or []
    if isinstance(measures, str):
        measures = [measures]
    if isinstance(groups, str):
        groups = [groups]
    for g in groups:
        if g not in f["_groups"]:
            raise SpecError(f"Can't group by '{g}'. Options: {sorted(f['_groups'])}")
    for m in measures:
        if m not in f["_measures"]:
            raise SpecError(f"No measure '{m}'. Options: {sorted(f['_measures'])}")
    limit = int(spec.get("limit") or (200 if not measures else 100))
    limit = max(1, min(limit, 1000))
    if not measures:  # list the matching rows
        cols = [c for c in f["_kinds"]]
        sel = ", ".join(f'"{c}" AS {_q(f["_kinds"][c]["label"])}' for c in cols)
        order = ""
        if spec.get("sort", {}).get("by") in f["_kinds"]:
            order = f' ORDER BY "{spec["sort"]["by"]}" {"DESC" if spec["sort"].get("dir", "desc") == "desc" else "ASC"} NULLS LAST'
        return (f'SELECT {sel} FROM "{table}"{where}{order} LIMIT {limit}',
                f'SELECT count(*) AS {_q("Matching " + f["row_noun"])} FROM "{table}"{where}', presets)
    gsel = [f'COALESCE(CAST({f["_groups"][g]["sql"]} AS VARCHAR), \'(blank)\') AS {_q(f["_groups"][g]["label"])}'
            for g in groups]
    msel = [f'{f["_measures"][m]["sql"]} AS {_q(f["_measures"][m]["label"])}' for m in measures]
    sql = f'SELECT {", ".join(gsel + msel)} FROM "{table}"{where}'
    total = None
    if groups:
        sql += " GROUP BY ALL"
        sort = spec.get("sort") or {}
        by = sort.get("by")
        if by in measures:
            key = _q(f["_measures"][by]["label"])
        elif by in groups:
            key = _q(f["_groups"][by]["label"])
        elif any(":" in g and g.split(":")[1] in ("month", "quarter", "year") for g in groups):
            key, sort = ", ".join(str(i + 1) for i in range(len(groups))), {"dir": "asc"}
        else:
            key = _q(f["_measures"][measures[0]]["label"])
        sql += f' ORDER BY {key} {"ASC" if sort.get("dir") == "asc" else "DESC"} NULLS LAST LIMIT {limit}'
        total = f'SELECT {", ".join(msel)} FROM "{table}"{where}'
    return sql, total, presets


def _q(label):
    return '"' + str(label).replace('"', "'") + '"'


def _dmy(v):
    try:
        return dt.date.fromisoformat(fk._to_iso(v)).strftime("%d/%m/%Y")
    except ValueError:
        return str(v)


def describe(f, spec, presets):
    """The spec in words, e.g. 'Total amount by Employee; Category is Hardware; Claim date 2026-08-26 to ...'."""
    ms = [f["_measures"][m]["label"] for m in (spec.get("measures") or []) if m in f["_measures"]]
    gs = [f["_groups"][g]["label"] for g in (spec.get("group_by") or []) if g in f["_groups"]]
    parts = [(" and ".join(ms) or f"Matching {f['row_noun']}") + (" by " + ", ".join(gs) if gs else "")]
    labels = {x["column"]: x["label"] for x in f["filters"]}
    parts += [f"rule: {p}" for p in presets]
    for c, v in (spec.get("filters") or {}).items():
        if isinstance(v, list):
            parts.append(f"{labels.get(c, c)} is {' or '.join(map(str, v))}")
        elif isinstance(v, str):
            parts.append(f"{labels.get(c, c)} is {v}")
        elif isinstance(v, dict):
            isdate = any(x["column"] == c and x["kind"] == "date" for x in f["filters"])
            bits = [f"{ {'min': 'from', 'max': 'up to', 'to': 'up to'}.get(k, k)} {_dmy(v[k]) if isdate and k in ('from', 'to', 'min', 'max') else (', '.join(v[k]) if isinstance(v[k], list) else v[k])}"
                    for k in ("from", "to", "min", "max", "contains", "not") if v.get(k) not in (None, "")]
            parts.append(f"{labels.get(c, c)} " + ", ".join(bits))
    d = dict(spec.get("date") or {})
    if d.get("period"):
        d["from"], d["to"] = period(d["period"])
    if d.get("from") or d.get("to"):
        d = {**d, "from": d.get("from") and _iso_edge(d["from"], False), "to": d.get("to") and _iso_edge(d["to"], True)}
        col = d.get("column") or (f["date_columns"][0] if f["date_columns"] else "")
        parts.append(f"{labels.get(col, col)} " + (f"{_dmy(d['from'])} to {_dmy(d['to'])}" if d.get("from") and d.get("to")
                     else f"from {_dmy(d['from'])}" if d.get("from") else f"up to {_dmy(d['to'])}"))
    return "; ".join(parts)


def run(con, f, table, spec):
    sql, total_sql, presets = compile_spec(f, table, spec)
    df = con.execute(sql).fetchdf()
    total = con.execute(total_sql).fetchdf() if total_sql else None
    return {"columns": list(df.columns), "rows": _records(df), "total": _records(total)[0] if total is not None else None,
            "described": describe(f, spec, presets), "sql": sql}


def _records(df):
    out = []
    for r in df.itertuples(index=False):
        row = []
        for v in r:
            if v is None or (isinstance(v, float) and v != v):
                row.append(None)
            elif isinstance(v, float):
                row.append(round(v, 2))
            elif hasattr(v, "isoformat"):
                row.append(v.isoformat()[:10])
            elif hasattr(v, "item"):
                row.append(v.item())
            else:
                row.append(v)
        out.append(dict(zip(df.columns, row)))
    return out


def indian(v):
    """12345678.5 -> '1,23,45,678.5' (Indian digit grouping)."""
    neg, v = v < 0, abs(v)
    whole, _, frac = (f"{v:.2f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)).partition(".")
    head, tail = whole[:-3], whole[-3:]
    while len(head) > 2:
        tail = head[-2:] + "," + tail
        head = head[:-2]
    out = (head + "," + tail) if head else tail
    return ("-" if neg else "") + out + ("." + frac if frac else "")


def answer_text(res, f, spec):
    """Plain text with the numbers exactly as computed (the model relays it, never recomputes)."""
    money = re.compile(r"(?i)\(\s*(rs|inr|₹)\s*\)|\b(rs|inr|rupees?|amount|stipend|cost|paid|spend|debts?|savings|income)\b")
    def name(label):
        return re.sub(r"\s*\(\s*(?:Rs|INR|₹)\s*\)", "", str(label)).strip()
    def fmt(label, v):
        if v is None:
            return "none"
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        if isinstance(v, (int, float)):
            return ("Rs " if money.search(str(label)) else "") + indian(v)
        if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            return _dmy(v)
        return str(v)
    head = res["described"] + "."
    if not res["rows"]:
        return head + " No rows match."
    if not spec.get("measures"):
        n = list(res["total"].values())[0] if res["total"] else len(res["rows"])
        kinds = {k["label"]: k["kind"] for k in f["_kinds"].values()}
        cols = [c for c in res["columns"] if kinds.get(c) not in ("contact",)][:6]
        lines = ["- " + ", ".join(f"{c}: {fmt(c, r[c])}" for c in cols if r.get(c) not in (None, ""))
                 for r in res["rows"][:15]]
        more = f"\n({n - 15} more in the form)" if n > 15 else ""
        return head + f" {n} match:\n" + "\n".join(lines) + more
    gcols = [c for c in res["columns"] if c not in (res["total"] or {}) and c not in
             [f["_measures"][m]["label"] for m in spec.get("measures") or [] if m in f["_measures"]]]
    mcols = [c for c in res["columns"] if c not in gcols]
    def measures(r):
        if len(mcols) == 1:
            return fmt(mcols[0], r[mcols[0]])
        return ", ".join(f"{name(c)} {fmt(c, r[c])}" for c in mcols)
    if not gcols:
        return head + " " + measures(res["rows"][0]) + "."
    lines = [f"- {' / '.join(str(r[c]) for c in gcols)}: {measures(r)}" for r in res["rows"][:15]]
    if res["total"] and len(res["rows"]) > 1:
        lines.append(f"- All: {measures(res['total'])}")
    more = f"\n({len(res['rows']) - 15} more rows in the form)" if len(res["rows"]) > 15 else ""
    return head + "\n" + "\n".join(lines) + more


# ---------------------------------------------------------------- contract test
def contract(skill, sheets, con=None, built=None):
    """Is this still the file the skill was taught on? status ok | drift (answer, but say it) | changed (re-teach)."""
    tabs = tabs_of(skill)
    m = map_tabs(skill, sheets)
    msgs, status, detail = [], "ok", {}

    def worse(s):
        nonlocal status
        if s == "changed" or (s == "drift" and status == "ok"):
            status = s

    for tab, spec in tabs.items():
        sheet, score = m[tab]
        d = detail[tab] = {"sheet": sheet, "overlap": score}
        if sheet is None or score < 0.5:
            msgs.append(f"Tab '{tab}' is missing.")
            worse("changed")
            continue
        have = {fk.slug(c): c for c in sheets[sheet].columns if not str(c).lower().startswith("check:")}
        want = set(spec.get("headers") or [])
        missing = sorted(w for w in want if not any(h == w or h.endswith("_" + w) or w.endswith("_" + h) for h in have))
        new = sorted(h for h in have if not any(h == w or h.endswith("_" + w) or w.endswith("_" + h) for w in want))
        d["missing"], d["new"] = missing, new
        used = _used_columns(spec, skill.get("questions") or [])
        if missing:
            hard = [c for c in missing if c in used]
            msgs.append(f"Tab '{tab}': column{'s' if len(missing) > 1 else ''} {', '.join(missing)} "
                        f"{'are' if len(missing) > 1 else 'is'} gone"
                        + (" (the form uses " + ", ".join(hard) + ")" if hard else "") + ".")
            worse("changed" if hard else "drift")
        if new:
            msgs.append(f"Tab '{tab}' has new column{'s' if len(new) > 1 else ''}: {', '.join(have[c] for c in new)}.")
            worse("drift")
        if sheet != tab and tab not in ("Data",) and not (len(tabs) == 1):
            msgs.append(f"Tab '{tab}' is now called '{sheet}'.")
            worse("drift")
        if con is not None and built and tab in built:
            t = built[tab]["table"]
            kinds = column_kinds(spec, sheets[sheet])
            for c, k in kinds.items():
                if k["kind"] not in ("number", "date") or c not in have:
                    continue
                n_raw, n_ok = con.execute(f'SELECT count(NULLIF(TRIM(r."{c}"), \'\')), count(c."{c}") FROM '
                                          f'"{t}_raw" r POSITIONAL JOIN "{t}_clean" c').fetchone()
                if n_raw >= 5:
                    rate = n_ok / n_raw
                    d.setdefault("parse", {})[c] = round(rate, 2)
                    if rate < 0.8:
                        msgs.append(f"Tab '{tab}': only {rate:.0%} of '{k['label']}' reads as a {k['kind']} now.")
                        worse("changed" if c in used else "drift")
            for c, vals in _known_values(spec).items():
                if c not in have:
                    continue
                seen = [r[0] for r in con.execute(f'SELECT DISTINCT "{c}" FROM "{t}" WHERE "{c}" IS NOT NULL').fetchall()]
                extra = sorted(v for v in map(str, seen) if v.strip().lower() not in {x.lower() for x in vals})
                if extra:
                    d.setdefault("new_values", {})[c] = extra[:10]
                    msgs.append(f"Tab '{tab}': '{kinds.get(c, {}).get('label', c)}' has new value"
                                f"{'s' if len(extra) > 1 else ''} {', '.join(extra[:5])}.")
                    worse("drift")
    return {"status": status, "messages": msgs, "tabs": detail}


def _known_values(spec):
    out = {}
    for c, s in (spec.get("columns") or {}).items():
        if s.get("values"):
            out[c] = list(s["values"])
    for r in spec.get("validations") or []:
        if r.get("rule") == "in_list" and r.get("arg") and r["column"] not in out:
            out[r["column"]] = list(r["arg"])
    for c, n in (spec.get("normalize") or {}).items():
        if n.get("map") and c in out:
            out[c] += list(n["map"].values())
    return out


def _used_columns(spec, questions=()):
    """Columns the form depends on: named in taught measures, groupings, presets, lookups or questions, plus
    every date and number column the teacher described (date ranges and totals rely on them)."""
    heads = set(spec.get("headers") or [])
    text = json.dumps([spec.get("measures"), spec.get("group_by"), spec.get("presets"),
                       [q.get("sql", "") for q in questions]])
    used = set(re.findall(r"[a-z][a-z0-9_]*", text)) & heads
    used |= set(spec.get("date_columns") or [])
    for p in spec.get("presets") or []:
        used |= set((p.get("filters") or {}).keys())
    for lk in spec.get("lookups") or []:
        used |= set(lk["on"].keys())
    for c, cs in (spec.get("columns") or {}).items():
        if cs.get("type") in ("date", "number") or (spec.get("normalize") or {}).get(c, {}).get("type") in ("date", "number"):
            used.add(c)
    return used


def today():
    return dt.date.today().isoformat()


# ---------------------------------------------------------------- checks on every tab
def check(path, skill, out_dir):
    """Run every tab's validations. Writes '<name> - checked.xlsx': each tab with its values, one formula column
    per check, problem cells in red, and a Problems sheet. The original is never touched.
    Returns (problems, out_path); a problem is {"tab", "row", "column", "value", "problem"}."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    sheets, hdr = fk.raw_sheets(path)
    m = map_tabs(skill, sheets)
    problems = []
    wb = Workbook()
    wb.remove(wb.active)
    red = PatternFill("solid", fgColor="F8D7DA")
    for tab, spec in tabs_of(skill).items():
        sheet = m[tab][0]
        if sheet is None:
            continue
        df = sheets[sheet]
        by_slug = {fk.slug(c): c for c in df.columns}
        rules = [r for r in spec.get("validations") or [] if r.get("column") in by_slug and r.get("rule") in fk.RULES]
        bad = set()
        for r in rules:
            col = by_slug[r["column"]]
            for i, v in enumerate(df[col]):
                try:
                    ok = fk.RULES[r["rule"]](v, r.get("arg"))
                except Exception:
                    ok = False
                if not ok:
                    row = hdr[sheet] + 1 + i
                    bad.add((row, col))
                    problems.append({"tab": sheet, "row": row, "column": col, "value": v,
                                     "problem": r.get("message") or f"{r['rule']} check failed"})
        for lk in spec.get("lookups") or []:  # a key with no match in the other tab (e.g. a misspelt officer name)
            other = m.get(lk.get("tab"), (None,))[0]
            (left, right), = lk["on"].items()
            if other is None or left not in by_slug:
                continue
            ob = {fk.slug(c): c for c in sheets[other].columns}
            if right not in ob:
                continue
            keys = {re.sub(r"\s+", " ", str(x)).strip().lower() for x in sheets[other][ob[right]] if str(x).strip()}
            amap = {str(k).strip().lower(): str(x) for k, x in ((spec.get("normalize") or {}).get(left, {}).get("map") or {}).items()}
            firsts = {}
            if lk.get("match") == "first_name":
                for x in keys:
                    firsts.setdefault(x.split(" ")[0], set()).add(x)
            for i, v in enumerate(df[by_slug[left]]):
                k = re.sub(r"\s+", " ", v).strip().lower()
                if not v.strip() or k in keys or amap.get(k, "").strip().lower() in keys:
                    continue
                if " " not in k and len(firsts.get(k, ())) == 1:
                    continue
                row = hdr[sheet] + 1 + i
                bad.add((row, by_slug[left]))
                why = (f"first name shared by several people in the {other} tab ({ob[right]})"
                       if " " not in k and len(firsts.get(k, ())) > 1 else f"not found in the {other} tab ({ob[right]})")
                problems.append({"tab": sheet, "row": row, "column": by_slug[left], "value": v, "problem": why})
        ws = wb.create_sheet(str(sheet if sheet != "csv" else "Data")[:31])
        headers = list(df.columns)
        ws.append(headers + [f"Check: {by_slug[r['column']]}" for r in rules])
        for c in range(1, len(headers) + len(rules) + 1):
            ws.cell(1, c).font = Font(bold=True)
        for i, row in df.iterrows():
            r = i + 2
            for j, h in enumerate(headers, start=1):
                v = row[h]
                x = fk.as_number(v) if re.fullmatch(r"-?\d+(\.\d+)?", v or "") else None
                ws.cell(r, j, x if x is not None else v)
                if (hdr[sheet] + 1 + i, h) in bad:
                    ws.cell(r, j).fill = red
            for k, rule in enumerate(rules):
                ref = f"{get_column_letter(headers.index(by_slug[rule['column']]) + 1)}{r}"
                fml = fk.excel_formula(rule["rule"], ref, rule.get("arg"), rule.get("message") or rule["rule"])
                if fml is None:
                    fml = "" if (hdr[sheet] + 1 + i, by_slug[rule["column"]]) not in bad else (rule.get("message") or "check")
                ws.cell(r, len(headers) + k + 1, fml)
    ps = wb.create_sheet("Problems")
    ps.append(["Tab", "Row in original", "Column", "Value", "Problem"])
    for p in problems:
        ps.append([p["tab"], p["row"], p["column"], p["value"], p["problem"]])
    import os
    os.makedirs(out_dir, exist_ok=True)
    name = re.sub(r"\s*-\s*checked$", "", os.path.splitext(os.path.basename(path))[0])
    out = os.path.join(out_dir, f"{name} - checked.xlsx")
    wb.save(out)
    return problems, out
