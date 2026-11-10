"""E2: teaching from today's fake copy (fake, fake2), the fixed fake copy (fixed, fixed2) and the real synthetic file
(real, real2), all judged on the real file.  python3 harness/e2_table.py
Only files taught in every mode being compared count in its totals (so a missing run doesn't skew the comparison)."""
import glob
import json
import os

E = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODES = ["fake", "fake2", "fixed", "fixed2", "real", "real2"]
# Owner's decisions (2026-11-10): values Idli reads correctly anyway ("Rs. 1,200", "approx 12", casing, "n/a", a
# second date format) are not misses; info blocks above a table aren't readable yet (new engine work). Both are
# reported in their own rows and left out of the main recall.
READ_OK = {"unit_in_cell", "na_text", "casing", "mixed_date_format"}
NOT_READABLE = {"info_block"}


def split(r):
    """(found, n) for the main recall, read-correctly kinds, and not-readable kinds."""
    out = {"main": [0, 0], "read_ok": [0, 0], "not_readable": [0, 0]}
    for k, v in r.get("per_kind", {}).items():
        if v["expect"] != "flag":
            continue
        g = "read_ok" if k in READ_OK else "not_readable" if k in NOT_READABLE else "main"
        above = min(v.get("above_header") or 0, v["n"])  # mistakes inside an info block above the table
        if above and g == "main":
            # Idli reads one table per tab, so these can't be checked yet: count them apart (owner's decision 3)
            in_table = v["n"] - above
            found_in_table = min(v["found"], in_table)
            out["not_readable"][0] += v["found"] - found_in_table
            out["not_readable"][1] += above
            out["main"][0] += found_in_table
            out["main"][1] += in_table
            continue
        out[g][0] += v["found"]
        out[g][1] += v["n"]
    return out
S = {}
for m in MODES:
    for p in glob.glob(f"{E}/results/e6/{m}/*.score.json"):
        r = json.load(open(p))
        t = r.get("teach", {})
        # a run only counts if teaching finished and the scripted owner answered (the usage limit broke some runs)
        if not r.get("error") and t.get("done") and (t.get("user_cost") or 0) > 0:
            S[(m, r["fixture"].replace(".xlsx", ""))] = r
files = sorted({f for _, f in S})
print("Main recall excludes read-correctly kinds and info blocks (owner's decisions); see the totals below.")
print(f"{'file':30} " + " ".join(f"{m:>12}" for m in MODES))
for f in files:
    cells = []
    for m in MODES:
        r = S.get((m, f))
        cells.append(f"{split(r)['main'][0]:2}/{split(r)['main'][1]:2} fa{r['false_alarm_cells']:<3}" if r else f"{'-':>12}")
    print(f"{f:30} " + " ".join(f"{c:>12}" for c in cells))
print()
for m in MODES:
    have = [f for f in files if (m, f) in S]
    if not have:
        continue
    g = {k: [sum(split(S[(m, f)])[k][i] for f in have) for i in (0, 1)] for k in ("main", "read_ok", "not_readable")}
    fa = sum(S[(m, f)]["false_alarm_cells"] for f in have)
    rows = sum(S[(m, f)]["data_rows"] for f in have)
    pct = lambda a: f"{a[0]}/{a[1]} ({100 * a[0] / a[1]:.0f}%)" if a[1] else "-"
    print(f"{m:7} files {len(have)}  mistakes found {pct(g['main'])}  | read correctly anyway (flag optional) "
          f"{pct(g['read_ok'])}  | not readable yet (info blocks) {pct(g['not_readable'])}  | false alarms {fa} in {rows} rows")
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
