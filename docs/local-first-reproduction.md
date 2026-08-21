# Reproduce the local-first prototype

This runbook separates what was measured on this Linux host from the proposed
Windows event path. Do not present the Windows path as tested until the laptop
rehearsal is recorded.

## Measured Linux path

From the repository root, create the pinned Python environment:

```bash
uv venv .venv-v2
uv pip install --python .venv-v2/bin/python -r benchmarks/v2/requirements.txt
.venv-v2/bin/python -m playwright install chromium
```

Check the exact Q4 model before starting it:

```bash
sha256sum /mnt/seagate/io-models/Arctic-Text2SQL-R1-7B-GGUF-Q4_K_M/Arctic-Text2SQL-R1-7B.Q4_K_M.gguf
```

Expected SHA-256:

```text
9c005244e3ab7fada2c53a9511999f4d22fbbd4f76a4416416a6d41d82702255
```

The exact measured container command is in
[`benchmarks/v2/README.md`](../benchmarks/v2/README.md). It exposes an
OpenAI-compatible service at `http://127.0.0.1:8022/v1`.

Run the three participant turns into the same `--session` directory. This keeps
the prior questions and validated SQL as conversation state:

```bash
.venv-v2/bin/python benchmarks/scripts/run_local_first_insight.py \
  --data benchmarks/cases/v2-agriculture-journey-001/inputs/field_harvest.csv \
  --question 'one csv is there. make a 2024 Monsoon block wise crop yield dashboard, tonnes per hectare highest first. i should see source and download the table' \
  --session benchmarks/runs/MY-LOCAL-SESSION \
  --fallback-endpoint https://openrouter.ai/api/v1 \
  --fallback-api-key-file ~/.config/idlisseus/openrouter.json
```

Repeat the command with the next question and the same session path. For a
private deployment, replace the OpenRouter URL with the trusted local Qwen 3.8
27B endpoint and omit the OpenRouter key file. The output is
`benchmarks/runs/MY-LOCAL-SESSION/index.html`; it opens directly in a browser.

Run the browser acceptance check without starting a web server:

```bash
.venv-v2/bin/python benchmarks/scripts/check_split_dashboard.py \
  --url file:///ABSOLUTE/PATH/TO/benchmarks/runs/MY-LOCAL-SESSION/index.html \
  --output benchmarks/runs/MY-LOCAL-SESSION/browser
```

## Viewing a server result from a laptop

If the benchmark runs over SSH, serve only the chosen session on loopback:

```bash
python3 -m http.server 18090 --bind 127.0.0.1 \
  --directory benchmarks/runs/MY-LOCAL-SESSION
```

On the laptop, open a tunnel:

```bash
ssh -L 18090:127.0.0.1:18090 USER@SERVER
```

Then open `http://127.0.0.1:18090/`. This does not expose the page on the
server's public network interface.

## Proposed Windows model service

The official llama.cpp installation guide currently documents:

```powershell
winget install llama.cpp
```

The official server guide documents `llama-server.exe` on Windows. The matching
prototype command is:

```powershell
llama-server.exe `
  -m C:\NGOInsight\models\Arctic-Text2SQL-R1-7B.Q4_K_M.gguf `
  --alias Snowflake/Arctic-Text2SQL-R1-7B-Q4_K_M `
  --host 127.0.0.1 --port 8022 --ctx-size 8192 --parallel 1 `
  --gpu-layers 99 --threads 8 --threads-batch 8 --jinja
```

References: [official llama.cpp installation guide](https://github.com/ggml-org/llama.cpp/blob/master/docs/install.md)
and [official server guide](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

This command is documentation, not benchmark evidence. We have not yet tested
the model on Windows, CPU-only inference, different GPU backends or the mix of
laptops expected at the event. Do not ask participants to run these commands.
The event deliverable should be one preinstalled, signed application bundle
that starts the service, checks health, chooses local or DGX routing, opens the
page and hides traces from the participant.

## Privacy check

The generated frontier request is saved but not sent. Verify it against the
real result values:

```bash
PYTHONPATH=benchmarks/scripts .venv-v2/bin/python \
  benchmarks/scripts/check_frontier_boundary.py \
  --dashboard-run benchmarks/runs/MY-LOCAL-SESSION \
  --output benchmarks/runs/MY-LOCAL-SESSION/privacy
```

The check must report `passed: true`. The allowed envelope is limited to a
value-free intent outline, result column name/type/role and fixed layout
contract. The raw participant question is excluded.
