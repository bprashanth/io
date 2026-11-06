# AionUi 2.2.2: official binary versus the open-source backend, real Muse, two users

Same shape as the [Paseo run](../paseo/README.md): one container per user, an isolated per-user
network, the logging model proxy and in-namespace packet capture. Nothing public was used, and no
IO service was changed.

## What ships

- **Where the binaries are.** GitHub releases for AionUi carry no installers (0 assets since at least
  v2.1.54). Binaries are on `static.aionui.com/releases/<ver>/`.
  - `AionUi-2.2.2-linux-arm64.deb` has sha256 `3e8e2f29…15e2`, and its sha512 matches the
    publisher's `latest-linux-arm64.yml` manifest.
  - The package bundles AionCore 0.2.2, a Rust backend (`aioncore`), plus a managed Node 24.
- **The official build is the "AionPro" build.** Its main process hard-codes
  `CORE_IDENTITY_MODE = "aionpro"`. The comment says `--local` "is reserved for the open-source AionUI
  embedded build".
  - **Desktop:** after onboarding it shows only "Sign in to AionUi" (an `aionui.com` account), with no
    skip ([shot](screenshots/aiond-01.png)). I did not create an account.
  - **Remote WebUI:** `--webui --remote` under Xvfb, as in the headless deployment guide. Logging in
    with a local password fails with backend `401 USER_CONTEXT_REQUIRED`, even after setting the admin
    password with `aioncore user set-password` and restarting ([shot](screenshots/aion-a-02-loggedin.png)).
  - **Telemetry baked into the build:** a Sentry DSN (`o4505147559706624.ingest.us.sentry.io`),
    Firebase config, and GA4 `G-5KG1MNHX4K` posting to `google-analytics.com/g/collect`.
    This corrects my earlier source-only note that Sentry needs `SENTRY_DSN`.
- **Open-source path.** I ran the same bundled `aioncore` with `--identity-mode webui`, which uses
  local users with passwords. In front of it is [webhost.mjs](webhost.mjs), a ~30-line equivalent
  of upstream `packages/web-host/src/static-server.ts` that serves the packaged renderer and proxies
  `/api`, `/login`, `/logout` and WebSocket upgrades to aioncore. It has no auth logic. Upstream's own
  standalone server (`Dockerfile`, `bun run server:start`) would replace it but needs a source build.
- **How agents run.** With the CLIs on `PATH`, aioncore ran the **real binaries**:
  - **Codex:** `codex app-server` (IO's 0.154.0). Its user agents are `aionui-session` and
    `aionui-title`.
  - **Claude Code:** `claude --print --input-format stream-json …` (2.1.319). AionUi warns it was
    verified only against 2.1.236.
  - No ACP adapter was downloaded. Seeded metadata still references
    `npx @agentclientprotocol/claude-agent-acp` and managed `codex-acp@1.1.2` for other setups.

## Image and runtime

- **Image.** See [Dockerfile](Dockerfile): `node:22-bookworm-slim`, the arm64 `.deb`, Electron
  libraries the `.deb` does not declare (`libgbm1` and others), IO's Codex and Claude Code 2.1.319.
  Uid 1000, `--cap-drop ALL`, `no-new-privileges`, 4 GiB memory, 1024 pids.
- **Configs.** The Codex config is the same as Paseo's. Claude gets [claude-settings.json](claude-settings.json),
  with the `env` block pointing at Muse and `WebSearch`/`WebFetch` denied.
- **Warm-up.** Both containers first ran on an internet-connected bridge to observe the official
  binary. Then they moved to `io-oss-private` (A, 172.31.77.3) and `io-oss-private-b` (B, 172.31.78.3)
  for every behavioural test.

## Results (open-source backend, isolated networks, browser client)

| Check | Result |
|---|---|
| Login | Local `admin` user per container; B's password on A stays on the login page with no visible error ([shot](screenshots/aion-x-wrong-password.png)). Session cookie survived a container restart. |
| Home | Detects Claude Code and Codex CLI; built-in "Aion CLI" and "Butler" also offered ([shot](screenshots/aion-oss-a-01.png)). |
| Upload | "+", then "Upload from device", put the client-only CSV in `/tmp/aionui/general/` in the container ([shot](screenshots/aion-a-20-attached.png)). |
| A, Codex → Muse | Correct `result.csv` in 30 s, in a per-conversation folder under `/home/node/work/conversations/...` ([shot](screenshots/aion-a-21-result.png)). |
| Model label | The Codex picker lists only OpenAI names (GPT-6-Astra …) and a conversation header showed "GPT-6-Astra", but every request carried `muse-glimmer-30b` ([shot](screenshots/aion-a-13-models.png)). Misleading for Private. |
| Titles | `aionui-title` requests go to Muse; one title came out as the whole answer. |
| Download | Opening the file from the Files tree shows a preview with a "Download file" button. The downloaded copy is correct ([shot](screenshots/aion-a-23-preview.png), [file](downloaded-result-a.csv)). The tree's "⋮" menu has no download. |
| B, Claude Code → Muse | Correct (Northfield 11, Southgate 8) in 64 s. Claude's native prompts appeared as Allow / Allow Always / Reject for Read and Bash ([shot](screenshots/aion-b-20-permission.png)). |
| Stop | The UI went idle with the transcript of that turn empty, but **`python3 slow.py` kept running** under `codex app-server`, the same as Paseo. Old app-server processes also accumulate, one per conversation ([shot](screenshots/aion-a-31-stopped.png)). |
| Model down, Codex | Live status: "error sending request (attempt 6, 2m29s so far — the agent's provider keeps dropping the connection; AionUi is waiting it out.)". It never gives up on its own ([shot](screenshots/aion-a-40-model-down.png)). |
| Model down, Claude Code | `USER_LLM_PROVIDER_NETWORK_ERROR`, "Connection refused (ECONNREFUSED)", after about 3 min ([shot](screenshots/aion-b-40-model-down.png)). |
| Restart and resume | After `docker restart` and relaunching aioncore: conversations, files and session intact, and the follow-up recalled the earlier file and totals ([shot](screenshots/aion-a-50-resumed.png)). |
| Server egress (isolated) | A: 49 new connections, all to its proxy. B: 12, all to its proxy. No UDP, no DNS. See [egress.txt](egress.txt). |
| Client egress | **The renderer sends GA4 events from the viewer's browser**: `app_launched` and `page_view` with path and a random client id, 3–6 requests per page load. No chat content was seen in them. Server isolation cannot stop this; it needs a renderer patch or a CSP. |

## Official binary egress during warm-up

Both users, on the internet-connected bridge (DNS names decoded from the capture, see [egress.txt](egress.txt)):
- **Spell-check dictionaries.** `redirector.gvt1.com` and an `rr2---….gvt1.com` cache host,
  on Electron start, partly over QUIC.
- **Sentry.** `o4505147559706624.ingest.us.sentry.io`, from both containers.
- **Desktop-only traffic.** `www.google-analytics.com` and `static.aionui.com` (update feed).

## Reading

- **Non-developer fit.** AionUi's open-source backend behaves well with Muse on a per-user server:
  - real Codex and Claude Code
  - local accounts and native permission prompts
  - per-conversation folders and download from the preview
  - the clearest model-outage message of the three tools
- **The official binaries are not usable for Private as shipped.** The desktop needs an `aionui.com`
  account, the remote WebUI login fails in `aionpro` mode, and Sentry, GA and the update feed are
  compiled in.
- **The cost of adopting it.** Adopting AionUi means building from source (AionUi with Bun, AionCore
  with Cargo) and maintaining a fork that:
  - removes GA and Sentry
  - fixes the Codex model labels
  - packages the desktop for Windows and macOS without the AionPro sign-in

  None of this was measured here.
