# 2026-09-15, 11:59 IST — first x64 laptop run: answers came back as codes

Machine: Pop!_OS 22.04, kernel 6.12.10, x64, GNOME on X11. First time io's Codex mode has
been run on an x64 laptop (`docs/io-codex.md` listed Linux x64 as "binary pinned, not yet
run"). Screenshots: `benchmarks/runs/2026-09-15-laptop/`. Synthetic corpus only
(`benchmarks/pii/corpus`); no real beneficiary data was opened.

## Getting it to start at all

Two things blocked the first launch, both already understood by the time of this run:

- `node-pty` was declared in `app/io/package.json` but absent from `node_modules`. `run.sh`
  only installs when `node_modules` is missing entirely, and the tree here predates the
  commit that added the dependency, so it was never picked up. `npm install` fixed it.
- The Chromium sandbox guard in `main.js` was standing the sandbox down whenever
  `chrome-sandbox` was not root:4755, and an unsandboxed Chromium on this machine cannot
  allocate shared memory at all — it aborts before the splash loads, with a misleading
  "/dev/shm" message. The fix (keep the sandbox when the namespace route is open) had
  already landed in `11bb364`; this run confirms it works here. `/dev/shm` itself was fine
  the whole time, and the same failure follows the allocation into TMPDIR.

## The real finding: nothing was being restored

Every answer reached the person as codes. Asked for the village in the first row of
`household_survey.csv`, Codex printed `PLACE_003`. Asked who `CFS0001` is, it printed
`NAME_001` and `NAME_200`. The footer read "0 restored" for the whole session, and no
response log line carried a `restored` or `events` field at all (screenshots 16, 22).

Cause: `Proxy._handle` decided how to treat the upstream response from its `Content-Type`
header, and chatgpt.com streams `/backend-api/codex/responses` back **with no Content-Type
at all**. I confirmed this by logging `ctype` live — it is the empty string. With no
"event-stream" and no "json" in it, the body fell through to the raw pass-through branch at
the end of the function: forwarded verbatim, `stream_sse` never entered, no rehydration.

The test suite never caught it because every SSE test in `test_codex_proxy.py` sets
`Content-Type: text/event-stream` on the fake upstream.

Fix in `codex_proxy.py`: on a content route, when the header says neither event-stream nor
json, read the first 8 KB and look at it — an SSE body opens with an `event:` or `data:`
line — then hand those already-read bytes to `stream_sse` as a `prefix` so nothing is lost.
Test added: `test_sse_without_a_content_type_is_still_restored`, with the upstream harness
taught to omit the header when `ctype` is None. It fails without the fix with exactly the
live symptom (`the name is NAME_001 today` instead of `the name is Alice Example today`).

Re-tested in the app: the same question now answers **Karpi**, which is the village in the
first data row, and the footer counts 45 restored (screenshot 24).

## Second finding: a conversation could not be typed into

Repro: open a sheltered folder, press **home**, type into the chat box on the shelf. The
conversation screen comes up, Codex's banner renders with the right chat folder, a real
codex process is running there — and the keyboard is dead. Nothing appears, and no request
reaches the proxy. The first message typed into the chat box is lost too. Pressing
**restart Codex** makes everything work (screenshots 32-38).

Cause: `main.js` keeps one module-level `session`, and the `onExit` callback closed over
that variable. Leaving the folder kills the old Codex; it takes a moment to die, and its
exit event arrives *after* the replacement has already been spawned and assigned. The late
callback then ran `session = null` on the **new** session. Output kept flowing, because
`onData` is bound to the pty object itself, but `codex-input` guards on `session` and so
dropped every keystroke. The same stale event also told the renderer Codex had ended, which
is where the spurious "restart Codex" button came from.

Fix: capture the pty in a local and only clear the handle if it is still the current one
(`if (session === mine) session = null`), and mark that exit `stale` so the renderer ignores
it. Re-tested: the chat-box message is delivered on the first try and Codex answers, with no
restart button (screenshot 49). A genuine exit still reports normally — verified by
accident when a Ctrl+C with no selection interrupted Codex and the end-of-session notice
appeared as it should (screenshot 51).

## Third finding: a page Codex writes cannot be opened

io's AGENTS.md tells Codex to open a page it has written with `xdg-open`. That cannot work
inside the wall: the "io" permissions profile grants `:minimal`, the workspace, tmp and
Codex's own package, and nothing else — in particular not the session D-Bus socket under
`/run/user/1000` that `gio open` needs. Worse, `xdg-open` exits 0 anyway, because its GNOME
branch only checks `gio help open`, so Codex believes it succeeded and tells the person "I
made and opened the map" when no window ever appeared. Reproduced outside io with an
unreachable bus socket: silent, no output, exit 0.

The fallback in AGENTS.md — print the path so they can click it — did not work either. The
terminal only loaded `WebLinksAddon`, which matches http(s) and nothing else, so the
filename Codex named was dead text.

Fixed the half that belongs to io: a link provider in `ui/index.html` makes an openable
filename or path clickable, and `open-external` in `main.js` now resolves a bare relative
name against the sheltered folder before the existing containment check decides. Clicking
`main_locations_map.html` in the terminal now opens it in the browser (verified).

**Left for a decision (not done):** whether Codex should be able to open a page itself.
Options are granting the sandbox the D-Bus socket, having io watch the folder for a new
page, or a small io-provided `open` shim on the sandbox PATH. All three change the wall or
add a mechanism, so they are not mine to choose.

## A map with no map under it

Asked to plot survey locations, Codex wrote a self-contained page: points positioned by
lat/lon on a CSS grid, no basemap. Pushed to add real streets, it referenced
`tile.openstreetmap.org` — and every tile came back **403, "App is not following the tile
usage policy"** (screenshot 28). So the page got worse, not better.

Three separate reasons a street basemap does not work today, worth recording together:

1. Codex cannot fetch anything at build time: network is off in a folder session
   (`enabled = false` in the profile).
2. At view time the browser does have network, but OSM refuses tiles to an unidentified
   `file://` page under its usage policy.
3. Even if tiles loaded, every tile request would carry the bounding box of the surveyed
   villages to a third-party server, outside io's proxy. io's privacy claim covers Codex to
   the model provider and nothing else, so this would be a real hole opened by a page io
   told Codex to write.

AGENTS.md already says pages must be self-contained and need no internet to view; Codex
overrode that when the person asked directly. **Left for a decision:** whether AGENTS.md
should tell Codex to refuse an external resource that would carry the person's data and say
why, and/or whether io should ship an offline outline basemap so "put it on a map" has an
honest answer. Both are product choices.

## What passed

- Confirm dialog lists spreadsheets as scanned, documents and pdf as coming soon, 16 other
  files ignored (screenshot 4). Review sheet flags names, birth dates and coach; Preview
  shows what actually leaves — codes for names and places, year only for dates (5, 6).
- "what files do you see?" answered with no approval prompt; the sandbox ran `rg --files` (9).
- The generated script uses the real column names `village`, `gps_lat`, `gps_lon`, and
  neither the script nor the page contains a single code (verified by grep).
- The wall held in both modes. In the folder session Codex declined `ls /home/desinotorious`
  and `cat /etc/hostname`; in a conversation it declined the same. Nothing outside the
  folder was read. Note that all three refusals came from the model rather than an observed
  bwrap denial — the profile is the enforcement, but this run did not get to watch it bite.
- Restart: io came back signed in with no OAuth round trip, and `~/.codex/auth.json` was
  untouched throughout (size 4041, mtime 2026-09-07, before and after).
- attach a file: the CSV was copied in, ran the same review (names, emails, PAN, UPI all
  flagged), returned to the same conversation with a note and nothing typed for the person,
  and the follow-up question answered correctly with a restored name and a rupee amount
  (45, 46, 47).
- Terminal: Ctrl+V pastes, Ctrl+C copies a selection, Ctrl+C with no selection interrupts,
  the "copy text" button copies the screen, a file Codex named opens on click, and the
  terminal reflows when the window is resized (50-55).
- Proxy over the whole session: 153×200, 11×403, 15×426, **zero leak lines**. Refusals were
  15 websocket 426 (by design, Codex falls back to SSE), 2 `not ready` during a rescan
  (fail-closed, expected), and 9 `path not allowed` on
  `GET /backend-api/accounts/verified_access`.

**Left for a decision:** `verified_access` is not on the allow list, so it fails closed nine
times a session. Nothing visibly breaks. It carries no workspace content, so it could join
the pass list, but adding an endpoint to that list is a privacy-surface decision.

## Tests

`app/io/.venv/bin/python app/io/tests/test_codex_proxy.py` — 29 pass (was 28; one added).
`node app/io/tests/test_codex_launcher.js` — 9 pass.
