#!/bin/sh
# Local 9B servers for the benchmark (llama.cpp, OpenAI- and Anthropic-compatible), on the DGX next to Muse.
# Obeys ~/src/github.com/bprashanth/GPU_COORDINATION.md: refuses below 40 GB available, bounded context,
# containers named idli9b-*. Thinking is off (as Idli's local-9b/serve.sh runs it); the template is
# local-9b's, which renders mid-conversation system messages (Claude Code sends them).
#   serve.sh raw|lora004d|lora003 [up|down]
set -e
M=/mnt/seagate/io-models
T=$(dirname "$0")/../2026-11-06-oss-desktop-independent/cowork/local-9b/qwen35-midsystem.jinja
mkdir -p $M/idli9b-bench/templates && cp "$T" $M/idli9b-bench/templates/
case "$1" in
  raw)      F=Qwen3.5-9B-GGUF/Qwen3.5-9B-Q5_K_M.gguf; A=qwen3.5-9b; P=8291 ;;
  lora004d) F=idli9b-bench/merged-9b-004d-Q8_0.gguf;   A=lora-9b-004d; P=8292 ;;
  lora003)  F=idli9b-bench/merged-9b-003-Q8_0.gguf;    A=lora-9b-003;  P=8293 ;;
  *) echo "usage: serve.sh raw|lora004d|lora003 [up|down]"; exit 2 ;;
esac
if [ "$2" = down ]; then docker rm -f idli9b-$1 >/dev/null 2>&1 || true; echo "stopped idli9b-$1"; exit 0; fi
avail=$(free -g | awk 'NR==2{print $7}')
[ "$avail" -ge 40 ] || { echo "only ${avail}G available (want >= 40): not starting"; exit 1; }
docker run -d --name idli9b-$1 --gpus all --network host --memory 24g -v $M:/m:ro ghcr.io/ggml-org/llama.cpp:server-cuda13 \
  -m /m/$F --alias $A -ngl 999 -c 65536 -np 2 --host 127.0.0.1 --port $P --jinja \
  --chat-template-file /m/idli9b-bench/templates/qwen35-midsystem.jinja --chat-template-kwargs '{"enable_thinking":false}' \
  -fa on --cache-type-k q8_0 --cache-type-v q8_0
echo "idli9b-$1 on 127.0.0.1:$P"
