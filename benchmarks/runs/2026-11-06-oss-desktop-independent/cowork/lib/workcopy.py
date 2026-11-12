"""A working copy of a spreadsheet with its problems marked, for the person to fix in Google Sheets.

The original file is opened as it is (formatting, other tabs, everything) and gets:
- live red highlights: one conditional-format rule per checked column, built from the same checks Idli runs, so a
  cell turns white again as soon as it's fixed. Checks a formula can't express exactly get a static amber fill
  instead (it stays until Idli checks again).
- one comment per kind of problem, not per cell: on the first cell, with what's wrong, the suggested fix and the
  other cells with the same problem. Google Sheets imports these as real comments (a count shows on each tab).
- grey on layout rows Idli skips (repeated headings), with one comment saying so.
- a last tab, "Idli checks", listing the kinds of problems with their first cell, and the allowed-value lists the
  highlights look up.
The copy is uploaded next to the original (sites/google: working_copy). When the person says they're ready, Idli
downloads the copy, drops the "Idli checks" tab (strip()) and runs the form on it.
"""
import re

from lib import filekit as fk
from lib import fixkit
from lib import formkit as fm

CHECKS_TAB = "Idli checks"
SKILL_TAB = "_idli_skill"  # hidden: what Idli learned about this file, so a colleague's Idli can use it (lib/share.py)
CHUNK = 40000  # Google Sheets keeps up to 50,000 characters in a cell
MAX_REFS = 6


def _runs(rows):
    """[5,6,7,9,10] -> [(5,7),(9,10)]"""
    out = []
    for r in sorted(rows):
        if out and r == out[-1][1] + 1:
            out[-1][1] = r
        else:
            out.append([r, r])
    return [tuple(x) for x in out]


def _cond(f):
    """excel_formula's =IF(test,"message","") as a true/false test for conditional formatting."""
    return f"LEN({f[1:]})>0"


def _group_key(p):
    v = re.sub(r"\s+", " ", str(p.get("value") or "")).strip().lower()
    if p["rule"] == "layout":
        return (p["tab"], "layout", p.get("kind"), bool(p.get("skipped")))
    if p["rule"] == "row_check":  # a taught check across columns or tabs: one comment per check
        return (p["tab"], p["column"], "row_check", p.get("check") or p.get("problem"))
    if p["rule"] in ("required",) or not v:
        return (p["tab"], p["column"], p["rule"], "")
    sg = p.get("suggestion") or {}
    if sg.get("to") is None and p["rule"] in ("number", "range", "date", "phone", "email"):
        return (p["tab"], p["column"], p["rule"], "?" + (sg.get("why") or "")[:20])  # same kind of note
    return (p["tab"], p["column"], p["rule"], v)


def _fix_text(p):
    sg = p.get("suggestion") or {}
    if sg.get("action") == "skip_row":
        return "Suggested: delete this row, or keep rows like it out of the table."
    if sg.get("to") == "":
        return f"Suggested: leave it blank. {sg.get('why', '')}".strip()
    if sg.get("to") is not None:
        return f"Suggested: {sg['to']} ({sg.get('why', '')})"
    return sg.get("why") or ""


def groups(problems):
    """Problems grouped by kind: [{key, first, cells, problem, fix, count}] in sheet order."""
    out = {}
    for p in problems:
        g = out.setdefault(_group_key(p), {"tab": p["tab"], "first": p, "cells": [], "count": 0})
        g["cells"].append(p.get("cell"))
        g["count"] += 1
    return list(out.values())


def build(path, skill, problems, out_path):
    """Write the working copy of `path` (an .xlsx) to out_path. Returns {"groups", "live", "static"}."""
    from openpyxl import load_workbook
    from openpyxl.comments import Comment
    from openpyxl.formatting.rule import FormulaRule
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.utils.cell import coordinate_from_string

    red = PatternFill("solid", fgColor="F4CCCC", bgColor="F4CCCC")
    amber = PatternFill("solid", fgColor="FFE599")
    grey = PatternFill("solid", fgColor="E9ECEF")
    book = load_workbook(path)
    if CHECKS_TAB in book.sheetnames:
        del book[CHECKS_TAB]
    lists = book.create_sheet(CHECKS_TAB)
    sheets, hdr = fk.raw_sheets(path)
    m = fm.map_tabs(skill, sheets)
    live, list_col = set(), [4]  # cells a live rule covers; next free column for allowed-value lists

    def add_list(title, values):
        list_col[0] += 1
        c = list_col[0]
        lists.cell(1, c, title).font = Font(bold=True)
        for k, v in enumerate(values, start=2):
            lists.cell(k, c, str(v))
        letter = get_column_letter(c)
        return f"INDIRECT(\"'{CHECKS_TAB}'!{letter}$2:{letter}${len(values) + 1}\")"

    for tab, spec in fm.tabs_of(skill).items():
        sheet = m[tab][0]
        if sheet is None or sheet not in book.sheetnames:
            continue
        ws, df, h = book[sheet], sheets[sheet], hdr[sheet]
        by_slug = {fk.slug(c): c for c in df.columns}
        layout = fixkit.layout_rows(df)
        record_rows = [i for i in range(len(df)) if i not in layout]

        def letter(col):
            return re.match(r"[A-Z]+", fk.cell_ref(df, 0, col, h)).group(0)

        def add_rule(col, test_for):
            L = letter(col)
            rows = [fk.sheet_row(df, i, h) for i in record_rows]
            for a, b in _runs(rows):
                ws.conditional_formatting.add(f"{L}{a}:{L}{b}", FormulaRule(formula=[test_for(f"{L}{a}")], fill=red,
                                                                            stopIfTrue=False))
            live.update((sheet, f"{L}{r}") for r in rows)

        for r in spec.get("validations") or []:
            col = by_slug.get(r.get("column"))
            if not col or r.get("rule") not in fk.RULES:
                continue
            if r["rule"] == "in_list" and r.get("arg"):
                ref = add_list(f"{col} (allowed)", r["arg"])
                add_rule(col, lambda c, ref=ref: f'AND(LEN(TRIM({c}))>0,COUNTIF({ref},TRIM({c}))=0)')
                continue
            if r["rule"] == "regex":
                continue
            f = fk.excel_formula(r["rule"], "@@", r.get("arg"), "x")
            if f:
                add_rule(col, lambda c, f=f: _cond(f.replace("@@", c)))
        for lk in spec.get("lookups") or []:
            other = m.get(lk.get("tab"), (None,))[0]
            (left, right), = lk["on"].items()
            if other is None or left not in by_slug or lk.get("match") == "first_name":
                continue
            ob = {fk.slug(c): c for c in sheets[other].columns}
            if right not in ob:
                continue
            keys = sorted({str(x).strip() for x in sheets[other][ob[right]] if str(x).strip()})
            accept = [re.compile(a, re.I) for a in lk.get("accept") or []]  # the team's own codes (UKS1, Fern)
            if accept:
                keys += sorted({str(v).strip() for v in df[by_slug[left]] if str(v).strip()
                                and any(a.fullmatch(str(v).strip()) for a in accept)})
            amap = ((spec.get("normalize") or {}).get(left, {}).get("map") or {})
            keys += [str(k).strip() for k in amap if str(k).strip()]  # spellings the skill already maps
            ref = add_list(f"{by_slug[left]} (known in {other})", keys)
            add_rule(by_slug[left], lambda c, ref=ref: f'AND(LEN(TRIM({c}))>0,COUNTIF({ref},TRIM({c}))=0)')

    gs = groups(problems)
    static = 0
    for g in gs:
        p = g["first"]
        if p["tab"] not in book.sheetnames or not p.get("cell"):
            continue
        ws = book[p["tab"]]
        if p["rule"] == "layout":
            for cell in g["cells"]:
                _, row = coordinate_from_string(cell)
                for c in ws[row]:
                    c.fill = grey
        else:
            for cell in g["cells"]:
                if (p["tab"], cell) not in live:
                    ws[cell].fill = amber
                    static += 1
        others = [c for c in g["cells"][1:] if c]
        if p["rule"] == "layout":
            text = fixkit.LAYOUT_WHY[p["kind"]] + (" Idli skips rows like this; no need to change them."
                                                  if p.get("skipped") else " " + _fix_text(p))
            more = f"\n{g['count']} rows like this (grey): " if g["count"] > 1 else ""
        else:
            text = f"{p['problem']}. {_fix_text(p)}".replace("..", ".")
            more = f"\nSame problem in {g['count'] - 1} more cell{'s' if g['count'] > 2 else ''}: " if others else ""
        if more:
            more += ", ".join(others[:MAX_REFS]) + (" ..." if len(others) > MAX_REFS else "")
        c = ws[p["cell"]]
        old = c.comment.text + "\n\n" if c.comment else ""
        c.comment = Comment(f"{old}Idli: {text}{more}", "Idli")
        c.comment.width, c.comment.height = 320, 140
    # the list of kinds, first, so the tab reads top-down
    lists.cell(1, 1, "Tab").font = Font(bold=True)
    lists.cell(1, 2, "First cell").font = Font(bold=True)
    lists.cell(1, 3, "Cells").font = Font(bold=True)
    lists.cell(1, 4, "What to do").font = Font(bold=True)
    k = 2
    for g in gs:
        p = g["first"]
        if p["rule"] == "layout" and p.get("skipped"):
            continue
        lists.cell(k, 1, p["tab"])
        cl = lists.cell(k, 2, p.get("cell"))
        if p.get("cell") and p["tab"] in book.sheetnames:
            cl.hyperlink = f"#'{p['tab']}'!{p['cell']}"
            cl.font = Font(color="1155CC", underline="single")
        lists.cell(k, 3, g["count"])
        lists.cell(k, 4, (f"{p['column']}: " if p["rule"] != "layout" else "") + f"{p['problem']}. {_fix_text(p)}")
        k += 1
    for col, w in (("A", 22), ("B", 10), ("C", 7), ("D", 90)):
        lists.column_dimensions[col].width = w
    embed(book, skill)
    book.save(out_path)
    return {"groups": len([g for g in gs if not (g["first"]["rule"] == "layout" and g["first"].get("skipped"))]),
            "cells": sum(g["count"] for g in gs if not g["first"].get("skipped")), "live": len(live), "static": static}


def embed(book, skill):
    """A hidden tab carrying the file's skill (form, checks, charts; no fake copy, no rows of data). Anyone who opens
    the shared sheet with Idli is offered it instead of teaching from scratch. IDLI_EMBED_SKILL=0 turns it off."""
    import os
    if os.environ.get("IDLI_EMBED_SKILL", "1") == "0" or not (skill or {}).get("id"):
        return False
    try:
        from lib import share
        data, _ = share.pack_bytes(skill["id"], with_mock=False)
    except Exception:  # noqa: BLE001  (the copy is still useful without it)
        return False
    text = share.to_text(data)
    if SKILL_TAB in book.sheetnames:
        del book[SKILL_TAB]
    ws = book.create_sheet(SKILL_TAB)
    ws.sheet_state = "hidden"
    ws.cell(1, 1, "What Idli learned about this file, for colleagues who use Idli. Leave this tab as it is.")
    for i in range(0, len(text), CHUNK):
        ws.cell(2 + i // CHUNK, 1, text[i:i + CHUNK])
    return True


def embedded(path):
    """The skill bundle a shared sheet carries (bytes), or None."""
    from openpyxl import load_workbook
    try:
        book = load_workbook(path, read_only=True)
    except Exception:  # noqa: BLE001
        return None
    try:
        if SKILL_TAB not in book.sheetnames:
            return None
        rows = [r[0] for r in book[SKILL_TAB].iter_rows(min_row=2, max_col=1, values_only=True) if r and r[0]]
    finally:
        book.close()
    from lib import share
    try:
        return share.from_text("".join(str(x) for x in rows))
    except Exception:  # noqa: BLE001
        return None


def strip(path):
    """Drop Idli's tabs ("Idli checks", the hidden skill) from a downloaded working copy, so the form reads only the
    person's tabs."""
    from openpyxl import load_workbook
    book = load_workbook(path)
    gone = [t for t in (CHECKS_TAB, SKILL_TAB) if t in book.sheetnames]
    for t in gone:
        del book[t]
    if gone:
        book.save(path)
    return bool(gone)
