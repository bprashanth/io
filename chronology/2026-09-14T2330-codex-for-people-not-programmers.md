# 2026-09-14 23:30 - Codex for people who are not programmers: terminal manners, AGENTS.md, a conversation without a folder, and the scan clock

Asked for, after the first real run on the laptop: copy/paste and clickable links in the
terminal; Codex told who it is talking to (no jargon, no technical questions back, open
pages in the browser); the cheapest model by default; a way to talk to Codex without
sheltering a folder, with "attach a file" bringing a file through the same review; and the
scan of a nine-file corpus that took minutes.

## The scan clock (this DGX; `benchmarks/pii/corpus`, 5 tables incl. two sheets, 3 text/pdf)

| path | review scan | coding on Looks right |
|---|---|---|
| on-device model, CPU, engine as of this morning | minutes on the laptop (user report) | |
| on-device model, CPU, one model pass + batched chunks | 87.5 s | 18.1 s |
| privacy server on the DGX GPU | 16.6 s | 7.2 s |
| + per-cell calls batched (`cell_spans`, 200 cells -> a few calls) | **5.1 s** | 7.4 s |

The server path was bound by round trips, not the GPU: the review sheet asks the scanner
about each of the first 200 cells of every free-text column, one call each. Joined into
1,500-character chunks with the separator `redact_cells` already uses, a column is a few
calls. Same spans, same "why" text on the cells (checked: the hidden columns and cell counts
per table are identical before and after). Left: the column classifier still makes one call
per window of eight values, and Looks right still codes column by column; both are the next
batching targets if 7 s matters. Nothing here needed excel-only sheltering.

## Codex settings live in a profile now

`<home>/io.config.toml`, launched with `-p io`. Codex layers it over its own `config.toml`,
so the model a person picks with `/model` is kept across launches (io used to rewrite
`config.toml` every time and would have wiped it). `model_reasoning_effort = "low"` by
default; the model itself is left to Codex's default for the account's plan - naming a
model the plan does not have only produces "metadata not found" warnings. `--profile` is
accepted by runtime commands only (`codex`, `exec`, ...), so login and status run without
it, which is fine: they need no base URL.

## AGENTS.md

`<home>/AGENTS.md` is Codex's *global* instructions file (read by
`codex-home/src/instructions`, "Failed to read global AGENTS.md" is its error string); a
project AGENTS.md in the folder is appended after it, never instead. io writes it on every
launch: the audience (NGO staff in India, not programmers), plain words, no technical
questions back, short answers, charts and reports as one self-contained HTML file opened
with `xdg-open` / `open` / `start`, paths and links on their own line, codes like NAME_001
are labels never to be explained or guessed, do not upload or paste their data anywhere,
work only inside the current folder. The conversation variant adds: no sheltered folder
here, do not read elsewhere, tell them to press "attach a file".

## Terminal manners

Ctrl+C with a selection copies (without one it still interrupts Codex); Ctrl+V and
Ctrl+Shift+V paste; right-click copies a selection or pastes the clipboard. Links are
clickable (xterm web-links addon, vendored) and go to the shell's `open-external`, which
opens http(s) anywhere, and local files only under the sheltered folder or io's data dir
(that is where Codex writes a dashboard), nothing else.

## A conversation without a folder

Typing into the chat box on the shelf, in Codex mode, calls `/api/chat-workspace`: an empty
io-owned folder under `<IO_HOME>/chats/<stamp>/`, approved trivially (nothing to review,
vault empty), Codex started there with the conversation profile (`network_access = true`
so it can fetch what it is asked for) and the first message typed in on the person's
behalf once the screen is up (`codex-say`: the text, then Enter after 700 ms, because the
composer treats a burst as a paste). The header says "conversation (no data)".

"attach a file" (`pick-file` dialog -> `/api/attach`): the file is copied into that folder
(Codex works on real files), the folder is rescanned, the review sheet shows exactly what
will leave, approval is withdrawn until Looks right, then back to the same terminal with
"I attached x.csv in this folder..." typed in. The proxy refuses in between.

Not solved: Codex's sandbox lets commands *read* anywhere on disk. In the conversation the
instruction not to read outside the folder is text, not a wall. Codex 0.154 has a
`[permissions.<name>.filesystem]` profile mechanism (`FilesystemPermissionsToml`, and a
managed `deny_read`) that could make it a wall; not tried yet.

## Driven (`drive-chat/`, `drive-profile/`)

Profile-based config: the full folder drive passes unchanged (answer restored, edit on
disk, fail closed, restart keeps the login, `~/.codex` untouched); `io.config.toml` and
`AGENTS.md` sit in the home, no `config.toml` was needed.

Conversation: shelf -> chat box -> Codex up in `chats/20260914-231303` with the header
"conversation (no data)" -> the typed question arrived intact and was answered in the
AGENTS.md register ("Use short, clear names that say what the column contains...") ->
attach visits.csv -> review sheet (11 codes) -> Looks right -> same terminal, "I attached
visits.csv..." typed in. Two fixes on the way: the typed-in line is now a bracketed paste
(a bare "?" was eaten as the shortcuts key, and Enter 700 ms after a burst was folded into
it; 1.5 s works), and the proxy walks a request body twice when the vault grows during the
walk - the scanner minted a code from the user message after the instructions string had
already been transformed, and the final check stopped the turn once before the retry
went through. Regression test added. WebSocket 426s no longer count as "refused" in the
footer.

## 23:45 - Second laptop run: the wall, the 403, and what the page should not do

The user's screenshot (`/tmp/io_codex_fail_2.png` on the laptop): a conversation, two CRM
exports attached (1,473 codes), both summarised correctly through the proxy; then every
question refused with "io stopped this request: 1 private value(s) were about to leave".
Diagnosis by construction: the final leak check ran over the whole serialised body, and a
1,473-value vault from a CRM (tags, notes) can contain a word that is also a protocol
constant - "auto", "text", "low" - which then matches inside `"tool_choice": "auto"` on
every request. The check now runs over the transformed content strings only (the walk the
transform itself did), and the log line names the *code* and the JSON keys where a leak
sat, never the value (`leaks: [{"code": "NAME_017", "keys": ["text"]}]`). Test added.

Attaching a file no longer types a line into Codex: the file is copied in, the review runs,
and a grey note says "x.csv is in the folder now. Ask Codex about it in your own words."
The red "policy no longer approved" banner that flashed during the rescan was the status
poll seeing approval withdrawn for a moment; suppressed while an attach is in progress.
"folders" is "home"; "End session" is gone. Opening a different folder now replaces the
running Codex instead of refusing with "a session is already running"; the same folder
reattaches. Home leaves Codex running in the background so coming back resumes.

**The wall.** Codex 0.154 permission profiles: `default_permissions = "io"` with
`[permissions.io.filesystem] ":minimal" = "read"` (what the platform needs to run
anything) and `[permissions.io.filesystem.":workspace_roots"] "." = "write"` (the cwd is
a workspace root by default) - everything else unreadable, enforced through bwrap
(`linux-sandbox/src/landlock.rs`: "Restricted read-only access is not supported by the
legacy Linux Landlock backend", which is the deprecated one). Network in the profile:
`enabled = true` for a conversation, `false` for a sheltered folder. Two facts learned
running it here: the profile is applied even to Codex's own read of `<home>/AGENTS.md`
("failed to load AGENTS.md instructions ... fs sandbox helper failed"), so that one file is
granted read; and this DGX cannot run bwrap, so the dev bypass skips the profile and the
wall itself is **untested until the laptop runs it**. Escape hatch: `IO_CODEX_NO_WALL=1`.
Check on the laptop: in a conversation ask "list the files in my home folder" - the
sandbox must refuse, and the AGENTS.md register must still be in the answers.

## 2026-09-15 09:30 - privacy.idli.cc live; the scan rewritten for a network instead of a loopback

The Cloudflare Tunnel answers (`/health` 200, `/scan` 200 in 0.13 s). Two things broke the
moment a real network sat between io and the scanner, and both are fixed:

1. Cloudflare's bot rules answer python's default user agent with 403 (`curl` got 200,
   io got 403). The client now sends `User-Agent: io-privacy-client/1`.
2. The review was written for a loopback: one HTTP call per question, 334 for the nine-file
   pii corpus. On the tailnet that was 5 s; through the tunnel from this box, 35 s. The
   tailnet shortcut is gone from the defaults (users in the office have no tailnet either;
   it would have hidden the delay everyone else pays) and the scan now batches:
   the server accepts `{"texts": [...]}` and answers in one GPU batch; the client and the
   GLiNER engine expose a `.many` path; `batched_calls` runs the classifier, the cell
   marks and the coding pass twice - once recording every text they ask about, once
   answering from a single batch - so each phase is one call per table. First attempt
   still made 220 calls: the validators+model wrapper was a plain lambda that lost the
   batch path; `State.with_regex` keeps it.

   Then the coding pass was 8 s with five calls in it: `known_regex` recompiled a
   1,100-value alternation every time a row minted a code, 107 rebuilds = 4.0 of 4.1 s
   (profiled). Bulk mode rebuilds every 64 values; free-text columns are coded last, after
   one refresh, so every name and place from the other columns is known by then - faster
   and better recall in the same change.

| corpus, via privacy.idli.cc from this box | calls | review scan | coding |
|---|---|---|---|
| per-question calls | 334 | 35.5 s | 9.8 s |
| batched, wrapper losing the batch path | 220 | 23.3 s | 10.8 s |
| batched | 20 | 3.4 s | 7.9 s |
| + regex rebuild throttle, free text last | 20 | **3.5 s** | **1.7 s** |

Same hidden columns and cell marks per table as the per-question run (one cell count moved
by one on a batch-padding difference); vault 1,108 codes both ways; zero vault values left
in the coded output.
