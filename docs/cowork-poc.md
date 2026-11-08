# Co-work POC: start here

**Status (2026-11-07):** a working proof of concept on the owner's laptop. It is driven from the DGX over a tunnel.
The owner tests it by hand next and designs the next experiments. **Agents: verify, and fix what the owner
asks. Don't start new experiments on your own.**

## What changed (newest first): DGX agent, read this after every `git pull`

Either agent adds an entry here for every change that needs something done on the other machine. The mechanism, and what the owner starts on the laptop, are in [laptop-dgx-sync.md](laptop-dgx-sync.md).

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

NGO staff do repetitive work on websites and spreadsheets that hold personal data. Two modes:
- **DIY mode** (Claude Code with the user's own subscription) writes small "site plugins" against **test**
  accounts and mock files.
- **Co-work mode** (the private T4GC model Muse, with no shell) uses those plugins on the user's **real**
  accounts and files.

Personal data only reaches the private model. When co-work can't do something, a tool prints a gap
report. The user removes personal details from it and pastes it into DIY, which builds the missing tool.
The user then retries co-work in a new chat.

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

## Rules carried over from the owner

- Co-work never sends email and never edits documents. It drafts and suggests only. Don't add tools that send,
  delete, submit, pay or publish.
- No custom agent instructions (AGENTS.md and the like) as a workaround for UX gaps. Fix it in a plugin.
- DIY uses only test accounts and mock data, and works only in the cowork folder.
- The laptop has no disk space for models. Serve models on the DGX.
- Commits are `declaude`d before they go to GitHub. Pushing is the owner's call.
- Write a chronology entry before you stop (see agent-handoff.md).
