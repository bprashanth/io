"""Pass rates per (model, variant) for chosen scenario files, from scores.json.
  python harness/by_set.py <run dir> held3.json[,held2.json] [segment-breakdown]"""
import json
import os
import sys
from collections import defaultdict

rows = json.load(open(os.path.join(sys.argv[1], "scores.json")))
sets = sys.argv[2].split(",")
segs = ["start", "find", "open", "ask", "chart", "teach", "clean", "skills", "starthere"]
agg = defaultdict(lambda: defaultdict(list))
for r in rows:
    if r["scenario"] not in sets:
        continue
    k = (r["model"], r["variant"])
    agg[k]["all"].append(r["pass"])
    agg[k][r["segment"]].append(r["pass"])
    agg[k]["inv"].append(bool(r["invented"]))
    if "spec" in r["checks"]:
        agg[k]["spec"].append(r["checks"]["spec"])
        agg[k]["relay"].append(r["checks"]["relay"])


def pct(x):
    return f"{100 * sum(x) / len(x):4.0f}" if x else "   -"


print(f"{'model':22} {'variant':9} {'n':>4} {'ALL':>4} " + " ".join(f"{s[:6]:>6}" for s in segs) + "   spec relay inv")
for (m, v), d in sorted(agg.items()):
    print(f"{m:22} {v:9} {len(d['all']):4} {pct(d['all'])} " + " ".join(f"{pct(d[s]):>6}" for s in segs)
          + f"   {pct(d['spec'])} {pct(d['relay'])} {pct(d['inv'])}")
