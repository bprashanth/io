# Agent handoff: evaluate an OSS desktop for Open + Private intelligence

## Task

Evaluate replacing IO's desktop scaffold with an existing open-source desktop client.
Research, recommend and build only the smallest isolated proof needed to establish
feasibility. Do not replace main IO, change the live gateway/model/tunnel or migrate
user state as part of the evaluation. Work on io_silo_untested or an isolated checkout.
Record exact revisions, commands, findings and evidence in chronology/benchmarks.

## Catch up first

IO repo: /home/beeps/src/github.com/bprashanth/io
- README.md final untested checkpoint and docs/execution-and-laptop-rollout.md (manual checklist).
- chronology/2026-11-06-main-publication.md and benchmarks/runs/2026-11-06-main-handoff/.
- app/io/gateway/README.md, desktop.js, server.py and runtime.py: current remote client,
  identity mapping and persistent per-user containers. app/io/remote/config.js and worker.py:
  current direct ChatGPT OAuth, Offline commands, conversation lifecycle.
- app/io/codex.js: local provider/profile settings. docs/sandboxing.md: actual contract.
- proposals/v1-remote-runtime-local-diagnostic.md for original scope.

Sibling Silo repo: /home/beeps/src/github.com/bprashanth/silo
- chronology/2026-10-11T1500-codex-drives-local-muse.md and its linked evidence.
- tg-bridge/serve_muse.sh and tg-bridge/io_config.js; README.md for orientation.
Read source, not credentials. Do not touch existing untracked IO docs/sandbox.md.

## Simplified product: exactly two user-facing modes

**Open:** desktop starts the user's local agent CLI (at least Codex and Claude Code),
using that CLI's normal subscription OAuth login. The person accepts local file/tools/
computer access and the provider's data handling. No IO-specific strong sandbox promise
is necessary for this mode. Preserve useful native permission prompts. Do not extract
OAuth tokens and turn them into general API keys or forward them to Idli.

**Private / on-Idli intelligence:** desktop reaches an authenticated Idli service;
inference runs on the model we host. The user explicitly trusts Idli with submitted data.
Use explicit-copy upload/work/download if execution moves to the server. No silent
third-party model fallback, no sending subscription OAuth to the hosted model, and no
claim that this means data stays on the laptop. Provider authentication for Open and
Idli authentication for Private are different mechanisms.

Determine TWO architectures separately before selecting the minimum implementation:
A. Local agent + Idli-hosted inference: configure its provider URL/model; tools still
   execute on the laptop. Label this honestly; it is not a remote execution silo.
B. Desktop remote environment + agent/tools/workspace on Idli + Idli-hosted inference:
   stronger match for keeping both execution and intelligence on Idli. Reuse upstream
   remote-environment support where possible; preserve per-user isolation, rather than
   sharing a single privileged daemon among unrelated users.
Default preference for Private is B, but report the extra work versus A rather than
assuming endpoint redirection alone moves command execution.

## Required capabilities

- Windows, macOS (Intel/ARM) and Linux desktop; distinguish native support from WSL.
- Multiple agent CLIs, especially Codex and Claude Code; native subscription OAuth in Open.
- Minimal provider/base-URL/model or remote-environment configuration for Private.
- Streaming text/tools/stdout/stderr, interruption, multi-turn resume, file attachments,
  generated downloads and sensible handling of expired login/disconnection.
- Usable for NGO/non-developer tasks such as CSV analysis, without requiring Git projects.
- OSS license permitting adaptation and redistribution; measure actual patch size and
  maintenance cost. Free client does not make subscription/compute free.
- Private mode must account for telemetry, title generation, embedding/search, plugins,
  auxiliary models and cloud relays; disable or route them explicitly and verify egress.

## Candidates and research request

Start with https://github.com/pingdotgg/t3code / https://t3.codes/.
Do not assume it is best. Compare at least Paseo (https://github.com/getpaseo/paseo)
and Happy (https://github.com/slopus/happy plus happy-desktop/happy-agent), and search
for a better current OSS alternative. Exclude pure API chat UIs if they cannot drive
real Codex AND Claude Code using the users' normal logins. Distinguish documented,
source-confirmed and behaviorally demonstrated capabilities.

Read upstream provider, installation, remote access, telemetry and licensing docs;
pin a commit/release. T3 inspection on Nov6 found HEAD
6577c6b6185167c0e502fa01f9e8e8f2dee6ff25. Docs describe Codex login, Claude
configuration/environment overrides, remote environments and all three desktop OSes.
T3 telemetry must be evaluated/disabled (`T3CODE_TELEMETRY_ENABLED=false`). Its
Muse Code provider must NOT be assumed to be our llama.cpp Muse-Glimmer endpoint.
Paseo documents a local/remote daemon and provider/lifecycle plugins; Happy documents
subscription reuse and separate desktop/agent/relay repositories. These are research
leads, not tested integration claims.

## Idli endpoint and existing model

Owner confirmed https://io.idli.cc for the new Private path (earlier idli.io.cc was a typo).
This hostname already serves IO; do not replace its route or change Access policy for
an experiment without preserving the existing service. Verify requested ownership/routing/TLS/Access
before any external test. Existing IO gateway is localhost8789, not a model API.

On Nov6, read-only checks found idli-muse running, /health status ok and
/v1/models listing muse-glimmer-30b at http://127.0.0.1:8181 (llama.cpp).
No new generation test was run in this evaluation. Silo's Oct11 evidence shows
Codex0.162.1 using a custom Responses provider at /v1/responses successfully for
workbook analysis, with model-metadata fallback and excessive tool calls. This is
not IO's pinned0.154.0 qualification or proof of T3 integration. Benchmark latency,
tool use and correctness; don't assume all OpenAI-compatible APIs are equivalent.

Prefer the real hosted model. A local deterministic mock can prove transport only.
OpenRouter can be an explicit non-private development comparison, never evidence
that private data remains on Idli. No need to read/use an OpenRouter secret merely
because one exists. Never commit credentials, auth caches or user files.

A hostname redirect is insufficient: identify the exact client/agent protocol
(Responses, Chat Completions, Anthropic Messages, app-server, ACP or WebSocket),
streaming/tool-call semantics and authentication. Adapt protocols only if necessary.
Cloudflare browser login cannot be assumed to work in a CLI HTTP client. Explain
how desktop authentication reaches HTTPS/WebSocket/model requests without distributing
shared administrative credentials, and how tenant/workspace ownership is enforced.

## Deliverables / evidence

1. Comparison table: OS/architecture, Codex+Claude login, local/remote execution,
   endpoint customization, uploads/downloads, license, telemetry, minimum patch.
2. Recommendation with concrete reasons and unresolved tests, including “no suitable
   replacement” if that is what the evidence supports.
3. Small isolated demo: Open native CLI login, Private real Muse via Idli runtime or
   clearly labelled inference-only routing, streamed response/tool execution, CSV
   upload/analyze/download, cancel/resume and failure with no external fallback.
4. Launch/drive the actual UI, take redacted screenshots and inspect routing/egress.
   Linux-only execution here is not proof of Windows/macOS; provide CI/manual matrix.
5. Test two users before claiming a remote daemon is tenant-safe. Existing IO's JWT
   gateway protocol is not automatically compatible with upstream clients.
6. Chronology entry, benchmarks links and concise copy/paste manual test instructions.
   Keep IO baseline usable until we decide whether to retain, fork or replace it.

## First benchmark completed

See [benchmark](../benchmarks/runs/2026-11-06-oss-desktop/t3-private/README.md). Packaged T3 Linux desktop → paired remote container → real Muse succeeded; browser CSV upload/Python/table preview, interruption and restart/reconnect passed. Generated CSV download UX, public Access routing, tenant integration, fresh OAuth and Windows/macOS remain unverified.
