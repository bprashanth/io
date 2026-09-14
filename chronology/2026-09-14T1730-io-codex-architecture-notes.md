# 2026-09-14 17:30 - io + Codex: architecture notes before the first spike

Work order: `.prompt/codex_trials.md` (written by a chatbot without repository access; the
user asked for its up-front doubts to be verified before any UI work). Scope: the mainline
`app/io/` used at the Pune event. Range / astronaut / lane work is out of scope.

## What io is today (inspected, not assumed)

- `app/io/main.js` (Electron) spawns `service.py` (stdlib python + pandas + the vendored
  shield engine) on `127.0.0.1:<port>` and loads the UI from it. `preload.js` exposes one
  IPC call (`pickFolder`). The renderer never has node access.
- Flow: provider screen (OpenRouter key **or** any OpenAI-compatible server address, kept
  in memory) -> consent -> folder shelf -> scan (GLiNER on CPU + regex validators) ->
  review sheet (click a column / cell / span to keep it) -> Preview ("this is what leaves")
  -> "Looks right" (`/api/accept` builds the vault) -> chat. Chat at the event is the
  blind 3-model compare with votes; every payload passes `S.sub_known` (known-values
  regex) and `leak_check`, answers pass `pmap.rehydrate`.
- Privacy primitives to reuse, all in `service.py` / `engine/pseudonymize.py`:
  `PseudonymMap` (`forward`, `token()`, `known_regex()`, `rehydrate()`),
  `redact_question()` (known values -> partial known names -> detector for unseen values),
  `S.sub_known`, `S.leak_check`, `S.kept_all()`.
- Portable mode (`io-data/` beside the app) keeps *everything* io writes on the stick,
  including the vault, on purpose: the design goal is to leave nothing on someone else's
  laptop. The brief's "secrets should be per-user, not on the USB" is the opposite
  instinct; io's own philosophy wins here and is documented below.

## Machine facts that shape the spikes

- This session runs on the DGX (aarch64, kernel 6.17 nvidia), **no display** (tty session,
  Xvfb + firefox available). The x64 laptop is not in reach. So: Electron is driven under
  Xvfb with screenshots, and the ChatGPT OAuth step for "account B" can only be completed
  by the user (device-code flow makes that possible from any device).
- A developer Codex 0.149.0 is installed (`~/.local/bin/codex` -> `~/.codex/packages/...`),
  logged in under `~/.codex`. io must never read it. One slip to record: an early probe
  grepped the `auth_mode` field out of `~/.codex/auth.json` (value `chatgpt`, no token
  printed). It should not have; nothing was copied, nothing else in that file was read,
  and no later step touches `~/.codex`.
- The agent shell this ran in is itself sandboxed, so Codex's bwrap sandbox fails inside it
  (`bwrap: loopback: Failed RTM_NEWADDR`). Seen before on 2026-08-23. Codex launched from
  Electron on a laptop is not nested; tests that need the real sandbox run with the
  tool sandbox off.

## Codex 0.154.0 (latest stable, 2026-09-09) - verified from source, not docs

Source: sparse clone of `openai/codex` at tag `rust-v0.154.0`. Findings:

1. **Where ChatGPT-auth requests go.** `ModelProviderInfo::to_api_provider`
   (`model-provider-info/src/lib.rs`): base URL = the provider's `base_url` if set, else
   `https://chatgpt.com/backend-api/codex` for ChatGPT auth modes. Endpoint paths under it:
   `responses` (SSE), `responses/compact`, `memories/trace_summarize`, `alpha/search`,
   `models`.
2. **`[model_providers.openai]` in config.toml is ignored.** `merge_configured_model_providers`
   does `entry(key).or_insert(provider)` - the built-in wins. The supported knob is the
   top-level `openai_base_url` (`config/src/config_toml.rs:401`, "Base URL override for the
   built-in openai model provider"). So the brief's "provider base-URL override" has a
   different spelling than it assumed. `supports_codex_backend_routes()` stays true only if
   the override ends with `/backend-api/codex`, so the loopback URL must keep that suffix.
3. **Transport is WebSocket first.** The openai provider has `supports_websockets: true` and
   it cannot be turned off by config (see 2). `stream_responses_websocket` falls back to
   HTTP SSE for the rest of the session exactly when the upgrade returns **HTTP 426**
   (`core/src/client.rs:1808`). The proxy therefore answers every `Upgrade: websocket` with
   426, and Codex uses plain `POST .../responses` with `text/event-stream`.
4. **Request bodies are zstd-compressed** when `enable_request_compression` (stable, on by
   default) and ChatGPT auth and the openai provider all hold (`core/src/client.rs:1535`).
   The IO config disables the feature; the proxy still refuses any `Content-Encoding` it
   cannot decode rather than forwarding bytes it did not read.
5. **Other ChatGPT traffic** (`backend-client`): rate limits, `wham/accounts/check`,
   `wham/profiles/me`, `wham/config/bundle`, `wham/settings/user`, plugins - all under
   `chatgpt_base_url` (default `https://chatgpt.com/backend-api/`). None carry workspace
   content. Both base URLs are pointed at the proxy so one log shows everything Codex sent.
6. **Auth storage**: `auth.json` under `CODEX_HOME` in File mode (`secret_auth_storage`
   feature is off by default; `codex doctor --json` reports `"auth storage mode": "File"`).
   `codex login status` prints `Logged in using ChatGPT` / `Not logged in` (exit 1) on
   stderr - a supported status check that never exposes tokens.
7. **Login**: `codex login` = browser flow (`webbrowser::open`, callback on
   `localhost:1455`, prints the auth URL on stderr if the browser did not open);
   `codex login --device-auth` prints a URL and a one-time code. Both honour `CODEX_HOME`.
   Login first revokes any credential in *that* `CODEX_HOME` only.
8. **SSE events Codex consumes** (`codex-api/src/sse/responses.rs`): `output_item.done`,
   `output_text.delta`, `reasoning_summary_text.delta/.done`, `reasoning_text.delta`,
   `custom_tool_call_input.delta`, `created`, `failed`, `incomplete`, `completed`,
   `output_item.added`, `reasoning_summary_part.added`; `function_call_arguments.delta`
   and `output_text.done` are ignored by Codex but still transformed for safety.
9. **Sandbox network**: `workspace-write` maps to `NetworkSandboxPolicy::Restricted`
   unless `network_access = true` (`config/src/config_toml.rs:796`). So commands Codex
   runs under its default sandbox have no network; the Responses traffic is the only
   default egress, and it goes through the proxy.
10. **Bundling**: GitHub releases ship a single static binary per target
    (`codex-<triple>.tar.gz`, one file inside). Pinned below.

## Pinned Codex binary

| target | asset (rust-v0.154.0) | tar.gz sha256 | binary sha256 |
|---|---|---|---|
| linux-arm64 | `codex-aarch64-unknown-linux-musl.tar.gz` | `583b48df32804213bdcd338c2e5adb06b34340821fa757a726cc0a524fa33c27` | `9b7c1c7abdc26fc3c4f47c77656a8e9121def5483dbae830ef1ee561758448a9` |
| linux-x64 | `codex-x86_64-unknown-linux-musl.tar.gz` | `d7e18b2597ae8f242f5f31ee9e90deef48dbc9edd634d9868fb6435d08c07f02` | `3188814c35471432d4123203e0eb38e5bddc60226e3d7ddf0e59e649ea140022` |

Recorded in `app/io/codex-pins.json`; fetched by `node fetch-codex.js` into the gitignored
`app/io/codex-bin/<platform>-<arch>/codex`. `./linux-arm64/codex --version` -> `codex-cli 0.154.0`.
macOS assets exist (`codex-aarch64-apple-darwin`, `codex-x86_64-apple-darwin`) and are
pinned but not fetched or tested.

## The shape to build

```
renderer (ui/index.html, served by service.py)
   xterm.js  <-IPC->  main.js: node-pty  ->  codex-bin/<plat>/codex
                                              CODEX_HOME=<data>/codex/home
                                              cwd=<sheltered folder>
                                              config.toml written by io on every launch:
                                                openai_base_url  = http://127.0.0.1:P/backend-api/codex
                                                chatgpt_base_url = http://127.0.0.1:P/backend-api/
                                                features.enable_request_compression = false
   service.py: privacy proxy on 127.0.0.1:P  (second ThreadingHTTPServer, same process,
               same PseudonymMap as the chat)
       POST backend-api/codex/responses         : body strings -> tokens; SSE -> rehydrate, streaming
       POST backend-api/codex/responses/compact : body -> tokens; JSON reply -> rehydrate
       POST backend-api/codex/memories/*, alpha/search : same, JSON both ways
       GET  backend-api/codex/models, backend-api/wham/* : pass through, logged
       Upgrade: websocket                       : 426
       anything else                            : 403, logged
       not accepted / no vault                  : 403 on everything (fail closed)
```

Outbound policy = io's existing question policy, applied per string: known values (vault,
longest first) -> partial known NAME/PLACE words -> detector for unseen values, where the
detector is regex validators (phones, Aadhaar, emails, accounts...) on every string and
GLiNER additionally on `role: user` messages only (the same thing chat does to a typed
question today; running GLiNER over every tool output would take seconds per turn on CPU).
Each string is transformed once and cached by hash, because Codex resends the whole
history every turn.

Inbound: `pmap.rehydrate` on every string; for `*.delta` events the tail that could be the
start of a token (`[A-Z][A-Z_]*\d*$`) is held back until the next delta or the `.done`
event, so a token split across two chunks is still restored.

Login UX (user's amendment to the brief): the provider screen gets a third choice, **Sign in
with ChatGPT**, next to API key / server, so login is asked as soon as io opens.

## Next

Spike 1 (routing + isolation) and spike 2 (streaming round trip), with `codex exec` first
(scriptable) and the TUI after. Evidence goes to `benchmarks/runs/2026-09-14-io-codex/`.

## 18:00 - Spike 2 passed on the first real run (streaming round trip, real Codex)

`benchmarks/runs/2026-09-14-io-codex/spike2_exec.py`: bundled `codex exec` 0.154.0, custom
provider `io-dev` -> proxy `/dev/v1` -> OpenRouter `/api/v1/responses` (OpenAI-shaped SSE)
with `openai/gpt-5.2`, a deterministic 6-value mapping, a workspace CSV holding the values.
Prompt: read the file with `cat`, answer about two named people.

Result (`spike2-out/summary.json`): exit 0 in 5.8 s, 2 requests, upstream traffic held
`NAME_001 NAME_002 PHONE_001 PHONE_002 PLACE_001 PLACE_003` and **zero** real values (the
`cat` output was tokenised in the `function_call_output` item, the prompt in the user
message); the second response had 24 restorations; Codex's own answer quoted
`SecretVillage`, `9876543210`, `Alice Example`. Proxy log lines carry only ids, sizes,
counts and latency. Request shape seen: `store:false`, `stream:true`,
`include:[reasoning.encrypted_content]`, 17 KB `instructions`, tools `exec_command`,
`write_stdin`, `request_user_input`, `apply_patch` (custom), `view_image`, `tool_search`,
`web_search`. Note for the privacy claim: `web_search` runs at the provider, from the
tokenised view - the model never has a real value to search for, but the search itself is
provider-side traffic.

Two things learned: (1) this box's kernel refuses bwrap (`loopback: Failed RTM_NEWADDR`)
even outside the tool sandbox, so the first run had Codex politely refusing to `cat`; the
spike bypasses Codex's sandbox on this machine only (throwaway workspace). On the laptop
the sandbox is the default and stays on. (2) `supports_websockets=false` is honoured on a
*custom* provider; for the built-in openai provider the proxy's 426 answer is the mechanism.

## 18:20 - Spike 1 passed: ChatGPT-mode Codex routes through the loopback proxy

`benchmarks/runs/2026-09-14-io-codex/spike1_routing.py`. Isolated `CODEX_HOME` (a scratch
directory; `codex login status` there says `Not logged in` before the fixture), a
*fixture* `auth.json` (JWT-shaped id_token carrying the claims Codex parses, placeholder
access/refresh tokens - signed by nobody), io's config (`openai_base_url` and
`chatgpt_base_url` at the proxy), proxy upstream = the real `https://chatgpt.com`.

What the proxy saw, in order (`spike1-out/summary.json`):

1. `GET /backend-api/ps/plugins/suggested/codex` -> 403 (not on the allow list)
2. `POST /backend-api/ps/mcp` -> 403 twice (Codex's hosted-apps MCP; its rmcp worker logs
   the refusal and carries on)
3. `POST /backend-api/codex/responses` with `Upgrade: websocket` -> **426** (Codex logs
   "failed to connect to websocket: 426 Upgrade Required ... ws://127.0.0.1:<port>/...")
4. `POST /backend-api/codex/responses`, bearer auth, SSE -> forwarded -> **401 from
   chatgpt.com** ("Could not validate your token") - the fixture doing its job
5. one retry of 4, then Codex tried a token refresh at `auth.openai.com` directly (the OAuth
   token endpoint, no workspace content) and gave up: "Please log out and sign in again"
6. `POST /backend-api/codex/analytics-events/events` -> 403

So with only configuration, ChatGPT-mode Codex sends its model traffic to 127.0.0.1 and
uses plain SSE. The last step - a real token from the user's account B - is the one thing
this machine cannot do; the UI's Connect ChatGPT runs the same `codex login` in the same
home. Decisions from the extra endpoints: hosted apps/MCP, plugin suggestions and
analytics stay refused at the proxy *and* are switched off in io's config
(`features.apps/plugins/remote_plugin = false`, `[analytics] enabled = false`) so the
transcript is not full of 403 noise. The developer `~/.codex` was never read; the fixture
home holds only what the spike wrote (listed in the summary).

## 18:50 - The embedded terminal works; the first live turn was stopped by our own leak gate

Built: `app/io/codex.js` (binary path, io-owned home, config writer, `login status`,
`codex login [--device-auth]` with the link/code streamed to the page, node-pty session),
IPC in `main.js`/`preload.js` (terminal bytes and status strings only), `ui/index.html`
(a third choice on the first screen, **Sign in with ChatGPT**; a sign-in screen; a terminal
screen with the three status pills and a footer that says *Protected by io* only when policy,
proxy and login all hold), `codex_proxy.py` wired into `service.py` as `IoPolicy` (io's
question policy per string, GLiNER on role=user text), xterm.js 6.0.0 vendored under
`ui/vendor/`, node-pty 1.1.0 (N-API; builds from source on Linux, loads in Electron 33).

Driven for real under Xvfb by `benchmarks/runs/2026-09-14-io-codex/drive.js` (playwright over
CDP against the dev checkout). Sign-in screen (no credential) shows *Not connected yet*;
"use a code instead" ran the bundled `codex login --device-auth` and the page showed a real
one-time code and `https://auth.openai.com/codex/device` (cancelled; screenshots in
`drive-login/`). With the fixture credential the gate passes, the review sheet and preview
are unchanged, "Looks right" opens the terminal and the real Codex 0.154.0 TUI paints inside
Electron (`drive-out/06-codex-terminal-before-prompt.png`).

Three real bugs found by using it, all fixed:

1. `GET /dev/v1/models` through the proxy sent a 4-byte body (`null`) with a GET and the
   upstream closed the connection after 15 s, three times; the TUI sat on "model: loading".
   GETs now carry no body and are passed through. Same code path as `backend-api/codex/models`
   on the real upstream.
2. The stylesheet hid the device code (`display:none` beaten by `style.display=''`) - the
   code was in the DOM but invisible. Same bug class on the terminal's error banner. Fixed.
3. **The leak gate stopped a real turn.** The proxy refused `POST responses` (50 KB) three
   times with "1 private value(s) still present" while the title-generation request went
   through. Vault after the run: 14 codes, four of them minted by GLiNER from Codex's own
   `<environment_context>` message: `bprashanth` (the home directory in `<cwd>`) as a NAME,
   `Asia` and `Kolkata` (the timezone) as PLACEs. The outbound cache had already
   transformed the 17 KB `instructions` string under the older vault, so when the same
   request was re-serialised the cached string still held one of the new values and the
   final known-values check caught it. Two fixes: the cache key now includes a vault
   version (`IoPolicy.version()` = vault identity + size; regression test
   `test_cache_is_invalidated_when_the_vault_grows`), and the scanner no longer runs on
   role=user messages that are Codex wrappers (`<environment_context>`,
   `<user_instructions>`, `<permissions instructions>`, ...); the validators still do.

Also learned: Codex's composer treats a burst of keystrokes as a paste and an Enter inside
the burst as a newline, so the driver waits a second before Enter, as a person would.

## 19:05 - End to end in the Electron app: passed, with evidence

`drive-out/` (dev checkout, fixture credential, dev upstream behind the real proxy,
`results.json`, 17 screenshots, `proxy-dump/`, `io.log`). No timeouts, no errors:

- review sheet flags name/village/phone; preview shows `NAME_001 PLACE_001 PHONE_001`;
  Looks right -> terminal with *Privacy 11 codes approved · Proxy active · ChatGPT connected*
  and *Protected by io*.
- Turn 1: "Read visits.csv with cat and tell me which village Alice Example lives in..." ->
  Codex ran `cat`, answered **"Alice Example lives in SecretVillage and her phone is
  9876543210."** in the terminal (`09-codex-answer.png`); the model saw `NAME_001`,
  `PLACE_001`, `PHONE_001` (tool output tokenised, 96 SSE events restored).
- Turn 2: long numbered list + 10-line summary, scroll state (`10`, `11`).
- Turn 3: "Append a new row for Kiran Demo in SecretVillage with phone 9222222222" ->
  Codex ran `printf ... >> visits.csv && tail -n 1 visits.csv`; **the file on disk holds the
  real row** `Kiran Demo,SecretVillage,9222222222,3,`; the typed values were minted as
  `NAME_005` / `PHONE_006` (scanner + validator on the person's text) and that is what left.
- Fail closed: another folder opened in io while Codex still ran -> the proxy answered 403
  "the privacy policy for this folder has not been approved", Codex showed it after 5
  retries, the footer flipped to **NOT protected** with the red banner (`13`, `14`).
- Resize 1280x820 -> 900x600: PTY followed, 146x41 -> 101x25 (`15`).
- Quit and restart: `codex login status` in io's home still "Logged in using ChatGPT";
  `~/.codex/auth.json` size and mtime identical before and after (`results.json`).

Evidence scan over all 12 upstream bodies (1.03 MB): tokens `NAME_001..005`,
`PHONE_001..006`, `PLACE_001..003`; **none** of the 12 synthetic values present. One word did
leave as itself, 36 times: `bprashanth`, the repository path under `<cwd>` - not beneficiary
data, but a reminder that *paths* go to the model as paths. Two scanner quirks in the vault
worth knowing: "phone number" became `PHONE_005` (GLiNER over the typed sentence) and
"borewell" a `PLACE` (from the notes column) - the same behaviour a typed chat question
has today, visible in the vault count.

One expectation in the driver was wrong, not the app: re-opening the approved folder after
Codex edited a file rescans it (the folder signature changed) and the policy has to be
approved again with Looks right; until then the terminal says NOT protected and Codex is
refused. Correct, and documented as a limitation to smooth later.

Packaging: `npm run pack` now builds one architecture per machine (the cross-build of
node-pty from arm64 to x64 died on `g++ -m64`); `io-linux-arm64.tar.gz` carries
`resources/codex/linux-arm64/codex`, `resources/io/codex_proxy.py`, `ui/vendor/xterm*`
and the unpacked node-pty.

## 19:25 - Packaged build, copied elsewhere, passes the same drive

`npm run pack` (arm64, this machine) -> `dist/io-linux-arm64.tar.gz` (200 MB; the static
Codex binary is 227 MB uncompressed). Unpacked into a scratch directory that stands in for
"copied off a USB stick", launched from there (`drive.js --exe .../io-linux-arm64/io`,
`drive-packaged/`), with the checkout's venv and model cache linked into the data dir in
place of the thin build's first-run install. Same 17 screenshots, same outcome: answer
restored, file edited with real values, fail-closed banner, PTY resize, restart with the
login kept, `~/.codex` untouched, 12 upstream bodies with 14 codes and **zero** real values.
`results.json` names the binary that answered `codex login status`:
`.../io-linux-arm64/resources/codex/linux-arm64/codex` - the bundled one.

## What is and is not done, against the brief's definition of done

Done, with evidence: bundled pinned Codex; isolated `CODEX_HOME`; the proxy as the single
enforcement point (outbound codes, inbound values, streamed deltas, fail closed); the
embedded PTY terminal; approval -> launch gating; the status bar that only says protected
when it is; the ChatGPT sign-in screen with browser and device-code flows running the real
`codex login`; 25 proxy tests + 8 launcher tests; a real Electron run; a packaged run from
a copied location; docs (`docs/io-codex.md`, READMEs) and this trail.

Not done here, and why:

- **Account B.** The one step that needs a person with a ChatGPT account and a browser.
  Spike 1 shows ChatGPT-mode Codex reaching the proxy and the proxy reaching chatgpt.com
  with the credential Codex holds; the drive shows the sign-in screen producing a real
  device code. What remains is pressing Connect ChatGPT on a laptop and watching the first
  turn come back. Expected wrinkle to watch for: `GET backend-api/codex/models` and the
  `wham/*` calls pass through the proxy untouched - if chatgpt.com rejects a header the
  proxy forwards (it forwards everything except hop-by-hop), the log will show it.
- **x64 Linux.** Binary pinned and hashed; node-pty compiles on x64 the same way; not run.
- **macOS / Windows.** Not built. Gaps listed in `docs/io-codex.md`.
- **Re-approval after Codex edits a file** when the folder is re-opened (correct, but a
  speed bump).
- **Paths.** Folder and file names reach the model as themselves; contents do not.
