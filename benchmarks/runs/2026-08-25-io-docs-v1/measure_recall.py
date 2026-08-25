#!/usr/bin/env python3
"""Mention-level recall of the io doc scanner against planted PII in
benchmarks/t0/text-fixtures/gold.json: every occurrence of every planted value
must fall inside a highlighted span (that is the redaction guarantee)."""
import json, re, urllib.request

def api(p, b=None):
    req = urllib.request.Request("http://127.0.0.1:8801" + p, data=json.dumps(b).encode() if b else None, headers={"Content-Type": "application/json"}, method="POST" if b else "GET")
    return json.load(urllib.request.urlopen(req, timeout=900))

api("/api/folder", {"path": "/home/beeps/src/github.com/bprashanth/io/benchmarks/t0/text-fixtures"})
rev = api("/api/review")
gold = json.load(open("benchmarks/t0/text-fixtures/gold.json"))
docs = {f["name"]: f for f in rev["files"] if f.get("kind") == "doc"}
print(f"{'file':<26} {'class':<10} mentions covered  missed(value@pos)")
TP = TM = 0
for fname, classes in gold.items():
    if fname.startswith("_") or fname.startswith("mixed/"):
        continue
    stem = fname.rsplit(".", 1)[0]
    d = next((v for k, v in docs.items() if k.startswith(stem)), None)
    if not d:
        print(fname, "NOT LOADED"); continue
    text = d["text"]; low = text.casefold()
    spans = [(sp["s"], sp["e"]) for sp in d["spans"]]
    for cls, vals in classes.items():
        if cls.startswith("_"):
            continue
        vals = list(vals.keys()) if isinstance(vals, dict) else vals
        mention = cover = 0; missed = []
        for v in vals:
            vl = str(v).casefold()
            for m in re.finditer(re.escape(vl), low):
                mention += 1
                if any(s <= m.start() and m.end() <= e for s, e in spans):
                    cover += 1
                else:
                    missed.append(f"{v}@{m.start()}")
        if mention:
            TM += mention; TP += cover
            print(f"{fname[:25]:<26} {cls:<10} {mention:>8} {cover:>7}  {missed[:3]}")
print(f"overall mentions covered: {TP}/{TM} ({100.0*TP/max(TM,1):.1f}%)")
