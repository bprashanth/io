#!/bin/sh
# Launcher for Paseo provider idli-teach: Claude Code for teaching, run in this cowork/ folder (fake data, file skills)
# whatever workspace the chat sits in. In split mode the teaching chat lives in Idli's workspace, next to Idli
# (Paseo patches P13/P14), and Paseo would start it in Idli's private folder; this keeps Claude here.
# Checked on the DGX with Paseo 0.15.2 (todos/idli-insights/p1/split_panel.md).
cd "$(dirname "$0")/.." || exit 1
CLAUDE_BIN=${CLAUDE_BIN:-$(command -v claude || echo "$HOME/.local/bin/claude")}
exec "$CLAUDE_BIN" "$@"
