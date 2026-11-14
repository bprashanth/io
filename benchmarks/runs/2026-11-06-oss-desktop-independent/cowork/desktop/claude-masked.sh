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
# Project skills travel with this work folder, including their local chart templates.
mkdir -p "$WORK/.claude/skills" || exit 1
for skill in "$COWORK"/idli/claude-skills/*; do
  [ -d "$skill" ] || continue
  cp -R "$skill" "$WORK/.claude/skills/" || exit 1
done
# Idli's local server too (Idli home, charts, Minis): Drivey's "+" opens Idli home beside this terminal
(cd "$COWORK" && "$COWORK/.venv/bin/python" -I -c "import sys; sys.path.insert(0, '.'); from lib import formserver, drivestubs; formserver.ensure(sys.argv[1]); drivestubs.refresh(sys.argv[1])" "$DATA") >/dev/null 2>&1 || true
PORT=$("$COWORK/.venv/bin/python" -I "$COWORK/lib/ccproxy.py" ensure --data-dir "$DATA") || {
  echo "Idli's privacy proxy didn't start; not starting Claude (nothing was sent)." >&2; exit 1; }
# Pass the workspace explicitly so the MCP can find its left chat.
export IDLI_DATA="$DATA" IDLI_CLAUDE_WORK="$WORK"
"$COWORK/.venv/bin/python" -I - "$COWORK" "$WORK/.idli-mcp.json" <<'PYCONFIG'
import json, os, sys
root, target = sys.argv[1:]
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, 'w') as f:
    json.dump({'mcpServers': {'idli': {'command': root + '/.venv/bin/python',
               'args': ['-I', root + '/lib/idli_mcp.py'],
               'env': {k: os.environ[k] for k in ('IDLI_WORKSPACE', 'IDLI_AUTHOR', 'IDLI_DATA', 'IDLI_CLAUDE_WORK')
                       if k in os.environ}}}}, f)
PYCONFIG
if [ "$?" -ne 0 ]; then exit 1; fi
# Idli's own folder for Claude: answer Claude Code's one-time "do you trust this folder?" the way the person would
# (the same entry Claude writes when they pick "Yes, I trust this folder"), so the first question isn't blocked.
python3 - "$WORK" <<'PY' 2>/dev/null || true
import json, os, sys
p = os.path.expanduser("~/.claude.json")
if os.path.exists(p):
    c = json.load(open(p))
    e = c.setdefault("projects", {}).setdefault(os.path.realpath(sys.argv[1]), {})
    if not e.get("hasTrustDialogAccepted"):
        e["hasTrustDialogAccepted"] = True
        json.dump(c, open(p + ".idli-tmp", "w"), indent=2)
        os.replace(p + ".idli-tmp", p)
PY
cd "$WORK" || exit 1
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN CLAUDE_CONFIG_DIR
export ANTHROPIC_BASE_URL="http://127.0.0.1:$PORT"
CLAUDE_BIN=${CLAUDE_BIN:-$(command -v claude || echo "$HOME/.local/bin/claude")}
# --mcp-config takes several files, so give it as one --flag=value: a prompt after it would be read as another file
exec "$CLAUDE_BIN" "--mcp-config=$WORK/.idli-mcp.json" "$@"
