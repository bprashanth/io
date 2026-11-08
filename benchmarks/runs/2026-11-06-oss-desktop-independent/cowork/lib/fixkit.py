"""Suggested fixes for the problems the checks find, and rows that are layout rather than data.

Plain rules, no model: each suggestion is something a person can accept or reject in the dashboard. When the fix
needs a human (a blank required cell, two numbers in one cell), there's no suggestion, only a note on what to do.
Nothing here edits the original file: accepted fixes go into a fixed copy and a fix list with cell links.

Layout rows (found in any sheet, not just one form):
  repeated_header  a row that repeats the column headings (sections pasted under each other)   skipped by default
  subheading       a row with one label and nothing else, e.g. "Transect 2"                     suggested: skip
  total            a row starting "Total" / "Grand total"                                       suggested: skip
A skill can set "skip_rows": [...] per tab to skip kinds for good (Claude decides this with the person).
"""
import datetime as dt
import difflib
import re

from lib import filekit as fk

DEFAULT_SKIP = ["repeated_header"]
LAYOUT_WHY = {
    "repeated_header": "This row repeats the column headings.",
    "subheading": "This row looks like a sub-heading (one label, no data).",
    "total": "This row looks like a totals row; counting it would double the numbers.",
}
PLACEHOLDERS = {"-", "--", "n/a", "na", "nil", "none", "pending", "tbd", "?", "nd", "not available", "x"}


def _norm(v):
    return re.sub(r"\s+", " ", str(v)).strip().lower()


def layout_rows(df):
    """{data row index: kind} for rows that are layout, not records."""
    if df.empty:
        return {}
    heads = {_norm(c) for c in df.columns if not str(c).startswith("column_")}
    filled = (df != "").sum(axis=1)
    typical = float(filled.median()) if len(filled) else 0
    out = {}
    for i, row in df.iterrows():
        vals = [(c, v) for c, v in row.items() if str(v).strip()]
        if not vals:
            continue
        same = sum(1 for c, v in vals if _norm(v) == _norm(c) or _norm(v) in heads)
        if len(vals) >= 2 and same >= 0.6 * len(vals):
            out[i] = "repeated_header"
            continue
        first = _norm(vals[0][1])
        if re.match(r"^(grand\s+)?(sub-?)?totals?\b", first):
            out[i] = "total"
            continue
        if (len(vals) == 1 and typical >= 3 and fk.as_number(vals[0][1]) is None
                and list(df.columns).index(vals[0][0]) <= 1 and len(str(vals[0][1])) <= 60):
            out[i] = "subheading"
    return out


def skip_kinds(spec):
    return spec.get("skip_rows", DEFAULT_SKIP) if isinstance(spec.get("skip_rows", DEFAULT_SKIP), list) else DEFAULT_SKIP


def keep_rows(df, spec):
    """The sheet without the layout rows this tab skips, keeping each record's real spreadsheet row."""
    kinds = set(skip_kinds(spec))
    drop = {i for i, k in layout_rows(df).items() if k in kinds}
    if not drop:
        return df
    keep = [i for i in range(len(df)) if i not in drop]
    rows, cols = df.attrs.get("sheet_rows"), df.attrs.get("sheet_cols")
    out = df.iloc[keep].reset_index(drop=True)
    out.attrs["sheet_rows"] = [rows[i] for i in keep] if rows else None
    out.attrs["sheet_cols"] = cols
    out.attrs["skipped"] = sorted(drop)
    return out


def _num(v):
    s = str(v).strip()
    low = s.lower()
    if low in PLACEHOLDERS:
        return {"to": "", "why": f"'{s}' stands for no value; leave the cell blank."}
    nums = re.findall(r"-?\d+(?:\.\d+)?", s.replace(",", "") if re.fullmatch(r"[\d,.\s]+", s) else s)
    if len(nums) >= 2:
        return {"to": None, "why": f"{len(nums)} numbers in one cell ({', '.join(nums[:3])}): keep one, or record "
                                   "them in separate columns."}
    fixed = re.sub(r"(?<=\d)[oO]|[oO](?=\d)", "0", s)
    fixed = re.sub(r"(?<=\d)[lI]|[lI](?=\d)", "1", fixed)
    if fixed != s and fk.as_number(fixed) is not None:
        return {"to": fixed, "why": "letters that look like digits (O for 0, l for 1)."}
    m = re.fullmatch(r"(?i)\s*(?:approx\.?|about|around|~|c\.|ca\.?)\s*(-?[\d,]+(?:\.\d+)?)\s*\??\s*", s) or \
        re.fullmatch(r"\s*(-?[\d,]+(?:\.\d+)?)\s*(?:\?|\+|approx\.?)\s*", s)
    if m:
        return {"to": m.group(1).replace(",", ""), "why": "an approximate number written with words or symbols."}
    m = re.fullmatch(r"\s*(-?[\d,]+(?:\.\d+)?)\s*([a-zA-Z%]{1,6})\s*", s)
    if m:
        return {"to": m.group(1).replace(",", ""), "why": f"the unit '{m.group(2)}' is written in the cell."}
    return None


def _date(v, arg):
    fmts = arg or ["%d/%m/%Y"]
    s = str(v).strip()
    if re.fullmatch(r"\d{5}", s):  # an Excel date serial number
        d = dt.date(1899, 12, 30) + dt.timedelta(days=int(s))
        if 1990 <= d.year <= 2100:
            return {"to": d.strftime(fmts[0]), "why": "a spreadsheet date number shown as plain digits."}
    for f in fk.DATE_FORMATS:
        try:
            d = dt.datetime.strptime(s, f).date()
        except ValueError:
            continue
        return {"to": d.strftime(fmts[0]), "why": f"written as {s}; the column uses another date format."}
    return None


def _future(v, arg):
    for f in arg or ["%d/%m/%Y"]:
        try:
            d = dt.datetime.strptime(str(v).strip(), f).date()
        except ValueError:
            continue
        if d.day <= 12 and d.day != d.month:
            try:
                sw = dt.date(d.year, d.day, d.month)
            except ValueError:
                return None
            if sw <= dt.date.today():
                return {"to": sw.strftime(f), "why": "day and month look swapped (that date is in the future)."}
        return None
    return None


def _closest(v, options, what):
    vals = [str(o) for o in options if str(o).strip()]
    by = {_norm(o): o for o in vals}
    if _norm(v) in by:
        return {"to": by[_norm(v)], "why": f"same as '{by[_norm(v)]}' apart from capitals or spaces."}
    near = difflib.get_close_matches(_norm(v), list(by), n=2, cutoff=0.75)
    if len(near) == 1 or (len(near) == 2 and difflib.SequenceMatcher(None, _norm(v), near[0]).ratio()
                          - difflib.SequenceMatcher(None, _norm(v), near[1]).ratio() > 0.08):
        return {"to": by[near[0]], "why": f"close to '{by[near[0]]}' in {what}; looks like a typo."}
    return None


def note(rule, value, arg=None):
    """When there's no mechanical fix: what's wrong and what a person should check."""
    v = str(value or "").strip()
    digits = re.sub(r"\D", "", v)
    if rule == "phone":
        return f"{len(digits)} digits; a mobile number has 10. Check the number with the person." if digits else \
            "Not a phone number."
    if rule == "email":
        return "No '@'." if "@" not in v else "Nothing after the '@' that looks like a domain (like example.org)."
    if rule == "date":
        return f"There's no such date as {v}. Check the record." if re.fullmatch(r"[\d/.-]+", v) else \
            f"'{v}' isn't a date. Fill in the real date, or leave it blank if it isn't known yet."
    if rule == "not_future":
        return f"{v} is after today. Check the day, month and year."
    if rule in ("in_list", "lookup"):
        return f"'{v}' isn't one of the known values and isn't close to one. Check the spelling, or add it to the list."
    if rule == "number":
        return f"'{v}' isn't a number. Put the number in, or leave it blank."
    return None


def suggest(rule, value, arg=None, options=None, what="the list"):
    """One suggestion for one problem: {"to": new value ("" = clear) or None (a person must decide), "why"}."""
    got = _suggest(rule, value, arg, options, what)
    if got is None:
        n = note(rule, value, arg)
        return {"to": None, "why": n} if n else None
    return got


def _suggest(rule, value, arg=None, options=None, what="the list"):
    v = str(value or "")
    if rule == "required":
        return {"to": None, "why": "This cell must be filled in; only someone who knows the record can."}
    if not v.strip():
        return None
    if rule in ("number", "range"):
        return _num(v)
    if rule == "date":
        if v.strip().lower() in PLACEHOLDERS | {"tbd", "tba", "unknown", "not known"}:
            return {"to": "", "why": f"'{v.strip()}' means the date isn't known yet; leave it blank until it is."}
        return _date(v, arg)
    if rule == "not_future":
        return _future(v, arg)
    if rule == "email":
        t = re.sub(r"\s+", "", v).rstrip(".").replace("(at)", "@").replace("[at]", "@")
        t = re.sub(r"(?i)\bat\b", "@", t) if "@" not in t else t
        return {"to": t, "why": "spaces or a spelled-out 'at' in the address."} if fk.EMAIL.match(t) and t != v else None
    if rule == "phone":
        t = re.sub(r"[^\d+]", "", v)
        t = re.sub(r"^(\+?91|0)(?=\d{10}$)", "", t)
        return {"to": t, "why": "extra characters or a country code around a 10-digit number."} \
            if re.fullmatch(r"\d{10}", t) and t != v else None
    if rule in ("in_list", "lookup") and options:
        return _closest(v, options, what)
    return None
