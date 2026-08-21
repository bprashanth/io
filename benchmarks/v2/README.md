# V2 local-first benchmark

This directory contains the frozen contracts and environment for the
laptop-model -> Qwen 3.8 27B -> value-free frontier routing experiment.

Create the isolated runner environment from the repository root:

```bash
uv venv .venv-v2
uv pip install --python .venv-v2/bin/python -r benchmarks/v2/requirements.txt
.venv-v2/bin/python -m playwright install chromium
```

Do not install these packages globally. Raw runs belong below
`benchmarks/runs/<date>-v2/`; this directory holds only versioned manifests,
schemas and small summary records.

The active isolated query gate is `query-suite-v2.json`. Version 1 is retained
only to reproduce an evaluator defect discovered during its first model runs:
it exposed unrelated datasets and allowed paraphrases to omit scope required by
the gold answer.

Run a local OpenAI-compatible model:

```bash
.venv-v2/bin/python benchmarks/scripts/run_v2_query_gate.py \
  --model MODEL_ID \
  --endpoint http://127.0.0.1:8020/v1 \
  --output benchmarks/runs/RUN_ID
```

The measured laptop-tier candidate is the exact Q4_K_M file below. The path is
outside the repository and the checksum is part of the result contract:

```text
/mnt/seagate/io-models/Arctic-Text2SQL-R1-7B-GGUF-Q4_K_M/Arctic-Text2SQL-R1-7B.Q4_K_M.gguf
SHA-256 9c005244e3ab7fada2c53a9511999f4d22fbbd4f76a4416416a6d41d82702255
```

Start it with an official llama.cpp server build (the container is the measured
Linux path; a packaged llama.cpp executable is the intended Windows path):

```bash
docker run --rm --name io-v2-arctic7b-q4 --gpus all \
  --memory 16g --cpus 8 \
  -v /mnt/seagate/io-models/Arctic-Text2SQL-R1-7B-GGUF-Q4_K_M:/models:ro \
  -p 127.0.0.1:8022:8080 ghcr.io/ggml-org/llama.cpp:server-cuda13 \
  -m /models/Arctic-Text2SQL-R1-7B.Q4_K_M.gguf \
  --alias Snowflake/Arctic-Text2SQL-R1-7B-Q4_K_M \
  --host 0.0.0.0 --port 8080 --ctx-size 8192 --parallel 1 \
  --gpu-layers 99 --threads 8 --threads-batch 8 --jinja
```

Reproduce the strict gate and generic routing replay:

```bash
.venv-v2/bin/python benchmarks/scripts/run_v2_query_gate.py \
  --model Snowflake/Arctic-Text2SQL-R1-7B-Q4_K_M \
  --endpoint http://127.0.0.1:8022/v1 --max-tokens 1024 \
  --temperature 0 --timeout-seconds 120 \
  --output benchmarks/runs/RUN_ID

.venv-v2/bin/python benchmarks/scripts/replay_query_router.py \
  --run benchmarks/runs/RUN_ID \
  --output benchmarks/runs/RUN_ID/router-replay.json
```

Run one local-first turn with Qwen 3.8 27B fallback. Only public or synthetic
fixtures may be sent to OpenRouter. In private deployment, point the fallback
endpoint at the trusted local DGX service instead.

```bash
.venv-v2/bin/python benchmarks/scripts/run_local_first_insight.py \
  --data benchmarks/cases/v2-agriculture-journey-001/inputs/field_harvest.csv \
  --question 'show 2024 Monsoon tonnes per hectare by block highest first, keep source and download' \
  --session benchmarks/runs/LOCAL_SESSION \
  --fallback-endpoint https://openrouter.ai/api/v1 \
  --fallback-api-key-file ~/.config/idlisseus/openrouter.json
```

The script writes `index.html`, a filtered CSV download, the exact selected SQL,
route decision, conversation state and a frontier envelope that is not sent.
The frontier envelope contains no raw question or values.

Run Qwen 3.8 27B through OpenRouter for development-only public or synthetic
fixtures:

```bash
.venv-v2/bin/python benchmarks/scripts/run_v2_query_gate.py \
  --model qwen/qwen3.8-27b \
  --endpoint https://openrouter.ai/api/v1 \
  --api-key-file ~/.config/idlisseus/openrouter.json \
  --reasoning-effort low --max-tokens 2048 --temperature 0 \
  --output benchmarks/runs/RUN_ID
```

Every question is standalone and carries only its selected dataset schema.
Required result columns may appear inside a wider useful result, but extra rows,
wrong units, wrong values, and missing obligations fail. Ranking order is
required only when the user asks for a ranking.
