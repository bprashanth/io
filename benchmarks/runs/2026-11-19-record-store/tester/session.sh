#!/bin/bash
# session.sh NAME WORLD(leads|insights|diy) PERSONA MAPPER(remote|nine) PORT
set -euo pipefail
T=$(dirname "$(realpath "$0")"); NAME=$1; WORLD=$2; PERSONA=$3; MAPPER=$4; PORT=$5
RUN=${RS_RUN:-/tmp/rs}; mkdir -p "$RUN/$NAME/work"
# each session gets its own copy of the store (DuckDB allows one writer per file)
rm -rf "$RUN/$NAME/sbx"; cp -r "${RS_BASE:?set RS_BASE to the synced sandbox}" "$RUN/$NAME/sbx"; export IDLI_SANDBOX="$RUN/$NAME/sbx"
PY="$T/../../2026-11-06-oss-desktop-independent/cowork/.venv/bin/python"
"$PY" "$T/serve.py" --port "$PORT" --mapper "$MAPPER" --log "$RUN/$NAME/turns.jsonl" > "$RUN/$NAME/serve.out" 2>&1 &
SP=$!; trap 'kill $SP 2>/dev/null || true' EXIT
for i in $(seq 1 60); do grep -q serving "$RUN/$NAME/serve.out" 2>/dev/null && break; sleep 2; done
cat "$T/prompts/persona-$PERSONA.txt" "$T/prompts/$WORLD.txt" "$T/prompts/common.txt" > "$RUN/$NAME/prompt.txt"
cd /tmp && timeout 3000 "$T/../../2026-11-19-blind-tester/wall.sh" "$RUN/$NAME/work" "$PORT" "$RUN/$NAME/prompt.txt" > "$RUN/$NAME/tester.jsonl" 2> "$RUN/$NAME/tester.err" || true
echo "done $NAME"
