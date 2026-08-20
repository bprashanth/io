# Event insight-journey benchmark

This directory extends the original Antigravity-versus-Cline benchmark from
whole coding agents to deployable data-to-insight systems for an approximately
20-person NGO workshop.

The unit under test is one complete journey:

```text
ordinary-language request -> admitted data -> checked calculation -> rendered
desktop dashboard -> follow-up change -> cited/exportable result
```

The same cases, ordered messages, immutable inputs and numerical oracles are
reused from `../cases/`. An architecture is not excused from correctness because
it uses a planner/executor/renderer split. Conversely, a split architecture is
not penalised for avoiding general-purpose code generation when the participant
receives an equivalent or better result.

## Frozen phase-one arms

- `whole-agent-antigravity`: preserved default-product baseline.
- `whole-agent-cline-qwen38-27b`: current OpenRouter product candidate.
- `split-qwen38-27b-deterministic`: 27B emits a validated plan; local code
  computes and renders.
- `split-qwen35-9b-deterministic`: small untuned control for the restricted
  plan task. This is distinct from the existing local Algebra LoRA.
- `split-algebra-2b-or-9b-deterministic`: owner-approved live replay of the
  tuned compiler, blocked while the documented endpoints are offline.
- `schema-only-layout-ablation`: a remote model sees only a schema, visual
  intent and synthetic placeholders; local code hydrates real computed values.

Arms may share the deterministic ingest, executor, result contract, renderer
and browser checks. They must not share model outputs or case workspaces.

## Success and early stopping

Use `event-v1.json` with the existing critical-failure gates. Phase one is
desktop-only. A system must recover without user debugging, and a follow-up is
successful only when the durable page and export reflect it.

A small compiler may stop after three cases if it cannot produce a valid,
executable plan in two of them. A valid-plan result is not enough to claim
equivalence: passing arms still complete the rendered visual and multi-turn
suite. Routing policies are frozen before holdout and report their escalation
rate as well as combined quality.

## Evidence layout

Each run will be stored below `../runs/<batch>/<case>/<arm>/<rep>/` using the
existing run-record conventions plus:

- `dataset-profile.json`: deterministic local profile shown to the compiler;
- `plan-request.json` and `plan-response.json`;
- `validated-plan.json` or `plan-error.json`;
- `insight-report.json`: computed values and provenance given to the renderer;
- `workspace/`: self-contained page and downloads;
- browser log, control assertions and desktop screenshot;
- routing and retry events, timing, usage and cost.

Never store API credentials, participant data or local model caches.
