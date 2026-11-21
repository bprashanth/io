# Idli home proof of concept

Implemented `/home`, `/view?id=…` and `/mini?id=…` in the existing loopback formserver, using its token checks.
All changes are inside this COWORK directory. Existing dashboard, privacy, Drive index and taught-file Mini routes
remain available.

- Home searches the Drive index and local `drive/*.xlsx` files, supports Enter/Tab chips and `@` mentions, and
  reviews every sheet before sending. New files default to Mask / Ask. Column changes save through `/api/privacy`
  and refresh the samples and masked question. Existing Fake copy settings have an explicit Use Mask button.
- Send finds the Drivey workspace, starts or reuses its labelled masked Claude chat, strips `PASEO_*` from CLI
  calls, focuses the right pane, and records the agent and selected files in `.idli/home.json`.
- `lib/idli_mcp.py` provides `idli_show` and `idli_save_mini` over stdio. It confines file paths, saves local chart
  views, opens their browser tabs, copies Mini scripts, and records selected files with their Drive source IDs.
  The Claude launcher generates an owner-only MCP config and retains the masking proxy's `ANTHROPIC_BASE_URL`.
  Claude's instructions require chart consent and checked results before saving a Mini.
- Views use the bundled Vega libraries and a local CSV API. Chart popovers send questions to the originating
  Claude through `/api/say`. Mini scripts run with Python `-I`, validated parameters, a `drive/` link and a
  60-second timeout; text, markdown tables and optional charts render locally. The chat box proposes a saved
  question and parameters using Muse's `idli-9b` JSON schema response, with word matching on failure. The person
  checks the choice before pressing Run. Dark mode and narrow layouts are supported.
- Privacy codes remain stable in the session vault. Home and the proxy use the currently selected cell values,
  so switching a column off updates the preview and outgoing masking without deleting its stable codes.

## Verification

Run from COWORK:

```
HOME_BROWSER=1 .venv/bin/python -m pytest lib/test_home.py lib/test_privacy.py lib/test_ccproxy.py -q
.venv/bin/python -m lib.test_formkit
.venv/bin/python -m lib.test_fixkit
.venv/bin/python lib/test_driveindex.py
node --check lib/home.js
node --check lib/home-chart.js
sh -n desktop/claude-masked.sh
```

The combined pytest run passed all 30 tests, including the Chromium browser flow. The three existing standalone
regression suites passed. JavaScript/shell syntax checks and `git diff --check` passed.

Home tests copy both synthetic grounded-9B fixture workbooks into temporary data folders. They cover all-sheet
privacy defaults, reversible column masking, fake Drive download/source metadata, first send and chat reuse,
archived chat replacement, stripped CLI environment, stdio MCP tools and path confinement, Mini scripts and
parameters, a fake 9B router and unreachable-router fallback, and the shell launcher's generated MCP config.
The browser test covers two chips (including `@`), review/toggle/send, a chart bar popover and its message,
Mini parameters/table/chart, no-agent popover behavior, and a 360px dark layout.

Screenshots are in `HOME_SHOTS/` (review, sent, chart popover, dark Mini); generated PNGs and the local test virtual
environment are ignored and are not committed. Screenshots were inspected; the stylesheet CSP issue found in
that inspection was fixed and the browser test repeated.

## Limits

This is a local proof of concept, not a laptop deployment. Google access, the real Paseo app, the person's Claude
subscription and the live Muse router were not exercised; their boundaries use fake services in the tests.
The launcher test starts neither Claude nor the real proxy. Restart formserver and start a new masked Claude chat
to pick up the new routes and MCP config. Open `/home` using the existing formserver token, without printing it.

Files are Excel workbooks; charts use local CSV or script-provided rows. Minis use the selected downloaded files,
not automatically refreshed Drive versions, and scripts must be self-contained. Mini scripts execute trusted
local Python with a timeout, not an OS sandbox. Chart consent and result checking are Claude instructions rather
than a separate approval protocol. Word matching uses defaults and recognized choice values; arbitrary numeric
or text extraction needs the 9B router or manual input. Existing regex/scanner masking limits still apply.
No credentials were printed, logged or committed. Nothing was pushed.
