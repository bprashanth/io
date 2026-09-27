# Build from app/io: docker build -f remote/Dockerfile --build-arg CODEX_TARGET=linux-arm64 .
FROM node:22-bookworm@sha256:0557ac14e0d45d02ed563067b82856ca5e7aa3437fa28d98d4350ea9c3d9494a
ARG CODEX_TARGET
COPY codex-bin/${CODEX_TARGET}/ /opt/codex/
COPY codex.js codex-pins.json /opt/io/
COPY remote/config.js remote/worker.py remote/conformance.py /opt/remote/
COPY tests/sandbox/probe.py /opt/remote/probe.py
RUN ln -s /opt/codex/bin/codex /usr/local/bin/codex-linux-sandbox \
 && mkdir /state /workspace && chown 1000:1000 /state /workspace \
 && /opt/codex/bin/codex --version
USER 1000:1000
ENV HOME=/state CODEX_HOME=/state/codex PATH=/opt/codex/bin:/usr/local/bin:/usr/bin:/bin
WORKDIR /workspace
EXPOSE 8787
CMD ["python3", "/opt/remote/worker.py"]
