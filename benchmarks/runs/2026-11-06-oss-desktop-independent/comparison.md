# OSS desktop candidates for Open + Private: independent research, 2026-11-06

Independent of the evaluation running on `io_silo_untested`; nothing here was read from or
written to its files. Sources were cloned read-only at the commits below. No candidate app
was installed or launched. Tags: **doc** = documented upstream, **src** = read in source,
**run** = shown working here.

## Pinned revisions

| repo | commit | license |
|---|---|---|
| pingdotgg/t3code (latest release v0.1.7) | 6577c6b6185167c0e502fa01f9e8e8f2dee6ff25 | MIT |
| getpaseo/paseo (latest release v0.15.2) | 616f5e155c38cc7dcc015db15781d9b13c79bce1 | Apache-2.0 (GitHub shows NOASSERTION; LICENSE is Apache-2.0 with third-party carve-out) |
| slopus/happy | 665b1f14f3b35d89dead49b7c5c97b58df42f48d | MIT |
| slopus/happy-desktop | ed30e20061dfc5c0978f007b85c4e998a2c84f8f | MIT |
| slopus/happy-agent | 70c1b383390cce86815d945ffda4214fa7233f4a | MIT |
| iOfficeAI/AionUi (latest release v2.2.2) | e108b6b56b1a6eb99a00904878d0582f657b2908 | Apache-2.0 (backend AionCore also Apache-2.0) |
| nimbalyst/nimbalyst | 826adb4f93dbe86db35b76ce2502a3a33abe0489 | MIT |

Also looked at and set aside: winfunc/opcode (Claude Code only, AGPL), siteboon/claudecodeui
(web only, AGPL), BloopAI/vibe-kanban (git-worktree kanban for developers), Zed (an editor; ACP
works but not an NGO tool), Dimillian/CodexMonitor (Codex only).

## Comparison

| | T3 Code | Paseo | Happy | AionUi |
|---|---|---|---|---|
| Desktop OS (doc) | macOS arm64+x64, Windows x64+arm64 native, Linux x64+arm64; WSL optional | macOS arm64+x64, Windows x64+arm64, Linux x64 (deb/rpm/AppImage) | macOS, Windows, Linux (separate young repo, 106 stars) | macOS, Windows, Linux |
| How it runs Codex (src) | real `codex app-server` (JSON-RPC) | real `codex app-server` | reimplemented inside Happy Agent by default | via ACP adapter in AionCore |
| How it runs Claude Code (src) | `@anthropic-ai/claude-agent-sdk` (spawns real `claude`) | Claude Agent SDK | default harness reads `claudeAiOauth.accessToken` from `.credentials.json` and calls the model itself; real Claude Code only as optional "foreign harness" | ACP adapter (`claude-code-acp`) |
| Native subscription login for Open (doc) | yes: `codex login`, `claude auth login` on the host. Also offers OpenAI app token-sharing where T3 holds the token | yes, uses the CLIs' own logins | conflicts with brief: extracts OAuth tokens by default | yes for external agents; built-in agent wants an API key |
| Execution model (doc) | client to one "environment" server that owns providers, files, terminals | client to one daemon that owns agents and files | daemon + E2E relay | Electron app plus local HTTP backend; remote = browser WebUI of a headless Electron under Xvfb |
| Remote execution (doc) | pairing link with scoped bearer/DPoP tokens; desktop-managed SSH starts a server on a Linux host and forwards the port; T3 Connect relay (their cloud) | direct WebSocket with `PASEO_PASSWORD`; official Docker image; optional E2E relay (self-hostable) | relay server (self-host package exists) | `--webui --remote`, browser login |
| Multi-user on one host (doc) | no: a session holds `terminal:operate`, a shell as the server's user. One server per Unix user/container | no: one password per daemon. One container per user | not designed for it | no |
| Model endpoint for Private (doc/src) | per-instance env vars; Codex reads its own `CODEX_HOME` config; `T3CODE_CODEX_LAUNCH_ARGS` passes `-c` overrides; T3 forces no provider (src) | documented: `extends: codex` + `OPENAI_BASE_URL` maps to a Responses provider (llama.cpp named); `extends: claude` + `ANTHROPIC_BASE_URL` | n/a | "any API key" for built-in agent |
| Its "Muse" provider | Meta's Muse Code (`muse login`, `META_API_KEY`), **not** our llama.cpp Muse | same Meta product | none | none |
| Telemetry (doc/src) | ON by default: product events to `ingest.t3.codes` then PostHog with hashed OpenAI/Claude account ids; relay traces to Axiom. Off with `T3CODE_TELEMETRY_ENABLED=false` or managed policy; browser/mobile clients not covered | claims none; no analytics packages found in source | analytics catalog in repo | Sentry wired in the desktop, reporting only when `SENTRY_DSN` is set |
| Non-developer fit | project/git-oriented developer UI; works on plain folders | developer UI (worktrees, diffs, terminals) | developer | strongest: office assistants (xlsx/docx/pptx), "cowork" framing |
| Activity | 49k stars, pushed today | 23k stars, pushed today | 25k (mobile/CLI), desktop 106 | 34k, pushed yesterday |

Uploads, downloads and attachments were not compared in this pass. Patch size is unmeasured
until a build exists.

## What the wire and agent probes showed (run)

Muse is llama.cpp build b10524, model `muse-glimmer-30b`, 4 slots, context 65,536.
`protocol/probe-results.json`: one streamed request per protocol, each offering a `shell` tool.

| protocol (agent that uses it) | status | first byte | total | tool call |
|---|---|---|---|---|
| `/v1/chat/completions` | 200 SSE | 0.92 s | 3.1 s | `shell {"cmd":"head -n 20 /data/visits.csv"}` |
| `/v1/responses` (Codex) | 200 SSE | 0.18 s | 1.6 s | `shell {"cmd":"cat /data/visits.csv"}` |
| `/v1/messages` (Claude Code) | 200 SSE | 0.17 s | 2.7 s | `shell {"cmd":"head -n 20 /data/visits.csv"}` |

Real agents, isolated config homes, synthetic `agents/visits.csv`, task "write result.csv with
total visits per village". Every `connect()` traced with strace.

| agent | wall time | result.csv | connections |
|---|---|---|---|
| Codex 0.154.0 (IO's pin), Responses provider | 74 s | correct (6 / 3 / 12) | 5, all `127.0.0.1:8181` |
| Claude Code 2.1.319, `ANTHROPIC_BASE_URL` | 43 s | correct (6 / 3 / 12) | 3, all `127.0.0.1:8181` |
| Codex, model port closed | killed at 300 s | none | 40, all to the dead port; retries "waiting for network" forever |
| Claude Code, model port closed | fails in seconds | none | 11, all to the dead port; "Connection refused" |

No DNS lookups and no third host in any run, so neither agent fell back to another model.
Configs used: `agents/codex-muse.config.toml`, `agents/claude-muse.env`.

Caveats found:
- Codex warns `Model metadata for muse-glimmer-30b not found. Defaulting to fallback metadata`
  (same as silo's October run).
- Claude Code assumes a 200k context for an unknown model; Muse has 65k. Long sessions would
  overflow before auto-compact. Needs the documented window override.
- Codex hangs rather than failing when the model is down; a desktop must time out and say so.
- One sample each. No latency distribution, no long task, no tool-call quality comparison.

## Reading of the evidence

- **Private architecture A works today at the agent level.** Both real CLIs drive Muse
  end-to-end with tool use and contact nothing else. The desktop only has to pass an
  environment or a config home. This is inference on Idli with execution on the laptop.
- **Private architecture B maps onto T3 and Paseo the same way:** run one server per user in a
  container on Idli, with the agent configured as in A against Muse on loopback. Neither
  server is safe to share between users; isolation comes from one container per identity,
  which is what IO's gateway already does for Codex.
- **The unsolved piece for B is authentication through Cloudflare Access.** T3's client
  source has no custom-header or Access login support (grep); Paseo's is not yet checked. Options
  to test: Access for the SSH route via `cloudflared access ssh` with T3's desktop-managed SSH;
  per-user Access service tokens (a credential per person, not shared); or IO's own gateway
  minting a T3 pairing link per identity after Access login.
- **Happy is out for Open** as briefed (token extraction by default). **AionUi** is the best
  fit for non-developers but its remote mode is a browser in front of a headless Electron per
  user, not a desktop client to a remote environment.

## Not done

No candidate installed or launched, no UI screenshots, no remote-environment test, no
two-user test, no egress capture of any desktop app, no Windows/macOS run. The other
agent already has T3 v0.1.7 and Paseo 0.15.2 running on this box; those runs are theirs.
