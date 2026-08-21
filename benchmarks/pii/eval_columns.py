#!/usr/bin/env python3
"""Score classify_columns against corpus ground truth."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from detect import CORPUS, NON_PII, build_engine, load_table
from columns import classify_columns

engine = build_engine(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] != "none" else None
summary = {}
for path in sorted(CORPUS.iterdir()):
    if path.suffix not in {".csv", ".xlsx"}:
        continue
    gold = json.loads((CORPUS / f"{path.stem}.columns.json").read_text())
    frame = next(iter(load_table(path).values()))
    t0 = time.monotonic()
    pred = classify_columns(frame, engine)
    secs = round(time.monotonic() - t0, 2)
    tp = fp = fn = 0; missed = []; extra = []; right_class = 0; pii_total = 0
    for col, truth in gold.items():
        truth_set = set(truth) if isinstance(truth, list) else {truth}
        g = bool(truth_set - NON_PII)
        p = pred.get(col, {}).get("class", "none") not in NON_PII
        if g: pii_total += 1
        if g and p:
            tp += 1
            if pred[col]["class"] in truth_set: right_class += 1
        elif g: fn += 1; missed.append(f"{col}({truth})")
        elif p: fp += 1; extra.append(f"{col}->{pred[col]['class']}/{pred[col]['rule']}")
    summary[path.name] = {"pii_cols": pii_total, "recall": round(tp / pii_total, 3), "fp_cols": fp, "class_exact": f"{right_class}/{tp}", "missed": missed, "extra": extra, "seconds": secs}
    print(json.dumps({path.name: summary[path.name]}))
out = Path("benchmarks/runs/2026-08-21-pii-detection/columns-" + (sys.argv[1].replace("/", "_").replace(":", "-") if len(sys.argv) > 1 else "none") + ".json")
out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(summary, indent=2))
