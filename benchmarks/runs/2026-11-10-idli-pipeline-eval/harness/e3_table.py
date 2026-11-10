"""Summarize E3 bounce runs per model."""
import argparse
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL = os.path.dirname(HERE)
RESULTS = os.path.join(EVAL, "results")


def load_logs(root):
    out = []
    for dirpath, _, files in os.walk(root):
        if "e3-logs" in dirpath:
            continue
        for name in files:
            if not name.endswith(".json"):
                continue
            path = os.path.join(dirpath, name)
            try:
                log = json.load(open(path))
            except Exception:
                continue
            if "turns" in log and "model" in log:
                out.append(log)
    return out


def table(rows):
    agg = defaultdict(lambda: defaultdict(float))
    counts = defaultdict(int)
    for r in rows:
        model = r["model"]
        counts[model] += 1
        e3 = r.get("e3") or {}
        for k in ("routed_right", "sent", "claude_done", "came_back", "answered_right_after", "wrong_bounces",
                  "never_returned"):
            agg[model][k] += 1 if e3.get(k) else 0
        agg[model]["minutes"] += float(e3.get("minutes") or 0)
        agg[model]["cost"] += float(e3.get("cost") or 0)

    header = (
        f"{'model':24} {'chats':>5} {'routed':>7} {'sent':>5} {'done':>5} {'back':>5} "
        f"{'right':>5} {'wrong':>5} {'min/bounce':>10} {'$/bounce':>9}"
    )
    print(header)
    for model in sorted(counts):
        n = counts[model]
        sent = agg[model]["sent"] or 0
        min_per = agg[model]["minutes"] / sent if sent else 0.0
        cost_per = agg[model]["cost"] / sent if sent else 0.0
        print(
            f"{model:24} {n:5d} {int(agg[model]['routed_right']):7d} {int(agg[model]['sent']):5d} "
            f"{int(agg[model]['claude_done']):5d} {int(agg[model]['came_back']):5d} "
            f"{int(agg[model]['answered_right_after']):5d} {int(agg[model]['wrong_bounces']):5d} "
            f"{min_per:10.2f} {cost_per:9.4f}"
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", nargs="?", default=os.path.join(RESULTS, "e3"))
    a = ap.parse_args()
    rows = load_logs(a.run_dir)
    table(rows)


if __name__ == "__main__":
    main()
