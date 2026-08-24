#!/usr/bin/env python3
"""Recall of the io doc scanner against planted PII in benchmarks/t0/text-fixtures/gold.json."""
import json, urllib.request
def api(p, b=None):
    req = urllib.request.Request("http://127.0.0.1:8801" + p, data=json.dumps(b).encode() if b else None, headers={"Content-Type": "application/json"}, method="POST" if b else "GET")
    return json.load(urllib.request.urlopen(req, timeout=900))
api("/api/folder", {"path": "/home/beeps/src/github.com/bprashanth/io/benchmarks/t0/text-fixtures"})
rev = api("/api/review")
gold = json.load(open("benchmarks/t0/text-fixtures/gold.json"))
docs = {f["name"]: f for f in rev["files"] if f.get("kind") == "doc"}
print(f"{'file':<28} {'class':<14} planted found missed")
total_p = total_f = 0
for fname, classes in gold.items():
    stem = fname.rsplit(".", 1)[0]
    d = next((v for k, v in docs.items() if k.startswith(stem)), None)
    if not d:
        print(fname, "NOT LOADED"); continue
    covered = set()
    for sp in d["spans"]:
        covered.add(sp["text"].strip().casefold())
    text_l = d["text"].casefold()
    for cls, vals in classes.items():
        if not isinstance(vals, list):
            continue
        planted = [v for v in vals if str(v).casefold() in text_l]
        found = [v for v in planted if any(str(v).casefold() in c or c in str(v).casefold() for c in covered)]
        missed = [v for v in planted if v not in found]
        total_p += len(planted); total_f += len(found)
        print(f"{fname[:27]:<28} {cls:<14} {len(planted):>7} {len(found):>5} {missed[:3]}")
print(f"overall: {total_f}/{total_p}")
