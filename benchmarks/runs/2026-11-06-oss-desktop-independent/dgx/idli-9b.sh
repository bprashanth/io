#!/bin/sh
# The local 9B behind Idli's "Idli 9B" and "Steam powered" modes (cowork/lib/modes.py; the router in
# muse_prefix_proxy.py sends them to 127.0.0.1:8291). Qwen3.5-9B Q5_K_M, as in the 9B benchmark and E7, but 2 slots of
# 32k: a real chat's tool results outgrow E7's 16k slots (measured 16,421 tokens on the 4th question), and the second
# slot serves the split's spec call while the chat waits. ~10 GB. GPU_COORDINATION.md: refuses below 40 GB available.
#   idli-9b.sh [up|down|status]
M=${IDLI_MODELS:-/mnt/seagate/io-models}
case "${1:-up}" in
  down) docker rm -f idli-9b >/dev/null 2>&1; echo stopped ;;
  status) docker ps --filter name=^idli-9b$ --format '{{.Names}} {{.Status}}'; curl -s -m 3 http://127.0.0.1:8291/health; echo ;;
  up)
    docker ps -q --filter name=^idli-9b$ | grep -q . && { echo "already up"; exit 0; }
    avail=$(free -g | awk 'NR==2{print $7}')
    [ "$avail" -ge 40 ] || { echo "only ${avail}G available (want >= 40): not starting"; exit 1; }
    docker rm -f idli-9b >/dev/null 2>&1
    docker run -d --name idli-9b --restart unless-stopped --gpus all --network host --memory 24g -v "$M":/m:ro \
      ghcr.io/ggml-org/llama.cpp:server-cuda13 \
      -m /m/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q5_K_M.gguf --alias qwen3.5-9b -ngl 999 -c 65536 -np 2 --host 127.0.0.1 \
      --port 8291 --jinja --chat-template-file /m/idli9b-bench/templates/qwen35-midsystem.jinja \
      --chat-template-kwargs '{"enable_thinking":false}' -fa on --cache-type-k q8_0 --cache-type-v q8_0 >/dev/null &&
      echo "idli-9b on 127.0.0.1:8291 (2 slots of 32k)" ;;
esac
