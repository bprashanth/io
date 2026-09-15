#!/usr/bin/env python3
"""Measure the wall on this machine, one Codex `exec` per setting.

A probe script is placed in the workspace; the model is asked only to run it. The script
tries the things the wall is supposed to allow or refuse and writes a JSON file *inside the
workspace*, so the verdicts are read off disk by us, never taken from the model's prose.

  python3 wall_probe.py <out-dir> [offline|tools|open ...]

Needs: bwrap able to run here (see the chronology entry for the AppArmor profile), the
OpenRouter key file for the dev provider (never printed), io's checkout venv as libsDir.
"""
from __future__ import annotations

import json, os, shutil, subprocess, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parents[2] / "app" / "io"
sys.path.insert(0, str(APP))
from codex_proxy import MapPolicy, Proxy  # noqa: E402

OUT = Path(sys.argv[1]).resolve()
WALLS = sys.argv[2:] or ["offline", "tools", "open"]
OUT.mkdir(parents=True, exist_ok=True)
key = json.load(open(Path.home() / ".config" / "idlisseus" / "openrouter.json"))["api_key"]
codex_dir = APP / "codex-bin" / ("linux-arm64" if os.uname().machine == "aarch64" else "linux-x64")
libs = APP / ".venv"

# a loopback listener outside the sandbox: "did a command reach the network" without touching the internet
hits: list[str] = []
class L(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        hits.append(self.path); b = b"listener ok"; self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
srv = ThreadingHTTPServer(("127.0.0.1", 0), L); lport = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

PROBE = r'''#!/bin/bash
# runs inside Codex's sandbox; every line writes a verdict, nothing is inferred from prose
out=probe-result.json
j() { printf '"%s": "%s",\n' "$1" "$(echo "$2" | tr -d '"\n' | cut -c1-160)"; }
{
echo "{"
j home_ls "$(ls /home/beeps 2>&1 | head -2 | tr '\n' ' ')"
j etc_hostname "$(cat /etc/hostname 2>&1)"
j codex_auth "$(ls /home/beeps/.local/share/io 2>&1 | head -2 | tr '\n' ' ')"
j tmp_write "$(touch /tmp/io-wall-probe-$$ 2>&1 && echo ok)"
j ws_write "$(echo hi > probe-wrote.txt 2>&1 && cat probe-wrote.txt)"
j python "$(command -v python3)"
j pandas "$(python3 -c 'import pandas, numpy, openpyxl; print(pandas.__version__, numpy.__version__, openpyxl.__version__)' 2>&1)"
j loopback "$(curl -s -m 4 http://127.0.0.1:LPORT/probe 2>&1; echo " exit=$?")"
j internet "$(curl -s -m 6 -o /dev/null -w '%{http_code}' https://example.com 2>&1; echo " exit=$?")"
j rg "$(command -v rg 2>&1)"
j uid "$(id -u) $(cat /proc/self/status | grep CapEff)"
printf '"done": true\n}\n'
} > $out 2>&1
cat $out
'''.replace("LPORT", str(lport))

results = {}
for wall in WALLS:
    home = OUT / f"home-{wall}"; ws = OUT / f"ws-{wall}"
    shutil.rmtree(home, ignore_errors=True); shutil.rmtree(ws, ignore_errors=True)
    home.mkdir(parents=True); ws.mkdir(parents=True)
    (ws / "probe.sh").write_text(PROBE); os.chmod(ws / "probe.sh", 0o755)
    (ws / "visits.csv").write_text("name,village\nAlice Example,SecretVillage\n")
    log: list[str] = []
    proxy = Proxy(MapPolicy({"Alice Example": "NAME_001"}), upstream="http://127.0.0.1:9", log=log.append,
                  dev_upstreams={"/dev/v1": "https://openrouter.ai/api/v1"})
    port = proxy.start()
    subprocess.run(["node", "-e", f"""
      const c=require('{APP}/codex.js');
      c.writeConfig('{home}', {port}, {{devProvider:true, model:'openai/gpt-5.2', trust:'{ws}', codexDir:'{codex_dir}', libsDir:'{libs}', wall:'{wall}'}});
    """], check=True)
    hits.clear()
    env = {k: v for k, v in os.environ.items() if not k.startswith("OPENAI")}
    env["CODEX_HOME"] = str(home); env["IO_DEV_KEY"] = key
    env["PATH"] = f"{libs}/bin:" + env.get("PATH", "")
    args = [str(codex_dir / "bin" / "codex"), "exec", "-p", "io", "--skip-git-repo-check", "-C", str(ws), "--color", "never"]
    # `-a never` is an interactive-session flag (spawnSession adds it for Offline); `codex exec`
    # rejects it and is non-interactive anyway, so no escalation prompt can exist here.
    t0 = time.time()
    p = subprocess.run(args + ["Run `bash probe.sh` exactly once and then reply with the single word done. Do not retry, do not run anything else, do not fix anything."],
                       env=env, capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)   # exec appends stdin to the prompt and waits for EOF
    took = round(time.time() - t0, 1)
    (OUT / f"codex-{wall}.txt").write_text(p.stdout + "\n--- stderr ---\n" + p.stderr)
    try:
        res = json.loads((ws / "probe-result.json").read_text())
    except Exception as e:  # noqa: BLE001
        res = {"error": f"no probe result: {e}"}
    cfg = (home / "io.config.toml").read_text()
    results[wall] = {"exit": p.returncode, "seconds": took, "listener_hits": list(hits), "probe": res,
                     "network_in_profile": "enabled = true" in cfg.split("[permissions.io.network]")[-1][:40],
                     "sandbox_words": [l.strip()[:160] for l in (p.stdout + p.stderr).splitlines() if "sandbox" in l.lower() or "bwrap" in l.lower()][:4]}
    proxy.stop()
(OUT / "summary.json").write_text(json.dumps(results, indent=1))
print(json.dumps(results, indent=1))
