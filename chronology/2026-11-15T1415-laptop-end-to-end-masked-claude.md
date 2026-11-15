# Laptop end to end: masked Claude, reveals, charts and the query service (2026-11-15 afternoon)

Synced everything since the last laptop sync (masked copies, unmask and column reveals, newsroom charts, query
service, small-number rule) and tested on the owner's test account with the real field_vars_indicators file.

## Set up
- Code by tarball from the DGX (as before); laptop commit "sync from DGX".
- Query service key copied to `~/.config/idlisseus/openrouter.json` (0600), never printed.
- Name scanner now runs on the laptop: user unit `idli-scanner` (GLiNER pii-edge, 127.0.0.1:8899, new
  `IO_PRIVACY_HOST`). `claude-masked.sh` uses it when it answers.
- DGX router restarted.

## What broke and was fixed (each with a test)
1. Mini query: a column heading equal to a hidden value went out as `VALUE_010` and the service's SQL named the
   column by the code. Idli now puts real names back into quoted identifiers; table names come from masked sheet
   names. After the fix "which plots had rapcap?" asked back which sheet, then answered: 15 plots, the same as the
   Mini's saved question.
2. Claude started with "Instruction file not loaded (a Read deny rule covers it): CLAUDE.md": a sibling
   `Claude-masked` was denied and Claude Code matches paths without regard to case.
3. Species reveal refused: "Species name expanded" was classed as a person's name, an unnamed column with the same
   value counted as personal, and the final NAME_ step edited a record shared by the whole column.
4. Headings showed as codes in the copies (old vault entries from repeated header rows).
5. Every request refused (403) after the reveal: hidden species codes are words inside revealed names
   ("fern" in "Fern sp."). The leak check now skips revealed values, like masking does.
6. Claude wrote to `~/idli-insights/NAME_007-masked/`: an old vault entry `NAME_007` = "Claude" and the close-match
   step ignored the product-word list. Removed the stray folder (one masked script).

## Result
Big trees question: Claude proposed the whole-column reveal, both consent steps worked, it searched the web with
the real names (six sources) and drew "39 of 47 big trees are shola natives". Wire audit, 80 requests: no hidden
value in any; 18 requests after fix 6 all show the real folder path.

## Also decided today
- `lookup` is not needed now; Claude unmasks then uses WebSearch. Future: run a script on the real file through Idli
  with masked output (p1 `todos/idli-insights/p1/run_on_real.md`).
- Numbers of up to three digits are not matched in free text; hidden columns are still coded whole.

## Left
- Claude's charts still open on the right; the left-chat binder and inline Mini draft are not built.
- Services started by hand on the laptop for this test (proxy with wire log) stay until the next restart.
- Extra Drivey workspaces from this test are still in the sidebar.
- `lib/test_chat.py` has 10 failures that predate today (also without these changes).
