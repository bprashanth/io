#!/usr/bin/env python3
"""Scorecard from the results-*.json files: per model and prompt, first try / with one retry, per question set."""
import glob
import json
import os
import re
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
SETS = ["questions", "holdout", "codex", "cursor"]
rows = {}
for p in glob.glob(os.path.join(HERE, "results-*.json")):
    m = re.match(r"results-(questions|holdout|codex|cursor)-([a-z0-9]+)(?:-(v[12]))?(?:-(r\d))?\.json$", os.path.basename(p))
    if not m:
        continue
    qset, model, prompt, rep = m.group(1), m.group(2), m.group(3) or "v1", m.group(4) or "r0"
    if model == "keywords":
        prompt = "-"
    rs = json.load(open(p))
    rows.setdefault((model, prompt), {}).setdefault(qset, {})[rep] = (sum(r.get("first_try_ok", r["ok"]) for r in rs),
                                                                      sum(r["ok"] for r in rs), len(rs),
                                                                      statistics.mean(r["secs"] for r in rs))
print("| Model | Dates | " + " | ".join(f"{s}" for s in SETS) + " | All (first try / one retry) | s/question | runs |")
print("|---|---|" + "---|" * len(SETS) + "---|---|---|")
for (model, prompt), by in sorted(rows.items()):
    if not all(s in by for s in SETS):
        continue
    reps = sorted(set.intersection(*[set(by[s]) for s in SETS]))
    tot1 = [sum(by[s][r][0] for s in SETS) for r in reps]
    tot2 = [sum(by[s][r][1] for s in SETS) for r in reps]
    n = sum(by[s][reps[0]][2] for s in SETS)
    cells = []
    for s in SETS:
        cells.append(f"{statistics.mean(by[s][r][1] for r in reps):.0f}/{by[s][reps[0]][2]}")
    secs = statistics.mean(by[s][r][3] for s in SETS for r in reps)
    print(f"| {model} | {prompt} | " + " | ".join(cells) +
          f" | {statistics.mean(tot1):.0f} / {statistics.mean(tot2):.0f} of {n} ({statistics.mean(tot2) / n:.0%}) | {secs:.1f} | {len(reps)} |")
