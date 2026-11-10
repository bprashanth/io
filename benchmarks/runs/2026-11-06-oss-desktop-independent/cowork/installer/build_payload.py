#!/usr/bin/env python3
"""Assemble what an Idli installer carries, for one platform:

    OUT/python/   standalone CPython 3.12 (python-build-standalone, via uv) + duckdb pandas openpyxl matplotlib
    OUT/cowork/   Idli's tools (tracked files of this cowork/ tree; no taught files, no dev bits)
    OUT/paseo/    the official Paseo release for the platform (unpacked on Linux, Paseo.zip on macOS,
                  Paseo-Setup.exe on Windows)
    OUT/VERSION

  python3 installer/build_payload.py --os linux|mac|win --arch x64|arm64 --out DIR [--paseo v0.15.4] [--version V]

Needs uv and gh (or curl) on the build machine. Run from the cowork/ folder.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tarfile

COWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBS = ["duckdb", "pandas", "openpyxl", "matplotlib"]
SKIP_TOP = {"file-skills", "cowork.mcp.json", "local-9b", "dashboard-links", ".gitignore", "teach", "charts"}
PASEO_ASSET = {  # (os, arch) -> release asset
    ("linux", "x64"): "Paseo-{v}-x64.tar.gz",
    ("mac", "arm64"): "Paseo-{v}-arm64.zip",
    ("mac", "x64"): "Paseo-{v}-x64.zip",
    ("win", "x64"): "Paseo-Setup-{v}-x64.exe",
    ("win", "arm64"): "Paseo-Setup-{v}-arm64.exe",
}


def run(cmd, **kw):
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def python(out, plat, arch):
    tmp = os.path.join(out, "_py")
    run(["uv", "python", "install", "3.12", "--install-dir", tmp, "--no-bin"])
    # uv adds a "cpython-3.12-..." link (a junction on Windows) next to the real "cpython-3.12.N-..." folder
    inner = os.path.realpath(next(os.path.join(tmp, d) for d in sorted(os.listdir(tmp), key=len, reverse=True)
                                  if d.startswith("cpython-3.12")))
    dest = os.path.join(out, "python")
    shutil.move(inner, dest)
    shutil.rmtree(tmp, ignore_errors=True)
    exe = os.path.join(dest, "python.exe") if plat == "win" else os.path.join(dest, "bin", "python3")
    if not os.path.exists(exe):
        print("python layout:", sorted(os.listdir(dest))[:40], flush=True)
        raise SystemExit(f"no {exe} in the uv-installed Python")
    subprocess.run([exe, "-c", "import sys; print(sys.version)"], check=True)
    exe = os.path.abspath(exe)
    # the interpreter's own pip (uv pip can't always find a moved standalone Python on Windows)
    subprocess.run([exe, "-m", "ensurepip", "--upgrade"], check=False, capture_output=True)
    run([exe, "-m", "pip", "install", "--quiet", "--no-cache-dir", "--break-system-packages",
         "--disable-pip-version-check", *LIBS])
    for root, dirs, _ in os.walk(dest):  # tests and caches the app never runs
        for d in list(dirs):
            if d in ("__pycache__", "tests", "test") and "site-packages" in root:
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)
    return exe


def tools(out):
    files = subprocess.run(["git", "ls-files", "-z", "."], cwd=COWORK, capture_output=True, check=True).stdout
    dest = os.path.join(out, "cowork")
    n = 0
    for rel in filter(None, files.decode().split("\0")):
        if rel.split("/")[0] in SKIP_TOP:
            continue
        os.makedirs(os.path.dirname(os.path.join(dest, rel)) or dest, exist_ok=True)
        shutil.copy2(os.path.join(COWORK, rel), os.path.join(dest, rel))
        n += 1
    for d in ("file-skills", os.path.join("teach", "inbox")):
        os.makedirs(os.path.join(dest, d), exist_ok=True)
    # Idli 30B's Claude settings (Muse's model names; the address is set per person by the setup page)
    shutil.copy2(os.path.join(COWORK, "..", "laptop", "claude-t4gc-settings.json"),
                 os.path.join(dest, "installer", "claude-t4gc-settings.json"))
    print(f"tools: {n} files", flush=True)


def paseo(out, plat, arch, tag):
    v = tag.lstrip("v")
    asset = PASEO_ASSET[(plat, arch)].format(v=v)
    dest = os.path.join(out, "paseo")
    os.makedirs(dest, exist_ok=True)
    dl = os.path.join(out, "_dl")
    os.makedirs(dl, exist_ok=True)
    if shutil.which("gh"):
        run(["gh", "release", "download", tag, "-R", "getpaseo/paseo", "-p", asset, "-D", dl, "--clobber"])
    else:
        run(["curl", "-fsSL", "-o", os.path.join(dl, asset),
             f"https://github.com/getpaseo/paseo/releases/download/{tag}/{asset}"])
    src = os.path.join(dl, asset)
    if plat == "linux":
        with tarfile.open(src) as t:
            t.extractall(dl)
        top = next(os.path.join(dl, d) for d in os.listdir(dl) if os.path.isdir(os.path.join(dl, d)))
        shutil.rmtree(dest)
        shutil.move(top, dest)
    else:
        shutil.move(src, os.path.join(dest, asset))
    shutil.rmtree(dl, ignore_errors=True)
    print(f"paseo: {asset}", flush=True)


def icon(out):
    """A plain Idli icon (PNG, 512 px) for the platform wrappers, drawn with the bundled matplotlib."""
    exe = os.path.join(out, "python", "python.exe") if os.name == "nt" else os.path.join(out, "python", "bin", "python3")
    code = ("import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, sys\n"
            "f = plt.figure(figsize=(5.12, 5.12), dpi=100); a = f.add_axes([0, 0, 1, 1]); a.axis('off')\n"
            "a.add_patch(plt.Circle((.5, .5), .47, color='#2f5d50')); a.set_xlim(0, 1); a.set_ylim(0, 1)\n"
            "a.text(.5, .47, 'idli', ha='center', va='center', color='white', fontsize=92, fontweight='bold')\n"
            "f.savefig(sys.argv[1], transparent=True)")
    run([exe, "-c", code, os.path.join(out, "idli.png")])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--os", required=True, choices=["linux", "mac", "win"])
    ap.add_argument("--arch", default="x64", choices=["x64", "arm64"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--paseo", default="v0.15.4")
    ap.add_argument("--version", default="0.1.0")
    ap.add_argument("--no-paseo", action="store_true", help="skip Paseo (local tests on a platform it doesn't ship)")
    a = ap.parse_args()
    if os.path.exists(a.out):
        shutil.rmtree(a.out)
    os.makedirs(a.out)
    python(a.out, a.os, a.arch)
    tools(a.out)
    if not a.no_paseo:
        paseo(a.out, a.os, a.arch, a.paseo)
    with open(os.path.join(a.out, "VERSION"), "w") as f:
        f.write(a.version)
    icon(a.out)
    print("payload ready:", a.out)


if __name__ == "__main__":
    sys.exit(main())
