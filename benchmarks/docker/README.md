# Agent tool image

Both measured agents run in the same outer image. It supplies ordinary tools a
Windows workshop installation can reasonably provide behind the editor:
Python, Node/npm, curl, jq, process inspection, ripgrep, unzip, PDF text
extraction, and pinned Python readers for Excel, PDF and HTML. Process
inspection was added after a v1 diagnostic showed that Antigravity could not
verify a background preview server without `ps` and then blocked on a
foreground server; that run is explicitly excluded.

Build and retain its immutable digest before a batch:

```sh
docker build -f benchmarks/docker/agent-tools.Dockerfile \
  -t io-benchmark-agent-tools:2026-08-20-v2 .
docker image inspect io-benchmark-agent-tools:2026-08-20-v2 \
  --format '{{.Id}} {{json .RepoDigests}}'
```

The image is an execution environment, not an agent prompt. Models may choose
any supplied tool or write dependency-free HTML. The generated application is
still evaluated in a separate read-only container without network access.

The built image ID and observed tool versions for the frozen batch live in
[`../config/agent-tools-image.json`](../config/agent-tools-image.json).
