"""E2: teaching from today's fake copy (fake, fake2), the fixed fake copy (fixed, fixed2) and the real synthetic file
(real, real2), all judged on the real file.  python3 harness/e2_table.py
Only files taught in every mode being compared count in its totals (so a missing run doesn't skew the comparison)."""
import glob
import json
import os

E = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODES = ["fake", "fake2", "fixed", "fixed2", "real", "real2"]
S = {}
for m in MODES:
    for p in glob.glob(f"{E}/results/e6/{m}/*.score.json"):
        r = json.load(open(p))
        t = r.get("teach", {})
        # a run only counts if teaching finished and the scripted owner answered (the usage limit broke some runs)
        if not r.get("error") and t.get("done") and (t.get("user_cost") or 0) > 0:
            S[(m, r["fixture"].replace(".xlsx", ""))] = r
files = sorted({f for _, f in S})
print(f"{'file':30} " + " ".join(f"{m:>12}" for m in MODES))
for f in files:
    cells = []
    for m in MODES:
        r = S.get((m, f))
        cells.append(f"{r['flag_found']:2}/{r['flag_items']:2} fa{r['false_alarm_cells']:<3}" if r else f"{'-':>12}")
    print(f"{f:30} " + " ".join(f"{c:>12}" for c in cells))
print()
for m in MODES:
    have = [f for f in files if (m, f) in S]
    if not have:
        continue
    found = sum(S[(m, f)]["flag_found"] for f in have)
    n = sum(S[(m, f)]["flag_items"] for f in have)
    fa = sum(S[(m, f)]["false_alarm_cells"] for f in have)
    rows = sum(S[(m, f)]["data_rows"] for f in have)
    doc = sum(S[(m, f)]["flag_found_in_doc"] for f in have), sum(S[(m, f)]["flag_in_doc"] for f in have)
    print(f"{m:7} files {len(have)}  found {found}/{n} ({100*found/n:.0f}%)  in notes {doc[0]}/{doc[1]}  "
          f"not in notes {found-doc[0]}/{n-doc[1]}  false alarms {fa} in {rows} rows")
# per kind, pooled per mode family
fam = {"today": ["fake", "fake2"], "fixed": ["fixed", "fixed2"], "real": ["real", "real2"]}
kinds = {}
for name, ms in fam.items():
    for m in ms:
        for f in files:
            r = S.get((m, f))
            for k, v in (r or {}).get("per_kind", {}).items():
                if v["expect"] != "flag":
                    continue
                a = kinds.setdefault(k, {}).setdefault(name, [0, 0])
                a[0] += v["found"]
                a[1] += v["n"]
print()
print(f"{'kind':22} " + " ".join(f"{n:>10}" for n in fam))
for k in sorted(kinds):
    print(f"{k:22} " + " ".join(f"{kinds[k][n][0]:>4}/{kinds[k][n][1]:<4} " if n in kinds[k] else f"{'-':>10}" for n in fam))
