# OSS desktop benchmark: T3 Code against Idli-hosted Muse

This is an isolated Linux ARM64 proof, not a replacement deployment of IO.
No DNS, Cloudflare policy, io.idli.cc route or existing IO service was changed.

## Setup

- T3 Code release0.1.7, Linux ARM64 CLI and packaged desktop (.deb unpacked to /tmp).
- CLI archive SHA256: 5a528e23af394cc6f359036d3cb8441fda14129d477630fc6c53e4f4a1025bc8,
  matched release SHA256SUMS. Source inspection at6577c6b6185167c0e502fa01f9e8e8f2dee6ff25;
  source HEAD and released artifact are separate version references.
- Codex0.167.0, separate CODEX_HOME, no OpenAI credentials in runtime.
- Real Muse-Glimmer-30B at localhost8181, Responses API, no OpenRouter mock.
- T3 runtime in io-t3-bench container based on existing io-remote-codex:v1,
  UID1000, cap-drop ALL, no-new-privileges, memory3GiB, pids256.
- Docker internal network io-t3-bench-private; direct public TCP returns errno101.
  Narrow host proxy172.26.0.1:8182 forwards POST only to localhost8181. No host
  documents/auth home/Docker socket mounted. Deliberate /tmp benchmark mounts only.
- Host loopback8791 HTTP/WebSocket reverse proxy to container8791. One-time T3
  pairing, not a Cloudflare-authenticated user/tenant gateway. No public exposure.
- T3 telemetry disabled. Upstream npm update lookup still attempted (and failed on
  the isolated network); this must be disabled/controlled in a product preset too.
- Browser automation used Playwright after connected Browser runtime reported no
  available browsers. Packaged desktop tested with Xvfb; Electron renderer
  --no-sandbox was a test-harness concession, not an approved shipping setting.

## Valid task

Type the prompt FIRST, attach final.csv SECOND, then click Submit. Attachment chips
live inside the editor: replacing editor contents after attachment removes the chip.
The earlier input.csv/pilot.csv attempts are exploratory and are NOT clean attachment
benchmarks. The initial input.csv also existed inside a mounted directory, so its
success alone was vacuous. final.csv existed only in /tmp/io-t3-client before upload.

Input amounts:91,208,337. Expected636. Codex used Python on the uploaded server copy,
produced final-result.csv with636.0; deterministic CSV assertion passed. T3 reported
8.5s. Screenshot shows result as a table. Subsequent native desktop smoke is recorded
separately in checks.json when complete.

## Behavior and limitations

- Streaming text/tools, Stop generation and “Run interrupted · Stopped by user” observed.
- Runtime restart and fresh browser navigation restored existing transcript, result636,
  interrupted state and pairing session.
- CSV preview works. An obvious Save/download action for a generated CSV was NOT
  established in the tested UI. Do not count server-file inspection as client download.
- Initial auxiliary title generation used gpt-6-luna even when chat selected Muse.
  It went to the configured local endpoint, not OpenAI. Set textGenerationModelSelection
  as well as defaultModelSelection to Muse; configure fallback/other auxiliary paths.
- Codex fallback metadata advertised258400 context while Muse slots have65536.
  A long conversation then failed. Test proxy initially hid HTTP error bodies, causing
  generic disconnected/retry messages; it was fixed to forward HTTP errors. Added
  model_context_window65536 and model_auto_compact_token_limit45000 for fresh sessions;
  compaction correctness itself is not yet benchmarked.
- Packaged desktop initially failed saving connections because secure storage was absent
  in headless session. A synthetic isolated D-Bus/gnome-keyring session fixed pairing.
  “basic” alone did not fix it. Real laptop credential storage still needs testing.
- No fresh human Codex/Claude OAuth test. Host CLI login status is read-only evidence,
  not proof of a new NGO user's login flow. No Windows/macOS execution here.
- No two-user ownership/routing integration. T3 pairing grants access to an environment;
  it does not implement IO's Cloudflare identity→per-user container product contract.

## Comparison smoke

Paseo0.15.2 installed independently in /tmp/io-paseo-benchmark, relay/voice/MCP disabled,
loopback8792, separate PASEO_HOME. Codex + custom CODEX_HOME + Muse completed
PASEO_MUSE_OK in15.602s via CLI. Initial --mode default was invalid; auto worked.
No Paseo GUI/attachment/desktop benchmark was completed, so this is not a fair UX ranking.
Paseo daemon was stopped after the smoke test. Happy remains documentation-only.

## Repeat / laptop acceptance

Runtime reproduction scripts are under this directory; they are evidence of this exact
machine setup, not an installer. Do not commit /tmp runtime homes, keyrings or pairing JSON.
For another laptop, install the same upstream desktop release, disable Local environment
for Private, and pair with a reachable test environment using a fresh one-time link.
Loopback8791 here is not reachable from another laptop. io.idli.cc currently serves IO's
existing protocol; T3 needs its own authenticated compatible route before this works there.

Required next: approved test routing at io.idli.cc, Access+T3 pairing/WS integration,
per-user environments, fresh native OAuth in Open, download UX, fail-closed provider
outage tests, auxiliary egress controls and actual Windows/macOS laptop acceptance.

## Screenshots inspected

- [Packaged desktop, remote Muse reply](desktop-remote-success.png)
- [Prompt plus client-only attachment](final-attached.png)
- [Correct result in conversation](final-result.png)
- [CSV table preview](file-viewer.png)
- [Interrupted streaming response](interrupted.png)
- [Restored session after runtime restart](reconnected.png)

The fresh packaged-desktop reply took about61s in its displayed UI (cold/new thread),
versus the warm CSV turn8.388s. These are different workloads and cache states, not
an inference-speed comparison between frameworks. Its screenshot retains the failed
long-context exploratory thread in the sidebar rather than concealing that failure.
