# Chart code reads the file the way the form does, and never drops rows on its own

From E3 (2026-11-11, `benchmarks/runs/2026-11-10-idli-pipeline-eval/REPORT.md`, `results/e3/refcheck.md`).

## Why
The trip to Claude and back works (sent 23/24, back 22/23, about a minute and $0.15 a trip), but Claude's chart
code gave exactly right numbers on the real file in only 12 of 24 trips, the same with the 9B and Muse. The misses
come from the chart code, not the chat model or the fake copy:
1. **Readable values split.** "cancel" and "Cancelled" became two bars (0.4% and 33.2% instead of 33.6%). Chart code
   gets `chartkit.tables()`, which doesn't apply the skill's lookups, casing and spelling rules the form uses.
2. **Rows dropped silently.** In 4 of 6 household charts Claude removed repeated-ID rows before counting.
3. **Units:** "12 cm" is blank in the chart tables, while the form reads it as 12.

## What to build
- `lib/chartkit.py`: `tables()` returns the form's reading of each table, with the same value rules (case, accept
  patterns, merged spellings, units) as `formkit`. One reader, two users.
- `teach-file` skill, chart section:
  - Chart code doesn't filter or dedupe rows unless the person agreed on a card.
  - The chart's subtitle says how many rows it used.
  - Status-like columns get a spelling map in the skill (taught on the fake copy, where the variants survive).
- **Owner decision 4 (open):** should a share question that the form can't answer become a new *measure* in the
  form (answers in words, reusable by the 9B), rather than a chart? Every E3 trip went as a chart.

## How to test
Rerun E3 (`harness/e3_all.sh`, then `e3_rescore.py` with the corrected refs in `results/e3/refcheck.md`). Exactly
right should go from 12/24 to most trips; no chart should drop rows.
