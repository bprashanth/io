# Driving the laptop's Paseo from the DGX

The co-work POC ([docs/cowork-poc.md](cowork-poc.md)) runs in the **Paseo desktop app on the laptop**.
That is where the user's signed-in browser tabs live, and only the desktop app has a workspace browser.
The DGX serves the models and runs the experiments. An agent on the DGX drives the laptop's Paseo
through one SSH connection that the **laptop** opens. The DGX never gets a shell on the laptop.

```
 laptop (Pop!_OS)                                              DGX
 ┌─────────────────────────────────┐   ssh (opened by laptop)   ┌──────────────────────────────┐
 │ Paseo app + daemon  127.0.0.1:6767 ◄──── -R 46767 ───────────┤ paseo-remote.sh (CLI)          │
 │ Paseo DevTools      127.0.0.1:9333 ◄──── -R 49333 ───────────┤ drive.py (Playwright, CDP)     │
 │ Muse via tunnel     127.0.0.1:8181 ───── -L 8181 ───────────►│ idli-muse llama.cpp :8181      │
 └─────────────────────────────────┘                            └──────────────────────────────┘
```

All three forwards bind to 127.0.0.1 on both ends.

| Channel (on the DGX) | What it can do | Tool |
|---|---|---|
| `127.0.0.1:46767`: the Paseo daemon | List, run and message agents; run commands in a laptop workspace terminal (`git pull`, tests); reload config; manage plugins | `cowork/desktop/paseo-remote.sh` (the Paseo 0.15.2 CLI from the `io-oss-paseo` image; the DGX host has no Node) |
| `127.0.0.1:46767/mcp/agents?callerAgentId=…` | Paseo's browser tools: the site plugins on the DGX can drive the laptop's tabs directly | `PASEO_MCP_URL=http://127.0.0.1:46767/mcp/agents` for `cowork_mcp.py` / `run_tests.py` |
| `127.0.0.1:49333`: Chrome DevTools of the app | Screenshot the app, read its text, click buttons such as the dashboard **Open** button | `cowork/desktop/drive.py` (Python Playwright, already on the DGX) |

> **What this grants.** While the tunnel is up, anything on the DGX that can reach 127.0.0.1 can:
> - drive every Paseo agent on the laptop;
> - read **every tab** in the workspace browser, including the user's real Gmail and Drive, through DevTools.
>
> The daemon has no password. Keep the tunnel up only during experiments: `laptop-up.sh stop`.

## ~/idli-insights

Everything outside the repo lives in one folder, on both machines. The repo has only code and docs.

```
~/idli-insights/
  config/                 chmod 700
    accounts.json         the test account + fixture ids (lib/accounts.py)        laptop + DGX
    claude-t4gc/          Claude Code config: model = Muse (CLAUDE_CONFIG_DIR)     laptop
    codex-t4gc/           Codex config: model = Muse (CODEX_HOME)                  laptop
    claude-or-9b/         OpenRouter 9B test config (holds the OpenRouter key)     laptop
  cowork-real/            co-work workspace: the "private" data (+ cowork.sites)  laptop
  cowork-real-9b/         the 9B test workspace (kept for now)                    laptop
  oss-test/, oss-test-paseo/   earlier dashboard test folders                     laptop
```
- **Workspaces:** each private-data workspace is a folder here.
- **DIY's limits:** its workspace is the repo's `cowork/` folder. Its sandbox blocks the private folders here; it may read only `config/accounts.json`.
- **Paseo only:** T3 and AionUi are no longer maintained against this layout.

**Bootstrap the laptop** (once):
```sh
mkdir -p ~/idli-insights/config/claude-t4gc && chmod 700 ~/idli-insights/config
R=~/src/github.com/bprashanth/io/benchmarks/runs/2026-11-06-oss-desktop-independent
cp $R/laptop/claude-t4gc-settings.json ~/idli-insights/config/claude-t4gc/settings.json   # Muse via 127.0.0.1:8181
#  ~/idli-insights/config/accounts.json: write it by hand (format below), chmod 600
```

**Bootstrap the DGX** (once). The DGX only runs the checks and tests through the tunnel, so it needs just
the test-account file:
```sh
mkdir -p ~/idli-insights/config && chmod 700 ~/idli-insights/config
# from the LAPTOP:
scp ~/idli-insights/config/accounts.json beeps@gx10-0a47.tail5ef239.ts.net:idli-insights/config/accounts.json
# on the DGX:
chmod 600 ~/idli-insights/config/accounts.json
rm -f ~/src/github.com/bprashanth/io/benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/accounts.local.json   # old location
```
`lib/accounts.py` still falls back to `cowork/accounts.local.json`, so nothing breaks before the move.

## One-time setup on the laptop

Prerequisites:
- Paseo 0.15.2;
- Claude Code;
- `~/idli-insights/config/claude-t4gc/settings.json` (above);
- Tailscale access to the DGX (`ssh beeps@gx10-0a47.tail5ef239.ts.net true` works).

Then do the following:

1. **Run the setup script** from the repo's cowork folder:
   ```sh
   cd ~/src/github.com/bprashanth/io/benchmarks/runs/2026-11-06-oss-desktop-independent/cowork
   python3 desktop/setup-laptop.py
   ```
   It is idempotent and backs up `~/.paseo/config.json`. It sets up:
   - the providers "Co-work · T4GC" and "DIY · Claude";
   - browser tools and plugins;
   - `cowork.mcp.json` and `.venv`;
   - `~/idli-insights/cowork-real`, the stand-in "real" workbook;
   - the `dashboard-links` plugin.
2. **Create `~/idli-insights/config/accounts.json`** (chmod 600; outside the repo):
   ```json
   {"google": {"test": "<the Google account signed in to Paseo>",
               "fixtures": {"pbv_sheet": "<sheet id>", "multi_tab_sheet": "<sheet id>", "a_doc": "<doc id>"}}}
   ```
   The fixture IDs are files in the test account that the Google tests use (see `sites/google/tests.json`).
3. **Make Paseo start with its DevTools port.** Quit Paseo with no agents running. Closing the window
   may leave it running, so check with `pgrep -f /opt/Paseo/Paseo.bin`. Then start it:
   ```sh
   setsid /opt/Paseo/Paseo --remote-debugging-port=9333 >/dev/null 2>&1 &
   ```
   To make the menu launcher do this every time:
   ```sh
   sed 's#^Exec=/opt/Paseo/Paseo #Exec=/opt/Paseo/Paseo --remote-debugging-port=9333 #' \
     /usr/share/applications/Paseo.desktop > ~/.local/share/applications/Paseo.desktop
   ```
   Workspace browser tabs come back after a restart. Sign-ins persist.
4. **In the app**, sign in to Google in a workspace browser tab. Open one workspace on `~/idli-insights/cowork-real` and
   one on the cowork folder, and start any chat in each, so that both have an agent.
5. **Don't take Paseo's in-app update** (0.15.3) unless you also move the DGX CLI image to that version.

## Each session

On the laptop:
```sh
cd ~/src/github.com/bprashanth/io/benchmarks/runs/2026-11-06-oss-desktop-independent/cowork
desktop/laptop-up.sh          # status / stop also work
```
If it says `ssh exited`, run `ssh beeps@gx10-0a47.tail5ef239.ts.net true` once by hand. Tailscale sometimes
asks for a browser sign-in.

On the DGX (checkout `~/src/github.com/bprashanth/io`, branch `oss-desktop-eval`):
```sh
cd ~/src/github.com/bprashanth/io && git pull
cd benchmarks/runs/2026-11-06-oss-desktop-independent/cowork
desktop/check-from-dgx.sh     # first time: bootstrap ~/idli-insights on the DGX (above)
```
`check-from-dgx.sh` checks, in order:
- the tunnel;
- the providers;
- the two workspaces;
- a command in a laptop terminal, reporting the laptop's commit;
- a screenshot (`~/io-oss-state/desktop-shots/dgx-check.png`);
- the site tests run **from the DGX copy** against the laptop's browser tabs.

It ends with `ALL CHECKS PASSED`.

## Common operations from the DGX

```sh
P=desktop/paseo-remote.sh                                   # from the cowork/ folder
$P ls                                                       # agents on the laptop
$P workspace ls                                             # workspace ids and laptop paths
$P run --provider t4gc-cowork --workspace <wks_cowork_real> --mode bypassPermissions --title "exp: …" \
   --wait-timeout 20m --json "the user's question"           # co-work on Muse; prints the agent id
$P logs <agent-id> | tail -40                               # its tool calls and answer
$P run --provider diy-claude --workspace <wks_diy> --mode bypassPermissions "…"   # DIY mode
```
- **Show the workspace in the app first:** `python3 desktop/drive.py goto <wks>`. Paseo opens a new browser
  tab only in the workspace the app is displaying. Otherwise the site tools fail with "Could not open a
  browser tab … open the browser pane". Tabs that already exist keep working.
- **Browser tools need a live caller agent.** Idle agents get closed (`inspect` shows `closed`), and then calls fail
  with "Parent agent … not found". `$P agent reload <id>` wakes one without a model call.
- **Always pass `--workspace` or `--cwd`** with laptop paths. The CLI runs in a container whose own folder means nothing to the laptop.
- **Tools load when a chat starts.** After changing a site plugin, start a new chat.
- **Tool-call log:** each co-work tool call is logged on the laptop in `/tmp/cowork.log`. Read it from a laptop terminal.

**Run a command on the laptop:**
```sh
T=$($P terminal create --workspace <wks_diy> --name dgx --json | python3 -c 'import json,sys;print(json.load(sys.stdin)["id"])')
sleep 2; $P terminal send-keys "$T" "git pull dgx oss-desktop-eval && .venv/bin/python run_tests.py sheets" Enter
sleep 10; $P terminal capture "$T" | tail -20; $P terminal kill "$T"
```
`Enter` is its own argument. Wait about 2 seconds after `create` before sending keys.

**Look at the app or click in it:**
```sh
python3 desktop/drive.py goto <wks_id>        # show a workspace (its latest chat)
python3 desktop/drive.py shot name            # screenshot + visible text
python3 desktop/drive.py click "Open field_visits_dashboard_q3.html"
python3 desktop/drive.py tabs                 # app page + all workspace-browser tabs
```
Screenshots work while the laptop screen is locked. Never type into the user's Gmail or Docs pages with DevTools.

## Moving code between the machines

The site plugins **run on the laptop** when co-work uses them, because the laptop's Paseo spawns
`cowork_mcp.py` from the laptop's checkout. So:

1. Edit on the DGX and test right away against the laptop's tabs:
   ```sh
   PASEO_MCP_URL=http://127.0.0.1:46767/mcp/agents .venv/bin/python run_tests.py --agent <agent in the DIY workspace>
   ```
2. Commit on the DGX (branch `oss-desktop-eval` in `~/src/github.com/bprashanth/io`).
3. Pull on the laptop from the DGX, through a laptop terminal: `git pull dgx oss-desktop-eval`. The laptop's
   `dgx` remote points at the DGX repo, which shares refs with the worktree.
4. Start a new co-work chat.

Pushing to GitHub stays the owner's call; `declaude` before any push.

## Models

- **Muse 30B:** `idli-muse` on the DGX, port 8181. Claude Code reaches it through the prefix proxy on DGX 8185
  (`dgx/muse_prefix_proxy.py`, user service `muse-prefix-proxy`), which the laptop gets as `-L 8181:127.0.0.1:8185`.
- **Another DGX model** (e.g. a 9B): serve it on another DGX port, add `-L <port>:127.0.0.1:<port>` to
  `laptop-up.sh`, and add a provider like `t4gc-cowork` whose `CLAUDE_CONFIG_DIR` settings point
  `ANTHROPIC_BASE_URL` at that port.
  - Qwen3.5 needs `cowork/local-9b/qwen35-midsystem.jinja`, because Claude Code sends system messages mid-conversation.
  - `cowork/local-9b/serve.sh` has the flags (use the CUDA image and `-ngl 999` on the DGX).
- **The laptop has no disk space for local models.**

## Recreating from nothing

1. Install Paseo 0.15.2, Claude Code, and the T4GC Claude config (laptop guide).
2. Check out branch `oss-desktop-eval`.
3. Bootstrap `~/idli-insights` (above), then run `python3 desktop/setup-laptop.py`.
4. Restart Paseo with `--remote-debugging-port=9333`.
5. Sign in to Google in a workspace tab and open the two workspaces.
6. Run `desktop/laptop-up.sh`.
7. On the DGX, run `git pull` then `desktop/check-from-dgx.sh`.

**Removing it all:**
- `laptop-up.sh stop`;
- `paseo plugin remove dashboard-links`;
- delete the `t4gc-cowork`, `diy-claude` (and `cowork-9b-or`) providers from `~/.paseo/config.json`;
- set `pluginsEnabled` and `daemon.browserTools.enabled` back to false;
- `paseo reload`.
