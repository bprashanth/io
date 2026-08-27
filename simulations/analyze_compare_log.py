#!/usr/bin/env python3
"""Turn compare-log.jsonl files into the per-task preference table.

Usage: python3 analyze_compare_log.py <log.jsonl> [more logs...]
Needs the OpenRouter key at ~/.config/idlisseus/openrouter.json (one cheap call per
turn to classify the question; answers/questions in the log are already tokenised).
"""
import json, sys, urllib.request
from collections import defaultdict
from pathlib import Path

TASKS = ["simple lookup", "data interpretation", "numeric aggregation", "explanation", "rewriting", "dashboard or page"]

def classify(q):
    key = json.load(open(Path.home() / ".config/idlisseus/openrouter.json"))["api_key"]
    body = {"model": "google/gemini-3.7-flash",
            "messages": [{"role": "user", "content":
                "Classify this question into exactly one of: " + ", ".join(TASKS) +
                ". Reply with the category only.\n\nQuestion: " + q}],
            "temperature": 0, "max_tokens": 400, "reasoning": {"effort": "low"}}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    msg = json.load(urllib.request.urlopen(req, timeout=60))["choices"][0]["message"]
    out = (msg.get("content") or msg.get("reasoning") or "").strip().lower()
    return next((t for t in TASKS if t in out), "other")

def main():
    rows = []
    for f in sys.argv[1:]:
        rows += [json.loads(l) for l in open(f) if l.strip()]
    if not rows:
        print("no rows; pass one or more compare-log.jsonl files"); return
    grid = defaultdict(lambda: defaultdict(int))
    for r in rows:
        task = classify(r.get("q_sent", ""))
        grid[task][r.get("outcome", "none")] += 1
    outs = ["9b", "27b", "frontier", "tie", "none"]
    print(f"{'task':<22}" + "".join(f"{o:>10}" for o in outs) + f"{'total':>8}")
    for task, counts in grid.items():
        n = sum(counts.values())
        print(f"{task:<22}" + "".join(f"{counts.get(o, 0):>10}" for o in outs) + f"{n:>8}")

if __name__ == "__main__":
    main()
