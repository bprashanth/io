"""E7 summary: results/before (last round, rescored) and results/e7-* (this round), per model/variant/set.
held3 r03 spans 3-4 are left out everywhere (last round asked an impossible question there; this round a fixed one),
so before and after count the same spans. "ask" = spans that check a file_ask answer.
  python3 harness/e7_table.py"""
import collections
import glob
import json
import os

E = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = []
for p in glob.glob(f"{E}/results/e7-*/scores.json") + [f"{E}/results/before/scores.json"]:
    if not os.path.exists(p):
        continue
    run = os.path.basename(os.path.dirname(p))
    for r in json.load(open(p)):
        if r["conv"] == "r03-claim-size" and int(r["span"]) in (3, 4):
            continue
        r["run"] = run
        rows.append(r)
g = collections.defaultdict(list)
for r in rows:
    g[(r["run"], r["model"], r["variant"], "held3" if r["scenario"] == "held3.json" else "other")].append(r)
print(f"{'run':9} {'model':16} {'variant':14} {'set':5} {'all spans':>12} {'ask spans':>12} {'own card':>8} "
      f"{'s/span':>6} {'chats':>5} {'reps':>4}")
for k in sorted(g):
    rs = g[k]
    n, ok = len(rs), sum(bool(r["pass"]) for r in rs)
    ask = [r for r in rs if r.get("segment") == "ask"]
    aok = sum(bool(r["pass"]) for r in ask)
    own = sum("card_where_user_types" in (r.get("deviations") or []) for r in rs)
    secs = sum(r.get("secs") or 0 for r in rs) / n
    print(f"{k[0]:9} {k[1]:16} {k[2]:14} {k[3]:5} {ok:3}/{n:3} {100 * ok / n:3.0f}% {aok:3}/{len(ask):3} "
          f"{100 * aok / max(1, len(ask)):3.0f}% {own:8} {secs:6.1f} {len({r['conv'] for r in rs}):5} "
          f"{len({r['rep'] for r in rs}):4}")
