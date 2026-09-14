#!/usr/bin/env python3
"""Spike 1: does the bundled Codex, in ChatGPT-auth mode, in an isolated CODEX_HOME, send its
model traffic to io's loopback proxy - and does the proxy's 426 make it fall back to SSE?

No real credential is involved. The isolated home gets a *fixture* auth.json: a JWT-shaped
id_token with the claims Codex reads (parse_chatgpt_jwt_claims) and placeholder access /
refresh tokens. Codex then behaves as a ChatGPT-mode client right up to the point where the
upstream rejects the placeholder (401 from chatgpt.com). The proxy log is the evidence:
which paths Codex used, in what order, with what auth header shape, and the 426 -> SSE
fallback. The developer's ~/.codex is never read; `codex login status` on the isolated home
before and after shows what that home holds.

Usage: python3 spike1_routing.py <out-dir>
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parents[2] / "app" / "io"
sys.path.insert(0, str(APP))
from codex_proxy import MapPolicy, Proxy  # noqa: E402

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "spike1-out").resolve()
shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir(parents=True)
HOME = OUT / "codex-home"
WORK = OUT / "workspace"
HOME.mkdir()
WORK.mkdir()
(WORK / "note.txt").write_text("Alice Example lives in SecretVillage.\n")

codex = APP / "codex-bin" / ("linux-arm64" if os.uname().machine == "aarch64" else "linux-x64") / "bin" / "codex"
env = {k: v for k, v in os.environ.items() if not k.startswith("OPENAI")}
env["CODEX_HOME"] = str(HOME)


def run(*args, timeout=120):
    p = subprocess.run([str(codex), *args], env=env, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr).replace(str(OUT), "<out>")


before = run("login", "status")

# ---- fixture credential (structurally a JWT; signed by nobody; rejected by any server)
b64 = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
now = int(time.time())
claims = {"iss": "https://auth.openai.com", "sub": "fixture", "exp": now + 3600, "iat": now,
          "email": "fixture@example.invalid",
          "https://api.openai.com/auth": {"chatgpt_account_id": "acct_fixture", "chatgpt_user_id": "user_fixture", "chatgpt_plan_type": "plus"}}
jwt = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64(claims)}.fixture-signature"
(HOME / "auth.json").write_text(json.dumps({
    "auth_mode": "chatgpt",
    "OPENAI_API_KEY": None,
    "tokens": {"id_token": jwt, "access_token": jwt, "refresh_token": "fixture-refresh", "account_id": "acct_fixture"},
    "last_refresh": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
}, indent=1))
after_fixture = run("login", "status")

# ---- proxy in front of the real chatgpt.com
log_lines: list[str] = []
proxy = Proxy(MapPolicy({"Alice Example": "NAME_001", "SecretVillage": "PLACE_001"}),
              upstream="https://chatgpt.com", log=log_lines.append, dump_dir=OUT / "proxy-dump")
port = proxy.start()
(HOME / "config.toml").write_text(f'''
openai_base_url = "http://127.0.0.1:{port}/backend-api/codex"
chatgpt_base_url = "http://127.0.0.1:{port}/backend-api/"
check_for_update_on_startup = false
model = "gpt-5.3-codex"

[features]
enable_request_compression = false
''')

t0 = time.time()
rc, out = run("exec", "--skip-git-repo-check", "-C", str(WORK), "-s", "read-only", "--ephemeral", "--color", "never",
              "Say the word ready and nothing else.", timeout=180)
took = time.time() - t0
proxy.stop()

entries = [json.loads(x) for x in log_lines if x.startswith("{")]
paths = [(e["method"], e["path"], e.get("status"), e.get("note") or "", e.get("auth")) for e in entries]
summary = {
    "codex": run("--version")[1].strip(),
    "login_status_before_fixture": before,
    "login_status_with_fixture": after_fixture,
    "exec_exit": rc, "exec_seconds": round(took, 1),
    "proxy_port": port,
    "requests_seen_by_proxy": paths,
    "websocket_426_then_sse": any(p[1].endswith("/responses") and "websocket" in p[3] for p in paths)
                              and any(p[1] == "/backend-api/codex/responses" and "websocket" not in p[3] for p in paths),
    "responses_reached_chatgpt_com": [p[2] for p in paths if p[1] == "/backend-api/codex/responses" and "websocket" not in p[3]],
    "auth_header_shape": sorted({p[4] for p in paths if p[4]}),
    "codex_output_tail": out[-1200:],
    "home_files": sorted(str(p.relative_to(HOME)) for p in HOME.rglob("*") if p.is_file())[:40],
}
(OUT / "summary.json").write_text(json.dumps(summary, indent=1))
(OUT / "proxy-log.jsonl").write_text("\n".join(log_lines) + "\n")
print(json.dumps({k: v for k, v in summary.items() if k not in ("codex_output_tail", "home_files")}, indent=1))
print("--- codex output tail ---")
print(out[-1500:])
