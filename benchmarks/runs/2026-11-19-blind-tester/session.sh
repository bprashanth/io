#!/bin/bash
# One blind session: a harness (the app's chat on the real test accounts) plus the walled tester.
#   session.sh <name> <world: leads|insights> <persona> <mapper: remote|nine> <port>
set -euo pipefail
B=$(dirname "$(realpath "$0")")
NAME=$1; WORLD=$2; PERSONA=$3; MAPPER=$4; PORT=$5
RUN=${BT_RUN:-/tmp/bt}; mkdir -p "$RUN/$NAME" "$B/results"
PY="$B/../2026-11-06-oss-desktop-independent/cowork/.venv/bin/python"
"$PY" "$B/harness.py" serve --port "$PORT" --mapper "$MAPPER" --world "$WORLD" --data "$RUN/$NAME/sandbox" \
  --log "$RUN/$NAME/turns.jsonl" > "$RUN/$NAME/harness.out" 2>&1 &
HP=$!
trap 'kill $HP 2>/dev/null || true' EXIT
for i in $(seq 1 60); do grep -q serving "$RUN/$NAME/harness.out" 2>/dev/null && break; kill -0 $HP 2>/dev/null || break; sleep 2; done
grep -q serving "$RUN/$NAME/harness.out" || { echo "harness did not start: $NAME"; exit 1; }
cat "$B/prompts/persona-$PERSONA.txt" "$B/prompts/$WORLD.txt" "$B/prompts/common.txt" > "$RUN/$NAME/prompt.txt"
mkdir -p "$RUN/$NAME/work"
cd /tmp && timeout 3600 "$B/wall.sh" "$RUN/$NAME/work" "$PORT" "$RUN/$NAME/prompt.txt" > "$RUN/$NAME/tester.jsonl" 2> "$RUN/$NAME/tester.err" || true
echo "done $NAME"
