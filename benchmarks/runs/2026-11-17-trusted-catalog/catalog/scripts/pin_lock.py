"""Pin each tool to what solved on the DGX, then solve (pixi lock only) for each platform on its own."""
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from specs import SPECS
from mkproj import ENVS, PIXI, toml

PLATS = ["linux-64", "linux-aarch64", "osx-arm64", "win-64"]
OUT = "/mnt/seagate/idli-catalog-work/pins.json"
PYTHON = sys.argv[1] if len(sys.argv) > 1 else "==3.11.18"

def norm(n):
    return n.lower().replace("_", "-")

def pins(tid):
    deps, pypi = SPECS[tid]
    got = json.loads(subprocess.run([PIXI, "list", "--json", "--manifest-path", f"{ENVS}/{tid}/pixi.toml"],
                                    capture_output=True, text=True, check=True).stdout)
    v = {(p["kind"], norm(p["name"])): p["version"] for p in got}
    cd = {k: (PYTHON if k == "python" else "==" + v[("conda", norm(k))]) for k in deps}
    pd = {k: "==" + v[("pypi", norm(k))] for k in pypi}
    return cd, pd

def lock(tid, cd, pd, plat):
    d = f"{ENVS}/_lock/{tid}/{plat}"
    os.makedirs(d, exist_ok=True)
    open(f"{d}/pixi.toml", "w").write(toml(tid, cd, pd, [plat]))
    if os.path.exists(f"{d}/pixi.lock"):
        os.remove(f"{d}/pixi.lock")
    r = subprocess.run([PIXI, "lock", "--manifest-path", f"{d}/pixi.toml"], capture_output=True, text=True)
    return plat, r.returncode == 0, (r.stderr or r.stdout)[-600:]

res = json.load(open(OUT)) if os.path.exists(OUT) else {}
only = sys.argv[2:]
for tid in SPECS:
    if only and tid not in only:
        continue
    cd, pd = pins(tid)
    with ThreadPoolExecutor(4) as ex:
        out = list(ex.map(lambda p: lock(tid, cd, pd, p), PLATS))
    res[tid] = {"dependencies": cd, "pypi-dependencies": pd, "platforms": [p for p, ok, _ in out if ok],
                "failed": {p: e for p, ok, e in out if not ok}}
    print(tid, res[tid]["platforms"], {p: e[-300:] for p, e in res[tid]["failed"].items()}, flush=True)
    json.dump(res, open(OUT, "w"), indent=1)
