# Idli chart embeds completed

Implemented parts 2 and 3 of EMBED_TASK.md and the formserver insertion endpoint, within this cowork directory.

- `/view?embed=1&ws=<workspace>` shows only the chart, fits the frame (including facets and multi-panel charts), and follows dark/light appearance and frame resizing. Page chrome is hidden before the chart libraries load.
- Left-click opens the existing popover. Its first action, "Where did this come from?", shows source paths, the data-making script, the saved CSV path, and matching CSV rows. This uses local code without a model. Aggregate marks match their shared CSV group fields.
- The remaining questions and comments POST to `/api/say` with the workspace. The server resolves its left chat using `paseo ls --json --label idli.ws=<workspace>` and sends there. Existing callers without a workspace retain their previous behavior.
- Right-click opens "Copy to Claude" and "Copy whole chart to Claude". Both POST `/api/claude-insert` with a single line of chart context and a trailing space. The server finds that workspace's existing Claude terminal, types the exact text with literal send-keys, and focuses it on the right. It never presses Enter or starts a terminal. Invalid input and missing terminals return errors; a stale terminal belonging to another workspace is ignored.
- `idli_show` accepts optional `sources` and `script` arguments and records them in the view JSON. Source paths must resolve to files under `drive/`; scripts must be inside an allowed work/data folder. Mini chart examples and answers record the Mini's files and the saved question script. Claude-created views also remember their workspace for standalone interactive links.
- Updated `idli/CLAUDE-masked.md` to always supply sources and script. Older views display "Not recorded" for missing provenance.

Validation: `HOME_BROWSER=1 .venv/bin/python -m pytest lib/test_home.py lib/test_chat.py -q`: **38 passed**.

Tests use synthetic fixtures and a fake Paseo on PATH. Headless Chromium checks a 320px embed, local provenance with no POST, left-chat questions, both context-menu POSTs, exact terminal text with no Enter, focus placement, dark/light axes, resizing, and aggregate rows in a scaled multi-panel chart. The existing full-page Home/Mini browser check also passes; its stale mapper assertion was corrected to match the unavailable-model response.

The P20 chat renderer, its fallback timer/modal, and its application CSP are outside this Idli-side task. No push was made.
