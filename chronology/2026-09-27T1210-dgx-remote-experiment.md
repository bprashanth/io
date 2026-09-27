# Remote Codex transport and isolation — DGX, 2026-09-27

## Seen

[Evidence](../benchmarks/runs/2026-09-27-remote-codex/README.md): the bundled Codex
0.154.0 runs inside a per-session Linux container. Its real parent/child sandbox
allows workspace operations and denies outside read/write, symlink traversal and
raw external TCP. Before/after controls succeed. The two-container API suite passes:
separate capabilities, workspaces and auth directories, no cross-container worker
TCP, explicit file transfers, safe path handling, and ephemeral lifecycle.

Actual Electron was opened under Xvfb with standalone Playwright. Browser plugin
discovery returned no available browsers after its documented troubleshooting step.
The UI copied a synthetic CSV, displayed results, downloaded `total\n20\n`, and left
the local original unchanged. Python ran through the actual Codex sandbox, invoked
by the operator harness. This was **not** a model-generated conversation. Fresh
`codex login --device-auth` produced the expected authorization page/code; the UI
also successfully cancelled login. Screenshots are linked from the evidence README.

## Causes and changes

Docker's unconfined AppArmor label was insufficient on this Ubuntu host: uid_map
setup failed. A named AppArmor profile granting userns works. Docker's default
seccomp profile is disabled for this nested-sandbox experiment; no privileged mode
or initial capabilities are granted. This relaxation is explicit in the proposal
and deployment README, and narrower hosting policies remain future work.

The first UI run exposed a missing controlling terminal: Ctrl+C failed. A small
exec wrapper acquires the PTY as controlling terminal before starting Codex. The
rerun passes. Restart testing exposed changing automatically published Docker ports;
provisioning now selects then explicitly binds a stable port. Worker instance IDs
allow the client to clear stale terminal replay and report that restart erased state.

Implemented opt-in `IO_REMOTE_CONNECTION` in Electron, skipping local scanner and
Codex bootstrap. The separate experimental renderer retains io's xterm, colours and
terminal controls. Main-process capabilities, authenticated streaming, explicit
upload/save dialogs, offline command policy, no escalation, per-session tmpfs,
expiry and End are implemented. Local mode remains unchanged. The remote UI states
that files go to the server and ChatGPT, without local masking.

Lower-model Cursor CLI (`gpt-5.4-mini-high`) did the bounded transport/UI and API-test
grind. Parent reviewed and fixed stream gaps, key ordering, reload/reset state,
packaged asset paths, file size/type checks and lifecycle handling. Two early API
assertions assumed diagnostic wording; one used a host path in the container.
The first failed report is retained rather than rewritten into success.

## Re-test

10 real-container integration tests and 2 client protocol tests pass locally.
Each container's actual sandbox has 3 allowed and 10 denied checks, with 13 allowed
positive controls both before and after. Existing local-mode suites remain green:
19 launcher tests (including actual wall) and 34 proxy tests. UI drive reports no
page errors. Its native file dialogs use deterministic test paths; no model answer
is simulated or counted as live evidence.

Added CI: client protocol fixtures on Linux x64, macOS x64/arm64 and Windows x64;
actual pinned Codex/container suite on Ubuntu x64. CI needs no model credentials.
CI execution is recorded separately once measured.

## Not tested and next handoff

The user did not complete the fresh OAuth authorization during this drive; its
15-minute code expired. No existing auth cache or API key was borrowed. Therefore
ChatGPT identity, live conversation/tool streaming, follow-up/resume of a real
conversation, and interruption of a model-driven command are still **unproven**.
Synthetic auth-file sentinels prove namespace boundaries, not real account identity.

The Pop!_OS Tailscale peer was offline, so no two-machine drive occurred. Docker
network namespaces are separate IPs on one host, not a substitute for that test.
Packaged/native Mac/Windows GUI operation also remains untested. The next step is
fresh user login and the CSV workflow from the laptop, using the exact
[deployment steps](../app/io/remote/README.md). Production account management,
container hardening, tokenisation placement, durable storage, sync and hybrid/local
executors remain deferred as specified in the [proposal](../proposals/remote-linux-codex.md).
