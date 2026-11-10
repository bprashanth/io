#!/bin/sh
# The local 9B (Qwen3.5-9B Q5_K_M) for E7, as the 9B benchmark's serve.sh raw, but 4 slots of 16k (64k context) so
# 4 chats run at once. GPU_COORDINATION.md: refuses below 40 GB available; container idli9b-raw.
#   serve9b.sh [up|down]
set -e
M=/mnt/seagate/io-models
if [ "$1" = down ]; then docker rm -f idli9b-raw >/dev/null 2>&1 || true; echo stopped; exit 0; fi
avail=$(free -g | awk 'NR==2{print $7}')
[ "$avail" -ge 40 ] || { echo "only ${avail}G available (want >= 40): not starting"; exit 1; }
docker run -d --name idli9b-raw --gpus all --network host --memory 24g -v $M:/m:ro \
  ghcr.io/ggml-org/llama.cpp:server-cuda13 \
  -m /m/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q5_K_M.gguf --alias qwen3.5-9b -ngl 999 -c 65536 -np 4 --host 127.0.0.1 \
  --port 8291 --jinja --chat-template-file /m/idli9b-bench/templates/qwen35-midsystem.jinja \
  --chat-template-kwargs '{"enable_thinking":false}' -fa on --cache-type-k q8_0 --cache-type-v q8_0
echo "idli9b-raw on 127.0.0.1:8291 (4 slots)"
