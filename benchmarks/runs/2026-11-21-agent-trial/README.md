# Agent trial: asking the scaffold what the owner would ask (2026-11-21)

The agent used the scaffold like the owner does: the real CLI (`desktop/idli ask`), test account 87profligate,
default models (the served 9B maps and words replies; Clef judges). A yes card was answered "yes". Each round ran
on a clean copy of the sandbox (no definitions, labels or views), and every answer was checked with read-only SQL.

- `turns.txt`, `drive.sh`: rounds 1 and 2 (22 questions: trust, search, explain, own categories, follow-ups,
  a workflow, things it can't do). `transcript-round1.md`, `transcript-round2.md`.
- `turns-round3.txt`: 12 new questions written and frozen by hash (`turns-round3.sha256`) before round 2's results
  were read, so they test the round-1 fixes rather than being tuned to them. `transcript-round3.md`.
- `turns-retry.txt`: round 3's failures after their fixes. `transcript-retry.md`.

The sandboxes are `~/idli-sbx/agent1` (round 1) to `agent4` (retry), on the DGX. They hold test-account data and
are not in git.

## What failed, and the general fix for each

| # | Ask | What happened | Fix (commit) |
|---|---|---|---|
| F1 | meetings next week | "three meetings" with 4 shown | list numbering no longer counts as numbers in the result; a count in the reply must match (e75cce6f) |
| F2 | did I decline any meetings? | `my_response = "declined"` errored | double-quoted values read as values unless they name a column (e75cce6f) |
| F3 | how many PDFs | "1 PDF, 86 pages long" | a count prints "Count: 86 files match." (e75cce6f) |
| F6 | which of those are really about it | the judge ran but Ran didn't show it after a repair | store-writing steps kept in Ran (e75cce6f) |
| F8 | explain border effects; caste and entrepreneurship | `summarise --search` crashed (3 columns) | fixed; the mapper's choice was right (e75cce6f) |
| F9 | find the article about adivasis | "adivasis" didn't find "adivasi" | a plural search word finds the singular (e75cce6f) |
| F10 | sheets with a column called Toda name | sheet search read names only | sheet search covers column names (e75cce6f). The column is on a later tab; sync reads first tabs only (p1 subtables) |
| F11 | which emails are newsletters | defined and judged a "newsletter" category, then excluded bulk mail | field meanings in the menu and `explain` (is_bulk = newsletters, promotions, notifications) (e75cce6f) |
| F12 | which emails need a reply | judged only mail containing "reply" (the 9B added `--search reply`) | in code: a judge narrows with `--search` only to a search already shown (6c05ad0b) |
| F13 | which documents are about trade policy | "19 documents" for 49 | count check; search notes how many have the words together (e75cce6f) |
| F14 | summarise wincoop | went to `summarise --search` | rule: a named file goes to `summarise file` (e75cce6f) |
| F15 | what's in the leads sheet | `get sheet --sheet` errored | tolerated (e75cce6f) |
| F17 | reply ... saying thanks | the 9B's JSON was cut off | one retry asking for short JSON (e75cce6f) |
| R2 | (same) | "the draft is ready in the unsent folder", false | a draft is never described as saved (6c05ad0b) |
| R3 | explain border effects | the explanation printed twice | no wording over `summarise` (6c05ad0b) |
| R4 | find the article about adivasis | good wording dropped over "2018" | counts checked against values shown (6c05ad0b) |
| 3.2 | who emails me the most | `'direction = \'in\''` unreadable | read as meant (069d76c4) |
| 3.7 | how many sheets, and which has most rows | grouped by row count; then only the second part shown | example for "which has the most"; two-part questions show each short step (069d76c4) |
| 3.10 | summarise the Thorat paper | no passages, yet the 9B wrote a paragraph | fall back to pages with the words; never call the 9B with nothing to read (069d76c4) |
| 3.11 | draft a reply to the latest partnership email | pasted a listing row as --reply-to; curly apostrophe | --reply-to takes a pasted row and matches words (069d76c4) |

## Round 3 (frozen questions), checked with SQL

7 right, 1 partly right, 4 wrong of 12 before the round-3 fixes. After them (`transcript-retry.md`):
"who emails me the most", "how many sheets and which has the most rows" and "summarise the Thorat paper" are right.
The draft still picks the latest email instead of the latest *partnership* email: the 9B leaves out the person's
word. "Which emails need a reply" copied the manual's `urgent` example (wording and name); the yes card shows it.

## Still open

- The 9B drops words the person said (partnership) and copies examples from the manual (urgent).
- Workflows ("have any of my leads emailed me?") need views and Minis; the 9B's SQL breaks.
- Sync reads only the first tab of a spreadsheet.

The turn-by-turn results and transcripts hold real rows from the test accounts, so they are kept on the DGX
and not in git.
