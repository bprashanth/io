#!/usr/bin/env python3
"""Does Idli's Drive search need a vector index, summaries or keywords? Scores ways of searching the real index.

Runs on the laptop, read-only on ~/idli-insights/config/drive-index.duckdb (built by Idli). Methods:
  names       lexical match on file names only
  peek        names + folders + first rows / opening lines
  summary     + Muse's one-line summaries (what drive_find does today)
  vector      a small local embedding model (fastembed BAAI/bge-small-en-v1.5) over the same text
  hybrid      summary score + vector score
Prints hit@1 / hit@3 and time per search, per question kind (named vs described), and writes search_eval.json.

  .venv/bin/python -I ../../2026-11-08-oobe/search_eval.py      (from the cowork folder on the laptop)
"""
import json
import os
import sys
import time

COWORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "2026-11-06-oss-desktop-independent", "cowork")
sys.path.insert(0, os.path.abspath(COWORK))
from lib import driveindex as di  # noqa: E402

# (question, a substring of the right file's name, kind) - kind: named (says part of the name) or described
QUESTIONS = [
    ("volunteer register", "volunteer_register", "named"),
    ("tech reimbursement form", "tech_reimbursement_form", "named"),
    ("the households sheet", "households", "named"),
    ("funder report q1", "funder_report_Q1", "named"),
    ("80g receipts", "80g_receipts", "named"),
    ("field vars indicators", "field_vars_indicators", "named"),
    ("milestones", "milestones", "named"),
    ("election data", "Election Data", "named"),
    ("wildfires doc", "Wildfires", "named"),
    ("lidar notes", "Lidar", "named"),
    ("oakes street", "Oakes street", "named"),
    ("econometrics summary slides", "Introduction to econometrics", "named"),
    ("donation receipts for tax exemption", "80g_receipts", "described"),
    ("which sheet has price to book ratios of banks", "p/bv ratio", "described"),
    ("the restaurant food menu", "Food Menu", "described"),
    ("class schedule for the winter term", "Winter 2023", "described"),
    ("hindi language lessons", "Linguaero Hindi", "described"),
    ("the book about dog health", "The Dog Its Behavior", "described"),
    ("tree species and trunk diameter measurements by plot", "field_vars_indicators", "described"),
    ("staff expense claims for laptops and data packs", "tech_reimbursement_form", "described"),
    ("household debt and savings by ward", "households", "described"),
    ("money we gave out to people", "disbursements", "described"),
    ("log of field visits to villages", "visits", "described"),
    ("paper on power and coalitions inside companies", "Coalitional Nature of the Firm", "described"),
    ("article on influencers versus online ads", "influencer marketing", "described"),
]


def rows():
    return di._read("SELECT id, name, kind, path, coalesce(peek, ''), coalesce(summary, '') FROM files")


def lexical(q, docs):
    qt = [t for t in di._tokens(q) if t not in di.STOP and t not in di.KIND_WORDS and len(t) > 1]
    out = []
    for d in docs:
        toks = di._tokens(d["text"])
        s = sum(di._match(t, toks) for t in qt) / max(1, len(qt))
        out.append(s)
    return out


def main():
    data = rows()
    import numpy as np
    variants = {
        "names": [{"name": r[1], "text": r[1]} for r in data],
        "peek": [{"name": r[1], "text": f"{r[1]} {r[3]} {r[4]}"} for r in data],
        "summary": [{"name": r[1], "text": f"{r[1]} {r[3]} {r[4]} {r[5]}"} for r in data],
    }
    t0 = time.time()
    from fastembed import TextEmbedding
    model = TextEmbedding("BAAI/bge-small-en-v1.5")
    texts = [f"{r[1]}. {r[2]}. {r[3]}. {r[5]} {r[4][:300]}" for r in data]
    emb = np.array(list(model.embed(texts)))
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    build_s = time.time() - t0
    names = [r[1] for r in data]
    results = {m: [] for m in ("names", "peek", "summary", "vector", "hybrid")}
    timing = {m: [] for m in results}
    for q, want, kind in QUESTIONS:
        scores = {}
        for m in ("names", "peek", "summary"):
            t = time.time()
            scores[m] = np.array(lexical(q, variants[m]))
            timing[m].append(time.time() - t)
        t = time.time()
        qv = np.array(list(model.query_embed(q)))[0]
        qv /= np.linalg.norm(qv)
        scores["vector"] = emb @ qv
        timing["vector"].append(time.time() - t)
        scores["hybrid"] = scores["summary"] + 0.8 * scores["vector"]
        timing["hybrid"].append(timing["summary"][-1] + timing["vector"][-1])
        for m, sc in scores.items():
            order = list(np.argsort(-sc))
            top = [names[i] for i in order[:3]]
            rank = next((k for k, i in enumerate(order) if want.lower() in names[i].lower()), None)
            results[m].append({"q": q, "kind": kind, "rank": rank, "top3": top})
    summary = {}
    for m, rs in results.items():
        row = {}
        for kind in ("named", "described", "all"):
            sel = [r for r in rs if kind == "all" or r["kind"] == kind]
            row[kind] = {"hit@1": sum(r["rank"] == 0 for r in sel), "hit@3": sum(r["rank"] is not None and r["rank"] < 3 for r in sel), "n": len(sel)}
        row["ms_per_search"] = round(1000 * sum(timing[m]) / len(timing[m]), 1)
        summary[m] = row
    print(f"files in index: {len(data)}; embedding the index took {build_s:.1f}s")
    print(f"{'method':8s} {'named @1/@3':>12s} {'described @1/@3':>16s} {'all @1/@3':>10s} {'ms':>7s}")
    for m, row in summary.items():
        f = lambda k: f"{row[k]['hit@1']}/{row[k]['hit@3']} of {row[k]['n']}"
        print(f"{m:8s} {f('named'):>12s} {f('described'):>16s} {f('all'):>10s} {row['ms_per_search']:7.1f}")
    for m in ("summary", "vector", "hybrid"):
        misses = [r for r in results[m] if r["rank"] != 0]
        print(f"\n{m} misses:")
        for r in misses:
            print(f"  {r['q']!r} -> rank {r['rank']}, top: {r['top3'][:2]}")
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "search_eval.json"), "w") as fh:
        json.dump({"summary": summary, "results": results, "embed_build_s": build_s}, fh, indent=1)


if __name__ == "__main__":
    main()
