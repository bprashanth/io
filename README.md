# Local-first NGO data insights

<p align="center">
  <img src="assets/io.jpg" alt="Jupiter and Io" width="360">
</p>

This repository is working toward one practical event experience: an NGO user
drops in an unfamiliar CSV, workbook or PDF, asks a short plain-language
question, gets a correct desktop dashboard, and can refine it without debugging
an agent or installing a new stack for every file.

## Current decision

The current event prototype is a checked model ladder, not Cline writing a
website from scratch:

```text
local CSV/XLSX/digital-PDF ingest
  -> Arctic-Text2SQL-R1-7B Q4 proposes read-only DuckDB SQL
  -> deterministic syntax, binding, scope, unit and result-shape checks
       -> accept, or escalate to Qwen 3.8 27B on the trusted DGX
  -> DuckDB calculates locally
  -> deterministic typed report and self-contained HTML dashboard
  -> browser, download, provenance and privacy checks
  -> optional frontier layout advice from value-free metadata only
```

Arctic Q4 scored 25/30 alone. The generic router accepted 21 correct answers,
accepted no wrong answers, and escalated nine. Qwen 3.8 27B passed 30/30 in its
separate qualification run, giving a 30/30 routed replay on the frozen suite.
The larger Arctic BF16 checkpoint scored 26/30 and passed a separate 15/15
holdout, but is a server/high-end option rather than the intended laptop tier.

Read [the event decision](docs/v2-local-first-event-decision.md) before changing
this architecture. Use [the reproduction guide](docs/local-first-reproduction.md)
to run it. The aggregate result is
[`benchmarks/results/v2-local-first-ladder-2026-08-21.json`](benchmarks/results/v2-local-first-ladder-2026-08-21.json).

The frontier boundary is firm: it may receive an allowlisted intent, result
column names/types/roles and a layout contract. It must not receive the raw
question, real rows, category values, aggregates, filenames, screenshots or
generated HTML. Real participant data stays on the laptop or trusted DGX. The
OpenRouter path is for public and synthetic fixtures unless the user explicitly
changes that policy.

This is a qualified prototype, not a finished event build. Windows packaging,
local Qwen replay on the DGX, a 20-user load rehearsal, scanned-PDF OCR,
arbitrary workbook-region correction and official-data discovery remain open.

## Earlier result

The first phase asked a different question: could the product experience of
Antigravity be matched by VS Code/Cline using Qwen 3.8 27B? The model was
competitive, and the real-editor smoke favoured Cline/Qwen, but both the
five-case product screen and the editor smoke had important limitations.
DeepSeek Web plus a generic guardrail was the strongest multi-case capability
result, but it was a different, expensive harness. That phase selected Qwen
3.8 27B and taught us what the event shell must guarantee; it did not qualify
Cline as the final event architecture.

Start with [the first-phase narrative](narrative/2026-08-20-local-model-equivalence-field-note.md),
[the product GUI findings](docs/product-gui-smoke-findings.md), and
[`benchmarks/results/screening-v2-counted.json`](benchmarks/results/screening-v2-counted.json)
when revisiting that comparison.

## Repository map

- `docs/` contains architecture decisions, implementation findings and
  operational runbooks. Start with the current event decision above.
- `benchmarks/` contains frozen cases, scripts, raw run evidence and derived
  aggregates. Read [`benchmarks/DESIGN.md`](benchmarks/DESIGN.md) before adding
  cases or changing a scorer.
- `chronology/` is the append-only, timestamped experiment trail. It explains
  what happened in order, including failed and excluded runs.
- `narrative/` turns the chronology and evidence into readable field notes.
- `checkpoint/` is a local, gitignored handoff for the next agent. On this
  machine, read `checkpoint/CHECKPOINT.md` after this README. If it is absent,
  reconstruct the state from the current decision, chronology and aggregate.
- `proposals/` contains forward-looking ideas. A proposal is not measured
  evidence or a current decision.

## Working here

Reverify a suspicious claim against its raw run before replacing the current
winner. Do not tune routing, extraction or validation to sector names or to the
answer bank. Extend through general table shapes, operators, provenance rules
and observable failures. Keep development, diagnostic, counted and holdout
runs labelled separately.

Every reportable experiment should retain its exact inputs and questions,
model and settings, selected SQL or plan, deterministic checks, browser output,
screenshot, timing and cost. Append a chronology entry as the work progresses;
update a narrative only when there is a coherent new result.
