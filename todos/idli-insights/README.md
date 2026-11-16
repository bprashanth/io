# Idli todos, by priority

- **p1/**: for the demo, and the work that decides the architecture.
  - [Pipeline evals](../../benchmarks/runs/2026-11-10-idli-pipeline-eval/PLAN.md): E6, E7, E1-E3 done (report on
    branch `idli-pipeline-eval`); E4 (answer wording) and E5 (charts) next.
  - [Charts on real data: what's left](p1/chart_code_reading.md): no silent row drops; messy rows go to the
    checked copy (shipped 2026-11-11). Next: the same for answers, try in the app, rerun E3.
  - [One file at a time: index and graph built as files are learned](p1/file_by_file_index.md)
  - [Read every table on a tab (subtables, info blocks)](p1/subtables.md): the owner's decision; today Idli reads
    one table per tab.
  - [Installers and the demo gaps](p1/deployment_strategy.md): D1-D11, with Pyodide as row 21.
  - [Paseo patches](p1/paseo_patches.md): P1, P3 and P12 for the demo.
  - [The Builder's exit test](p1/builder_acceptance_tests.md): the failing request becomes the person's test;
    on No, the next option on the capability menu.
- **p2/**: measured speed-ups, not integrated yet.
  - [Free tier capacity for ~100 people on one DGX (E11)](p2/capacity_free_tier.md): moved here because E7
    held up (the local 9B with the split matched Muse on fresh chats); test the 9B only.
  - [Fake copy: keep date order, read "12-Mar-22" dates](p2/fake_copy_dates.md) (E1).
  - [Teaching ticks off every rule the owner stated](p2/teach_rule_tickoff.md) (E6/E2 misses: counts across tabs,
    totals).
  - [Optimizations](p2/optimizations.md). Most of the index rows (1-4) wait on the one-file-at-a-time decision.
- **p3/**: later.
  - [Strict mode: flag every inconsistency](p3/strict_mode.md)
  - [Clone a Mini: the workflow without its file, for someone's own copy](p3/clone_mini.md)
  - Candidates: share questions become form measures instead of charts (decision 4 in
    [chart_code_reading](p1/chart_code_reading.md)); Claude planning on redacted questions (E10); a small model for
  setting the form's dials (E9) if constrained output isn't enough.

When something ships, record it in the chronology (`docs/cowork-poc.md`) and delete it here.
