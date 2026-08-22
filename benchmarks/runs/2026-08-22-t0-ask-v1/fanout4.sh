#!/bin/bash
# anchor-v1 (FW task now order-insensitive) with the io prompt style, top candidates + references
cd /home/beeps/src/github.com/bprashanth/io
O=benchmarks/runs/2026-08-22-t0-ask-v1
MODELS="qwen/qwen3.5-9b google/gemma-4-26b-a4b-it qwen/qwen3.6-35b-a3b qwen/qwen3.5-35b-a3b mistralai/ministral-8b-2512 mistralai/ministral-14b-2512 openai/gpt-oss-20b ibm-granite/granite-4.1-8b qwen/qwen3.5-27b google/gemini-3.7-flash"
run() { m=$1; slug=$(echo $m | tr '/' '_'); tag=anchor-v1-io
  [ -f $O/$slug/$tag/result.json ] && return
  eff=none; case $m in openai/gpt-oss-20b|google/gemini-3.7-flash) eff=low;; esac
  .venv-v2/bin/python benchmarks/scripts/run_v2_query_gate.py --manifest benchmarks/v2/query-anchor-v1.json --model $m \
    --endpoint https://openrouter.ai/api/v1 --api-key-file ~/.config/idlisseus/openrouter.json \
    --reasoning-effort $eff --prompt-style io --timeout-seconds 120 --output $O/$slug/$tag > $O/$slug.$tag.log 2>&1; }
for m in $MODELS; do run $m & done; wait; echo FANOUT4-DONE
