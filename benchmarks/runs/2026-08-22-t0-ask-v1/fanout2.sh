#!/bin/bash
# parallel version: one job per (model, suite), 8 at a time
cd /home/beeps/src/github.com/bprashanth/io
O=benchmarks/runs/2026-08-22-t0-ask-v1
MODELS="google/gemma-3-12b-it google/gemma-3n-e4b-it google/gemma-4-26b-a4b-it qwen/qwen3.6-35b-a3b qwen/qwen3.5-35b-a3b openai/gpt-oss-20b mistralai/ministral-8b-2512 mistralai/ministral-14b-2512 meta-llama/llama-3.1-8b-instruct ibm-granite/granite-4.1-8b nvidia/nemotron-3-nano-30b-a3b microsoft/phi-4 qwen/qwen3.5-27b google/gemini-3.7-flash"
run() { m=$1; s=$2; tag=$(basename $s .json | sed 's/query-//'); slug=$(echo $m | tr '/' '_')
  [ -f $O/$slug/$tag/result.json ] && return
  eff=none; case $m in openai/gpt-oss-20b|google/gemini-3.7-flash) eff=low;; esac
  .venv-v2/bin/python benchmarks/scripts/run_v2_query_gate.py --manifest $s --model $m \
    --endpoint https://openrouter.ai/api/v1 --api-key-file ~/.config/idlisseus/openrouter.json \
    --reasoning-effort $eff --prompt-style shell --timeout-seconds 120 --output $O/$slug/$tag > $O/$slug.$tag.log 2>&1; }
n=0
for m in $MODELS; do for s in benchmarks/v2/query-holdout-v2.json benchmarks/v2/query-suite-v2.json; do
  run $m $s & n=$((n+1)); if [ $((n % 8)) -eq 0 ]; then wait; fi
done; done; wait; echo FANOUT2-DONE
