#!/bin/bash
# Ask-lane fan-out: every candidate, shell prompt (known categories), thinking off.
cd /home/beeps/src/github.com/bprashanth/io
OUT=benchmarks/runs/2026-08-22-t0-ask-v1
MODELS="qwen/qwen3.5-9b qwen/qwen3-8b qwen/qwen3-14b google/gemma-3-12b-it google/gemma-3n-e4b-it google/gemma-4-26b-a4b-it qwen/qwen3.6-35b-a3b qwen/qwen3.5-35b-a3b openai/gpt-oss-20b mistralai/ministral-8b-2512 mistralai/ministral-14b-2512 meta-llama/llama-3.1-8b-instruct ibm-granite/granite-4.1-8b nvidia/nemotron-3-nano-30b-a3b microsoft/phi-4 qwen/qwen3.5-27b google/gemini-3.7-flash"
SUITES="${SUITES:-benchmarks/v2/query-holdout-v2.json benchmarks/v2/query-suite-v2.json}"
for m in ${MODELS_OVERRIDE:-$MODELS}; do
  for s in $SUITES; do
    tag=$(basename $s .json | sed 's/query-//'); slug=$(echo $m | tr '/' '_')
    [ -f $OUT/$slug/$tag/result.json ] && continue
    .venv-v2/bin/python benchmarks/scripts/run_v2_query_gate.py --manifest $s --model $m \
      --endpoint https://openrouter.ai/api/v1 --api-key-file ~/.config/idlisseus/openrouter.json \
      --reasoning-effort none --prompt-style shell --timeout-seconds 120 \
      --output $OUT/$slug/$tag > $OUT/$slug.$tag.log 2>&1 &
  done
  wait
done
echo FANOUT-DONE
