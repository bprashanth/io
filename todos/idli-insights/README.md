# Idli todos, by priority

- **p1/**: for the demo, and the work that decides the architecture.
  - [Pipeline evals](../../benchmarks/runs/2026-11-10-idli-pipeline-eval/PLAN.md): E6 (cleaning output on messy
    data) and E7 (fewer tools by phase) first, then E1-E3 (fake copy, teaching, bouncing to Claude).
  - [One file at a time: index and graph built as files are learned](p1/file_by_file_index.md)
  - [Installers and the demo gaps](p1/deployment_strategy.md): D1-D11, with Pyodide as row 21.
  - [Paseo patches](p1/paseo_patches.md): P1, P3 and P12 for the demo.
- **p2/**: measured speed-ups, not integrated yet.
  - [Optimizations](p2/optimizations.md). Most of the index rows (1-4) wait on the one-file-at-a-time decision.
- **p3/**: later (empty for now). Candidates: Claude planning on redacted questions (E10); a small model for
  setting the form's dials (E9) if constrained output isn't enough.

When something ships, record it in the chronology (`docs/cowork-poc.md`) and delete it here.
