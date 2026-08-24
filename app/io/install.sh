#!/usr/bin/env bash
# One-time setup. CPU only, ~600 MB disk, internet once. Needs python3 (3.10+) and node 18+.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
"${PYTHON:-python3}" -m venv "$HERE/.venv"
PIP="$HERE/.venv/bin/pip"
"$PIP" install --upgrade pip >/dev/null
"$PIP" install --index-url https://download.pytorch.org/whl/cpu "torch>=2.2"
"$PIP" install gliner==0.2.28 pandas openpyxl
HF_HOME="$HERE/hf-cache" "$HERE/.venv/bin/python" - <<'PY'
from gliner import GLiNER
GLiNER.from_pretrained("knowledgator/gliner-pii-edge-v1.0", map_location="cpu")
print("scanner cached")
PY
npm install --silent
echo "ready: npm start"
