"""Write a pixi project per tool under ENVS and install it for linux-aarch64 (the DGX)."""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
ENVS = "/home/beeps/idli-catalog-envs"
PIXI = os.path.expanduser("~/idli-insights/platform/bin/pixi")

def toml(name, deps, pypi, platforms):
    s = f'[workspace]\nname = "{name}"\nchannels = ["conda-forge"]\nplatforms = {json.dumps(platforms)}\n\n[dependencies]\n'
    s += "".join(f'{k} = "{v}"\n' for k, v in deps.items())
    if pypi:
        s += "\n[pypi-dependencies]\n" + "".join(f'{k} = "{v}"\n' for k, v in pypi.items())
    return s

def write(tid, deps, pypi, platforms=("linux-aarch64",)):
    d = os.path.join(ENVS, tid)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "pixi.toml"), "w").write(toml(tid, deps, pypi, list(platforms)))
    return d

if __name__ == "__main__":
    from specs import SPECS
    for tid in sys.argv[1:] or SPECS:
        deps, pypi = SPECS[tid]
        d = write(tid, deps, pypi)
        r = subprocess.run([PIXI, "install", "--manifest-path", d + "/pixi.toml"], capture_output=True, text=True)
        print(tid, "OK" if r.returncode == 0 else "FAIL\n" + r.stderr[-1500:], flush=True)
