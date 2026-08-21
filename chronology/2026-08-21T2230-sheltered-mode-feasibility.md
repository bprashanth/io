# Sheltered mode is feasible on a sub-8 GB laptop; schema-only frontier closes the dashboard gap

Built a synthetic Indian-PII corpus shaped like the participant survey (four
tables, two texts, ground truth by construction) and benchmarked CPU-class
redaction engines. A 181 MB GLiNER model plus generic rules classified 33/33
PII columns with the exact class and one false positive across the four tables
in 3-8 s each on four CPU threads, including dialect and mislabelled headers.
On free text the composed local engine reached 100 % (field report) and 93 %
(WhatsApp export) span recall with over-redaction; the remote Qwen 3.5 27B
reached 100 %/100 % at about two minutes per file. Bigger multilingual and
"Indian PII" GLiNER variants were worse than the small model.

A reversible class-token pseudonymiser with a local map carried a four-turn
conversation through the 27B: places tokenised in the question, SQL over
tokens, DuckDB local, names rehydrated only on the laptop, and an ambiguous
first name correctly returned as a clarification. A leak assertion on every
outbound payload caught two real bugs during development and then held.

Remote dashboards: Gemini 3.7 Flash given only the column schema wrote a
blind template that local code hydrated; every figure on the agriculture and
scholarship pages verified correct, at ~2 cents and ~1 minute with zero rows
sent. A 20-row tokenised sample improved it further. Embedding all rows in the
model output truncated at 40k tokens and is rejected. The model invented a
source label when not given the filename; a local `__SOURCE__` placeholder is
required. Claude Sonnet 5 needed reasoning capped and more output tokens.

Caveats: rules were tuned on this corpus (development set); no real laptop
timing; no Devanagari; no quasi-identifier protection.

Evidence: `docs/sheltered-mode-feasibility-2026-08-21.md`,
`benchmarks/results/sheltered-mode-feasibility-2026-08-21.json`,
`benchmarks/pii/`, `benchmarks/runs/2026-08-21-pii-detection/`,
`benchmarks/runs/2026-08-21-sheltered-demo/`,
`benchmarks/runs/2026-08-21-remote-dashboard/`.
