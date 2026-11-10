"""E7 summary from every results/e7-*/scores.json: per model and variant, held3 and the other chats.
  python3 harness/e7_table.py      (run harness/e7_env.sh score.py results/<run> first if a run was interrupted)"""
import collections
import glob
import json
import os

E = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = []
for p in glob.glob(f"{E}/results/e7-*/scores.json"):
    run = os.path.basename(os.path.dirname(p))
    for r in json.load(open(p)):
        r["run"] = run
        rows.append(r)
g = collections.defaultdict(list)
for r in rows:
    g[(r["run"], r["model"], r["variant"], "held3" if r["scenario"] == "held3.json" else "other")].append(r)
print(f"{'run':10} {'model':16} {'variant':11} {'set':5} {'pass':>9} {'own-card':>8} {'calls/span':>10} {'s/span':>7} "
      f"{'invented':>8} {'chats':>5}")
for k in sorted(g):
    rs = g[k]
    n = len(rs)
    ok = sum(bool(r["pass"]) for r in rs)
    own = sum("card_where_user_types" in (r.get("deviations") or []) for r in rs)
    calls = sum(r.get("model_calls") or 0 for r in rs) / n
    secs = sum(r.get("secs") or 0 for r in rs) / n
    inv = sum(bool(r.get("invented")) for r in rs)
    chats = len({r["conv"] for r in rs})
    print(f"{k[0]:10} {k[1]:16} {k[2]:11} {k[3]:5} {ok:3}/{n:3} {100 * ok / n:3.0f}% {own:8} {calls:10.1f} {secs:7.1f} "
          f"{inv:8} {chats:5}")
