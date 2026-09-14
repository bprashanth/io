#!/usr/bin/env python3
"""Spike 2: the real bundled Codex, non-interactive, through io's privacy proxy.

  codex exec  --(custom provider, API key)-->  127.0.0.1:<proxy>/dev/v1/responses
              --(tokenised)-->  OpenRouter /api/v1/responses  (OpenAI-shaped Responses SSE)

A deterministic mapping stands in for the vault. The workspace holds a CSV with the synthetic
values; Codex is asked to read it and answer about a named person. Evidence: the proxy dump
(tokenised request bodies + raw upstream SSE) must contain the tokens and not the values;
Codex's own transcript must contain the values (restored locally).

Usage: python3 spike2_exec.py <out-dir>   (needs the OpenRouter key file; never printed)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parents[2] / "app" / "io"
sys.path.insert(0, str(APP))
from codex_proxy import MapPolicy, Proxy  # noqa: E402

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "spike2-out").resolve()
shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir(parents=True)
HOME = OUT / "codex-home"
WORK = OUT / "workspace"
HOME.mkdir()
WORK.mkdir()

MAPPING = {"Alice Example": "NAME_001", "9876543210": "PHONE_001", "SecretVillage": "PLACE_001",
           "Bhavna Patel": "NAME_002", "9123456780": "PHONE_002", "Hillcrest": "PLACE_003"}
(WORK / "visits.csv").write_text(
    "name,village,phone,visits\n"
    "Alice Example,SecretVillage,9876543210,4\n"
    "Bhavna Patel,Hillcrest,9123456780,2\n"
    "Ravi Test,Hillcrest,9000000000,7\n")

key = json.load(open(Path.home() / ".config" / "idlisseus" / "openrouter.json"))["api_key"]
model = os.environ.get("SPIKE_MODEL", "openai/gpt-5.2")

log_lines: list[str] = []
proxy = Proxy(MapPolicy(MAPPING), upstream="http://127.0.0.1:9", log=log_lines.append,
              dump_dir=OUT / "proxy-dump", dev_upstreams={"/dev/v1": "https://openrouter.ai/api/v1"})
port = proxy.start()

(HOME / "config.toml").write_text(f'''
model = "{model}"
model_provider = "io-dev"
model_reasoning_effort = "low"
check_for_update_on_startup = false

[model_providers.io-dev]
name = "io-dev"
base_url = "http://127.0.0.1:{port}/dev/v1"
wire_api = "responses"
env_key = "IO_DEV_KEY"
supports_websockets = false

[features]
enable_request_compression = false
''')

codex = APP / "codex-bin" / ("linux-arm64" if os.uname().machine == "aarch64" else "linux-x64") / "codex"
env = {k: v for k, v in os.environ.items() if not k.startswith("OPENAI")}
env["CODEX_HOME"] = str(HOME)
env["IO_DEV_KEY"] = key
prompt = ("Read visits.csv in this folder (use cat). Then tell me: which village does Alice Example live in, "
          "what is her phone number, and who else lives in the same village as Bhavna Patel? "
          "Answer in one short paragraph and quote the exact values.")
t0 = time.time()
p = subprocess.run([str(codex), "exec", "--skip-git-repo-check", "-C", str(WORK), "--dangerously-bypass-approvals-and-sandbox", "--ephemeral",
                    "--color", "never", prompt], env=env, capture_output=True, text=True, timeout=600)
took = time.time() - t0
(OUT / "codex-stdout.txt").write_text(p.stdout)
(OUT / "codex-stderr.txt").write_text(p.stderr)
(OUT / "proxy-log.jsonl").write_text("\n".join(log_lines) + "\n")
proxy.stop()

# ---- evidence check
dumped = sorted((OUT / "proxy-dump").glob("*"))
leaked = []
tokens_seen = set()
for f in dumped:
    body = f.read_text(errors="replace")
    for v in MAPPING:
        if re.search(r"(?<![\w])" + re.escape(v) + r"(?![\w])", body, re.I):
            leaked.append((f.name, v))
    tokens_seen |= set(re.findall(r"\b(?:NAME|PHONE|PLACE)_\d{3}\b", body))
restored = [v for v in ("SecretVillage", "9876543210", "Alice Example") if v in p.stdout]
summary = {
    "model": model, "exit": p.returncode, "seconds": round(took, 1), "proxy_port": port,
    "requests": [json.loads(x) for x in log_lines if x.startswith("{")],
    "dump_files": [f.name for f in dumped],
    "tokens_in_upstream_traffic": sorted(tokens_seen),
    "real_values_in_upstream_traffic": leaked,
    "real_values_in_codex_output": restored,
    "verdict": "PASS" if (p.returncode == 0 and not leaked and tokens_seen and len(restored) >= 2) else "FAIL",
}
(OUT / "summary.json").write_text(json.dumps(summary, indent=1))
print(json.dumps({k: v for k, v in summary.items() if k != "requests"}, indent=1))
print("--- codex said ---")
print(p.stdout[-1500:])
if p.returncode:
    print("--- stderr tail ---")
    print(p.stderr[-2000:])
