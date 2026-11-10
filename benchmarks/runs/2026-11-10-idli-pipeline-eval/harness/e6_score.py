"""E6: score the cleaning output of one taught file against its manifest of planted mess.

  <cowork>/.venv/bin/python harness/e6_score.py <fixture.xlsx> <teach_out_dir> <score.json>

Runs, with the teach workspace's own lib (Claude may have added a rule): formkit.check on the real (synthetic)
file -> problems; workcopy.build -> the working copy (red cells, one comment per kind); then applies the
manifest's fixes to a copy of the real file and checks again (do the marks clear?).
"""
import json
import os
import shutil
import sys
import tempfile


def main(fixture, tdir, out):
    tr = json.load(open(os.path.join(tdir, "transcript.json")))
    ws = tr["workspace"]
    sys.path.insert(0, ws)
    from lib import filekit as fk
    from lib import formkit as fm
    from lib import workcopy
    from openpyxl import load_workbook

    man = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(fixture))), "manifests",
                                      os.path.splitext(os.path.basename(fixture))[0] + ".json")))
    skill_dir = os.path.join(tdir, "skill")
    res = {"fixture": os.path.basename(fixture), "teach": {k: tr.get(k) for k in
           ("secs", "rounds", "cards", "claude_cost", "user_cost", "done", "skill", "filekit_changed", "model", "real_teach")}}
    if not os.path.exists(os.path.join(skill_dir, "skill.json")):
        res["error"] = "no skill written"
        json.dump(res, open(out, "w"), indent=1)
        return
    skill = json.load(open(os.path.join(skill_dir, "skill.json")))
    skill["_dir"] = skill_dir
    sheets, _ = fk.raw_sheets(fixture)
    mapped = fm.map_tabs(skill, sheets)
    res["tabs_mapped"] = {t: v[0] for t, v in mapped.items()}
    hdr_rows = fk.raw_sheets(fixture)[1]
    res["header_rows"] = hdr_rows
    # rows Idli reads as data although they're not records (descriptions, MANDATORY/OPTIONAL, notes): flagged there
    # = a false alarm the person sees; listed so the report can say which
    tmp = tempfile.mkdtemp(prefix="e6-")
    problems, _ = fm.check(fixture, skill, tmp)[:2]

    def key(p):
        return (str(p.get("tab")), int(p["row"]))

    by_row = {}
    for p in problems:
        by_row.setdefault(key(p), []).append(p)
    items = man["items"]
    rows_with_items = {(i["tab"], int(i["row"])) for i in items}
    per_kind, hits = {}, []
    for it in items:
        k = per_kind.setdefault(it["kind"], {"category": it["category"], "expect": it["expect"], "n": 0, "found": 0,
                                             "skipped": 0, "in_doc": 0, "found_in_doc": 0})
        k["n"] += 1
        k["in_doc"] += bool(it.get("in_doc"))
        ps = by_row.get((it["tab"], int(it["row"])), [])
        cols = set(it.get("columns") or []) | {it["column"]}
        above = int(it["row"]) <= hdr_rows.get(it["tab"], 0)  # above Idli's header row: never read as data
        k.setdefault("above_header", 0)
        k["above_header"] += above
        if above:
            found = it["expect"] == "skip"  # a layout row outside the table is skipped; a value there is never checked
            k["skipped"] += found
        elif it["kind"] == "key_missing_species":  # the key lacks a code: every record using it is the evidence
            code = str(it.get("original") or "").strip().lower()
            found = any(str(p.get("value", "")).strip().lower() == code for p in problems)
        elif it["kind"] == "spacer":  # an empty row is dropped on reading; fine unless something flags it
            found = not any(p.get("rule") != "layout" for p in ps)
            k["skipped"] += found
        elif it["expect"] == "skip":
            lay = [p for p in ps if p.get("rule") == "layout"]
            found = bool(lay)
            k["skipped"] += any(p.get("skipped") for p in lay)
        elif it["category"] == "cross":
            found = any(p.get("rule") != "layout" for p in ps)
        else:
            found = any(p.get("column") in cols for p in ps if p.get("rule") != "layout")
        k["found"] += found
        k["found_in_doc"] += found and bool(it.get("in_doc"))
        if found:
            hits.append(it)
    data_rows = sum(man.get("data_rows", {}).values()) or 1
    missing_codes = {str(i.get("original") or "").strip().lower() for i in items if i["kind"] == "key_missing_species"}
    stray = [p for p in problems if key(p) not in rows_with_items
             and str(p.get("value", "")).strip().lower() not in missing_codes]
    stray_cells = len({(key(p), p.get("column")) for p in stray if p.get("rule") != "layout"})
    stray_layout = len({key(p) for p in stray if p.get("rule") == "layout"})
    flag = [i for i in items if i["expect"] == "flag"]
    ok_items = [i for i in items if i["expect"] == "ok"]
    ok_flagged = sum(1 for i in ok_items if any(p.get("column") in (set(i.get("columns") or []) | {i["column"]})
                                                for p in by_row.get((i["tab"], int(i["row"])), [])))
    res.update({
        "problems": len(problems), "data_rows": data_rows,
        "flag_items": len(flag), "flag_found": sum(1 for i in hits if i["expect"] == "flag"),
        "flag_in_doc": sum(1 for i in flag if i.get("in_doc")),
        "flag_found_in_doc": sum(1 for i in hits if i["expect"] == "flag" and i.get("in_doc")),
        "skip_items": sum(1 for i in items if i["expect"] == "skip"),
        "skip_found": sum(1 for i in hits if i["expect"] == "skip"),
        "ok_items": len(ok_items), "ok_flagged": ok_flagged,
        "false_alarm_cells": stray_cells, "false_alarm_layout_rows": stray_layout,
        "false_alarms_per_100_rows": round(100 * stray_cells / data_rows, 1),
        "per_kind": per_kind,
        "false_alarm_examples": [{k: str(p.get(k))[:60] for k in ("tab", "row", "column", "value", "problem")}
                                 for p in stray[:12]],
    })
    # the working copy: one comment per kind of problem
    wc = os.path.join(tmp, "working.xlsx")
    if fixture.lower().endswith(".xlsx"):
        try:
            made = workcopy.build(fixture, skill, problems, wc)
            book = load_workbook(wc)
            comments = [(ws_.title, c.coordinate, c.comment.text) for ws_ in book.worksheets for row in ws_.iter_rows()
                        for c in row if c.comment]
            res["working_copy"] = {"comments": len(comments), "groups": made.get("groups"),
                                   "cells": made.get("cells"), "live_cells": made.get("live"), "static_cells": made.get("static"),
                                   "comment_examples": [{"tab": t, "cell": a, "text": x[:400]} for t, a, x in comments[:8]]}
            shutil.copy(wc, os.path.join(os.path.dirname(out), os.path.basename(out).replace(".json", " - working copy.xlsx")))
        except Exception as e:  # noqa: BLE001
            res["working_copy"] = {"error": f"{type(e).__name__}: {e}"[:400]}
    # fix every planted value the way a person would, then check again
    fixed = os.path.join(tmp, "fixed.xlsx")
    book = load_workbook(fixture)
    applied = 0
    for it in flag:
        if it.get("fix") is None or it["category"] == "layout":
            continue
        ws_ = book[it["tab"]] if it["tab"] in book.sheetnames else None
        if ws_ is None:
            continue
        hdr_cells = {}
        for r in range(1, min(ws_.max_row, 40) + 1):
            for c in range(1, ws_.max_column + 1):
                if str(ws_.cell(r, c).value).strip() == it["column"]:
                    hdr_cells.setdefault(it["column"], c)
        col = hdr_cells.get(it["column"])
        if col:
            ws_.cell(int(it["row"]), col).value = it["fix"]
            applied += 1
    book.save(fixed)
    p2, _ = fm.check(fixed, skill, tmp)[:2]
    left = [p for p in p2 if p.get("rule") != "layout" and key(p) in {(i["tab"], int(i["row"])) for i in flag
                                                                       if i.get("fix") is not None and i in hits}]
    res["after_fix"] = {"fixes_applied": applied, "problems_before": sum(p.get("rule") != "layout" for p in problems),
                        "problems_after": sum(p.get("rule") != "layout" for p in p2),
                        "still_marked_on_fixed_items": len(left)}
    json.dump(res, open(out, "w"), indent=1, default=str)
    print(json.dumps({k: res[k] for k in ("fixture", "problems", "flag_items", "flag_found", "skip_items", "skip_found",
                                          "ok_items", "ok_flagged", "false_alarms_per_100_rows")}))


if __name__ == "__main__":
    main(*sys.argv[1:4])
