# io + Codex: the real Codex CLI inside io, behind the privacy boundary

Status 2026-09-14: built and verified on Linux (arm64 DGX; x64 binary pinned, not yet run on
an x64 machine). The one step that needs a person is signing io's Codex into a ChatGPT
account; everything either side of that step has evidence in
`benchmarks/runs/2026-09-14-io-codex/` and `chronology/2026-09-14T1730-*`.

## What a user does

1. Start io. On the first screen choose **Sign in with ChatGPT** (an API key or a server
   address still work; they use the old chat).
2. **Connect ChatGPT**: io runs its own bundled Codex's `codex login`. A browser opens on
   OpenAI's sign-in page; "use a code instead" shows a one-time code for a phone or another
   machine. io only ever shows the link and the code; the tokens go into io's own Codex
   home, never through the page.
3. Pick a folder, review what the scanner flagged, press **Preview** to see what leaves,
   press **Looks right**.
4. A Codex terminal opens inside io, in that folder. Use it exactly like Codex.

The bar above the terminal says *Privacy: N codes approved · Proxy: active · ChatGPT:
connected*, and the footer says *Protected by io* only when all three are true, with a live
count of requests sent as codes. If the policy is not approved (a different folder was
opened, say) the footer says *NOT protected* and Codex's requests are refused.

## What is actually happening

```
renderer (ui/index.html)         main.js                        service.py
  xterm.js  <---- IPC ---->  node-pty  --->  codex-bin/<target>/codex
                                              CODEX_HOME=<data>/codex/home
                                              cwd=<the sheltered folder>
                                              config.toml (rewritten every launch):
                                                openai_base_url  = http://127.0.0.1:P/backend-api/codex
                                                chatgpt_base_url = http://127.0.0.1:P/backend-api/
                                                enable_request_compression = false
                                                                     |
                                                                     v
                                                    codex_proxy.Proxy on 127.0.0.1:P
                                                    (same process and same vault as chat)
                                                      out: strings -> codes   in: codes -> values
                                                                     |
                                                                     v HTTPS
                                                             chatgpt.com (ChatGPT OAuth)
```

Three views of the same data exist at once:

| where | what it holds |
|---|---|
| the files on disk | real values, never rewritten by io |
| Codex (the terminal, its session files, the commands it runs) | real values, because it edits files and runs commands |
| the model provider | codes only (`NAME_001`, `PHONE_002`, `PLACE_003`) |

The proxy is the boundary between the last two. It is the *only* place enforcement happens:
what the user types in the terminal, what `cat` prints, what a patch contains and what the
model says all cross it. Nothing depends on pre-processing files or intercepting keystrokes.

### Outbound policy (request bodies)

Per string in the JSON body, the same policy `/api/chat` applies to a typed question:

1. exact known values from the folder's vault, longest first (case-insensitive);
2. the regex validators (phones, Aadhaar, emails, account numbers, PAN, ...) on every
   string, minting a new code for a value never seen before;
3. the on-device scanner (GLiNER) additionally on `role: user` text - what the person
   typed - never on tool output (seconds per turn on CPU, and the files were already scanned).

Values the user chose to *keep* in the review sheet stay clear. Each string is transformed
once and cached (Codex resends the whole history every turn). After transformation the
serialised body is checked once more against the vault; any known value still present
stops the request with 403 rather than sending it.

### Inbound (responses)

Every string in a JSON reply and every SSE event is rehydrated. For `*.delta` events the
tail of a chunk that could be the start of a code (`NAME_0` when the next chunk is `01`) is
held until the next chunk or the `.done` event, so a code split across two chunks still
comes back as the real value. Codes the vault does not know pass through untouched.

### What is refused

| request | reason |
|---|---|
| `Upgrade: websocket` | 426, so Codex falls back to plain SSE (verified in 0.154.0 source and live) |
| `POST backend-api/ps/mcp` | OpenAI-hosted apps/MCP: tool arguments could flow there |
| `GET backend-api/ps/plugins/...` | plugin catalogue |
| `POST backend-api/codex/analytics-events/events` | telemetry |
| anything not on the allow list | fail closed |
| any request while the folder's policy is not approved | fail closed |
| a body the proxy cannot read (zstd, non-JSON) | 415 / 400, never forwarded |
| a known value still present after transformation | 403 |

Passed through unchanged, logged: `GET backend-api/codex/models`, `backend-api/wham/*`
(rate limits, account check, settings; no workspace content).

### The session, from the person's side

- `<home>/io.config.toml` (launched with `-p io`) carries io's settings; Codex's own
  `config.toml` keeps what the person picks with `/model`. Effort is low by default.
- `<home>/AGENTS.md`, rewritten each launch, tells Codex who it is talking to: plain words,
  no technical questions, pages opened in the browser, codes are labels, stay in the folder.
- Copy and paste work the usual way (Ctrl+C with a selection, Ctrl+V, right-click); links
  are clickable; a local file Codex wrote under the folder opens with one click.
- **A conversation without a folder**: type into the chat box on the shelf. Codex runs in an
  empty io-owned folder with network on; "attach a file" copies a file in, runs the same
  review, and returns to the same conversation. Codex's sandbox does not stop commands
  from *reading* elsewhere on disk; the instruction to stay in the folder is text, and a
  `[permissions]` filesystem profile is the candidate wall.

## The privacy claim, precisely

**io tokenises what Codex sends to the model provider.** That is the claim, and it is
enforced at one point with tests around it.

What it does *not* claim:

- **Commands Codex runs** are not proxied. Under Codex's default `workspace-write` sandbox
  they have no network (`NetworkSandboxPolicy::Restricted`), so `curl` and Python sockets
  fail unless the user approves a command outside the sandbox. If a user says yes to
  "run this without the sandbox", that command can do anything, including send a file
  somewhere. The io footer cannot see that.
- **Codex's `web_search` tool** runs at the provider, from the tokenised context: the
  model never holds a real value to search for, but the search is provider-side traffic.
- **Token refresh** goes from Codex to `auth.openai.com` directly (the OAuth endpoint; no
  workspace content).
- **MCP servers / plugins / apps** are switched off in io's config and refused by the
  proxy. A user who edits io's config.toml by hand gets it rewritten on the next launch.

Two verified facts worth restating: the proxy binds `127.0.0.1` on an OS-chosen port and
refuses everything until a policy is approved; and a proxy that is down means Codex
requests fail with a visible error, never a direct connection to OpenAI (the config has no
other URL).

## Isolation from any other Codex on the machine

- The binary is `app/io/codex-bin/<platform>-<arch>/bin/codex` in a checkout and
  `resources/codex/<platform>-<arch>/bin/codex` in a packaged build, resolved in exactly one
  function (`codex.js: bundledCodexPath`). A system `codex` on PATH is never consulted.
  What ships is the release *package* tree, not the bare binary: `bin/codex-code-mode-host`
  (the process Codex runs every command through since 0.154; without it every shell call
  fails closed, which is exactly what the first laptop run showed), `codex-path/rg`,
  `codex-resources/bwrap` and `codex-resources/zsh`. Codex finds them relative to its own
  executable.
- `CODEX_HOME` is `<data>/codex/home` (`~/.local/share/io/codex/home`, or `io-data/codex/home`
  on a portable stick). `~/.codex` is never read, written or listed; the drive script records
  the size and mtime of `~/.codex/auth.json` before and after and they are equal.
- `codex login` writes `auth.json` into that home (File storage; the keyring feature is off
  by default in 0.154.0). `codex login status` is how io asks "connected?" - a supported
  command whose answer is one line and never a token.
- `OPENAI_*` and `CODEX_API_KEY` are stripped from Codex's environment, so a developer's
  API key cannot become the login by accident.

Portable mode: io's design is that a stick leaves nothing on someone else's laptop, so in
portable mode the Codex home (and therefore the OAuth token) lives on the stick with the
vault. That is the opposite of "never put credentials on the USB" and it is deliberate; a
user who wants the token off the stick deletes `io-data/codex/`. In normal mode the token is
in the per-user data dir.

## Development and QA on a machine without a display or a spare ChatGPT account

- `benchmarks/runs/2026-09-14-io-codex/spike1_routing.py` - ChatGPT-mode Codex, isolated
  home, fixture credential, proxy in front of the real chatgpt.com: proves routing and the
  426 fallback (upstream says 401, as it should for a fixture).
- `spike2_exec.py` - `codex exec` through the proxy to an OpenAI-shaped Responses server
  (OpenRouter), synthetic PII in a CSV: tokens upstream, real values back, file read via
  a tool call.
- `drive.js` - the Electron app under Xvfb, playwright over CDP, screenshots of every
  screen, a fixture credential in io's Codex home (so the sign-in gate passes) and the dev
  upstream behind the same proxy (`IO_CODEX_DEV_PROVIDER=1`, `IO_PROXY_DEV_UPSTREAM`,
  `IO_DEV_KEY`). None of these env vars exist in a user's environment.
- `IO_CODEX_NO_SANDBOX=1` sets `sandbox_mode = "danger-full-access"` for machines whose
  kernel refuses bwrap (the DGX). Never for users.
- `IO_PROXY_DUMP=<dir>` writes the tokenised request bodies and the raw upstream events -
  the evidence that only codes left - with nothing from the local side.

Tests: `app/io/.venv/bin/python app/io/tests/test_codex_proxy.py` (24: substitutions,
overlaps, Unicode, JSON, split tokens across chunks, tool args and outputs, unknown codes,
426, refusals, encodings, upstream errors, upstream down, not-ready, leak stop, multi-turn
cache, live-engine policy) and `node app/io/tests/test_codex_launcher.js` (8: paths, home,
config, env).

## Building

`node fetch-codex.js` (this machine's target) or `node fetch-codex.js linux-x64` before
`npm run pack`; the packer copies `codex-bin/<target>` into `resources/codex/<target>` and
warns if it is missing. One architecture per build machine: node-pty is compiled for the
target and the python payload has the same rule. The packaged arm64 build was driven end to
end from a copied location on 2026-09-14 (`benchmarks/runs/2026-09-14-io-codex/drive-packaged/`).

## Platforms

| | state |
|---|---|
| Linux x64 | binary pinned and hashed (`codex-x86_64-unknown-linux-musl`, static); node-pty builds from source with the usual toolchain; **not yet run** on an x64 laptop |
| Linux arm64 | verified end to end here |
| macOS | Codex ships `aarch64-apple-darwin` and `x86_64-apple-darwin` binaries; node-pty has prebuilds for both; `fetch-codex.js darwin-arm64` records the hash on first fetch. Open questions before claiming support: Gatekeeper on a binary copied from USB (io's own .app is already unsigned and needs right-click Open; the codex binary inside `resources/` inherits that), `xattr` quarantine on the tarball, and whether `codex login`'s `localhost:1455` callback works from a sandboxed .app (it should: io is not sandboxed). Not built, not tested. |
| Windows | Codex publishes `x86_64-pc-windows-msvc` binaries; node-pty uses ConPTY and has prebuilds; Codex's Windows sandbox is a different mechanism (experimental). Nothing here is tested on Windows. The proxy is pure python and needs nothing platform-specific. |

## Known limitations

- **Paths leave as paths.** Codex tells the model its working directory and file names
  (`<cwd>`, `cat visits.csv`). A folder called `~/clients/Jane-Rao/` would name Jane. The
  scan covers file *contents*; folder and file names are not in the vault unless a validator
  matches them. (Seen in the drive: the repository path, 36 times, tokens for everything else.)
- **Editing files changes the folder signature.** Codex edits files; when the user later
  re-opens that folder from the shelf, io rescans it and asks for Looks right again. Until
  then the terminal says NOT protected and requests are refused. Within one session nothing
  changes.

- The GLiNER pass on typed text costs about a second per new user message on CPU; tool
  outputs get the regex validators only (the files were scanned when the folder was
  sheltered). A name that appears only in a file *outside* the sheltered folder and is not
  in the vault goes out as itself unless a validator catches it.
- Codes are minted for values the validators find in tool output (a phone number in a log
  Codex reads, say). That is the same behaviour as a typed question in chat; the status bar
  shows the vault growing.
- `model: loading` in the TUI header for a while on the dev upstream: Codex asks
  `/models` at start; on chatgpt.com that call passes through the proxy.
- Reattaching to a running session after a page reload shows only new output; scrollback
  from before the reload is not replayed.
