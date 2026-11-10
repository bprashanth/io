"""Segment: the Drive index's one-line summaries (lib/driveindex.py summarise(), Muse today).

Each model writes the summaries for the fake Drive with the exact production prompt (batches of 6). They are
scored by what they are for: does drive_find put the right file first for questions in everyday words that
are not in the file names ("money given out", "job work", "animals hit by vehicles")? Plus: valid JSON, every
file covered, and seconds per batch. Search uses the real index code; only the summary column changes.

  python harness/summaries.py --models muse30b,or-qwen35-9b,... --out results/summaries.json
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import convo  # noqa: E402

QUERIES = [  # (words a person might use, the file that should come first)
    ("money given out to villages", "Field programme tracker Q3.xlsx"),
    ("job work in the villages", "MGNREGA works Valparai 2019-2023.xlsx"),
    ("employment guarantee scheme data", "MGNREGA works Valparai 2019-2023.xlsx"),
    ("animals hit by vehicles", "Road kill survey 2011-12.xlsx"),
    ("frogs and snakes dead on the road", "Road kill survey 2011-12.xlsx"),
    ("invasive trees in the forest patches", "Fragment tree plots 2000-2019.xlsx"),
    ("people moving away for jobs", "Out-migration records.xlsx"),
    ("tea garden workers count", "Estate labour census.xlsx"),
    ("how much the plantation pays per day", "Wage register monthly.xlsx"),
    ("staff phone and laptop claims", "Tech reimbursement form (Responses).xlsx"),
    ("family income and loans survey", "Household survey 2025.xlsx"),
    ("who helps us for free", "Volunteer register 2025.xlsx"),
    ("spending against plan", "Budget 2025-26.xlsx"),
    ("water tank repair proposal for donors", "Donor proposal - water bodies.docx"),
    ("how the roadkill counts were done", "Road kill survey - methods.pdf"),
]


def summarise(spec, batch):
    items = [{"n": i + 1, "name": f["name"], "kind": f["kind"], "folder": f["path"], "inside": (f.get("peek") or "")[:400]}
             for i, f in enumerate(batch)]
    prompt = ("For each file, write one short line: what it is and the key words someone might search for "
              "(people, places, projects, topics, years), plus the everyday words a non-expert would use for it "
              "(e.g. disbursements -> money given out, payments; 80G receipts -> donation tax receipts). Use only "
              "what is shown. Reply with JSON only: "
              '{"1": "...", "2": "..."}\n\n' + json.dumps(items, ensure_ascii=False))
    import re
    import urllib.request
    body = {"model": spec["model"], "temperature": 0, "max_tokens": 4000, "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}]}
    body.update({k: v for k, v in (spec.get("extra") or {}).items()})
    req = urllib.request.Request(spec["base"].rstrip("/") + "/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": "Bearer " + convo.api_key(spec)})
    with urllib.request.urlopen(req, timeout=300) as r:
        text = json.load(r)["choices"][0]["message"]["content"] or ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    m = re.search(r"\{.*\}", text, re.S)
    try:
        got = json.loads(m.group(0)) if m else {}
        ok = bool(m)
    except ValueError:
        got, ok = {}, False
    return {batch[int(k) - 1]["id"]: str(v)[:300] for k, v in got.items()
            if str(k).isdigit() and 0 < int(k) <= len(batch)}, ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import duckdb
    models = convo.load_models()
    with open(os.path.join(BENCH, "fixtures", "drive.json")) as f:
        files = json.load(f)["files"]
    for f in files:
        f["path"] = " / ".join(["My Drive"] + f["folder"].split("/"))
    out = {}
    for mid in a.models.split(","):
        spec = models.get(mid)
        t0, sums, json_ok, secs = time.time(), {}, 0, [0]
        batches = [files[i:i + 6] for i in range(0, len(files), 6)] if spec else []  # "none": names and peeks only
        for b in batches:
            t1 = time.time()
            try:
                got, ok = summarise(spec, b)
            except Exception as e:
                got, ok = {}, False
                print(mid, "error", str(e)[:200])
            secs.append(round(time.time() - t1, 1))
            json_ok += ok
            sums.update(got)
        home = tempfile.mkdtemp(prefix="idli9b-sum-")
        db = os.path.join(home, "idx.duckdb")
        shutil.copy(os.path.join(BENCH, "fixtures", "drive-index.duckdb"), db)
        con = duckdb.connect(db)
        con.execute("UPDATE files SET summary = NULL")
        for fid, s in sums.items():
            con.execute("UPDATE files SET summary = ? WHERE id = ?", [s, fid])
        con.close()
        os.environ["IDLI_DRIVE_INDEX"] = db
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(BENCH)), "runs",
                                        "2026-11-06-oss-desktop-independent", "cowork"))
        from lib import driveindex as di
        di.DB = db
        hits, top3 = 0, 0
        detail = []
        for q, want in QUERIES:
            r = di.search(q)
            names = [x["name"] for x in r["results"]]
            hits += bool(names) and names[0] == want
            top3 += want in names[:3]
            detail.append({"q": q, "want": want, "got": names[:3], "status": r["status"]})
        out[mid] = {"json_ok": f"{json_ok}/{len(batches)}", "covered": f"{len(sums)}/{len(files)}",
                    "top1": f"{hits}/{len(QUERIES)}", "top3": f"{top3}/{len(QUERIES)}",
                    "secs_per_batch": round(sum(secs) / len(secs), 1), "summaries": sums, "queries": detail}
        print(f"{mid:22} json {json_ok}/{len(batches)} covered {len(sums)}/{len(files)} top1 {hits}/{len(QUERIES)} "
              f"top3 {top3}/{len(QUERIES)} {out[mid]['secs_per_batch']}s/batch", flush=True)
    # names only (no summaries) as the floor
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
