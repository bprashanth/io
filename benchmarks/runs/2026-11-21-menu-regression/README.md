# Does the smaller menu hurt? (2026-11-21)

**Question:** the menu (what the mapper is told exists) was trimmed: every sheet and tab name, but columns only for
the sheets a question seems to be about. Fewer characters for the 9B to read; did it cost answers?

**Method:** the 53 dev tasks and the owner's 11, run twice with the 9B as mapper on two copies of one sandbox
(87profligate with embeddings, no definitions), the same code, once trimmed and once with `IDLI_MENU_FULL=1`.
Every turn logs a **menu miss** when a command or error used a sheet whose columns weren't sent. The dev runs were
graded blind with read-only SQL (`grade.sh`), one grader each.

| | step errors | repairs | empty results | menu misses | prompt (median chars) | correct | partial | wrong |
|---|---|---|---|---|---|---|---|---|
| trimmed | 4 | 6 | 9 | 3 (none with an error) | 9,218 | 17 | 12 | 5 |
| full | 6 | 9 | 12 | - | 13,705 | 26 | 5 | 1 |

**What the gap is made of** (the 9 tasks correct only with the full menu):
- 4 had the same or nearly the same commands in both runs and were graded differently (T12, T20, T21, T26): grader
  noise.
- 2 were different plans from the same 9B (T13, T29; T29 failed on `kind = slides`, an unquoted value, now read as a
  value in code).
- 3 had small plan differences not clearly caused by missing columns (T07, T14, T42); the folders were listed in
  full in both runs.
- The 3 menu misses all worked anyway (`get sheet --outline`, a correct column), one was a folder sharing a sheet's
  name (no longer counted).

**Decision:** not proven harmless, so the full menu is the default again; trimming is opt-in (`IDLI_MENU_TRIM=1`)
and every turn keeps logging the menu and any miss. To decide properly: repeat each arm 3 times with 2 graders, or
compare on a new held-out set.

`results/`: turns (`*-nine.jsonl` trimmed, `*-nine-fullmenu.jsonl` full), grades, `compare.py`.
