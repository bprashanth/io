#!/bin/bash
cd /home/beeps/src/github.com/bprashanth/io
O=benchmarks/runs/2026-08-22-t0-ask-v1
rm -rf $O/qwen_qwen3.5-9b/holdout-v2-io-quote $O/qwen_qwen3.5-9b/anchor-v1.1-io-quote
.venv-v2/bin/python benchmarks/scripts/run_v2_query_gate.py --manifest benchmarks/v2/query-holdout-v2.json --model qwen/qwen3.5-9b --endpoint https://openrouter.ai/api/v1 --api-key-file ~/.config/idlisseus/openrouter.json --reasoning-effort none --prompt-style io-quote --timeout-seconds 120 --output $O/qwen_qwen3.5-9b/holdout-v2-io-quote > $O/qwen_qwen3.5-9b.holdout-v2-io-quote.log 2>&1 &
.venv-v2/bin/python benchmarks/scripts/run_v2_query_gate.py --manifest benchmarks/v2/query-anchor-v1.1.json --model qwen/qwen3.5-9b --endpoint https://openrouter.ai/api/v1 --api-key-file ~/.config/idlisseus/openrouter.json --reasoning-effort none --prompt-style io-quote --timeout-seconds 120 --output $O/qwen_qwen3.5-9b/anchor-v1.1-io-quote > $O/qwen_qwen3.5-9b.anchor-v1.1-io-quote.log 2>&1 &
wait
