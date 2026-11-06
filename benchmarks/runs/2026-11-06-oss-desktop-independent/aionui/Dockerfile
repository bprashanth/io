# AionUi 2.2.2 (linux arm64 .deb from static.aionui.com, sha512 matches latest-linux-arm64.yml)
# headless WebUI (Electron under Xvfb), plus IO's pinned Codex CLI and Claude Code 2.1.319.
FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends xvfb xauth ca-certificates python3 procps libgbm1 libnss3 libasound2 libgtk-3-0 libxss1 libxkbcommon0 libdrm2 libatk-bridge2.0-0 libcups2 dbus-x11 \
    && rm -rf /var/lib/apt/lists/*
COPY AionUi-2.2.2-linux-arm64.deb /tmp/aionui.deb
RUN apt-get update && apt-get install -y --no-install-recommends /tmp/aionui.deb \
    && rm -rf /var/lib/apt/lists/* /tmp/aionui.deb
COPY codex /opt/codex
RUN ln -s /opt/codex/bin/codex /usr/local/bin/codex && ln -s /opt/codex/codex-path/rg /usr/local/bin/rg \
    && npm install -g @anthropic-ai/claude-code@2.1.319 && npm cache clean --force
# node image already has uid 1000 "node"
USER node
WORKDIR /home/node
ENV HOME=/home/node
EXPOSE 25808
CMD ["xvfb-run","--auto-servernum","--server-args=-screen 0 1600x1000x24","/opt/AionUi/AionUi","--webui","--remote","--no-sandbox"]
