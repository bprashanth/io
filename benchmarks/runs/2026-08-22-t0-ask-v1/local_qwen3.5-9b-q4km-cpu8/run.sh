#!/bin/bash
# Qwen3.5-9B Q4_K_M, llama.cpp CPU-only, 8 threads, -c 6144 -b 256 -ub 256, q8 KV, thinking off via chat template. No memory cap (peak RSS measured 5.6 GiB).
cd /home/beeps/src/github.com/bprashanth/io
.venv-v2/bin/python benchmarks/scripts/run_v2_query_gate.py --manifest benchmarks/v2/query-holdout-v2.json --model local --endpoint http://127.0.0.1:8020/v1 --prompt-style io --no-think-template --timeout-seconds 400 --output benchmarks/runs/2026-08-22-t0-ask-v1/local_qwen3.5-9b-q4km-cpu8/holdout-v2-io > benchmarks/runs/2026-08-22-t0-ask-v1/local_qwen3.5-9b-q4km-cpu8/holdout.log 2>&1
.venv-v2/bin/python benchmarks/scripts/run_v2_query_gate.py --manifest benchmarks/v2/query-anchor-v1.1.json --model local --endpoint http://127.0.0.1:8020/v1 --prompt-style io --no-think-template --timeout-seconds 400 --output benchmarks/runs/2026-08-22-t0-ask-v1/local_qwen3.5-9b-q4km-cpu8/anchor-v1.1-io > benchmarks/runs/2026-08-22-t0-ask-v1/local_qwen3.5-9b-q4km-cpu8/anchor.log 2>&1
echo LOCAL-DONE >> benchmarks/runs/2026-08-22-t0-ask-v1/local_qwen3.5-9b-q4km-cpu8/anchor.log
