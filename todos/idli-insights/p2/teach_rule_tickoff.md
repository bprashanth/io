# Teaching: a last step where Claude ticks off every rule the owner stated

From E6 and E2 (2026-11-10/11, `benchmarks/runs/2026-11-10-idli-pipeline-eval/REPORT.md`).

## Why
The checks Claude skips are the same in every version of the fake copy, and even when it learns from the real
file: counts across tabs (density vs tree rows, 4 of 7 times in E6), totals that don't add up (7 of 10) and
duplicate IDs (6 of 9 before the E1 fix). The file's notes said these outright, and 79% of stated rules were
caught vs about 57% of unstated ones. So this is a teaching gap, not a fake-copy gap.

## What to build (`cowork/.claude/skills/teach-file/`)
- Before the "Go back to Idli?" card, Claude lists every rule the owner stated (in the notes, cards or chat) and,
  for each, the check that covers it, or "not covered: why".
- Uncovered rules become checks, or one line on a card ("I couldn't check X because Y").
- Keep it to one step: no new card unless something is uncovered.

## How to test
Rerun E6/E2 teaching on the 5 planted-mess files, two runs each: count_mismatch, total_mismatch and duplicate_id
recall should rise, with false alarms no higher.
