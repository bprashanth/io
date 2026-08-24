#!/usr/bin/env python3
"""Payload-size ROI on benchmarks/t0/bigfolder (120 files, 18.5MB): what should io send
for a question against a big folder?

Conditions:
  full150k  - today's io: every file, 150KB total cap, files truncated when over
  caps      - naive limits: first 5 files alphabetically, 1MB per file
  bm25      - BM25 over 1500-char chunks of every file, top chunks up to 60KB
  bm25man   - bm25 + a locally computed manifest (per-CSV rowcounts and numeric sums)

Redaction: synthetic corpus; names/phones/emails are swapped for stable tokens with the
regex engine plus the staff/donor name lists (selection strategy is the variable under
test, not the scanner). Grading: normalised containment of the gold in the answer.
"""
import json, math, re, sys, time, urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BIG = ROOT / "benchmarks" / "t0" / "bigfolder"
QS = json.loads((ROOT / "benchmarks" / "t0" / "bigfolder-questions.json").read_text())
sys.path.insert(0, str(ROOT / "benchmarks" / "pii"))
from detect import regex_engine  # noqa: E402
from pseudonymize import PseudonymMap, redact_question  # noqa: E402

import pandas as pd  # noqa: E402

pm = PseudonymMap(None)
names = set()
for f, nrows in (("staff_list.csv", None), ("donor_list.csv", 800)):
    p = BIG / f
    if p.exists():
        df = pd.read_csv(p, dtype=str, nrows=nrows)
        for c in df.columns:
            if "name" in c.lower():
                names |= set(df[c].dropna())
names = {n for n in names if len(n) > 3}
name_re = re.compile("|".join(re.escape(n) for n in sorted(names, key=len, reverse=True) if len(n) > 3)) if names else None

def redact_text(t: str) -> str:
    if name_re:
        t = name_re.sub(lambda m: pm.token(m.group(0), "person_name"), t)
    spans = sorted(regex_engine(t), key=lambda x: x[0])
    out, pos = [], 0
    for s, e, cls, _ in spans:
        if s < pos:
            continue
        out.append(t[pos:s]); out.append(pm.token(t[s:e], cls)); pos = e
    out.append(t[pos:])
    return "".join(out)

def load_all():
    out = {}
    for p in sorted(BIG.iterdir()):
        if p.suffix.lower() in (".csv", ".txt"):
            out[p.name] = redact_text(p.read_text(errors="ignore"))
        elif p.suffix.lower() == ".xlsx":
            try:
                out[p.name] = redact_text(pd.read_excel(p, dtype=str).to_csv(index=False))
            except Exception:
                pass
    return out

TOK = re.compile(r"[a-z0-9_]+")
def toks(t): return TOK.findall(t.lower())

def bm25_chunks(files, budget):
    chunks = []
    for name, text in files.items():
        lines, cur, size = text.splitlines(True), [], 0
        head = lines[0] if lines and "," in (lines[0] if lines else "") else ""
        for ln in lines:
            cur.append(ln); size += len(ln)
            if size > 1500:
                chunks.append((name, head + "".join(cur) if head and head not in cur[0] else "".join(cur))); cur, size = [], 0
        if cur: chunks.append((name, head + "".join(cur) if head else "".join(cur)))
    df_, tf = Counter(), []
    for _, c in chunks:
        ts = toks(c); tf.append(Counter(ts)); df_.update(set(ts))
    N, avg = len(chunks), sum(len(c) for _, c in chunks) / max(len(chunks), 1)
    def score(q):
        qt = toks(q); sc = []
        for i, (_, c) in enumerate(chunks):
            s = 0.0
            for t in qt:
                f = tf[i].get(t, 0)
                if f:
                    idf = math.log(1 + (N - df_[t] + .5) / (df_[t] + .5))
                    s += idf * f * 2.2 / (f + 1.2 * (1 - .75 + .75 * len(c) / avg))
            sc.append(s)
        order = sorted(range(N), key=lambda i: -sc[i])
        picked, size = [], 0
        for i in order:
            if sc[i] <= 0 or size > budget: break
            picked.append(i); size += len(chunks[i][1])
        return [(chunks[i][0], chunks[i][1]) for i in sorted(picked)]
    return score

def manifest(files):
    rows = []
    for name, text in files.items():
        if name.endswith(".csv"):
            try:
                df = pd.read_csv(BIG / name, dtype=str)
                sums = {}
                for c in df.columns:
                    v = pd.to_numeric(df[c], errors="coerce")
                    if v.notna().mean() > .8:
                        sums[c] = round(float(v.sum()), 2)
                rows.append(f"{name}: {len(df)} rows, cols {list(df.columns)}, sums {sums}")
            except Exception:
                rows.append(f"{name}: unreadable")
        else:
            rows.append(f"{name}: text, {len(text)} chars")
    return "FOLDER MANIFEST (computed locally, trustworthy):\n" + "\n".join(rows)

def call(payload_text, question):
    key = json.load(open(Path.home() / ".config/idlisseus/openrouter.json"))["api_key"]
    body = {"model": "google/gemini-3.7-flash",
            "messages": [{"role": "user", "content": payload_text + "\n\nQUESTION: " + question +
                          "\nAnswer concisely with the exact number/name. Values like NAME_001 are codes; use them as-is."}],
            "reasoning": {"effort": "low"}}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    t0 = time.time()
    r = json.load(urllib.request.urlopen(req, timeout=300))
    return r["choices"][0]["message"]["content"], time.time() - t0

def norm(x): return re.sub(r"[^a-z0-9.]+", "", str(x).lower())

def graded(ans, gold):
    ans_n = norm(ans)
    if isinstance(gold, list):
        return all(norm(g) in ans_n for g in gold)
    g = norm(gold)
    if g in ans_n: return True
    m = re.fullmatch(r"([0-9.]+)%?", g)
    if m:
        return re.sub(r"(\d),(\d)", r"\1\2", norm(ans)).find(m.group(1)) >= 0
    return False

def main():
    files = load_all()
    print(f"{len(files)} files, {sum(len(v) for v in files.values())//1024}KB redacted text", flush=True)
    score = bm25_chunks(files, 60_000)
    man = manifest(files)
    results = []
    for q in QS if isinstance(QS, list) else QS["questions"]:
        question = q["q"]; gold = q["gold"]
        red_q = redact_question(question, pm, regex_engine)["redacted"]
        conds = {}
        full, total = [], 0
        for name, text in files.items():
            t = text
            if total + len(t) > 150_000:
                t = t[:max(0, 150_000 - total)]
            if t: full.append(f"--- {name} ---\n{t}")
            total += len(t)
        conds["full150k"] = "\n".join(full)
        capped = [f"--- {n} ---\n{files[n][:1_000_000]}" for n in sorted(files)[:5]]
        conds["caps"] = "\n".join(capped)
        picked = score(red_q)
        conds["bm25"] = "\n".join(f"--- {n} (excerpt) ---\n{c}" for n, c in picked)
        conds["bm25man"] = man + "\n\n" + conds["bm25"]
        for cname, payload in conds.items():
            try:
                ans, secs = call(payload, red_q)
                ok = graded(pm.rehydrate(ans), gold)
            except Exception as exc:
                ans, secs, ok = f"ERROR {exc}", 0, False
            results.append({"q": question, "kind": q["kind"], "cond": cname, "ok": ok,
                            "bytes": len(payload), "secs": round(secs, 1), "gold": gold,
                            "answer": pm.rehydrate(ans)[:300]})
            print(f"{q['kind']:<9} {cname:<9} ok={ok} {len(payload)//1024}KB {round(secs,1)}s", flush=True)
    out = Path(__file__).parent / "results.json"
    out.write_text(json.dumps(results, indent=1))
    agg = defaultdict(lambda: [0, 0, 0])
    for r in results:
        a = agg[r["cond"]]; a[0] += r["ok"]; a[1] += 1; a[2] += r["bytes"]
    print("\ncond      correct  avgKB")
    for c, (ok, n, b) in agg.items():
        print(f"{c:<9} {ok}/{n}     {b//n//1024}")

if __name__ == "__main__":
    main()
