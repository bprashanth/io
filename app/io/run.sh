#!/usr/bin/env bash
# Double-click me. First run sets things up, after that it just opens.
cd "$(dirname "$0")"
[ -d .venv ] || ./install.sh
[ -d node_modules ] || npm install --silent
exec npm start
