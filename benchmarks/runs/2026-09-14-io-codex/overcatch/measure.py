#!/usr/bin/env python3
"""Mention-level recall AND over-marking of the doc scanner against the planted-PII fixtures
(benchmarks/t0/text-fixtures/gold.json), through a running service on the given port.
Prints per file: mentions covered, total spans, spans that touch no planted value (over-marks)."""
import json, re, sys, urllib.request
PORT = int(sys.argv[1]); LABEL = sys.argv[2] if len(sys.argv) > 2 else "run"
ROOT = "/home/beeps/src/github.com/bprashanth/io"
def api(p, b=None):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}" + p, data=json.dumps(b).encode() if b else None, headers={"Content-Type": "application/json"}, method="POST" if b else "GET")
    return json.load(urllib.request.urlopen(req, timeout=1800))
api("/api/folder", {"path": f"{ROOT}/benchmarks/t0/text-fixtures"})
rev = api("/api/review")
gold = json.load(open(f"{ROOT}/benchmarks/t0/text-fixtures/gold.json"))
docs = {f["name"]: f for f in rev["files"] if f.get("kind") == "doc"}
rows = []; TP = TM = TS = TO = 0
for fname, classes in gold.items():
    if fname.startswith("_") or fname.startswith("mixed/"): continue
    stem = fname.rsplit(".", 1)[0]
    d = next((v for k, v in docs.items() if k.startswith(stem)), None)
    if not d: rows.append({"file": fname, "error": "not loaded"}); continue
    text = d["text"]; low = text.casefold()
    spans = [(sp["s"], sp["e"], sp["text"], sp.get("label")) for sp in d["spans"]]
    planted = []
    for cls, vals in classes.items():
        if cls.startswith("_"): continue
        vals = list(vals.keys()) if isinstance(vals, dict) else vals
        for v in vals:
            for m in re.finditer(re.escape(str(v).casefold()), low): planted.append((m.start(), m.end()))
    covered = sum(1 for s, e in planted if any(a <= s and e <= b for a, b, _, _ in spans))
    over = [(t, lab) for a, b, t, lab in spans if not any(s < b and a < e for s, e in planted)]
    bylab = {}
    for _t, lab in over: bylab[lab] = bylab.get(lab, 0) + 1
    rows.append({"file": fname, "mentions": len(planted), "covered": covered, "spans": len(spans), "overmarks": len(over), "by_label": bylab, "examples": sorted({t for t, _ in over})[:8]})
    TM += len(planted); TP += covered; TS += len(spans); TO += len(over)
out = {"label": LABEL, "files": rows, "mentions": TM, "covered": TP, "spans": TS, "overmarks": TO}
json.dump(out, open(f"{LABEL}.json", "w"), indent=1)
for r in rows: print(f"{r.get('file','?')[:26]:<27} covered {r.get('covered')}/{r.get('mentions')}  spans {r.get('spans')}  overmarks {r.get('overmarks')} {r.get('by_label')}")
print(f"TOTAL covered {TP}/{TM}  spans {TS}  overmarks {TO}")
