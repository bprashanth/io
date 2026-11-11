# Charts on real data: what's left after the 2026-11-11 fix

From E3 (2026-11-11, `benchmarks/runs/2026-11-10-idli-pipeline-eval/REPORT.md`, `results/e3/refcheck.md`).

## Done (commits 51392d9d, dabfad55; chronology 2026-11-11 afternoon)
- Chart code may not drop rows or merge values (teach-file skill).
- When a chart uses rows with problems, `chart_show` draws them as they are, makes or opens the checked copy and
  gives its link (owner's decision: no card, the person decides what to fix).

## Correction to the E3 report
Chart code already reads exactly what the form reads (`chartkit.tables()` calls `formkit.build`). "cancel" vs
"Cancelled" is split in the form too; the checks flag it, and the person now sees it in the checked copy.

## Left to do
1. **Answers too:** `file_ask` says "rows that failed checks are included" but doesn't make the checked copy or
   give the link. Do the same as `chart_show`? (Owner to confirm.)
2. **Try it in the app** on the laptop: a file with problems, a chart from Claude, the copy made from the chart.
3. **Rerun E3** with the corrected expected answers (`results/e3/refcheck.md`). The score now depends on whether
   the person fixes the copy, so it needs a scripted "fixed" step. Waiting for the owner's go.
4. **Owner question still open:** "measures" (see the chronology entry of 2026-11-11 afternoon).
