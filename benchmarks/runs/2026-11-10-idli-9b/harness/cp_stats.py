"""Claude-plans side logs (claude_plans.jsonl in each conversation's IDLI_HOME): $ per question, seconds, Claude calls,
how many questions went out with nothing redacted, how many were repaired by the shape-only backtrack.
  python harness/cp_stats.py <tmp dir with idli9b-* homes>"""
import glob
import json
import os
import sys
from collections import defaultdict

agg = defaultdict(list)
for p in glob.glob(os.path.join(sys.argv[1], "idli9b-*-*", "claude_plans.jsonl")):
    for line in open(p):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        agg[r["model"]].append(r)
out = {}
for k, rs in sorted(agg.items()):
    n = len(rs)
    out[k] = {"questions": n, "usd_per_q": round(sum(r["cost"] for r in rs) / n, 5),
              "secs_per_q": round(sum(r["secs"] for r in rs) / n, 1),
              "calls_per_q": round(sum(r["calls"] for r in rs) / n, 2),
              "intact": round(sum(r["intact"] for r in rs) / n, 2),
              "placeholders_per_q": round(sum(r["placeholders"] for r in rs) / n, 1),
              "backtracked": sum(1 for r in rs if r.get("backtracked"))}
    print(k, out[k])
json.dump(out, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "claude-plans-stats.json"), "w"), indent=1)
