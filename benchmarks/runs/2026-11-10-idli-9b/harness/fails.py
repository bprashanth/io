"""List failing spans for a model (and variant) from scores.json.  python harness/fails.py <run dir> <model> [variant]"""
import json
import os
import sys

rows = json.load(open(os.path.join(sys.argv[1], "scores.json")))
for r in rows:
    if r["model"] != sys.argv[2] or (len(sys.argv) > 3 and r["variant"] != sys.argv[3]) or r["pass"]:
        continue
    bad = {k: v for k, v in r["checks"].items() if not v}
    print(f"{r['conv']} r{r['rep']} s{r['span']} [{r['segment']}] fail={list(bad)} dev={r['deviations']} "
          f"inv={r['invented'][:4]} api={r['api_error']}")
    print("    tools:", r["tools"][:10], "| text:", r["text"][:260].replace("\n", " / "))
