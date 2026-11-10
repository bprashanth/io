"""Run scenarios x models (x variants x repeats), each conversation in its own process, then score.

  python harness/run.py --run <name> --models muse30b,or-qwen35-9b [--variants base] [--scenarios dev,held]
                        [--reps 2] [--par 4] [--only d01,d02]
Already-finished transcripts are kept (rerun to fill gaps). Local models run one conversation at a time
unless --par says otherwise; Muse at most 2 (it serves other people).
"""
import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
SDK_PY = os.environ.get("IDLI9B_SDK_PY", "/tmp/claude-1000/b9/sdkvenv/bin/python")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--models", required=True)
    ap.add_argument("--variants", default="base")
    ap.add_argument("--scenarios", default="dev")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--par", type=int, default=0)
    ap.add_argument("--only", default="")
    ap.add_argument("--harness", default="lean", choices=["lean", "cc"])
    a = ap.parse_args()
    with open(os.path.join(BENCH, "models.json")) as f:
        models = json.load(f)
    jobs = []
    for sname in a.scenarios.split(","):
        sfile = os.path.join(BENCH, "scenarios", sname + ".json")
        with open(sfile) as f:
            convs = [c["id"] for c in json.load(f)["conversations"]]
        for m in a.models.split(","):
            for v in a.variants.split(","):
                for c in convs:
                    if a.only and not any(c.startswith(o) for o in a.only.split(",")):
                        continue
                    for r in range(a.reps):
                        out = os.path.join(BENCH, "results", a.run, m, v, f"{c}-r{r}.json")
                        if not os.path.exists(out):
                            jobs.append((m, v, sfile, c, r, out))
    by_model = {}
    for j in jobs:
        by_model.setdefault(j[0], []).append(j)
    tmp = os.path.join(os.environ.get("IDLI9B_TMP", "/tmp/claude-1000/b9/tmp"))
    os.makedirs(tmp, exist_ok=True)
    env = dict(os.environ, IDLI9B_TMP=tmp)

    def one(j):
        m, v, sfile, c, r, out = j
        t0 = time.time()
        exe, script = ((SDK_PY, "cc_convo.py") if a.harness == "cc" else (sys.executable, "convo.py"))
        p = subprocess.run([exe, os.path.join(HERE, script), "--model", m, "--variant", v,
                            "--scenario", sfile, "--conv", c, "--out", out], capture_output=True, text=True,
                           timeout=3600, env=env)
        if p.returncode == 0 and os.path.exists(out):
            with open(out) as f:
                log = json.load(f)
            log["rep"] = r
            with open(out, "w") as f:
                json.dump(log, f, indent=1, default=str)
        print(f"{m} {v} {c} r{r}: {'ok' if p.returncode == 0 else 'FAIL ' + p.stderr[-300:]} {time.time() - t0:.0f}s",
              flush=True)

    def run_model(m):
        spec = models[m]
        par = a.par or (2 if m == "muse30b" else 1 if spec["base"].startswith("http://127.0.0.1") else 4)
        with ThreadPoolExecutor(par) as ex:
            list(ex.map(one, by_model[m]))

    with ThreadPoolExecutor(len(by_model) or 1) as ex:
        list(ex.map(run_model, list(by_model)))
    subprocess.run([sys.executable, os.path.join(HERE, "score.py"), os.path.join(BENCH, "results", a.run)])


if __name__ == "__main__":
    main()
