# Testing T3 Code, Paseo and AionUi from a laptop

This is an evaluation guide. IO itself and `io.idli.cc` are unchanged.

> **2026-11-07: Paseo only from here.** The T4GC config folders moved to `~/idli-insights/config/`
> (see [driving-desktop.md](driving-desktop.md#idli-insights)). T3 and AionUi still point at the old
> `~/.codex-t4gc` / `~/.claude-t4gc` paths and are no longer maintained. Their sections below are a
> record; re-point them by hand if you need them again.
Evidence: [T3 (other agent)](../benchmarks/runs/2026-11-06-oss-desktop/t3-private/README.md),
[Paseo](../benchmarks/runs/2026-11-06-oss-desktop-independent/paseo/README.md),
[AionUi](../benchmarks/runs/2026-11-06-oss-desktop-independent/aionui/README.md).

## The model in one table

There are two separate choices: **where the agent CLI runs** and **which model it talks to**.
Signing in to Codex or Claude only matters when the model is OpenAI's or Anthropic's.

| | Model: your ChatGPT / Claude subscription | Model: **T4GC model** (Muse on Idli) |
|---|---|---|
| **Runs on the laptop** | **Open.** The CLI runs locally, uses your `codex login` / `claude` login and touches your files. Traffic goes to OpenAI or Anthropic. Nothing goes to Idli. | **Private-A.** The CLI still runs locally and still touches your files, but every model request goes to Idli. No subscription login is used or needed. |
| **Runs on Idli** | Not offered. It would mean putting your OAuth token on Idli (IO V1 does this today; the new design avoids it). | **Private-B.** Only the GUI is on the laptop. The CLI, tools and files run in *your* container on Idli. You upload and download copies. |

So in your step 4, "local execution" means the Codex or Claude CLI runs on your laptop. Where its
traffic goes depends only on the model you picked in step 2:
- the normal Codex or Claude entry goes to OpenAI or Anthropic
- the T4GC entry goes to Idli

It never silently switches between them. In every app below, the T4GC entry is a separate
provider with its own config folder (`~/idli-insights/config/codex-t4gc`, `~/idli-insights/config/claude-t4gc`). That folder holds no
login, so your subscription token is never sent to Idli.

## One-time setup on the laptop

1. Join Tailscale and check that `ssh beeps@gx10-0a47.tail5ef239.ts.net` works.
2. Install the CLIs and sign in (Open mode): `npm i -g @openai/codex @anthropic-ai/claude-code`,
   then `codex login` and `claude` (`/login`).
3. Get the branch: `git fetch origin && git checkout oss-desktop-eval`. Set
   `R=benchmarks/runs/2026-11-06-oss-desktop-independent`.
4. Create the T4GC config folders.

   macOS or Linux:
   ```sh
   mkdir -p ~/idli-insights/config/codex-t4gc ~/idli-insights/config/claude-t4gc && chmod 700 ~/idli-insights/config
   cp $R/laptop/codex-t4gc-config.toml ~/idli-insights/config/codex-t4gc/config.toml
   cp $R/laptop/claude-t4gc-settings.json ~/idli-insights/config/claude-t4gc/settings.json
   ```
   Windows PowerShell:
   ```powershell
   $R='benchmarks\runs\2026-11-06-oss-desktop-independent'
   mkdir $HOME\idli-insights\config\codex-t4gc, $HOME\idli-insights\config\claude-t4gc -Force
   copy $R\laptop\codex-t4gc-config.toml $HOME\idli-insights\config\codex-t4gc\config.toml
   copy $R\laptop\claude-t4gc-settings.json $HOME\idli-insights\config\claude-t4gc\settings.json
   ```
5. **Open the tunnel** and leave it running while you test:
   ```sh
   ssh -N beeps@gx10-0a47.tail5ef239.ts.net \
     -L 8181:127.0.0.1:8181 \
     -L 16767:172.31.77.2:6767 -L 26767:172.31.78.2:6767 \
     -L 25808:172.31.77.3:25808 -L 35808:172.31.78.3:25808 \
     -L 8791:127.0.0.1:8791
   ```
   | Local port | What it reaches |
   |---|---|
   | 8181 | Muse (Private-A) |
   | 16767 | Paseo, user A |
   | 26767 | Paseo, user B |
   | 25808 | AionUi, user A |
   | 35808 | AionUi, user B |
   | 8791 | T3 remote environment |

   The tunnel is a test-only route. A real deployment needs Idli authentication in front of Muse
   and the per-user servers.
6. Check Muse: `curl http://127.0.0.1:8181/v1/models` should list `muse-glimmer-30b`.
7. Get the remote passwords:
   `ssh beeps@gx10-0a47.tail5ef239.ts.net 'cat ~/io-oss-state/paseo-a/password ~/io-oss-state/aion-a/password'`.
   Use `-b` instead of `-a` for user B.

The DGX side is already running. If it has been stopped, restart it on the DGX with
`benchmarks/runs/2026-11-06-oss-desktop-independent/dgx/up.sh` from the branch checkout.
Stop it with `dgx/down.sh` (add `--with-t3` to also stop T3).

Use a synthetic CSV, for example `$R/agents/visits.csv`. Ask: *"Using the attached visits.csv,
compute total visits per village with Python, write result.csv with columns village,total_visits,
and show the table."* Expected: Hillcrest 6, Lakeside 3, Riverbend 12.

## T3 Code (v0.1.7)

Install the desktop from https://github.com/pingdotgg/t3code/releases/tag/v0.1.7 (native macOS
arm64/x64, Windows x64/arm64, Linux).

- **Open.** Choose **Codex** or **Claude** (your logins) and run the CSV prompt in a plain folder.
  You should see native approval prompts. Traffic goes to OpenAI or Anthropic.
- **T4GC model (Private-A):**
  1. Open Settings → Providers → **Add provider**. Choose driver **Codex**, name it
     "T4GC model". Set **CODEX_HOME path** to `~/idli-insights/config/codex-t4gc` and add custom model
     `muse-glimmer-30b`.
  2. Add another provider with driver **Claude**, named "T4GC Claude". Set **CLAUDE_CONFIG_DIR path**
     to `~/idli-insights/config/claude-t4gc` and add custom model `muse-glimmer-30b`.
  3. In a new chat, pick T4GC model → `muse-glimmer-30b`, then run the CSV prompt.
  4. Also set the title / text-generation model to T4GC. Otherwise titles still go to your
     default provider (the other agent saw this).
- **Remote (Private-B):**
  1. On the DGX, run the pairing command printed by `dgx/up.sh`, which is
     `docker exec io-t3-bench … t3 auth pairing create … --base-url http://127.0.0.1:8791`.
  2. In T3 desktop, add an environment with that link. It works through the tunnel because the
     laptop's 8791 is the tunnel.
  3. Pick the remote environment's "Idli Private Muse" Codex, attach the CSV, and run.
  4. Optionally turn off the Local environment.

  This runtime is the other agent's single-user container (one environment, not per user).
- **Known:** no clear download button for generated files (preview only).

## Paseo (v0.15.2)

Install the desktop from https://github.com/getpaseo/paseo/releases/tag/v0.15.2 (native macOS
arm64/x64, Windows x64/arm64, Linux x64). It starts its own local daemon.

- **Open.** Choose Codex or Claude and run the prompt.
- **T4GC model (Private-A):**
  1. Merge `$R/laptop/paseo-providers.json` into `~/.paseo/config.json`, keeping your existing keys.
     Replace `REPLACE_WITH_HOME` with your absolute home path (Windows uses `C:\\Users\\you`).
  2. Run `paseo reload`, or restart the app.
  3. The model picker now shows **Codex · T4GC model** and **Claude Code · T4GC model** next to the
     normal ones. This exact config was verified on the DGX: only the T4GC entries reached Muse.
- **Remote (Private-B):**
  1. In Paseo, open Hosts → add → **Direct connection**. Use host `127.0.0.1`, port `16767`
     (user A) or `26767` (user B), and that user's password. Alternatively, open
     `http://127.0.0.1:16767` in a browser.
  2. Add project `/workspace`, pick Codex · T4GC model → Full access, attach the CSV and send.
  3. Download: Explorer → Files → right-click `result.csv` → Download.
  4. For Claude, use **Always ask**. Auto mode blocks Bash with Muse.
- **Known:**
  - Stop leaves a running command alive.
  - A Muse outage shows only a spinner with Codex.

## AionUi (v2.2.2)

Install from https://www.aionui.com/ (binaries are on `static.aionui.com`, not GitHub).

- **What the official desktop does.** It asks you to **Sign in to AionUi** (an `aionui.com` account)
  before anything else. It also sends Sentry and Google Analytics, which we agreed is acceptable for
  testing. It runs your real Codex and Claude Code CLIs.
- **Open.** Choose Codex CLI or Claude Code and run the prompt.
- **T4GC model (Private-A).** AionUi says "Only Aion CLI supports custom models", so there are two
  ways to get Muse:
  - **Built-in agent:** Settings → **Model** → **Add Model**. Use an OpenAI-compatible provider,
    base URL `http://127.0.0.1:8181/v1`, any key, model `muse-glimmer-30b`. Then pick **Aion CLI**
    with that model. This is AionUi's own agent, not Codex or Claude.
  - **Codex or Claude:** Settings → Agents → **Codex CLI** → Edit → Environment Variables →
    `CODEX_HOME=<home>/idli-insights/config/codex-t4gc`. For Claude Code, use `CLAUDE_CONFIG_DIR=<home>/idli-insights/config/claude-t4gc`.
    This switches that agent *entirely* to Muse until you remove the variable; it is a toggle,
    not a second entry.

  Neither path was tested on a laptop yet.
- **Remote (Private-B).** Use a browser, not the desktop app. AionUi's desktop is not a remote
  client, and the official remote WebUI cannot log in without the AionPro account.
  1. Open `http://127.0.0.1:25808` (user A) or `http://127.0.0.1:35808` (user B). Log in as `admin`
     with the password from step 7.
  2. Choose New Chat → **Codex CLI** → Permission **Full Access** → **+** → **Upload from device**,
     then send.
  3. Open `result.csv` in the Files panel, then press **Download file** in the preview.
  4. The server side runs the open-source backend mode, using Muse only.
- **Known:**
  - The Codex model label shows OpenAI names even though Muse is used.
  - Stop leaves a running command alive.

## What to record for each app

For Open, T4GC-local and remote:
- did login just work?
- was the T4GC choice obvious?
- did the CSV come back correct?
- could you download it?
- what happens on Stop?
- does a chat resume after closing the app?

Also note your OS. For a "model down" test, ask on the DGX to stop the proxy, or close the tunnel
during a reply. Expect no fallback to another model.
