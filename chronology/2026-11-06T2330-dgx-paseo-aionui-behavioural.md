# 2026-11-06, 23:30 IST — DGX: Paseo and AionUi driven against Idli Muse, two users each

The owner asked me to try Paseo and AionUi after reading the other agent's T3 run on
`io_silo_untested` (e69ca56). That agent built a T3 0.1.7 container that reaches only Muse through a
narrow proxy, paired the packaged desktop, and ran the client-only CSV upload, stop and restart.
I mirrored that shape for both candidates, with two users each. The work is on branch
`oss-desktop-independent` in its own worktree. Containers, networks and ports are mine
(`io-oss-*`, 172.31.77/78.0/24, proxy :8183). Nothing public, and no IO, tunnel, DNS or Muse change.

[Paseo evidence](../benchmarks/runs/2026-11-06-oss-desktop-independent/paseo/README.md),
[AionUi evidence](../benchmarks/runs/2026-11-06-oss-desktop-independent/aionui/README.md),
[manual tests](../benchmarks/runs/2026-11-06-oss-desktop-independent/MANUAL-TESTS.md),
[machine-readable](../benchmarks/runs/2026-11-06-oss-desktop-independent/results-ui.json).

## Setup common to both

- **One container per user.** Uid 1000, `--cap-drop ALL`, `no-new-privileges`, its own home and
  password, and its own Docker `--internal` network.
- **Model route.** A logging proxy on each network's gateway forwards only to Muse.
- **Agents.** Codex 0.154.0 (IO's pin) and Claude Code 2.1.319, both configured for Muse.
- **Client.** Playwright Chromium on the host drove each product's web UI.
- **Capture.** tcpdump ran in each container's network namespace.

## Paseo 0.15.2 (official image, configuration only, no code patch)

- **Works:**
  - client-only upload, then Codex correct in 77 s, then download from the explorer
  - Claude correct, with the native Deny/Accept prompt in "Always ask"
  - multi-turn, restart and resume
  - B's password rejected on A
- **Egress.** None besides the user's own proxy: no DNS, no other host.
- **Problems:**
  - Stop does not kill a running command.
  - Codex outage is a silent spinner.
  - Claude's default "Auto mode" denies all Bash without Anthropic's classifier.
  - There is a first-boot Codex sqlite race.
  - A shared network let A reach B's daemon, so the setup needs per-user networks.
  - There is no Linux arm64 desktop build, so I used the daemon-served web UI (same renderer).
- **Access.** One shared password per daemon, checked twice (WebSocket and hello). A
  browser through Cloudflare Access works on the same origin. The desktop app cannot send Access.

## AionUi 2.2.2

- **Official binaries are not usable for Private.**
  - The arm64 .deb is from `static.aionui.com` (GitHub releases have no assets) and is the
    "AionPro" build.
  - The desktop requires an `aionui.com` sign-in. Its WebUI password login fails
    (`USER_CONTEXT_REQUIRED`).
  - Sentry, GA4 and the update feed are compiled in and were observed. This corrects my
    earlier source-only Sentry note.
- **Open-source backend works.** The bundled `aioncore --identity-mode webui`, behind a ~30-line
  equivalent of upstream's web host, runs the **real** `codex app-server` and `claude` CLIs.
  - Codex correct in 30 s.
  - Claude correct in 64 s, with Allow / Allow Always / Reject prompts.
  - Download from the file preview.
  - Restart and resume, with the session cookie kept.
  - A visible retry message during a Codex outage.
  - Server egress on isolated networks: none besides the proxy.
- **Problems:**
  - GA4 is sent from the viewer's browser.
  - The Codex model picker shows OpenAI names while Muse is used.
  - Stop does not kill a running command.
  - Old app-server processes pile up.
  - Adopting it means a source build and a fork.

## Takeaways

- **Shared Stop gap.** "Stop" leaving `python3` running happened in both products and in both cases
  under `codex app-server`. It is likely Codex's interrupt, not the UI, but I have not proven that.
- **Paseo** is the cleanest base for Private architecture B: no patch, no telemetry seen, a
  working browser client through Access. Its desktop app would need Access support or an
  SSH route.
- **AionUi** is the better non-developer experience but needs a fork to be private.
- **Not done:** Windows and macOS, packaged Paseo desktop, fresh Open-mode OAuth, real Cloudflare
  Access, an AionUi source build. Single samples.
