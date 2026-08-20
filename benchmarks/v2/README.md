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
