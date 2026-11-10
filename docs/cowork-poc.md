# Co-work POC: start here

**Status (2026-11-07):** a working proof of concept on the owner's laptop. It is driven from the DGX over a tunnel.
The owner tests it by hand next and designs the next experiments. **Agents: verify, and fix what the owner
asks. Don't start new experiments on your own.**

## What changed (newest first): DGX agent, read this after every `git pull`

Either agent adds an entry here for every change that needs something done on the other machine. The mechanism, and what the owner starts on the laptop, are in [laptop-dgx-sync.md](laptop-dgx-sync.md).

- **2026-11-10 (evening), DGX (branch idli-9b-bench): free-tier split.** Spec building moved out of the chat model
  into a single-purpose sub-call inside `file_ask` (the 9B passes the person's words; no new tools). Fresh held3:
  9B + Qwen3.5-35B-A3B 83%, 9B building its own specs 83%, Muse 83%; fully local on the DGX 79-81% (Muse stopped
  13:02-13:18 IST for that run, restarted and checked through 8185). OpenRouter runs pinned per provider and
  quantization. Other spec builders within the bar: gpt-oss-120b, Ling-3.0-flash, Qwen3.5-122B-A10B. Under the real
  Claude Code CLI the split is 8-14 points under Muse on held3 (the 9B paraphrases answers: render answers and
  cards in the host). Claude planning from GLiNER-redacted questions: 75-77% (shape-only backtrack +10; GLiNER
  over-redacts). Muse-Glimmer-30B is a dense 28B with a Llama-4 tokenizer, not a Qwen. REPORT.md updated.
- **2026-11-10 (later), DGX (branch idli-9b-bench): 9B benchmark results.** Per-span pass rates, lean harness:
  dev+held+held2 Muse 85%, Qwen3.5-9B raw 65%, **9B + guards 86%** (local Q5 + guards 85%), LoRA 9B-004d 51% / 60%
  with guards (the algebra adapter doesn't carry over). Fresh held-out set (held3, long follow-ups, never tuned on):
  Muse 83%, 9B 65-73% depending on variant, Qwen3.5-35B-A3B (3B active) + stateful form 83%. Real Claude Code CLI:
  Muse 78% (partial), 9B + guards 76%. Index summaries: 9B 12/15 vs Muse 10/15. Start here chat: 9B 100%. Spec
  building alone: 9B 73%, 35B-A3B 89%. UX (blind rubric, Codex first pass): Muse 3.2/5, 9B + guards 2.7 (repeats
  from the card guard, unneeded questions). Verdict: a guarded 9B can take start, find, open, clean, teach-switch,
  skills, Start here and index summaries now; follow-up question-to-spec on long chats stays ~10-15 points behind:
  give that one step to a stronger model (35B-A3B class) or a stateful spec builder. Patches in `patches/`.
- **2026-11-10, DGX (branch idli-9b-bench): can a 9B replace Muse 30B? A standalone benchmark, in progress.**
  `benchmarks/runs/2026-11-10-idli-9b/`. Idli's real tools on a fake Drive (12 spreadsheets, 6 documents from
  totalrecall's synthetic livelihoods tables, two public Valparai ecology sets, and the taught-skill mocks; three new
  skills written as the Teach workspace would). 30 scripted multi-turn conversations in the owner's voice (dev 14,
  held-out 8, a second held-out 8 written by Codex and checked against the engine) plus the Start here chat. Two
  harnesses: a lean loop (same prompt for every model) and the real Claude Code CLI through the Agent SDK with
  cards answered the way Paseo does. Nothing touches `cowork/` or `~/idli-insights` (one leak found and fixed: the
  harness's skill deletes went to `~/idli-insights/archive`; removed, and `formserver.skills_delete` patched to
  honour `IDLI_HOME`). First findings: Muse ~98%; raw Qwen3.5-9B 64% (thinking 70%), failing mostly by writing
  cards as text and misrouting; general guards (a Stop hook that sends the model back once to show a pending card
  or drop a made-up number, and `drive_find(goal)` opening the spreadsheet itself) bring it to ~88%. Index summaries:
  the 9B finds files better than Muse (12/15 vs 10/15 top-1). Patches in `patches/`; report in `REPORT.md`.
- **2026-11-10, DGX: Muse through Cloudflare (silo.idli.cc).** The owner put Muse behind Cloudflare Access at
  `silo.idli.cc` (tunnel → DGX 8185, the prefix proxy → Muse) with a service token. `lib/muse.py` gives the URL and
  the two Access headers from `~/idli-insights/config/muse-access.json`; `desktop/muse-connect.py <token file>`
  checks the token and points the Idli 30B provider at silo through `ANTHROPIC_CUSTOM_HEADERS` (Claude Code sends
  them on every call). End to end on the laptop with nothing listening on 8181: start card, Analyse, "the cestrum
  field vars file" (16 s, two matches), the original (54 s with the download), checked copy (48 s), "how many
  cestrum trees, what share" (17 s: 317, 17.34%), chart of share by transect (12 s, bars in the chat). On the DGX
  the only client of 8185 during the run was `cloudflared`. Running chats keep the settings they started with:
  the bootstrap's spare was replaced and Start here reloaded. Copying the token needs the laptop's ssh to the DGX,
  which Tailscale gates with a browser check.
- **2026-11-09 (late night), DGX: "What Idli has learned" is a page again.** The owner preferred the list page to
  a chat table. Mission control now has two workspaces: Start here (setup chat) and What Idli has learned (the
  `/skills` page in a browser tab, plus a small chat that only points at it). The page says "Here is a list of files
  Idli has learned to analyze", refreshes itself every 5 s, and has Delete under each entry (P11 crops the right
  edge). The form server keeps its token across restarts and the bootstrap starts it, so the tab's link stays good.
  Found: Paseo's `browser_list_tabs` lists only the tabs of the workspace on screen, so each bootstrap rerun opened
  Drive and the page again; the bootstrap now remembers what it opened (`~/idli-insights/config/bootstrap-tabs.json`).
- **2026-11-09 (night), DGX: owner's feedback on the journey.**
  - **No waiting for "hi":** Idli always keeps one chat named "New chat" open on the start card (made by the
    bootstrap, then by `ensure_spare` in `sites/files/tools.py`). Using it renames it ("Clean: <file>",
    "Analyse: <file>", "Find: …") and opens the next one in the background (one spare at most, one start per 2 min).
  - **Mission control:** the first heading is now Mission control, with the workspace Start here holding two
    chats: "Start here" (setup, indexing) and "What Idli has learned" (tools `skills_list`, `skill_delete` with a
    confirm card). Bootstrap renames the heading and creates both chats.
  - **Teach card:** the Labels question has "None (Recommended)" (typing in Other is for a different answer);
    the fake copy opens in a `fake-copy.localhost` tab ("Fake copy for Claude: <file>") so the person sees exactly
    what Claude gets.
  - **A leak found and closed:** the households mock kept the real coordinate range, so Claude worked out the survey
    was around Pune. Coordinates (columns named lat/lon/…) are now faked around (0, 0) with the same spread, postal
    codes are random; IDs (PAN, receipt numbers, plot codes) keep their shape and fixed prefixes so checks can be
    written. The teach skill tells Claude never to put real-world places or extents in chart code.
  - **Teach skill:** step 0 discusses what they want to find out (the poverty-trap kind of brainstorm); clean-ups are
    phrased as how Idli reads the real file (Claude never tidies the fake copy); a question typed into Other is
    answered before the card is asked again.
  - Laptop: `file-skills/households` holds the owner's re-teach (uncommitted, kept across pulls with a stash).
- **2026-11-09 (evening), DGX: one journey, scoped.** Field note:
  [narrative/2026-11-09-one-journey-field-note.md](../narrative/2026-11-09-one-journey-field-note.md); test steps:
  [cowork-manual-test.md](cowork-manual-test.md) section "The Idli journey".
  - **Start:** an Idli chat opens with a card, *Clean up a file* / *Analyse a file* (tool `start`); a first
    message that already says what it wants skips it. `file_get`/`file_open` take `goal` and show the matching card.
  - **Clean:** unknown file -> teach card -> Claude (one step at a time, cards) -> back -> "Mark them in Drive"
    -> working copy next to the original (live red cells, one comment per kind of problem) -> "I'm ready" ->
    `working_copy_ready` re-checks the copy and moves on to analysis. Analysing a file with a working copy offers
    "Use the checked copy (Recommended)"; one without says it hasn't been cleaned.
  - **Analyse:** questions go to `file_ask` (multi-turn); a graph is `file_ask` with `chart` (one breakdown: bars;
    two: a grid), drawn from the form's answer into the chat and the dashboard. Anything the form can't draw, or
    "suggest analyses", goes to `chart_request`: a fake copy to Claude, who agrees the chart on cards, writes
    `file-skills/<id>/charts/<chart>.py`, renders it on the fake data in its chat, and hands back; Idli runs it on
    the real data (`chart_show`) inside a bubblewrap wall (no network, read-only, home hidden, `lib/chartkit.py`).
  - **Dashboard:** problems collapsed to one line with **View problems in Drive** (the working copy) and Details;
    the freed space has a live bar chart of the current answer and a gallery of the file's charts.
  - **Skills page** (`/skills`, tool `show_skills`): what Idli has learned, one per file, with Delete (moved to
    `~/idli-insights/archive/skills`). The cestrum skill was removed this way to retest teaching from scratch.
  - **Engine (from Claude's teaching session):** `row_checks` (taught SQL conditions across columns and tabs),
    lookup `accept` patterns for a team's own codes, `"case": "lower"`; small whole-number columns (transect,
    plot) are breakdowns.
  - **Removed from Idli:** the `sheets` site (free SQL, its own charts), which Muse used to make up a chart
    query that failed. `cowork.sites` in the Idli folder is now `google` + `files` (bootstrap rewrites it).
  - **Laptop:** `matplotlib` in the cowork venv; `bwrap` needed (present on Ubuntu/Pop). `__pycache__` is no longer
    tracked (it blocked pulls).
- **2026-11-08 (late), DGX: first-run experience (OOBE) played as a new user.** Field note:
  [narrative/2026-11-08-oobe-field-note.md](../narrative/2026-11-08-oobe-field-note.md); runs and numbers:
  `benchmarks/runs/2026-11-08-oobe/` (`oobe_test.py`, `results.jsonl`, `search_eval.py`, `search_chat_test.py`).
  - **Layout:** headings Start here / Idli / Claude, laid out by `desktop/idli-bootstrap.py` (run by
    `desktop/idli-launch.sh`, the "Idli" app-menu entry). Start here chat opens on low thinking.
  - **Start here:** greeting, "yes" (any go-ahead) starts the index, progress in a `drive-index.localhost` tab,
    finish with next steps in the chat (the indexer's "Drive index: done" note prompts it if the model stopped).
    30B: greeting ~10 s, acts ~5 s, index 182 files in 5.5 min; 9B: same, waits silently and writes the finish.
  - **Search:** vector index 23/25 first-place vs 22/25 for today's lexical+summaries; not adopted yet. Summaries
    now carry everyday words. 30B chat search 34-80 s (reasoning tokens at ~30 tok/s), 9B 7 s.
  - **Fixed:** double `.xlsx` on downloaded Excel names; Idli no longer downloads when only asked to find.
  - **Laptop:** `fastembed` added to the cowork venv (eval only).
- **2026-11-08 (night), owner + DGX: finding files in Drive.** The owner's live run took ~5 min of substring
  searching before Idli asked anything. Now:
  - **Drive index** (`lib/driveindex.py`, tools `drive_index` / `drive_index_status` / `drive_find`), built by Idli
    on the laptop after the user says yes. It walks My Drive and Shared with me (10 levels, loop-safe, big folders
    scrolled to the end) with 5 tabs, reads the first rows of Sheets/Excel and the opening of Docs, and Muse
    writes a one-line summary per file, 4 at a time. Photos and videos: name, folder, date only. Stored in
    `~/idli-insights/config/drive-index.duckdb`. Real Drive (182 files, 19 folders): ~3.5 min.
  - **drive_find**: index search in ~0.3 s (names, folders, contents, modified dates, date words such as "in
    December"). With no clear match, one quick Drive full-text search on the rarest word, then ask the user.
    "bikapathymund cestrum datasheet": "no file mentions 'bikapathymund'; 'cestrum' is in field_vars_indicators.xlsx".
  - **Sidebar, top to bottom**: "Start here" (its own folder `~/idli-insights/start-here`, instructions from
    `idli/START-HERE.md`: greeting, sign-in, Drive index; tabs: the chat, Drive, Gmail), "Idli insights" (the
    private folder, where the work happens), "Teacher - Claude" (the Teach folder). Order set by dragging in the
    app. `setup-laptop.py` doesn't create the start-here folder yet.
  - **Providers** relabelled: "Idli - 30B (private, on Muse)", "Idli - 9B (OpenRouter, not private)",
    "Teach - Claude (fake data and test accounts only)" (backup `~/.paseo/config.json.bak-20261108-labels`).
  - **Workspaces** renamed "Idli - private" and "Teach - Claude"; old chats and two extra workspaces archived;
    leftovers from the form runs moved to `~/idli-insights/archive/cowork-real-20261108/`.
  - **Open**: photo location (EXIF) isn't visible in Drive's list; needs the details panel or the Drive API.
    Paseo always defaults new Claude-based chats to Auto mode, which blocks Idli's tools; pick Bypass.
- **2026-11-08 (evening), DGX: the file form is built and run end to end.** Details and results:
  [JOURNEY.md](../benchmarks/runs/2026-11-08-form-fill-eval/JOURNEY.md) and the model comparison in
  [README.md](../benchmarks/runs/2026-11-08-form-fill-eval/README.md).
  - **Code:** `lib/formkit.py` (form per tab, spec to SQL, lookups across tabs, contract test, date words),
    `lib/formserver.py` + `lib/form.html` (the page, 127.0.0.1 only, token per start), files site tools
    `file_get` / `file_open` / `file_ask` / `teach_file` / `teach_send` (file_check and file_answer are gone),
    teach-file skill writes the form format; `idli/CLAUDE.md` rewritten.
  - **Skills:** existing three gained labels, measures and rules; `field_programme_tracker` (3 tabs) taught v1 and
    re-taught v2 by the laptop's Teach chat.
  - **Laptop actions (done by the DGX):** `git pull`; `idli/CLAUDE.md` copied to `~/idli-insights/cowork-real/`;
    `~/.paseo/config.json` co-work providers also disallow `mcp__cowork__sheet_query` and `sheet_profile`
    (backup `config.json.bak-20261108-forms`). Paseo's download behaviour was set to "save without asking" over
    DevTools for testing and set back to default.
  - **Owner:** four stale Save dialogs on the laptop need Cancel. `~/Downloads/volunteer_register.xlsx` was
    replaced by a fresh export of the same sheet during the test.
  - **Moving code:** the laptop's `ssh` to the DGX hangs (Tailscale check?), so code moved through GitHub
    (declaude, force-with-lease) and laptop files came back as base64 through a Paseo terminal.
- **2026-11-08 (later), owner + DGX: downloads work, and the file flow becomes a form.**
  - **Correction:** Paseo's browser *does* download. Opening `…/spreadsheets/d/<id>/export?format=xlsx` shows a red
    `GUEST_VIEW_MANAGER_CALL … ERR_FAILED (-2)` line (cosmetic: the page load is cancelled because the response is a
    file), then the system "Save as" dialog. The owner saved the volunteer register to `~/idli-insights/testdata` on the
    laptop and it is intact (`Rs. 300` present). Paseo 0.15.2 has no `will-download` handler, so Electron falls back to
    the dialog. Idli can't click a system dialog, so automatic downloads still need a small Paseo change (save into the
    workspace folder, no dialog). Plugins can't do it: they run in the daemon and app UI, not the browser session.
  - **Decision (owner):** for single-file work, the model's role shrinks. Teach describes a file once (measures,
    groupings, date columns, business rules, checks, every tab). Idli then opens a **form** for that file: dropdowns
    tailored to its data, the schema problems, and the answer, all computed by code. The model finds files, talks, and
    fills the form from a typed question; it never writes SQL or numbers. A **contract test** runs before every query,
    and a changed schema asks for re-teaching. The entry point is "open the form for <link>". Next: compare a plain form,
    a classifier with a date parser, and 4B/9B/30B models on filling the form from vague questions.
- **2026-11-08, DGX: teach Idli a file.** New `files` site (file_open, file_check, file_answer, teach_file, teach_send),
  `lib/filekit.py`, the `teach-file` Claude skill, `idli/CLAUDE.md` (copied into `~/idli-insights/cowork-real/CLAUDE.md`), and
  `cowork.sites` gains `files`. Three file skills taught in human-style runs; results in
  [TEACH-FILE.md](../benchmarks/runs/2026-11-07-cowork-event-eval/TEACH-FILE.md).
  - **Laptop action:** `git pull` (done by the DGX). If you rebuild the laptop, `setup-laptop.py` now writes both.
  - **Open:** Google's sheet export blanks text in number columns; Idli warns but a real Drive download is still needed.
- **2026-11-07 20:xx, DGX: Muse latency fixes.** Claude Code's "hi" in a new chat re-read 18.6k tokens cold (~28-41 s).
  - **Muse** now runs with `--cache-ram 32768` (same flags otherwise; restarted with silo's `tg-bridge/serve_muse.sh`).
  - **Prefix proxy** `dgx/muse_prefix_proxy.py` on DGX `127.0.0.1:8185` (user service `muse-prefix-proxy`). It rewrites
    Claude Code's mid-conversation `system` message to user text, so Muse's template stops printing every tool twice.
    Prompt 18.6k -> 10.7k tokens; a new folder re-reads ~2.2k ("hi" ~4-6 s instead of ~28 s).
  - **T4GC Claude settings** add `autoMemoryEnabled: false`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` (the per-folder memory path
    sat before the tools and broke the cache for every new folder) and `CLAUDE_CODE_MAX_CONTEXT_TOKENS=65536` (Muse's slot size;
    Claude Code assumed 200k).
  - **Laptop action:** `git pull`; merge the three keys from `laptop/claude-t4gc-settings.json` into
    `~/idli-insights/config/claude-t4gc/settings.json`; `laptop-up.sh stop && laptop-up.sh` (its `-L 8181` now targets DGX 8185).
    Done by the DGX through a laptop terminal on 2026-11-07 (settings backed up as `settings.json.bak-20261107`).
  - **Co-work tool list trimmed** (`desktop/setup-laptop.py`, and merged into the laptop's `~/.paseo/config.json`):
    unused Claude Code built-ins (Workflow, Cron*, plan mode, worktrees, SendMessage, ...) are disallowed, and so is
    `gmail_draft_reply`, because co-work is read-only (find, suggest, download). Co-work prompt 17,180 -> 3,859 tokens;
    measured co-work "hi": cold prefill 4.3 s, warm ~6 s end to end including agent start.
- **2026-11-07 20:xx, DGX: `~/idli-insights` bootstrapped.** Moved the DGX's old `cowork/accounts.local.json` to `~/idli-insights/config/accounts.json` (chmod 600), so no `scp` was needed. If the laptop's copy has changed since, `scp` it over. Added [laptop-dgx-sync.md](laptop-dgx-sync.md). `lib/accounts.py` now resolves the new path. `check-from-dgx.sh`: ALL CHECKS PASSED (google 8/8, sheets 5/5) once the tunnel was back. The laptop had no workspace on the repo's `cowork/` folder, so the DGX created one ("DIY (cowork)") and started a one-line DIY chat in it.

- **2026-11-07 19:50, `~/idli-insights` and Paseo only.**
  - **What moved:**
    - Everything outside the repo now lives in `~/idli-insights` (layout in
      [driving-desktop.md](driving-desktop.md#idli-insights)).
    - The test-account file moved from `cowork/accounts.local.json` to `~/idli-insights/config/accounts.json`.
      `lib/accounts.py` still falls back to the old path.
    - The co-work workspace is now `~/idli-insights/cowork-real`.
    - The DIY sandbox blocks the private folders there.
    - T3 and AionUi are no longer maintained.
  - **DGX action:** do "Bootstrap the DGX" in driving-desktop.md. That means creating
    `~/idli-insights/config/accounts.json` (the owner copies it from the laptop) and deleting the old
    `cowork/accounts.local.json`. Then rerun `desktop/check-from-dgx.sh`.
  - **Also recorded:** Muse first-turn latency (cowork/README.md, "Findings"): about 16k prompt tokens (co-work)
    or 34k (full Claude Code) are re-read when the prompt cache is cold.
- **2026-11-07 18:xx, single DGX checkout.** The DGX agent moved to `~/src/github.com/bprashanth/io` (`7a8a140`).

## The idea in one paragraph

Idli is a Drive assistant for NGO staff. It uses Claude and a private model together to ask better questions of
their own data and to manage the data-entry work around it. Claude, working only on a copy with fake values,
establishes each file's structure, cleaning and validation rules (a "skill"). The private model runs those rules
on the real file and flags issues as comments in a working copy in the person's Drive, where they fix them. Once
the file is clean (or they choose to go ahead), Idli builds a **form** over it, so a small private model (Muse, or
a 9B) can hold a conversation about the data and answer from the form, never from its own arithmetic. The aim is
not a dashboard but discovering questions through conversation; the form is the scaffolding that keeps the
answers true. Charts follow the same pattern: question -> fake data -> Claude writes and agrees the chart code ->
Idli runs it on the real data locally. Everyone starts in **Start here** (index the Drive, re-index any time),
then works in **Idli**, one file at a time.

The earlier framing (DIY site plugins for websites, gap reports) still exists in the code but is not the focus.

## Read in this order

1. [cowork/README.md](../benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/README.md): layout, wiring, results table, findings, caveats.
2. [docs/driving-desktop.md](driving-desktop.md): how the DGX drives the laptop's Paseo (tunnel, CLI, DevTools, moving code), and how to recreate everything.
3. [docs/cowork-manual-test.md](cowork-manual-test.md): the owner's hand-test steps. Bugs they find come from here.
4. Chronology, oldest first:
   - [16:15 desktop UX + first Gmail/Drive tools](../chronology/2026-11-07T1615-laptop-desktop-ux-and-cowork.md)
   - [17:50 POC + gap loop + 9B](../chronology/2026-11-07T1750-laptop-cowork-diy-poc.md)
   - [18:30 handoff](../chronology/2026-11-07T1830-laptop-cowork-handoff-to-dgx.md)
5. Background, only if needed:
   - [field note](../narrative/2026-11-07-cowork-ui-as-api-field-note.md)
   - [laptop app guide](oss-desktop-laptop-testing.md)
   - [handing work between agents](agent-handoff.md), [laptop ↔ DGX sync](laptop-dgx-sync.md)

## Verify before anything else (DGX agent)

The owner starts the tunnel on the laptop (`desktop/laptop-up.sh`). Then, on the DGX:
```sh
cd ~/src/github.com/bprashanth/io && git pull
cd benchmarks/runs/2026-11-06-oss-desktop-independent/cowork
desktop/check-from-dgx.sh
```
Expect `ALL CHECKS PASSED`. Report each FAIL line to the owner with what you think the cause is. Then show
you control the app:
1. Run one co-work question on Muse with `paseo-remote.sh run` (an example is in driving-desktop.md).
2. Read its answer with `logs`.
3. Open its workspace and screenshot it with `drive.py`.
4. If the answer mentions a dashboard, click its **Open** button and screenshot the dashboard tab.

## What is verified (single runs, laptop, 2026-11-07)

- **Site tests:** `google` 8/8, `sheets` 5/5 against the test account and mock workbook. From the DGX, check them through the tunnel.
- **Muse 30B on co-work:**
  - Excel question: partly right, it mis-merged spelling variants.
  - Google Sheet question: right.
  - Gmail and Docs tasks: right in the earlier prototype.
- **The full gap loop, once:** Muse's `report_gap` → scrubbed → DIY (Claude Opus) built `gsheet_read` in 13 minutes → Muse correct in a new chat.
- **Dashboard Open button:** shows under the reply and opens the rendered page in a workspace-browser tab.
- **Qwen3.5-9B, via OpenRouter** (test data left the machine, by the owner's choice): Sheet ✅, Doc ✅ mostly, Excel half, AWS email ❌.
- **The DGX drives the laptop:** the CLI (`ls`, `provider ls`, terminal), DevTools screenshot and tabs list were all checked by hand before this handoff. `check-from-dgx.sh` passed on the DGX at handoff, after the agent-reload and workspace-focus fixes.

## Known bugs and rough edges (candidates when the owner asks for a fix)

| # | Bug | Where |
|---|---|---|
| 1 | The dashboard **Open** button opens a new workspace-browser tab but doesn't bring it to the front | `dashboard-links/server/open.ts` (uses daemon `browser_new_tab`; timeline rows get no `navigation.openBrowser`) |
| 2 | Each co-work run in a new workspace leaves Gmail/Drive tabs behind, so tabs pile up | `lib/browser.tab_for` |
| 3 | New browser tabs only open in the workspace the app is **showing**; elsewhere `browser_new_tab` times out ("open the browser pane"). Found at handoff. Workaround: `drive.py goto <wks>` first. A real fix might have the plugin or tools ask the app to show the workspace | `lib/browser.tab_for`, `dashboard-links` |
| 3b | The browser tools refuse closed (idle) caller agents with "Parent agent … not found". Workaround: `paseo agent reload <id>` | `run_tests.py`, `lib/browser.py` |
| 4 | Test runs rewrite `sites/*/site.json` (`last_test`), which dirties git | `run_tests.py` |
| 5 | Claude Code's Linux sandbox blocks 127.0.0.1:6767, so DIY ran outside the sandbox | `cowork/.claude/settings.json` |
| 6 | `report_gap` text written by the model can include personal names; the user must scrub it | `cowork_mcp.py` |
| 7 | `gsheet_read` can blank out a stray text cell in a mostly numeric column (gviz) | `sites/google/tools.py` |
| 8 | The bar-chart CSS was changed for narrow windows; the change hasn't been looked at | `sites/sheets/tools.py` `t_sheet_chart` |
| 9 | In a narrow Paseo window a browser tab can get a viewport wider than the visible pane (1280 px shown in 630), so the right edge of the dashboard and the skills page's Delete buttons are cut off. Widening the window helps | Paseo (patch P11) |
| 10 | Working copies pile up in Drive (one per "Mark them"); the index only knows the ones built before the last re-index, so `drive_find` can offer an old copy | `sites/files/tools.py` `t_working_copy`, `lib/driveindex.py` |
| 11 | A chat keeps the tool code it started with; after a `git pull` on the laptop, start a new Idli chat | `cowork_mcp.py` (one process per chat) |
| 12 | Muse often stops after writing text when a `then` asks for a card afterwards; cards that must happen go first, with the text inside the card | Idli tools' `then` strings |
| 13 | The form server restarts on the next Idli tool call; an open dashboard tab from before shows "connection refused" until then | `sites/files/tools.py` `_server` |

## Rules carried over from the owner

- Co-work never sends email and never edits documents. It drafts and suggests only. Don't add tools that send,
  delete, submit, pay or publish.
- No custom agent instructions (AGENTS.md and the like) as a workaround for UX gaps. Fix it in a plugin.
- DIY uses only test accounts and mock data, and works only in the cowork folder.
- The laptop has no disk space for models. Serve models on the DGX.
- Commits are `declaude`d before they go to GitHub. Pushing is the owner's call.
- Write a chronology entry before you stop (see agent-handoff.md).

### 2026-11-09, DGX: cards before switching views

When Idli wants the person somewhere else, it asks first with a yes/no card, and switches only on yes. Two places:
after "yes, index my Drive" ("Switch to the progress tab to watch it?"), and when teaching starts ("Opening Claude to
teach this file. Switch there now?"), with Claude asking "Go back to Idli?" when teaching is done. Switching to a
chat in another workspace uses Paseo's own deep link (`paseo://h/<server>/agent/<id>`, handed to the running app by
launching it again), so it works in a normal install. Browser tabs have no deep link, so the progress tab is
clicked through the DevTools port for now (dev only; Paseo patch P7). Measured on the 30B: card 23 s after
"rebuild index", yes brought the progress tab forward, and the chat carried on waiting for the index. The teaching
round trip is wired but not yet run end to end.

### 2026-11-09, DGX: fewer rounds between finding and analysing

- Found a file: the open-it card now carries a picture of its first rows (an SVG drawn from the index, kept in the
  private workspace folder). Muse reliably calls a card but often stops after writing a line before one, so the
  picture goes inside the card. "Yes" opens the file read-only in a tab here (`file_peek`).
- "Help me analyse X": no Save box (dev builds set each browser tab's download behaviour over DevTools; shipping
  needs patch P1), then for a file Idli hasn't been taught, one card instead of four rounds: send a copy with fake
  values to Claude and switch there, plus which label columns may go as they are. Measured on Muse: find to card
  20 s; analyse to the teach card 42 s (search, download, open, fake copy).
- Bugs found on the way: the find tool still said "download spreadsheets" (overrode the peek card); index reads
  with parameters failed silently (no previews); a short word covering the start of a longer one scored as a near
  match ("field" for "fieldvars"). Search check after the fixes: 23 of 25 right first with today's index, same as
  the vector index.

### 2026-11-09, DGX: from problems to fixes; gaps go to Claude and back

- A question the dashboard can't answer (here: sheet row numbers) now goes to Claude with a card, not a paste-in
  gap report: Idli sends the fake copy plus what was missing, switches to Claude, Claude extends the skill (one
  card: "add row numbers"), and on "back to Idli" the watcher outside Claude's sandbox switches the app and Idli
  reruns the question. Ran end to end on Muse + Claude.
- Problems became fixes. Each problem has its real cell (blank rows and columns count, as in the sheet), and
  either a suggested fix (approx 12 -> 12, "pending" -> blank, a date in another format, a code one typo away
  from the list) or a note saying what a person must check. Accept/reject per fix in the dashboard; "Save fix
  list" writes the list and a fixed copy of the original with each changed cell commented. The checked copy has
  a comment on every problem cell. Nothing is written to the person's Drive.
- Layout: rows that repeat the headings are skipped (49 in the cestrum file, which had 439 problems; now 196),
  sub-headings and totals rows are suggested skips, and Claude sees them in the fake copy and discusses them in
  teach mode (skip, or a cleaner layout for their next version; their choice). A code missing from the list that
  recurs (UKS1, Fern) gets "add it to the list if your team uses it" rather than a typo guess.
- Not done: links straight to a cell in Google (needs each tab's id; clicking tabs to read them was unreliable),
  and comments on the live Google Sheet (a write; the person's call).
- Working copy in Drive (2026-11-09). After file_get the card offers "Mark them in a Drive copy". On yes, Idli builds a copy of the original with live red highlights (conditional formatting from the same checks, so a cell clears when fixed), one comment per kind of problem on its first cell (Google imports them as real comments, counted on each tab), grey skipped rows and an "Idli checks" tab, then drops it onto the original's Drive folder in a tab (DevTools drag-drop; Paseo patch P9) and opens it. The cestrum file: 196 problems -> 15 kinds, 17 comments. "I'm ready" downloads the copy, drops the checks tab, re-checks and answers from the copy (317 Cestrum trees, 48 s). The only Drive write, a new file, after a yes.
- Muse latency: the minute+ was mostly reasoning over two contradictions in Idli's instructions (link vs drive_find; "say say_to_user" vs "write nothing before the card"), 1,285 tokens in one step. Fixed, and file_get now opens the form itself (one turn fewer): link -> card 44 s, steps think 160-560 tokens. What's left: re-prefills and tool time (optimizations 7, 8).
