#!/bin/bash
# One-time setup for io desktop (Linux/macOS). Needs python3 (3.10+) and node (18+).
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet duckdb pandas openpyxl sqlglot esprima
npm install --silent
echo "Done. Start with: npm start"
