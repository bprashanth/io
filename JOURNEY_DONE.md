# Drivey journey: Idli side

Implemented items 6–9 from JOURNEY_TASK.md in
`benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/`.

## What changed

- Drivey has exactly five cowork tools: `drive_fetch`, `privacy_review_open`, `claude_handoff`,
  `mini_open`, and `mini_ask`. The router identifies the chat from this list, including its first
  message. Code writes every reply; the 9B is called only to map a question inside an open Mini.
- Drive mentions download the selected spreadsheets and show the Privacy card. Checking files opens
  a token-protected `/privacy-review?embed=1&...&a=<left-agent>` page. It shows each sheet's columns,
  plain reasons, real samples, codes and switches, plus the masked question. Done sends exactly
  `Privacy checked` to the originating chat. A fresh preview then shows the Claude consent card.
  Old reviews cannot change or resume a newer file selection. Repeat Done requests do not resend.
- Accepting the choices also shows a fresh masked-question preview. Only Switch to Claude submits
  the one-line `Files (masked by Idli): ...` prompt, presses Enter and focuses that workspace's
  Claude terminal. Mini fallbacks carry the Mini's files and a short context line.
- Minis open with the saved story, questions, options, pinned charts and computed example charts.
  Matched questions use their scripts. Unmatched questions get the masked handoff offer.
- Claude's `idli_show` opens `/view` on the right through `uiswitch.open_url` and the P21
  `window.__idliOpenTab` bridge. It no longer posts charts into the left chat. The chart page has
  persistent Pin/Pinned, Fit/Bigger zoom (including composite charts), source popovers,
  right-click Copy to Claude without Enter, chart follow-ups to Claude, and Back to Claude.
- `/mini` is installed by `desktop/claude-masked.sh`. It tells Claude to check every script and
  call `idli_draft_mini(title, story, questions, code)`. The tool takes this workspace's pinned
  charts, copies and checks scripts, and opens the editor on the right. The editor supports title,
  story, question and option edits, removing questions/charts, Save, Add to the starting Mini and
  Save as a new Mini. Save checks scripts again before publishing a cartridge. Repeated saves
  return the saved Mini. The 8-question / 3-option limits apply when adding too.
- The pages use calm light/dark layouts, visible progress, clear actions, keyboard-accessible
  controls, retry paths and narrow-pane layouts. Review pages report `idli-height` to their parent.
  Shared workspace records use the existing cross-process privacy lock when updated.

## Verification

All checks passed using synthetic files, local code and a fake `paseo` executable on PATH.
No real accounts, Drive downloads, Claude requests or model endpoints were used.

From the repository root, with the test Python activated:

```sh
python -m unittest discover -s benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/tests -p test_journey.py -v
python benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/tests/check_journey_browser.py
```

- **37 unit/integration tests:** every router transition, native reminder messages, exact tool
  identity, no chat-model calls, an isolated system-Python import without pandas, real masking,
  review changes and callbacks, stale reviews, exact terminal text and Enter behavior, workspace
  boundaries, Mini mapping/declines, script checks, Save/Add limits, public cartridges and MCP
  tool discovery. One full transcript runs real tools from download through review to handoff.
- **6 headless Chromium tests:** real loopback HTTP server; privacy switches, updated question,
  Done and reload; Pin persistence, Fit/Bigger, source popover, right-click insertion and Back;
  composite-chart zoom; editor edit/remove/Save/Add/new flows; missing-token read/write rejection.
  Light/dark checks at 360px, a 900px chart check, no horizontal page overflow, no browser script
  errors, and the visible-text character rule.
- `git diff --check`, Python compilation, JavaScript syntax checks and shell syntax check passed.
- **18 screenshots** are in [JOURNEY_SHOTS](JOURNEY_SHOTS/), including both themes, privacy samples
  and question, chart sources, composite-chart fit, edited questions, Save and Add/new states.

The temporary test environment is `/tmp/idli-journey-venv`, created with system site packages for
Playwright. Dependencies: pandas, openpyxl, duckdb, vl-convert-python and Playwright/Chromium.

## Limits and rollout

- This is the requested Idli-side change. Paseo P21's draft chat, cartridge refresh and generalized
  embeds are separate UI work. Right-pane opening requires its `__idliOpenTab` bridge and the
  existing DevTools connection. A tool returns a page link if opening the tab fails.
- Live laptop/Paseo/Drive/Claude integration and real 9B mapping were not exercised here. Restart
  the router after syncing `modes.py` and `minimap.py`; sync the cowork tools/pages/launcher to the
  laptop, rerun bootstrap for the five-tool allow-list, restart its form server, and use a fresh
  Drivey chat and Claude terminal to pick up the tool list, command and instructions.
- Column review supports Excel `.xlsx` and CSV spreadsheets. Drivey skips other formats before
  downloading them and explains how to continue with spreadsheet copies. A folder can contain
  more than twenty spreadsheets. The existing privacy engine/proxy still supplies masking; these
  tests use its local rules with a fake scanner, and do not certify detection of every private value.
- Mini scripts must remain self-contained and use relative `drive/` paths, as the Claude command
  explains. Scripts run locally with the existing 60-second limit. Charts and Minis stay local;
  this change does not add sharing or package their data for another computer.

Committed on the current branch. Nothing was pushed or installed on a live laptop.
