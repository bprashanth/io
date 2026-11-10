"""Summarise E6 scores: per file and per kind of mess.  python harness/e6_table.py [fake|real]"""
import glob
import json
import os
import sys

E = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mode = sys.argv[1] if len(sys.argv) > 1 else "fake"
rows, kinds = [], {}
for p in sorted(glob.glob(f"{E}/results/e6/{mode}/*.score.json")):
    r = json.load(open(p))
    if r.get("error"):
        print(r["fixture"], "ERROR", r["error"])
        continue
    wc = r.get("working_copy") or {}
    t = r["teach"]
    rows.append(r)
    print(f"{r['fixture']:34} flag {r['flag_found']:2}/{r['flag_items']:2}  skip {r['skip_found']:2}/{r['skip_items']:2}  "
          f"ok-flagged {r['ok_flagged']}/{r['ok_items']}  false alarms {r['false_alarm_cells']:3} "
          f"({r['false_alarms_per_100_rows']}/100 rows)  comments {wc.get('comments')} kinds {wc.get('groups')} "
          f"{'WC-ERR ' + wc['error'] if wc.get('error') else ''} after-fix left {r['after_fix']['still_marked_on_fixed_items']}"
          f"  teach {t['secs']}s cards {t['cards']} ${t['claude_cost']}")
    for k, v in r["per_kind"].items():
        a = kinds.setdefault(k, {"category": v["category"], "expect": v["expect"], "n": 0, "found": 0, "files": 0})
        a["n"] += v["n"]
        a["found"] += v["found"]
        a["files"] += 1
print()
for k, a in sorted(kinds.items(), key=lambda x: (x[1]["category"], x[0])):
    print(f"{a['category']:7} {k:22} expect {a['expect']:5} {a['found']:3}/{a['n']:3}  ({a['files']} files)")
tot = lambda key: sum(r[key] for r in rows)  # noqa: E731
print(f"\nALL: flag {tot('flag_found')}/{tot('flag_items')}, in doc {tot('flag_found_in_doc')}/{tot('flag_in_doc')}, "
      f"skip {tot('skip_found')}/{tot('skip_items')}, ok wrongly flagged {tot('ok_flagged')}/{tot('ok_items')}, "
      f"false-alarm cells {tot('false_alarm_cells')} over {tot('data_rows')} rows")
