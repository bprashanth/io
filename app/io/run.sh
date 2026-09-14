#!/usr/bin/env bash
# Double-click me. First run sets things up, after that it just opens.
cd "$(dirname "$0")"
[ -d .venv ] || ./install.sh
[ -d node_modules ] || npm install --silent
# a dependency added since the last install (node-pty, for the Codex terminal)
node -e "require.resolve('node-pty')" 2>/dev/null || npm install --silent
# the Codex io ships (pinned in codex-pins.json); needed for "Sign in with ChatGPT"
[ -x "codex-bin/$(node -p 'process.platform + "-" + process.arch')/codex" ] || node fetch-codex.js
exec npm start
