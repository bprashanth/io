#!/usr/bin/env python3
"""Astronaut eval: bare kernel -> interaction log -> COMPACT (t1 / t2) -> apply cards -> rerun.

Steps (each is a subcommand so runs can be resumed):
  bare     run the 22 corpus asks on a service started with IO_DISABLE_BUILTIN=1 (logs accumulate per folder)
  compact  for each org folder, call /api/astronaut/compact with tier t1 and t2; save cards under skills/<tier>/<org>/
  apply    copy a tier's cards (non-leaking) into <org>/.io/skills, rerun the 22 asks, remove them; record accuracy
  misfire  for each tier, apply EVERY org's cards to EVERY org and count skills firing on tables they were not proposed for
"""
import json, shutil, subprocess, sys, time, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "benchmarks/t0/ngo-corpus"
OUT = ROOT / "benchmarks/astronaut"
SERVICE = "http://127.0.0.1:8791"
sys.path.insert(0, str(ROOT / "benchmarks/t0"))


def api(path, body=None, timeout=900):
    req = urllib.request.Request(SERVICE + path, data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json"}, method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def orgs():
    return sorted(p.name for p in CORPUS.iterdir() if p.is_dir())


def run_cases(label):
    out = OUT / "runs" / label
    subprocess.run([str(ROOT / ".venv-v2/bin/python"), str(ROOT / "benchmarks/t0/run_corpus_cases.py"), "--output", str(out), "--label", label, "--lanes", "ask"], check=False)
    return json.loads((out / "results.json").read_text())["summary"]


def cmd_bare():
    print(run_cases("bare-kernel-9b"))


def cmd_compact(tiers=("t1", "t2"), rnd=""):
    for tier in tiers:
        for org in orgs():
            api("/api/folder", {"path": str(CORPUS / org)})
            t0 = time.time()
            try:
                r = api("/api/astronaut/compact", {"tier": tier})
            except Exception as exc:
                r = {"error": str(exc)[:300]}
            d = OUT / ("skills" + rnd) / tier / org
            d.mkdir(parents=True, exist_ok=True)
            (d / "_compact.json").write_text(json.dumps(r, indent=1, ensure_ascii=False))
            for c in r.get("cards", []):
                (d / f"{c['name']}.json").write_text(json.dumps({k: v for k, v in c.items() if k not in ("fires_on",)}, indent=1, ensure_ascii=False))
            print(tier, org, "cards", len(r.get("cards", [])), "leaks", sum(1 for c in r.get("cards", []) if c.get("leaks")), f"{round(time.time() - t0)}s", r.get("error", ""), flush=True)


def cmd_apply(tier, rounds=("",)):
    for org in orgs():
        dst = CORPUS / org / ".io" / "skills"
        dst.mkdir(parents=True, exist_ok=True)
        for rnd in rounds:
            d = OUT / ("skills" + rnd) / tier / org
            for p in d.glob("*.json"):
                if p.name.startswith("_"):
                    continue
                c = json.loads(p.read_text())
                if c.get("leaks"):
                    continue
                shutil.copy(p, dst / p.name)
    try:
        print(run_cases(f"compacted-{tier}-9b{'-'.join(rounds)}"))
    finally:
        for org in orgs():
            shutil.rmtree(CORPUS / org / ".io", ignore_errors=True)


def cmd_misfire(tier):
    rows = []
    for src in orgs():
        d = OUT / "skills" / tier / src
        cards = [json.loads(p.read_text()) for p in d.glob("*.json") if not p.name.startswith("_")]
        for dst in orgs():
            st = api("/api/folder", {"path": str(CORPUS / dst)})
            for c in cards:
                if c["kind"] not in ("hint", "mapping"):
                    continue
                pv = api("/api/skills/preview", {"skill": c})
                if pv["fires_on"]:
                    rows.append({"tier": tier, "from": src, "on": dst, "skill": c["name"], "tables": pv["fires_on"], "intended": src == dst})
    (OUT / f"misfire-{tier}.json").write_text(json.dumps(rows, indent=1))
    mis = [r for r in rows if not r["intended"]]
    print(tier, "firings", len(rows), "cross-org firings", len(mis), sorted({(r["skill"], r["on"]) for r in mis})[:20])


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "bare":
        cmd_bare()
    if c == "compact":
        cmd_compact(tuple(sys.argv[2].split(",")) if len(sys.argv) > 2 else ("t1", "t2"), sys.argv[3] if len(sys.argv) > 3 else "")
    if c == "apply":
        cmd_apply(sys.argv[2], tuple(sys.argv[3].split(",")) if len(sys.argv) > 3 else ("",))
    if c == "misfire":
        cmd_misfire(sys.argv[2])
