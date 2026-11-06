# Paseo 0.15.2 daemon + bundled web UI, plus IO's pinned Codex and Claude Code.
# Build context holds ./codex = app/io/codex-bin/linux-arm64 (node app/io/fetch-codex.js linux-arm64).
FROM ghcr.io/getpaseo/paseo:0.15.2@sha256:e12414fe71f33aa7cedf1eaf027bf2acfccdf01d6b692ba779a220b2ec1c46e6
USER root
COPY codex /opt/codex
RUN ln -s /opt/codex/bin/codex /usr/local/bin/codex \
 && ln -s /opt/codex/codex-path/rg /usr/local/bin/rg \
 && npm install -g @anthropic-ai/claude-code@2.1.319 \
 && npm cache clean --force \
 && apt-get update && apt-get install -y --no-install-recommends python3 && rm -rf /var/lib/apt/lists/*
