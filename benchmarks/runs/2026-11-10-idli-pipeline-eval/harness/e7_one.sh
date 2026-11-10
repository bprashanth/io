#!/bin/bash
# One E7 chat: harness/e7_one.sh <model> <variant> <scenario> <conv> [spec-model]
HERE="$(cd "$(dirname "$0")" && pwd)"
EVAL="$(dirname "$HERE")"
export PIPE_SPEC_MODEL=${5:-$1}
OUT="$EVAL/results/smoke/$4.$2.$1.json"
timeout 1200 "$HERE/e7_env.sh" convo.py --model "$1" --variant "$2" --scenario "$EVAL/scenarios/$3.json" --conv "$4" --out "$OUT"
python3 "$HERE/show_trace.py" "$OUT" | cut -c1-260
