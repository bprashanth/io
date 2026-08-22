# Stage 2 — Local-first query ladder and its re-verification (2026-08-20/21)

**Question.** Can a checked ladder (Arctic-Text2SQL 7B Q4 → generic router →
Qwen 3.8 27B → DuckDB → deterministic HTML) replace an open-ended agent for
private data?

**What held.** The SQL-model ranking (XiYan ≪ Arctic ~25/30 < Qwen 28–30/30);
DuckDB as the only calculator; read-only SQL parsing; the value-free frontier
envelope; the evidence discipline.

**What did not.** The regex router was tuned on the 30 dev phrasings and
accepted wrong answers out of sample (6/22 for Arctic Q4 on the realistic
holdout); the "30/30 routed replay" never passed Qwen's answers through the
router; Qwen's 30/30 was best-of-three; the dashboard gap to Antigravity was
far larger than "5–8 %".

**New measurements.** On a realistic holdout (messy headers, `State Total`
trap, text dates, joins): Arctic Q4 19/30; Qwen 3.8 27B 23/30 bare and 29/30
with the shell prompt (known categories + rules); Qwen 3.5 27B no-think 29/30
at a third of the latency; Qwen 3.5 9B no-think 24/30 (= Arctic on the dev
suite) — so the small SQL fine-tune is not the laptop tier. A frontier given
only the column schema writes a blind HTML template that local code hydrates:
Antigravity-class dashboards, all figures correct, ~$0.02, zero rows sent.

**Decision carried forward.** Tiers are general models (9B local / 27B DGX /
frontier), not a SQL fine-tune; the router must be replaced, not patched;
dashboards come from schema-only (or tokenised-sample) templates hydrated
locally; DuckDB stays as the calculator and the per-panel "how was this
computed" receipt.

**Evidence.** `docs/v2-local-first-event-decision.md`,
`docs/foundation-reverification-2026-08-21.md`,
`docs/sheltered-mode-feasibility-2026-08-21.md`,
`benchmarks/results/foundation-reverification-2026-08-21.json`,
`benchmarks/results/sheltered-mode-feasibility-2026-08-21.json`,
`benchmarks/v2/query-holdout-v2.json` (now seen; next rule change needs v3).

**Left open.** Serving the 9B/27B locally on the DGX and timing them; the
router replacement; 20-user rehearsal; Windows packaging of the Part 4 app.
