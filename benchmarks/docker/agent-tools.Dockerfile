FROM python:3.12.11-slim-bookworm

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        file \
        jq \
        nodejs \
        npm \
        poppler-utils \
        procps \
        ripgrep \
        unzip \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir \
        beautifulsoup4==4.13.4 \
        openpyxl==3.1.5 \
        pypdf==5.9.0 \
        requests==2.32.4

RUN useradd --create-home --uid 1000 --shell /bin/bash benchmark

USER benchmark
WORKDIR /workspace
