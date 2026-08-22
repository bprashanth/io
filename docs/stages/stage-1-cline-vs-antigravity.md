# Stage 1 — Cline + open-weights Qwen versus Antigravity (2026-08-19/20)

**Question.** Could the product experience of Antigravity (terse question →
working dashboard, follow-ups, download) be matched by VS Code/Cline driving an
open model (Qwen 3.8 27B via OpenRouter)?

**Outcome.** Qwen 3.8 27B was competitive and the real-editor smoke favoured
Cline/Qwen (91.2 vs 80.5 on one strict smoke), but both systems had serious
failures in three of five screened cases. DeepSeek-Web + Qwen + a generic NGO
guardrail was the best multi-case result (89 mean, no serious failure) but
operationally expensive. Qwen 3.8 27B was selected as the capable open model;
Cline was not qualified as the event shell. The stage produced the product
requirements (correct numbers/units, durable follow-ups, offline page, source
and download, bounded latency) that every later stage is graded against.

**Evidence.** `narrative/2026-08-20-local-model-equivalence-field-note.md`,
`docs/product-gui-smoke-findings.md`, `docs/screening-findings.md`,
`benchmarks/results/screening-v2-counted.json`,
`benchmarks/runs/2026-08-20-product-gui-smoke/`.

**Left open then.** No privacy story; agents spent many calls installing and
retesting arbitrary web stacks; Antigravity's CDN-dependent pages fail offline.
