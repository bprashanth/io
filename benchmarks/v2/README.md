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
