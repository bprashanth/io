#!/bin/bash
# Run Cursor's `agent` as the blind tester inside a bwrap wall (test harness only, not product).
# It sees: an empty work folder holding only `ask`, a throwaway HOME with its sign-in, its own install, and the
# system (read-only). Not the repo, not this folder, not ~/.config/idlisseus.
#   wall.sh <work-dir> <port> <prompt-file> [model]
set -euo pipefail
WORK=$(realpath "$1"); PORT=$2; PROMPT=$(cat "$3"); MODEL=${4:-}
AGENT_DIR=$(dirname "$(readlink -f "$HOME/.local/bin/agent")")
FAKE=$(mktemp -d); mkdir -p "$FAKE/.config/cursor" "$FAKE/.cursor"
cp "$HOME/.config/cursor/auth.json" "$FAKE/.config/cursor/"
python3 - "$HOME/.cursor/cli-config.json" "$FAKE/.cursor/cli-config.json" <<'PY'
import json, sys
c = json.load(open(sys.argv[1]))
keep = {k: c[k] for k in ('version', 'model', 'selectedModel', 'authInfo', 'privacyCache', 'serverConfigCache') if k in c}
keep['permissions'] = {'allow': ['Shell(./ask)', 'Shell(ask)'], 'deny': []}
json.dump(keep, open(sys.argv[2], 'w'))
PY
cat > "$WORK/ask" <<PY
#!/usr/bin/env python3
"""ask "your question": asks the app's chat and prints its reply."""
import json, sys, urllib.request
q = ' '.join(sys.argv[1:])
req = urllib.request.Request('http://127.0.0.1:$PORT/ask', json.dumps({'q': q}).encode(), {'Content-Type': 'application/json'})
print(urllib.request.urlopen(req, timeout=900).read().decode())
PY
chmod +x "$WORK/ask"
ARGS=(-p --force --trust --sandbox disabled --output-format stream-json --workspace /work)
[ -n "$MODEL" ] && ARGS+=(--model "$MODEL")
exec bwrap --unshare-all --share-net --die-with-parent \
  --ro-bind /usr /usr --symlink usr/bin /bin --symlink usr/sbin /sbin --symlink usr/lib /lib \
  $( [ -e /lib64 ] && echo --symlink usr/lib64 /lib64 ) \
  --ro-bind /etc /etc --ro-bind-try /run/systemd/resolve /run/systemd/resolve --proc /proc --dev /dev --tmpfs /tmp \
  --ro-bind "$AGENT_DIR" "$AGENT_DIR" \
  --bind "$FAKE" /home/tester --setenv HOME /home/tester --setenv PATH "$AGENT_DIR:/work:/usr/bin:/bin" \
  --bind "$WORK" /work --chdir /work \
  "$AGENT_DIR/cursor-agent" "${ARGS[@]}" "$PROMPT"
