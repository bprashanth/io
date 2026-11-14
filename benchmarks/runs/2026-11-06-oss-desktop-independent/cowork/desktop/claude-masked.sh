#!/bin/sh
# Launcher for Paseo provider idli-claude: the person's own Claude Code (their subscription login), with every request
# going through Idli's masking proxy (lib/ccproxy.py). Claude works on the real files in ~/idli-insights/claude-masked
# (drive/ links to Drivey's downloads); the proxy turns the values of masked columns into codes on the way out and back
# into real values on the way in, so the person sees real values and Anthropic sees codes.
COWORK="$(cd "$(dirname "$0")/.." && pwd)"
DATA=${IDLI_DATA:-$HOME/idli-insights/cowork-real}
WORK=${IDLI_CLAUDE_WORK:-$HOME/idli-insights/claude-masked}
mkdir -p "$WORK"
ln -sfn "$DATA/drive" "$WORK/drive"
cp "$COWORK/idli/CLAUDE-masked.md" "$WORK/CLAUDE.md"
PORT=$("$COWORK/.venv/bin/python" -I "$COWORK/lib/ccproxy.py" ensure --data-dir "$DATA") || {
  echo "Idli's privacy proxy didn't start; not starting Claude (nothing was sent)." >&2; exit 1; }
cd "$WORK" || exit 1
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN CLAUDE_CONFIG_DIR
export ANTHROPIC_BASE_URL="http://127.0.0.1:$PORT"
CLAUDE_BIN=${CLAUDE_BIN:-$(command -v claude || echo "$HOME/.local/bin/claude")}
exec "$CLAUDE_BIN" "$@"
