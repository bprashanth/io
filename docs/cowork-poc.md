# Co-work POC: start here

**Status (2026-11-07):** a working proof of concept on the owner's laptop. It is driven from the DGX over a tunnel.
The owner tests it by hand next and designs the next experiments. **Agents: verify, and fix what the owner
asks. Don't start new experiments on your own.**

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
   - [handing work between agents](agent-handoff.md)

## Verify before anything else (DGX agent)

The owner starts the tunnel on the laptop (`desktop/laptop-up.sh`). Then, on the DGX:
```sh
cd ~/src/github.com/bprashanth/io-oss-eval && git pull
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
