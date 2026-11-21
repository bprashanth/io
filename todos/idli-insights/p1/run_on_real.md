# Claude asks Idli to run a script on the real file, gets masked output

Owner decision 2026-11-15: `lookup` isn't needed today. For web search Claude asks to unmask a contextual value and
uses its own WebSearch (commit 32eb8775). What `lookup` may grow into is this tool.

## Why
Claude works on masked copies (`lib/maskcopy.py`). Codes in, codes out, and that covers most questions. Some don't
fit: a question about the text inside a hidden cell (how many names have a title, how long the addresses are, which
phone numbers are duplicates). Today Claude can only say it can't see that column.

## Shape
- New Idli tool, say `run_on_real(script, reason)`, in the "ask" list like `unmask`. The consent page shows the
  script and the reason in plain words.
- Idli runs the script on the real files, outside Claude's sandbox, with no network and a time limit.
- The output goes back to Claude masked. Claude writes the next script with those codes, which also match its copies.
- The person sees real values in Claude's replies and charts, as now.

## The risk and the limit
Masking finds values in the forms it knows. A script can print a value reversed, letter by letter, as character
numbers or as a hash, and nothing catches it. So:
- Output may hold only numbers, known codes and the column names. Anything else is refused and Claude is told why.
- Small counts are fine; a count of 1 next to a filter on a hidden value is still a reveal (one person). Consider
  refusing groups smaller than 5.
- Each run uses one reveal from the budget.

## Done when
- A test where Claude's script tries each escape above (reverse, ord(), base64, a hash) and gets refused.
- A live run on the shola fixture: "how many recorders' names have more than two words" answered without any name
  leaving the computer (wire audit).
