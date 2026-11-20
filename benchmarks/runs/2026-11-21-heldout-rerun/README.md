# Held-out rerun after the 20-21 Nov changes (2026-11-21)

**Question:** did the new surface (quoted phrases, ranked search, `summarise --search`, `judge --search`, folds,
the rewritten manual, the yes card, Clef as judge) make the mappers better, or confuse them?

**Method:** the same 27 frozen held-out tasks as 2026-11-20 (`../2026-11-19-record-store/bank/tasks_heldout.json`,
sha256 c81e4cd2...; unchanged), run once on frozen code (commit in `FROZEN_COMMIT`: 9afd8e93), each mapper on its
own copy of one synced sandbox (87profligate: 190 emails, 10 events, 192 files with text and cards; stores are not
in git). Graded by fresh blind graders with read-only SQL (`../2026-11-19-record-store/grader/grade.sh`, today set to
2026-11-21). Two changes to the harness, both logged per turn: a yes card is accepted on the tester's behalf
(`card_shown_and_accepted`), and Clef judges (the new default).

## Results

| mapper | date | correct | partial | wrong | refused ok | refused wrong | failed | fit / ack / not repetitive |
|---|---|---|---|---|---|---|---|---|
| 9B (served, Q5) | 2026-11-20 | 5 | 6 | 6 | 8 | 1 | 1 | 3.6 / 3.6 / 4.2 |
| 9B (served, Q5) | **2026-11-21** | **10** | 3 | 4 | 7 | 0 | 3 | 3.6 / 3.4 / 3.4 |
| idli-remote | 2026-11-20 | 13 | 4 | 1 | 8 | 0 | 1 | 4.5 / 4.8 / 4.6 |
| idli-remote | **2026-11-21** | **13** | 3 | 2 | 8 | 0 | 1 | 4.3 / 4.2 / 4.0 |

Graders differ between runs, so differences of 1 to 3 tasks are noise (as on 2026-11-20).

- **The 9B doubled its correct answers** (5 to 10). By kind: trust 3 of 5, own definition 6 of 10, workflow 1 of 7.
- **idli-remote held steady**: own definitions 9 of 10, trust 4 of 5. The larger manual did not confuse it.
- **Failures fixed after the freeze** (from the agent trial, `../2026-11-21-agent-trial/`): T55 "1 document" for
  a count (both mappers; F3), T56 `get sheet --sheet` (F15), T68 the 9B's cut-off JSON (F17), T70 quoting.
  T71 found two more gaps, fixed after: `--on "next month"` and `judge --since/--until/--on` (same flags as
  `list`); a repeated `--label` now means both.
- **Not fixed:** workflows (leads, prep lists) need views and Minis; the reply to T70 reversed which emails needed
  action.

These after-freeze fixes need a new held-out set to be measured: these 27 tasks have now been seen.

`results/`: `heldout-*.jsonl` (turns), `heldout-*.log`, `grades-*.json`. `python ../2026-11-19-record-store/analyze.py
results/heldout-remote.jsonl results/grades-remote.json` prints the tables.
