"""File skills: how Idli recognises a spreadsheet it has been taught, and how it asks to be taught one.

A *file skill* lives in `file-skills/<id>/skill.json`. It is data, not code: what the columns mean,
how to clean them, which validations to run, and one parameterised DuckDB query per question taught.
Claude writes it in the Teach workspace from a mock of the file (junk values, same structure); Idli
runs it on the real file. Idli never computes numbers itself: every number comes from a query here.

Pieces:
  fingerprint / match   - recognise a file by its header set, whatever its name
  make_mock             - same sheets, headers, formats, blanks and messiness; every value junk;
                          plus a hidden `_idli_teach` sheet (the watermark Claude's teach-file skill reads)
  build_tables          - raw table (all text) + cleaned table (`skill.normalize`) in DuckDB
  check                 - run `skill.validations`, return problems, write "<name> - checked.xlsx"
  answer                - run a taught question with parameters

CLI (for the Teach workspace):
  python -m lib.filekit inspect <file>                 columns, types and messiness of a file or mock
  python -m lib.filekit test <skill_dir> [<mock>]      run the skill's tests.json against a mock
"""
import datetime as dt
import hashlib
import json
import os
import random
import re
import string
import sys

import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.environ.get("IDLI_FILE_SKILLS") or os.path.join(HERE, "file-skills")
TEACH_DIR = os.environ.get("IDLI_TEACH_DIR") or os.path.join(HERE, "teach", "inbox")
WATERMARK = "_idli_teach"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).strip().lower()).strip("_") or "x"


# ---------------------------------------------------------------- reading
def raw_sheets(path):
    """{sheet: DataFrame of strings, header row applied}, plus {sheet: header_row_number (1-based)}."""
    if path.lower().endswith(".csv"):
        frames = {"csv": pd.read_csv(path, header=None, dtype=str, keep_default_na=False)}
    else:
        frames = pd.read_excel(path, sheet_name=None, header=None, dtype=object)
    out, hdr = {}, {}
    for name, df in frames.items():
        if name == WATERMARK:
            continue
        df = df.map(lambda v: "" if v is None or (isinstance(v, float) and pd.isna(v)) else _cell_text(v))
        df = df.loc[~(df == "").all(axis=1), ~(df == "").all(axis=0)]
        if df.empty:
            continue
        h = _header_index(df)
        header = [str(v).strip() or f"column_{j + 1}" for j, v in enumerate(df.iloc[h])]
        body = df.iloc[h + 1:].reset_index(drop=True)
        body.columns = _unique(header)
        out[name] = body
        hdr[name] = int(df.index[h]) + 1
    return out, hdr


def _cell_text(v):
    if isinstance(v, (dt.datetime, dt.date, pd.Timestamp)):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def _unique(names):
    seen, out = {}, []
    for n in names:
        seen[n] = seen.get(n, 0) + 1
        out.append(n if seen[n] == 1 else f"{n} ({seen[n]})")
    return out


def _header_index(df):
    width = (df != "").sum(axis=1).max()
    for i, (_, row) in enumerate(df.iterrows()):
        vals = [v for v in row if v != ""]
        texts = [v for v in vals if not re.fullmatch(r"[\d.,/ :-]+", v)]
        if len(vals) >= max(2, 0.6 * width) and len(texts) >= 0.8 * len(vals):
            return i
    return 0


def main_sheet(sheets):
    return max(sheets, key=lambda s: len(sheets[s]) * max(1, sheets[s].shape[1]))


# ---------------------------------------------------------------- recognising a file
def header_set(df):
    """Slugged headers, ignoring the 'Check: ...' columns Idli adds to a '- checked' copy."""
    return sorted(slug(c) for c in df.columns if not str(c).lower().startswith("check:"))


def fingerprint(df):
    return hashlib.sha1("|".join(header_set(df)).encode()).hexdigest()[:10]


def load_skills():
    out = []
    if not os.path.isdir(SKILLS_DIR):
        return out
    for d in sorted(os.listdir(SKILLS_DIR)):
        p = os.path.join(SKILLS_DIR, d, "skill.json")
        try:
            with open(p) as f:
                s = json.load(f)
            s["_dir"] = os.path.dirname(p)
            out.append(s)
        except (OSError, ValueError):
            continue
    return out


def _overlap(a, b):
    """Share of headers that correspond, counting 'title_row_volunteer_name' ~ 'volunteer_name'."""
    hit, used = 0, set()
    for x in a:
        y = next((y for y in b if y not in used and (y == x or x.endswith("_" + y) or y.endswith("_" + x))), None)
        if y:
            hit += 1
            used.add(y)
    return hit / len(a | b - used) if (a or b) else 0.0


def match(df):
    """Best skill for this table: same header set (>= 80% overlap), whatever the file is called."""
    have = set(header_set(df))
    best, score = None, 0.0
    for s in load_skills():
        want = set(s.get("headers") or [])
        if not want:
            continue
        j = _overlap(have, want)
        if j > score:
            best, score = s, j
    return (best, round(score, 2)) if score >= 0.8 else (None, round(score, 2))


# ---------------------------------------------------------------- column kinds (for mocks and hints)
DATE_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%m/%d/%Y", "%d %b %Y", "%d-%b-%Y", "%b %Y"]
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
PHONE = re.compile(r"^(\+?91[-\s]?)?[6-9]\d{4}[-\s]?\d{5}$")


def as_number(v):
    t = re.sub(r"(?i)(rs\.?|inr|₹|,|\s)", "", str(v))
    try:
        return float(t)
    except ValueError:
        return None


def date_format(vals):
    best, hits = None, 0
    for fmt in DATE_FORMATS:
        n = 0
        for v in vals:
            try:
                dt.datetime.strptime(v, fmt)
                n += 1
            except ValueError:
                pass
        if n > hits:
            best, hits = fmt, n
    return best, hits


def classify(series):
    vals = [v for v in series if v != ""]
    n = len(vals)
    info = {"blank": len(series) - n, "distinct": len(set(vals))}
    if not n:
        return {"kind": "empty", **info}
    fmt, hits = date_format(vals[:400])
    if hits >= 0.6 * min(n, 400):
        return {"kind": "date", "format": fmt, "bad": n - sum(1 for v in vals if _parses(v, fmt)), **info}
    emails = sum(1 for v in vals if EMAIL.match(v))
    if emails >= 0.6 * n:
        return {"kind": "email", "bad": n - emails, **info}
    phones = sum(1 for v in vals if PHONE.match(re.sub(r"[\s-]", "", v)) or PHONE.match(v))
    if phones >= 0.6 * n:
        return {"kind": "phone", "bad": n - phones, **info}
    nums = [as_number(v) for v in vals]
    good = [x for x in nums if x is not None]
    if len(good) >= 0.8 * n:
        styled = sum(1 for v in vals if re.search(r"(?i)rs|inr|₹|,", v))
        return {"kind": "number", "bad": n - len(good), "min": min(good), "max": max(good),
                "decimals": max((len(v.split(".")[1]) for v in vals if re.fullmatch(r"-?\d+\.\d+", v)), default=0),
                "styled": styled, **info}
    if info["distinct"] <= max(12, 0.2 * n):
        return {"kind": "category", **info}
    avg = sum(len(v) for v in vals) / n
    return {"kind": "longtext" if avg > 40 else "text", "avg_len": round(avg), **info}


def _parses(v, fmt):
    try:
        dt.datetime.strptime(v, fmt)
        return True
    except ValueError:
        return False


def _not_future(v, fmts):
    """True unless v parses (in one of fmts) to a date after today. Unparseable is left to the 'date' rule."""
    for f in fmts or ["%d/%m/%Y"]:
        try:
            return dt.datetime.strptime(v, f).date() <= dt.date.today()
        except ValueError:
            pass
    return True


# ---------------------------------------------------------------- mocks
WORDS = ("lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore "
         "et dolore magna aliqua enim ad minim veniam quis nostrud").split()


def _variant(fake, real):
    """Give the fake value the real value's casing ('pune' -> 'district b', 'SATARA' -> 'DISTRICT C')."""
    if real.islower():
        return fake.lower()
    if real.isupper():
        return fake.upper()
    return fake


def mock_column(series, header, rnd, keep_labels=False):
    info = classify(series)
    kind, out = info["kind"], []
    vals = list(series)
    real_variants = _variant_groups(vals) if kind == "category" else {}
    if kind == "date":  # fake dates stay inside the real column's range (no invented future dates)
        fmts = [info["format"]] + [f for f in DATE_FORMATS if f != info["format"]]
        ds = [dt.datetime.strptime(v, f).date() for v in vals if v for f in [next((f for f in fmts if _parses(v, f)), None)] if f]
        lo_d, hi_d = (min(ds), max(ds)) if ds else (dt.date(2026, 1, 1), dt.date(2026, 6, 30))
    cats = {}
    for i, v in enumerate(vals):
        if v == "":
            out.append("")
            continue
        if kind == "date":
            if _parses(v, info["format"]):
                d = lo_d + dt.timedelta(days=rnd.randint(0, max(0, (hi_d - lo_d).days)))
                out.append(d.strftime(info["format"]))
            else:  # another date format keeps its format (mixed formats are a real-world quirk); junk stays junk
                other = next((f for f in DATE_FORMATS if _parses(v, f)), None)
                d = lo_d + dt.timedelta(days=rnd.randint(0, max(0, (hi_d - lo_d).days)))
                out.append(d.strftime(other) if other else rnd.choice(["TBD", "31/02/2026", "next week", "2026"]))
        elif kind == "number":
            x = as_number(v)
            if x is None:
                out.append(rnd.choice(["n/a", "-", "approx 500", "pending"]))
                continue
            lo, hi = info["min"], info["max"]
            y = rnd.uniform(lo, hi) if hi > lo else lo
            y = round(y, info["decimals"]) if info["decimals"] else int(round(y))
            s = str(y)
            if re.search(r"(?i)rs|inr|₹|,", v):  # keep the styling quirks, not the value
                s = rnd.choice(["Rs. {:,}", "₹{:,}", "{:,}", "{:,} INR"]).format(y)
            out.append(s)
        elif kind == "email":
            out.append(f"person{i + 1}@example.org" if EMAIL.match(v) else rnd.choice(["person at example", "n/a"]))
        elif kind == "phone":
            ok = PHONE.match(re.sub(r"[\s-]", "", v)) or PHONE.match(v)
            num = "9" + "".join(rnd.choice(string.digits) for _ in range(9))
            out.append((num if not re.search(r"[\s-]", v) else f"{num[:5]} {num[5:]}") if ok
                       else num[:rnd.randint(5, 8)])
        elif kind == "category" and keep_labels:
            out.append(v)  # the user agreed these labels (e.g. Approved / Pending) are not private
        elif kind == "category":
            base = real_variants.get(v, v)
            if base not in cats:
                cats[base] = f"{header} {_label(len(cats))}"
            fake = cats[base]
            out.append(_variant(fake, v))
        elif kind == "longtext":
            n = max(3, len(v) // 6)
            out.append(" ".join(rnd.choice(WORDS) for _ in range(n)).capitalize())
        else:
            out.append(f"{header} {i + 1}")
    return out, info


def _label(k):
    s = ""
    k += 1
    while k:
        k, r = divmod(k - 1, 26)
        s = chr(65 + r) + s
    return s


def _variant_groups(vals):
    """value -> canonical value, for case/space spelling variants in a category column."""
    canon = {}
    for v in vals:
        if v == "":
            continue
        k = re.sub(r"[^a-z0-9]", "", v.lower())
        canon.setdefault(k, v)
    return {v: canon[re.sub(r"[^a-z0-9]", "", v.lower())] for v in vals if v != ""}


def scrub(text, sheets, keep=()):
    """Replace any real value from the file's text columns that appears in `text` (names, villages...)."""
    for df in sheets.values():
        for c in df.columns:
            info = classify(df[c])
            if info["kind"] in ("number", "date", "empty") or fk_slug_in(c, keep):
                continue
            for v in sorted({x for x in df[c] if len(x) >= 3}, key=len, reverse=True):
                if re.search(r"(?i)\b" + re.escape(v) + r"\b", text):
                    text = re.sub(r"(?i)\b" + re.escape(v) + r"\b", f"<a value from '{c}'>", text)
    return text


def make_mock(path, question, title=None, caller_agent=None, seed=7, share_labels=()):
    """Write teach/inbox/<id>/mock.xlsx (+ request.json). Returns the request dict and a preview."""
    sheets, hdr = raw_sheets(path)
    if not sheets:
        raise ValueError("The file has no data.")
    rnd = random.Random(seed)
    main = main_sheet(sheets)
    fp = fingerprint(sheets[main])
    skill, score = match(sheets[main])
    title = title or re.sub(r"\s*-\s*checked$", "", os.path.splitext(os.path.basename(path))[0])
    rid = f"{slug(title)[:40]}-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    rdir = os.path.join(TEACH_DIR, rid)
    os.makedirs(rdir, exist_ok=True)
    clean_q = scrub(question, sheets, keep=share_labels)
    mocks, kinds = {}, {}
    for name, df in sheets.items():
        cols, k = {}, {}
        for c in df.columns:
            cols[c], info = mock_column(df[c], c, rnd, keep_labels=c in share_labels or fk_slug_in(c, share_labels))
            k[c] = {x: info[x] for x in ("kind", "format", "bad", "blank", "distinct") if x in info}
        mocks[name] = pd.DataFrame(cols)[list(df.columns)].head(300)
        kinds[name] = k
    req = {"kind": "idli-teach-request", "version": 1, "id": rid, "title": title, "fingerprint": fp,
           "main_sheet": main, "question": clean_q, "existing_skill": skill["id"] if skill else None,
           "existing_version": skill.get("version") if skill else None, "caller_agent": caller_agent,
           "created": dt.datetime.now().isoformat(timespec="seconds"), "columns": kinds,
           "real_labels": sorted(c for df in sheets.values() for c in df.columns if fk_slug_in(c, share_labels))}
    mock_path = os.path.join(rdir, "mock.xlsx")
    with pd.ExcelWriter(mock_path, engine="openpyxl") as w:
        for name, df in mocks.items():
            df.to_excel(w, sheet_name=("Sheet1" if name == "csv" else str(name))[:31], index=False)
        pd.DataFrame([{"key": k, "value": json.dumps(v) if isinstance(v, (dict, list)) else v}
                      for k, v in req.items()]).to_excel(w, sheet_name=WATERMARK, index=False)
        w.book[WATERMARK].sheet_state = "hidden"
    with open(os.path.join(rdir, "request.json"), "w") as f:
        json.dump(req, f, indent=1)
    preview = {name: df.head(3).to_dict("records") for name, df in mocks.items()}
    return req, mock_path, preview


def fk_slug_in(c, cols):
    return slug(c) in {slug(x) for x in cols or ()}


def label_columns(path):
    """Category columns and their labels, so the user can choose which labels may be shared."""
    sheets, _ = raw_sheets(path)
    out = {}
    for df in sheets.values():
        for c in df.columns:
            if classify(df[c])["kind"] == "category":
                out[c] = sorted({v for v in df[c] if v})[:12]
    return out


# ---------------------------------------------------------------- running a skill on a real file
def _lit(v):
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def build_tables(con, path, skill, base):
    """Register <base>_raw (text as in the file) and <base> (cleaned per skill.normalize)."""
    sheets, hdr = raw_sheets(path)
    sheet = skill.get("sheet") if skill.get("sheet") in sheets else main_sheet(sheets)
    df = sheets[sheet].copy()
    df.columns = [slug(c) for c in df.columns]
    con.register(base + "_raw", df)
    cols = skill.get("columns") or {}
    norm = skill.get("normalize") or {}
    sel = []
    for c in df.columns:
        spec, n = cols.get(c, {}), norm.get(c, {})
        expr = f'NULLIF(TRIM("{c}"), \'\')'
        if n.get("map"):
            cases = " ".join(f"WHEN lower(trim({expr})) = {_lit(str(k).strip().lower())} THEN {_lit(v)}"
                             for k, v in n["map"].items())
            expr = f"CASE {cases} ELSE {expr} END"
        if n.get("case") == "title":
            expr = f"array_to_string(list_transform(string_split(lower({expr}), ' '), lambda x: upper(x[1]) || x[2:]), ' ')"
        kind = n.get("type") or spec.get("type")
        if kind == "number":
            expr = f"TRY_CAST(regexp_replace({expr}, '(?i)(rs\\.?|inr|₹|,|\\s)', '', 'g') AS DOUBLE)"
        elif kind == "date":
            fmts = n.get("formats") or [spec.get("format") or "%d/%m/%Y"]
            expr = "COALESCE(" + ", ".join(f"TRY_STRPTIME({expr}, {_lit(f)})::DATE" for f in fmts) + ")"
        sel.append(f'{expr} AS "{c}"')
    con.execute(f'CREATE OR REPLACE VIEW "{base}" AS SELECT {", ".join(sel)} FROM "{base}_raw"')
    return sheet, hdr[sheet], df


RULES = {
    "required": lambda v, a: v != "",
    "number": lambda v, a: v == "" or as_number(v) is not None,
    "date": lambda v, a: v == "" or any(_parses(v, f) for f in (a or ["%d/%m/%Y"])),
    "email": lambda v, a: v == "" or bool(EMAIL.match(v)),
    "phone": lambda v, a: v == "" or bool(PHONE.match(re.sub(r"[\s-]", "", v))),
    "in_list": lambda v, a: v == "" or v.strip().lower() in {str(x).strip().lower() for x in (a or [])},
    "range": lambda v, a: v == "" or (as_number(v) is not None and a[0] <= as_number(v) <= a[1]),
    "regex": lambda v, a: v == "" or bool(re.fullmatch(a, v)),
    "not_future": lambda v, a: v == "" or _not_future(v, a),  # arg: date formats
}


def excel_formula(rule, ref, arg, message):
    m = message.replace('"', "'")
    if rule == "required":
        return f'=IF(LEN(TRIM({ref}&""))=0,"{m}","")'
    if rule == "number":
        return (f'=IF({ref}="","",IF(ISNUMBER({ref}),"",IF(ISERROR(VALUE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE('
                f'{ref},",",""),"Rs.",""),"₹",""))),"{m}","")))')
    if rule == "email":
        return f'=IF({ref}="","",IF(ISERROR(FIND(".",{ref},FIND("@",{ref}))),"{m}",""))'
    if rule == "phone":
        return (f'=IF({ref}="","",IF(LEN(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE({ref}&""," ",""),"-",""),"+91",""))'
                f'=10,"","{m}"))')
    if rule == "date":
        fmts = arg or ["%d/%m/%Y"]
        ok = []
        for f in fmts:  # one shape test per accepted format; formats Excel can't test are checked in Python
            if f in ("%d/%m/%Y", "%d-%m-%Y"):
                s = f[2]
                ok.append(f'AND(LEN({ref})=10,MID({ref},3,1)="{s}",MID({ref},6,1)="{s}",VALUE(LEFT({ref},2))<=31,'
                          f'VALUE(MID({ref},4,2))<=12)')
            elif f == "%Y-%m-%d":
                ok.append(f'AND(LEN({ref})=10,MID({ref},5,1)="-",MID({ref},8,1)="-",VALUE(MID({ref},6,2))<=12,'
                          f'VALUE(RIGHT({ref},2))<=31)')
            else:
                return None
        return (f'=IF({ref}="","",IF(ISNUMBER({ref}),"",IF(OR(' + ",".join(f"IFERROR({c},FALSE)" for c in ok)
                + f'),"","{m}")))')
    if rule == "in_list" and arg and len(arg) <= 15:
        opts = ",".join(f'{ref}="{str(x)}"' for x in arg)
        return f'=IF({ref}="","",IF(OR({opts}),"","{m}"))'
    if rule == "range":
        return f'=IF({ref}="","",IFERROR(IF(AND(VALUE({ref})>={arg[0]},VALUE({ref})<={arg[1]}),"","{m}"),"{m}"))'
    if rule == "not_future":
        to_date = {"%d/%m/%Y": f"DATE(VALUE(RIGHT({ref},4)),VALUE(MID({ref},4,2)),VALUE(LEFT({ref},2)))",
                   "%d-%m-%Y": f"DATE(VALUE(RIGHT({ref},4)),VALUE(MID({ref},4,2)),VALUE(LEFT({ref},2)))",
                   "%Y-%m-%d": f"DATE(VALUE(LEFT({ref},4)),VALUE(MID({ref},6,2)),VALUE(RIGHT({ref},2)))"}
        fmts = arg or ["%d/%m/%Y"]
        if any(f not in to_date for f in fmts):
            return None
        d = to_date["%Y-%m-%d"] if fmts == ["%Y-%m-%d"] else to_date[fmts[0]]
        if "%Y-%m-%d" in fmts and fmts != ["%Y-%m-%d"]:
            d = f'IF(MID({ref},5,1)="-",{to_date["%Y-%m-%d"]},{d})'
        return f'=IF({ref}="","",IFERROR(IF(IF(ISNUMBER({ref}),{ref},{d})>TODAY(),"{m}",""),""))'
    return None  # computed in Python only (e.g. regex)


def check(path, skill, out_dir):
    """Run the skill's validations. Writes '<name> - checked.xlsx' (original values, one formula column per
    rule, problem cells highlighted, a Problems sheet). Never touches the original file."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    sheets, hdr = raw_sheets(path)
    sheet = skill.get("sheet") if skill.get("sheet") in sheets else main_sheet(sheets)
    df = sheets[sheet]
    by_slug = {slug(c): c for c in df.columns}
    problems = []
    rules = [r for r in skill.get("validations") or [] if r.get("column") in by_slug]
    for r in rules:
        col = by_slug[r["column"]]
        fn = RULES.get(r["rule"])
        if not fn:
            continue
        for i, v in enumerate(df[col]):
            try:
                ok = fn(v, r.get("arg"))
            except Exception:
                ok = False
            if not ok:
                problems.append({"row": hdr[sheet] + 1 + i, "column": col, "value": v,
                                 "problem": r.get("message") or f"{r['rule']} check failed"})
    wb = Workbook()
    ws = wb.active
    ws.title = "Data"
    headers = list(df.columns)
    ws.append(headers + [f"Check: {by_slug[r['column']]}" for r in rules])
    red = PatternFill("solid", fgColor="F8D7DA")
    for c in range(1, len(headers) + len(rules) + 1):
        ws.cell(1, c).font = Font(bold=True)
    bad = {(p["row"], p["column"]) for p in problems}
    for i, row in df.iterrows():
        r = i + 2
        for j, h in enumerate(headers, start=1):
            v = row[h]
            x = as_number(v) if re.fullmatch(r"-?\d+(\.\d+)?", v or "") else None
            ws.cell(r, j, x if x is not None else v)
            if (hdr[sheet] + 1 + i, h) in bad:
                ws.cell(r, j).fill = red
        for k, rule in enumerate(rules):
            ref = f"{get_column_letter(headers.index(by_slug[rule['column']]) + 1)}{r}"
            f = excel_formula(rule["rule"], ref, rule.get("arg"), rule.get("message") or rule["rule"])
            if f is None:
                f = "" if (hdr[sheet] + 1 + i, by_slug[rule["column"]]) not in bad else (rule.get("message") or "check")
            ws.cell(r, len(headers) + k + 1, f)
    ps = wb.create_sheet("Problems")
    ps.append(["Row in original", "Column", "Value", "Problem"])
    for p in problems:
        ps.append([p["row"], p["column"], p["value"], p["problem"]])
    os.makedirs(out_dir, exist_ok=True)
    name = re.sub(r"\s*-\s*checked$", "", os.path.splitext(os.path.basename(path))[0])
    out = os.path.join(out_dir, f"{name} - checked.xlsx")
    wb.save(out)
    return problems, out, sheet


def fill(sql, params, specs):
    for k, spec in (specs or {}).items():
        v = params.get(k)
        if v in (None, "") and spec.get("default") is not None:
            v = spec["default"]
        if v in (None, ""):
            if not spec.get("optional"):
                raise ValueError(f"Missing '{k}': {spec.get('description', '')}")
            v = None
        elif spec.get("type") == "date":
            v = _to_iso(v)
        elif spec.get("type") == "number":
            v = float(v)
        lit = "NULL" if v is None else (str(v) if isinstance(v, float) else _lit(v))
        if spec.get("type") == "date" and v is not None:
            lit = f"DATE {lit}"
        sql = sql.replace("{{" + k + "}}", lit)
    left = re.findall(r"\{\{(\w+)\}\}", sql)
    if left:
        raise ValueError("Unfilled parameter in query: " + ", ".join(left))
    return sql


def _to_iso(v):
    v = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return dt.datetime.strptime(v, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"Could not read the date '{v}'. Use YYYY-MM-DD.")


# ---------------------------------------------------------------- CLI for the Teach workspace
def _inspect(path):
    sheets, hdr = raw_sheets(path)
    out = {}
    for name, df in sheets.items():
        out[name] = {"header_row": hdr[name], "rows": len(df), "fingerprint": fingerprint(df),
                     "columns": {slug(c): {"header": c, **classify(df[c])} for c in df.columns}}
    if not path.lower().endswith(".csv"):
        try:
            wm = pd.read_excel(path, sheet_name=WATERMARK)
            out["_watermark"] = dict(zip(wm["key"], wm["value"]))
        except Exception:
            out["_watermark"] = None
    return out


def _test(skill_dir, mock=None):
    import duckdb
    with open(os.path.join(skill_dir, "skill.json")) as f:
        skill = json.load(f)
    with open(os.path.join(skill_dir, "tests.json")) as f:
        tests = json.load(f)
    mock = mock or os.path.join(skill_dir, "mock.xlsx")
    sheets, _ = raw_sheets(mock)
    s, score = match(sheets[main_sheet(sheets)])
    fails = 0 if (s and s.get("id") == skill.get("id")) else 1
    print(("ok  " if not fails else "FAIL") + f" recognises the mock (overlap {score})")
    con = duckdb.connect()
    build_tables(con, mock, skill, "t")
    problems, _, _ = check(mock, skill, os.path.join(skill_dir, ".check"))
    print(f"ok   validations ran: {len(problems)} problems in the mock")
    qs = {q["id"]: q for q in skill.get("questions", [])}
    for t in tests:
        q = qs.get(t["question"])
        try:
            got = con.execute(fill(q["sql"].replace("{{table}}", '"t"'), t.get("params", {}), q.get("params"))).fetchall()
            exp = t.get("expect")
            ok = exp is None or _close(got, exp)
            print(("ok  " if ok else "FAIL") + f" {t['question']} {t.get('params', {})} -> {got[:3]}"
                  + ("" if ok else f" expected {exp}"))
            fails += 0 if ok else 1
        except Exception as e:
            print(f"FAIL {t['question']}: {e}")
            fails += 1
    print("ALL PASSED" if not fails else f"{fails} FAILED")
    return fails


def _close(got, exp):
    g = [list(r) for r in got]
    if len(g) != len(exp):
        return False
    for a, b in zip(g, exp):
        for x, y in zip(a, b):
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                if abs(x - y) > 0.01 * max(1, abs(y)):
                    return False
            elif str(x) != str(y):
                return False
    return True


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "inspect":
        print(json.dumps(_inspect(sys.argv[2]), indent=1, default=str, ensure_ascii=False))
    elif len(sys.argv) >= 3 and sys.argv[1] == "test":
        sys.exit(1 if _test(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None) else 0)
    else:
        sys.exit(__doc__)
