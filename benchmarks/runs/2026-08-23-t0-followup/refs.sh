#!/bin/bash
# References the first pass missed: Qwen 3.8 27B (the standing T1 winner) on all suites + build; Arctic 7B Q8 (GPU) on ask suites.
cd /home/beeps/src/github.com/bprashanth/io
O=benchmarks/runs/2026-08-23-t0-followup; K=~/.config/idlisseus/openrouter.json
for s in query-suite-v2 query-holdout-v2 query-anchor-v1.1; do tag=${s#query-}
  .venv-v2/bin/python benchmarks/scripts/run_v2_query_gate.py --manifest benchmarks/v2/$s.json --model qwen/qwen3.8-27b --endpoint https://openrouter.ai/api/v1 --api-key-file $K --reasoning-effort none --prompt-style shell --timeout-seconds 120 --output $O/qwen3.8-27b/$tag > $O/qwen3.8-27b.$tag.log 2>&1 &
done
.venv-v2/bin/python benchmarks/t0/run_build_gate.py --model qwen/qwen3.8-27b --api-key-file $K --reasoning-effort none --output $O/qwen3.8-27b/build-v1 > $O/qwen3.8-27b.build.log 2>&1 &
docker rm -f io-arctic >/dev/null 2>&1
docker run -d --name io-arctic --gpus all -v /mnt/seagate/io-models/Arctic-Text2SQL-R1-7B-GGUF-Q8_0:/models:ro -p 127.0.0.1:8022:8080 ghcr.io/ggml-org/llama.cpp:server-cuda13 -m /models/$(ls /mnt/seagate/io-models/Arctic-Text2SQL-R1-7B-GGUF-Q8_0 | grep gguf | head -1) --host 0.0.0.0 --port 8080 --ctx-size 8192 --parallel 1 --gpu-layers 99 --jinja >/dev/null
for i in $(seq 1 90); do curl -sf localhost:8022/health >/dev/null && break; sleep 2; done
for s in query-holdout-v2 query-anchor-v1.1; do tag=${s#query-}
  .venv-v2/bin/python benchmarks/scripts/run_v2_query_gate.py --manifest benchmarks/v2/$s.json --model arctic --endpoint http://127.0.0.1:8022/v1 --prompt-style shell --timeout-seconds 300 --output $O/arctic-7b-q8/$tag > $O/arctic-7b-q8.$tag.log 2>&1
done
wait; echo REFS-DONE
