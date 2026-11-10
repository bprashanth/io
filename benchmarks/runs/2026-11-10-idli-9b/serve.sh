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
  # ask-step (spec builder) models for the split: single-message prompts, their own GGUF chat templates
  q38)  F=/s/models/qwen38-27b/Qwen3.8-27B-UD-Q4_K_M.gguf;               A=qwen3.8-27b;  P=8294; OWN=1 ;;
  a35)  F=/s/models/idli9b-ask/Qwen3.5-35B-A3B-Q4_K_M.gguf;              A=qwen3.5-35b-a3b; P=8295; OWN=1 ;;
  nemo) F=/s/models/idli9b-ask/Nemotron-3.5-Lightning-30B-A3B-Q4_K_M.gguf; A=nemotron-3.5-lightning; P=8296; OWN=1 ;;
  *) echo "usage: serve.sh raw|lora004d|lora003|q38|a35|nemo [up|down]"; exit 2 ;;
esac
if [ "$2" = down ]; then docker rm -f idli9b-$1 >/dev/null 2>&1 || true; echo "stopped idli9b-$1"; exit 0; fi
avail=$(free -g | awk 'NR==2{print $7}')
[ "$avail" -ge 40 ] || { echo "only ${avail}G available (want >= 40): not starting"; exit 1; }
TPL="--chat-template-file /m/idli9b-bench/templates/qwen35-midsystem.jinja"
[ -n "$OWN" ] && TPL=""
docker run -d --name idli9b-$1 --gpus all --network host --memory 24g -v /mnt/seagate:/s:ro -v $M:/m:ro \
  ghcr.io/ggml-org/llama.cpp:server-cuda13 \
  -m $(case "$F" in /*) echo "$F";; *) echo "/m/$F";; esac) --alias $A -ngl 999 -c 32768 -np 2 --host 127.0.0.1 --port $P --jinja \
  $TPL --chat-template-kwargs '{"enable_thinking":false}' \
  -fa on --cache-type-k q8_0 --cache-type-v q8_0
echo "idli9b-$1 on 127.0.0.1:$P"
