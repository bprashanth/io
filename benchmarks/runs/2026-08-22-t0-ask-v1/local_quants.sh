#!/bin/bash
# Apples-to-apples quant check: Q4_K_M then Q5_K_M, shell prompt, thinking off, CPU 8 threads, no memory cap.
cd /home/beeps/src/github.com/bprashanth/io
N=benchmarks/runs/2026-08-22-t0-ask-v1
run_quant() { q=$1; dir=$2
  docker rm -f io-q9b >/dev/null 2>&1
  docker run -d --name io-q9b --cpus 8 -p 8020:8080 -v /mnt/seagate/io-models/Qwen3.5-9B-GGUF:/models ghcr.io/ggml-org/llama.cpp:server-cuda13 -m /models/Qwen3.5-9B-$q.gguf -ngl 0 -t 8 -c 6144 -b 256 -ub 256 --host 0.0.0.0 --port 8080 --jinja -fa on --cache-type-k q8_0 --cache-type-v q8_0 >/dev/null
  for i in $(seq 1 60); do curl -sf localhost:8020/health >/dev/null && break; sleep 2; done
  mkdir -p $N/$dir
  .venv-v2/bin/python benchmarks/scripts/run_v2_query_gate.py --manifest benchmarks/v2/query-holdout-v2.json --model local --endpoint http://127.0.0.1:8020/v1 --prompt-style shell --no-think-template --timeout-seconds 400 --output $N/$dir/holdout-v2-shell > $N/$dir/holdout-shell.log 2>&1
}
# Q4 done in the first invocation
while [ ! -s /mnt/seagate/io-models/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q5_K_M.gguf ] || [ $(stat -c %s /mnt/seagate/io-models/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q5_K_M.gguf) -lt 6570000000 ]; do sleep 10; done
run_quant Q5_K_M local_qwen3.5-9b-q5km-cpu8
echo QUANTS-DONE >> $N/local_qwen3.5-9b-q5km-cpu8/holdout-shell.log
