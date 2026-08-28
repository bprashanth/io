#!/usr/bin/env bash
# One-time setup for running io from a git checkout.
#
# Needs python3 (3.10+) and node 18+ already on the machine. If you do not have those,
# use a packaged build instead - it carries its own python and needs nothing installed:
# see installation/INSTALL-linux.md.
#
# Package versions come from pins.json, the same file the packaged builds use, so a
# checkout install and a downloaded build run identical code. ~1.9 GB on disk, internet
# needed once.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

command -v node >/dev/null || { echo "node 18+ is required and was not found on PATH"; exit 1; }
"${PYTHON:-python3}" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' \
  || { echo "python 3.10+ is required (found: $("${PYTHON:-python3}" -V 2>&1))"; exit 1; }

# read the pins so this cannot drift from what the packaged builds ship
read -r TORCH_INDEX TORCH REST <<EOF
$(node -e '
  const p = require("./pins.json");
  const torch = p.packages.find(x => x.startsWith("torch=="));
  const rest = p.packages.filter(x => x !== torch);
  console.log(p.torchIndex, torch, rest.join(" "));
')
EOF

echo "==> python environment"
"${PYTHON:-python3}" -m venv .venv
PY=".venv/bin/python"
"$PY" -m pip install --quiet --upgrade pip

echo "==> $TORCH (CPU build, this is the big one)"
case "$(uname -s)" in
  Darwin) "$PY" -m pip install "$TORCH" ;;             # macOS wheels on PyPI are already CPU
  *)      "$PY" -m pip install --index-url "$TORCH_INDEX" "$TORCH" ;;
esac

echo "==> the rest"
# shellcheck disable=SC2086
"$PY" -m pip install $REST

echo "==> on-device scanner (about 500 MB)"
HF_HOME="$HERE/hf-cache" "$PY" - <<'PY'
import json, os, pathlib, sys
model = json.load(open("pins.json"))["model"]
from gliner import GLiNER
GLiNER.from_pretrained(model, map_location="cpu")
print("scanner cached")
sys.stdout.flush()
# hf_xet leaves non-daemon threads running after a download, which blocks interpreter
# shutdown for minutes. The cache is fully written by now, so leave without finalising.
os._exit(0)
PY

echo "==> electron"
npm install --silent

echo
echo "ready. start io with:  ./run.sh    (or: npm start)"
