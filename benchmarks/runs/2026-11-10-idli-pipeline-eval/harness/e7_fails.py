"""Why E7 spans failed, per variant: which check broke, and how often the own-card guard fired."""
import collections
import glob
import json
import os
import sys

E = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
run = sys.argv[1] if len(sys.argv) > 1 else "e7-local12"
rows = json.load(open(f"{E}/results/{run}/scores.json"))
fails = collections.defaultdict(collections.Counter)
for r in rows:
    if r["pass"] or (r["conv"] == "r03-claim-size" and int(r["span"]) in (3, 4)):
        continue
    c = r.get("checks") or {}
    why = [k for k, v in c.items() if v is False] or (["invented numbers"] if r.get("invented") else []) or \
        (r.get("deviations") or ["?"])
    fails[r["variant"]][",".join(sorted(why))] += 1
for v, cnt in fails.items():
    print(v, sum(cnt.values()), "failed spans")
    for k, n in cnt.most_common(8):
        print(f"   {n:3}  {k}")
blocked = collections.Counter()
phase_miss = collections.Counter()
for p in glob.glob(f"{E}/results/{run}/*/*/*.json"):
    log = json.load(open(p))
    for t in log.get("turns", []):
        for e in t["events"]:
            if e.get("error") == "own_card_blocked":
                blocked[log["variant"]] += 1
            if e["type"] == "tool" and isinstance(e.get("result"), dict) and "unknown tool" in str(e["result"]):
                phase_miss[log["variant"]] += 1
print("own cards blocked by the guard:", dict(blocked))
print("calls to a tool not listed in that phase:", dict(phase_miss))
