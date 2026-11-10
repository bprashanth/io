"""Footprint table for the pinned run: per config, held3 % and dev+held+held2 %, seconds per span (chat model time +
spec sub-call time), the providers that actually served the chat and spec calls.
  python harness/footprint.py results/pinned"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

run = sys.argv[1]
rows = json.load(open(os.path.join(run, "scores.json")))
agg = defaultdict(lambda: defaultdict(list))
for r in rows:
    k = (r["model"], r["variant"])
    s = "held3" if r["scenario"] == "held3.json" else "rest"
    agg[k][s].append(r["pass"])
    agg[k]["secs"].append(r["secs"])
prov = defaultdict(Counter)
spec_secs = defaultdict(list)
for p in glob.glob(os.path.join(run, "*", "*", "*.json")):
    if os.path.basename(p) == "scores.json":
        continue
    log = json.load(open(p))
    k = (log["model"], log.get("variant"))
    for t in log.get("turns", []):
        for e in t["events"]:
            if e["type"] == "model":
                prov[k]["chat:" + str(e.get("provider"))] += 1
            if e["type"] == "tool" and isinstance(e.get("result"), dict) and e["result"].get("spec_model_secs"):
                spec_secs[k].append(e["result"]["spec_model_secs"])
for p in glob.glob("/tmp/claude-1000/b9/tmp/idli9b-pin-*/spec_calls.jsonl"):
    pass
print(f"{'variant':16} {'held3':>6} {'rest':>6} {'s/span':>7} {'spec s':>7}  providers")
for k, d in sorted(agg.items()):
    pct = lambda x: f"{100 * sum(x) / len(x):5.0f}" if x else "    -"
    ss = spec_secs.get(k) or []
    print(f"{k[1]:16} {pct(d['held3']):>6} {pct(d['rest']):>6} {sum(d['secs']) / len(d['secs']):7.1f} "
          f"{(sum(ss) / len(ss)) if ss else 0:7.1f}  {dict(prov[k].most_common(3))}")
