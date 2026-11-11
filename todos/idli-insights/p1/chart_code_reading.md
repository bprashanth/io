# Charts on real data: what's left after the 2026-11-11 fix

From E3 (2026-11-11, `benchmarks/runs/2026-11-10-idli-pipeline-eval/REPORT.md`, `results/e3/refcheck.md`).

## Done (commit 51392d9d, chronology 2026-11-11 "Charts never drop rows silently")
- Chart code may not drop rows on its own (teach-file skill).
- `chart_show` asks "Skip them / Fix them first" when rows the chart uses have problems (owner's decision).

## Correction to the E3 report
Chart code already reads exactly what the form reads (`chartkit.tables()` calls `formkit.build`). "cancel" vs
"Cancelled" was split in the form too: Claude never added a `normalize` map for the status column while teaching.
So the cause is teaching, not a second reader.

## Left to do
1. **Teaching adds `normalize` maps for readable variants that would split a count** (status spellings, village
   casing): owner decision 1 of 2026-11-10 ("flag only when it would confuse the 9B"). The teach skill now says so
   for charts; check the main teaching steps say it too, and that the fake copy keeps such variants (E1: casing
   survives; "cancel"-style synonyms not measured).
2. **Units in number cells** ("12 cm", "approx 12") read as blank, in the form and the charts alike
   (`filekit.as_number` and `formkit._clean_view` strip only Rs/INR/commas). Read them quietly.
3. **Rerun E3** with the corrected expected answers (`results/e3/refcheck.md`), after 1-2, to measure the gain.
   Waiting for the owner's go.
4. **Owner question still open:** "measures" (see the chronology entry of 2026-11-11 for what that means).
