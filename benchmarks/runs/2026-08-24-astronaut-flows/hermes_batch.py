#!/usr/bin/env python3
"""Run corpus ask cases through Hermes (container io-hermes) with the 9B: config 'tools' (AGENTS.md + io.py) or 'free'."""
import json, os, re, shutil, subprocess, sys, time
from pathlib import Path
ROOT = Path("/home/beeps/src/github.com/bprashanth/io"); H = Path.home() / ".cache/io-hermes"
sys.path.insert(0, str(ROOT / "benchmarks/t0")); import run_corpus_cases as rc  # noqa
config, label = sys.argv[1], sys.argv[2]; model = sys.argv[3] if len(sys.argv) > 3 else "qwen/qwen3.5-9b"
cases = [c for c in json.loads((ROOT / "benchmarks/t0/ngo-corpus/cases.json").read_text())["cases"] if c["lane"] == "ask"]
out = ROOT / "benchmarks/runs/2026-08-24-astronaut-flows" / label; out.mkdir(parents=True, exist_ok=True)
def grade(last, c):
    txt = re.sub(r'(?<=\d),(?=\d)', '', last).replace('₹', ' ')
    lines = [{'t': l} for l in txt.splitlines() if l.strip()]
    exp = [list(x.values()) for x in c.get('expected_rows') or []]
    if not exp or not last.strip(): return False
    if len(exp) == 1: return rc.rows_match([{'t': txt}], exp, False, c['prompt'])[0]
    return all(rc.rows_match(lines, [er], False, c['prompt'])[0] for er in exp)
recs = []
for c in cases:
    work = H / "work"
    for p in work.iterdir():
        if p.name not in (".venv",):
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    for p in (ROOT / "benchmarks/t0/ngo-corpus" / c["org"]).iterdir():
        if p.is_file(): shutil.copy(p, work / p.name)
    if config == "tools":
        for p in (ROOT / "benchmarks/t0/harness-skill").iterdir():
            (shutil.copytree if p.is_dir() else shutil.copy)(p, work / p.name)
        (work / "AGENTS.md").write_text((work / "AGENTS.md").read_text().replace("python3 io.py", "/work/.venv/bin/python io.py"))
        task = f"{c['prompt']}\n\nRead AGENTS.md in this folder first and follow it (use /work/.venv/bin/python io.py schema and io.py query). Finish with the answer as a short table."
    else:
        task = f"{c['prompt']}\n\nThe data files are in this folder. Write and run python with /work/.venv/bin/python (pandas, openpyxl, duckdb available) to compute the answer, then finish with the answer as a short table."
    t0 = time.time()
    r = subprocess.run(["docker", "exec", "io-hermes", "sh", "-c", f"cd /work && timeout 420 hermes --yolo -m {model} -z {json.dumps(task)} 2>&1"], capture_output=True, text=True)
    last = r.stdout[-6000:]
    (out / f"{c['id']}.txt").write_text(r.stdout)
    ok = grade(last, c)
    sec = round(time.time() - t0, 1)
    recs.append({"id": c["id"], "passed": ok, "seconds": sec, "chars": len(r.stdout)})
    print(f"{'PASS' if ok else 'FAIL'} {c['id']} {c['prompt'][:60]:<60} {sec}s", flush=True)
    (out / "results.json").write_text(json.dumps({"config": config, "model": model, "passed": sum(x["passed"] for x in recs), "total": len(recs), "records": recs}, indent=1))
print(json.dumps({"config": config, "model": model, "passed": sum(x["passed"] for x in recs), "total": len(recs), "mean_seconds": round(sum(x["seconds"] for x in recs) / len(recs), 1)}))
