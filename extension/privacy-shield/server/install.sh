#!/usr/bin/env bash
# Creates the Python environment for the privacy shield next to this script and
# downloads the 181 MB GLiNER model. CPU only: no CUDA, no GPU needed.
# Needs python3 (3.10+) and internet once. Roughly 600 MB on disk.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON:-python3}"
"$PY" -m venv "$HERE/.venv"
PIP="$HERE/.venv/bin/pip"
"$PIP" install --upgrade pip >/dev/null
# CPU-only torch first, so gliner does not pull the multi-GB CUDA build.
"$PIP" install --index-url https://download.pytorch.org/whl/cpu "torch>=2.2" 
"$PIP" install -r "$HERE/requirements.txt"
export HF_HOME="$HERE/hf-cache"
"$HERE/.venv/bin/python" - <<'PY'
from gliner import GLiNER
GLiNER.from_pretrained("knowledgator/gliner-pii-edge-v1.0", map_location="cpu")
print("model cached")
PY
echo "privacy shield environment ready: $HERE/.venv"
