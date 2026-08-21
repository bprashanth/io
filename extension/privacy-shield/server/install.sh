#!/usr/bin/env bash
# Creates the Python environment for the privacy shield next to this script and
# downloads the 181 MB GLiNER model. Needs python3 (3.10+) and internet once.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON:-python3}"
"$PY" -m venv "$HERE/.venv"
"$HERE/.venv/bin/pip" install --upgrade pip >/dev/null
"$HERE/.venv/bin/pip" install -r "$HERE/requirements.txt"
export HF_HOME="$HERE/hf-cache"
"$HERE/.venv/bin/python" - <<'PY'
from gliner import GLiNER
GLiNER.from_pretrained("knowledgator/gliner-pii-edge-v1.0")
print("model cached")
PY
echo "privacy shield environment ready: $HERE/.venv"
