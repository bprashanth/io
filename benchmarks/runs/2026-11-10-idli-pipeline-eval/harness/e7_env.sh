#!/bin/bash
# Run the 9B benchmark's harness on this eval's link-first chats and E7 variants.
#   harness/e7_env.sh run.py --run e7 --models ... --variants e7-soft --scenarios held3
#   harness/e7_env.sh convo.py --model ... --variant e7-soft --scenario scenarios/held3.json --conv r01... --out x.json
HERE="$(cd "$(dirname "$0")" && pwd)"
EVAL="$(dirname "$HERE")"
B9="$(dirname "$EVAL")/2026-11-10-idli-9b"
export IDLI9B_VARIANTS="$EVAL/variants" IDLI9B_SCENARIOS="$EVAL/scenarios" IDLI9B_RESULTS="$EVAL/results"
export IDLI9B_TOTAL_SEPARATE=1 IDLI9B_TMP=${IDLI9B_TMP:-/tmp/claude-1000/pipe-eval/tmp}
mkdir -p "$IDLI9B_TMP"
SCRIPT=$1; shift
exec /tmp/claude-1000/b9/sdkvenv/bin/python "$B9/harness/$SCRIPT" "$@"
