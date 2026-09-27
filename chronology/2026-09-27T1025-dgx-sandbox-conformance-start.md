# DGX: start direct Codex sandbox conformance

The owner narrowed the first CI pass to the bundled command sandbox, before io launch gates
or other security surfaces. Recorded the full scope and phased plan in
[the proposal](../proposals/sandbox-conformance-ci.md). This entry precedes implementation;
no new conformance result is claimed yet.

Starting branch io_codex_3 at 65894df. Existing untracked September 14 evidence and
`docs/sandbox.md` remain unrelated and untouched. Plan to use a separate sandbox-conformance
branch for the requested CI experiments, without touching main or publishing a release.
GitHub authentication is available; existing package workflow is startup-only. Read-only
inspection of the five most recent runs showed successful main package runs, which is not
sandbox evidence.

Use io's pinned Codex 0.154.0 and generated permissions directly. The Windows unelevated
setting and native Mac behavior must be measured. The owner's anticipated Windows/Mac
failures are a hypothesis, not expected-failure assertions. Startup failure must remain
separate from actual prohibited TCP connections or filesystem access. Existing DGX Linux
arm64 evidence cannot substitute for the required Linux x64 CI row.

Implementation evidence will be kept in `benchmarks/runs/2026-09-27-sandbox-conformance/`.
Smaller CLI models may handle bounded probe/reporting plumbing; privacy contract, controls,
interpretation and final CI review remain with the coordinating agent. No model secrets or
live model requests are needed to execute the suite itself.
