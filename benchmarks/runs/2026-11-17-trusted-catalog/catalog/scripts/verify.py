"""Install each catalog tool from its pins alone, fetch its files through the router, run its example offline.
Writes needs.json and verify.json."""
import hashlib, json, math, os, re, shutil, subprocess, sys, tarfile, time, urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8196/idli/catalog"
ONLY = sys.argv[2:]
PIXI = os.path.expanduser("~/idli-insights/platform/bin/pixi")
ENVS = "/home/beeps/idli-catalog-envs/_verify"
W = "/mnt/seagate/idli-catalog-work"
STORE = f"{W}/verify-files"  # the shared model folder (IDLI_FILES)
IN, OUT = f"{W}/inputs", f"{W}/verify-out"
os.makedirs(STORE, exist_ok=True); os.makedirs(OUT, exist_ok=True)
RUN = {
 "media-ffmpeg": (["face.mp4", "subs_hi.srt", "@clip.mp4", "0", "3.5"], "wrote"),
 "speech-whisper-small": (["hi_speech.wav", "hi", "whisper-small"], "स्कूल"),
 "speech-whisper-turbo": (["hi_speech.wav", "hi", "whisper-large-v3-turbo"], "बैठक"),
 "voice-piper": (["=नमस्ते, आज हमारी बैठक दस बजे गाँव के स्कूल में होगी।", "@piper.wav"], "wrote"),
 "voice-kokoro": (["=नमस्ते, आज हमारी बैठक दस बजे गाँव के स्कूल में होगी।", "@kokoro.wav"], "wrote"),
 "translate-nllb": (["report_en.txt", "@report_hi.txt", "eng_Latn", "hin_Deva"], "बैठक"),
 "ocr-tesseract": (["table_hi.png", "@table.xlsx"], "शिवगढ़"),
 "ocr-rapidocr": (["text_hi.png"], "किसान"),
 "speech-vad": (["mixed.wav"], "speech"),
 "sound-classes": (["mixed.wav"], "music"),
 "face-blur": (["face.mp4", "@face_blur.mp4"], "100 frames"),
 "voice-anonymise": (["kokoro_hi.wav", "@anon.wav", "hi"], "wrote"),
 "office-files": (["@office"], "मासिक"),
 "page-server": ([], "page ok"),
}
CORES = {"speech-whisper-small": 2, "speech-whisper-turbo": 4, "translate-nllb": 4, "voice-anonymise": 4,
         "voice-kokoro": 2, "media-ffmpeg": 2, "face-blur": 2}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def du(p):
    return int(subprocess.run(["du", "-sb", p], capture_output=True, text=True).stdout.split()[0])


cat = json.load(urllib.request.urlopen(BASE + "/catalog.json"))
needs = json.load(open(f"{W}/needs.json")) if os.path.exists(f"{W}/needs.json") else {}
report = json.load(open(f"{W}/verify.json")) if os.path.exists(f"{W}/verify.json") else {}
for t in cat["tools"]:
    tid = t["id"]
    if ONLY and tid not in ONLY:
        continue
    d = f"{ENVS}/{tid}"
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    s = f'[workspace]\nname = "{tid}"\nchannels = ["conda-forge"]\nplatforms = ["linux-aarch64"]\n\n[dependencies]\n'
    s += "".join(f'{k} = "{v}"\n' for k, v in t["pixi"]["dependencies"].items())
    if t["pixi"]["pypi-dependencies"]:
        s += "\n[pypi-dependencies]\n" + "".join(f'{k} = "{v}"\n' for k, v in t["pixi"]["pypi-dependencies"].items())
    open(f"{d}/pixi.toml", "w").write(s)
    t0 = time.time()
    r = subprocess.run([PIXI, "install", "--manifest-path", f"{d}/pixi.toml"], capture_output=True, text=True)
    if r.returncode:
        report[tid] = {"ok": False, "stage": "install", "err": r.stderr[-800:]}; print(tid, "INSTALL FAIL"); continue
    env_bytes = du(f"{d}/.pixi/envs/default")
    model_bytes = 0
    for m in t["models"] + [{"file": t["example"], "sha256": None, "bytes": None, "unpack": "none"}]:
        p = os.path.join(STORE, m["file"])
        if not (os.path.exists(p) and m["sha256"] and os.path.getsize(p) == m["bytes"]):
            os.makedirs(os.path.dirname(p), exist_ok=True)
            urllib.request.urlretrieve(BASE + "/files/" + urllib.request.quote(m["file"]), p + ".part")
            os.replace(p + ".part", p)
        if m["sha256"]:
            assert os.path.getsize(p) == m["bytes"] and sha(p) == m["sha256"], f"{tid}: {m['file']} does not match"
            model_bytes += m["bytes"]
        if m["unpack"] == "tar":
            stem = os.path.join(os.path.dirname(p), os.path.basename(p)[:-4])
            if not os.path.isdir(stem):
                with tarfile.open(p) as tf:
                    names = tf.getnames()
                    assert all(n == os.path.basename(stem) or n.startswith(os.path.basename(stem) + "/") for n in names)
                    tf.extractall(os.path.dirname(p), filter="data")
            model_bytes += du(stem)
    args, expect = RUN[tid]
    argv = []
    for a in args:
        argv.append(a[1:] if a.startswith("=") else os.path.join(OUT, a[1:]) if a.startswith("@") else
                    os.path.join(IN, a) if os.path.exists(os.path.join(IN, a)) else a)
    py = f"{d}/.pixi/envs/default/bin/python"
    ex = os.path.join(STORE, t["example"])
    cmd = [py, "-I", f"{W}/scripts/page_driver.py", ex] if tid == "page-server" else [py, "-I", ex] + argv
    env = dict(os.environ, IDLI_FILES=STORE, PATH=f"{d}/.pixi/envs/default/bin:" + os.environ["PATH"])
    full = ["/usr/bin/time", "-f", "TIME %e %M", "bwrap", "--dev-bind", "/", "/", "--unshare-net"] + cmd
    r = subprocess.run(full, capture_output=True, text=True, env=env, cwd=OUT)
    m = re.search(r"TIME ([\d.]+) (\d+)", r.stderr)
    secs, rss = float(m.group(1)), int(m.group(2)) * 1024
    ok = r.returncode == 0 and expect in r.stdout
    report[tid] = {"ok": ok, "seconds": secs, "max_rss_bytes": rss, "env_bytes": env_bytes, "model_bytes": model_bytes,
                   "install_seconds": round(time.time() - t0 - secs, 1), "stdout": r.stdout[-1500:],
                   "stderr": "" if ok else r.stderr[-1500:]}
    disk = env_bytes + model_bytes
    needs[tid] = {"disk_gb": math.ceil(disk / 1e9 * 1.1 * 10) / 10, "ram_gb": max(0.5, math.ceil(rss / 1e9 * 1.5 * 2) / 2),
                  "cores": CORES.get(tid, 1), "gpu": False}
    print(tid, "OK" if ok else "FAIL", f"{secs}s rss={rss >> 20}MB env={env_bytes >> 20}MB models={model_bytes >> 20}MB", flush=True)
    json.dump(report, open(f"{W}/verify.json", "w"), indent=1, ensure_ascii=False)
    json.dump(needs, open(f"{W}/needs.json", "w"), indent=1)
