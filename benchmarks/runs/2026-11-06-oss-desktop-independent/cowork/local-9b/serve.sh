#!/bin/sh
# Qwen3.5-9B Q4_K_M (CPU flags as used on the laptop; on the DGX use the cuda image and -ngl 999), Anthropic-compatible on 127.0.0.1:8282, for the cowork-9b provider.
# Model: https://huggingface.co/unsloth/Qwen3.5-9B-GGUF (Qwen3.5-9B-Q4_K_M.gguf) in ~/models.
# The patched template renders mid-conversation system messages instead of raising (Claude Code sends them).
cp "$(dirname "$0")/qwen35-midsystem.jinja" ~/models/templates/ 2>/dev/null || { mkdir -p ~/models/templates && cp "$(dirname "$0")/qwen35-midsystem.jinja" ~/models/templates/; }
docker run -d --name cowork-q9b --network host -v "$HOME/models:/models:ro" ghcr.io/ggml-org/llama.cpp:server \
  -m /models/Qwen3.5-9B-Q4_K_M.gguf --alias qwen3.5-9b -t 11 -c 49152 -np 1 -b 1024 -ub 512 \
  --host 127.0.0.1 --port 8282 --jinja --chat-template-file /models/templates/qwen35-midsystem.jinja \
  -fa on --cache-type-k q8_0 --cache-type-v q8_0 --chat-template-kwargs '{"enable_thinking":false}'
# Claude Code config for the provider: ~/.claude-t4gc-9b/settings.json = the T4GC one with
# ANTHROPIC_BASE_URL=http://127.0.0.1:8282 and every model name set to qwen3.5-9b.
