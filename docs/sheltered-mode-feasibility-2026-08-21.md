# Sheltered mode: can a sub-8 GB laptop redact, and does the frontier close the dashboard gap?

Date: 2026-08-21. Aggregate:
[`benchmarks/results/sheltered-mode-feasibility-2026-08-21.json`](../benchmarks/results/sheltered-mode-feasibility-2026-08-21.json).
Code under `benchmarks/pii/`. Everything here ran on synthetic data; the real
participant survey (`/tmp/io.xlsx`) was read only to shape the corpus and stayed
local.

## Answers first

1. **Replace Arctic with the 27B?** Yes. The laptop tier should be a general
   model or nothing; the SQL fine-tune added no accuracy and cannot help with
   redaction, clarification or layout.
2. **Was "frontier gets only the schema" ever tried?** No — Codex generated the
   envelope every turn and never sent it. Tried now: it works, and it closes
   the dashboard gap (below).
3. **Can a laptop with <8 GB do content-based redaction?** For spreadsheets,
   yes, with a 181 MB model on 4 CPU threads in 3–8 s per file. For free text,
   mostly (93–100 % span recall) with over-redaction; the trusted 27B is
   perfect on the same text but slow. The survey says 11 of 30 participants
   have *less than* 8 GB, so CPU-only is the real floor and it holds.

## What was built

| Piece | File | What it does |
|---|---|---|
| Corpus | `benchmarks/pii/build_pii_corpus.py` → `corpus/` | 4 tables + 2 texts shaped like the survey's data (scholarship applicants, donors, child fitness, KoBo household survey, WhatsApp export, field report). Hinglish/dialect/generic headers (`Naam`, `Gaon`, `col_17`), Verhoeff-valid Aadhaar, PAN, phones in three formats, lowercase/ALLCAPS/initialled names. Ground truth by construction, offsets self-verified. |
| Span engines | `benchmarks/pii/detect.py` | regex+validators, Presidio, GLiNER variants, a composed `textv2` engine, and a remote-LLM engine; span and column scorers. |
| Column classifier | `benchmarks/pii/columns.py` | Generic ordered rules: validators → long-unique-number → code-like ids → precise coordinates → categoricals (sensitive vocab / name-shaped) → GLiNER on `header: v1; v2; …` windows → free text. Returns the rule and confidence for a UI. |
| Pseudonymiser | `benchmarks/pii/pseudonymize.py` | Class-prefixed stable tokens (`NAME_146`), local reversible map, cross-column consistency, DOB→year, GPS→2 dp, free-text span replacement, `redact_question` with partial-name resolution and ambiguity return. |
| Sheltered conversation | `benchmarks/pii/sheltered_query_demo.py` | Pseudonymise → 27B writes SQL over tokens → DuckDB local → rehydrate; leak assertion on every outbound payload. |
| Remote dashboards | `benchmarks/pii/remote_dashboard.py` | `schema`, `redacted-sample`, `redacted`, `full` envelopes; Playwright offline checks. |

## Results

### Redaction on a laptop-class engine (CPU, 4 threads, 181 MB model)

Column level (the redaction unit for spreadsheets), GLiNER-edge + rules:

| File | PII columns | Found | Exact class | False-positive columns | Seconds |
|---|---:|---:|---:|---|---:|
| scholarship_applicants.csv (20 cols, dialect/mislabelled headers) | 12 | 12 | 12 | 0 | 5.0 |
| donor_transactions.csv | 5 | 5 | 5 | 1 (`Date`→dob) | 2.7 |
| child_fitness_scores.xlsx | 7 | 7 | 7 | 0 | 3.7 |
| household_survey.csv (40 KoBo cols) | 9 | 9 | 9 | 0 | 8.0 |

Rules alone (no model): 43 % / 60 % / 43 % / 11 % — the model is what finds
names and places under headers it cannot read. The first per-cell approach
(model on isolated cells, no header) found everything but flagged up to 20
false-positive columns per file; header-anchored windows fixed that. A
generic "8+ digits, nearly unique" rule catches bank accounts and ration cards
under any header; Aadhaar is caught by checksum even inside other digits.

Free text, span level (overlap match):

| Engine | Field report (117 spans) | WhatsApp export (534 spans) | Time |
|---|---:|---:|---|
| regex+validators | 5 % | 15 % | ms |
| Presidio + spaCy lg | 88 % / p .53 | 66 % / p .45 | <1 s |
| GLiNER-edge alone | 98 % / p .72 | 68 % / p .99 | 2–4 s |
| **GLiNER-edge composed (chat-sender rule, title-cased second pass, propagate found names)** | **100 % / p .64** | **93 % / p .68** | 4–9 s |
| Qwen 3.5 27B remote, no thinking | 100 % / p 1.0 | 100 % / p 1.0 | ~2 min per file |

GLiNER-multilingual (1.1 GB) and the "Indian PII" fine-tune were *worse* than
the 181 MB edge model. Presidio's names come from spaCy and miss Indian names.
Remaining local misses are lowercase names the title-case pass still skips and
ages written as bare numbers; remaining false positives are over-redaction of
school/scheme phrases, which is the safe direction but costs analytic value.

### Follow-ups with names (the "which Sameer" problem)

`benchmarks/runs/2026-08-21-sheltered-demo/fitness/transcript.json`, Qwen 3.5 27B, ~2 s per turn:

| Turn | Local question | Sent | Outcome |
|---|---|---|---|
| 1 | 3 tallest boys in Shirur and Kalyanpur | `…in PLACE_040 and PLACE_049…` | SQL over tokens; rows `NAME_146, 155.9, 7` rehydrated locally to Santosh Kulkarni |
| 2 | what is Santosh's shuttle run time | *not sent* | two children match "Santosh" → UI asks which |
| 3 | Santosh Kulkarni, what is his… | `NAME_146, what is his…` | correct row |
| 4 | which coach trains the most children in Basaith | `…in PLACE_021` | `NAME_204, 3` → coach name rehydrated locally |

The leak assertion (no map value in any outbound payload) held on all turns.
It fired twice during development — once when the detector tokenised the
word "height", once when it re-tokenised an existing token — and both were
real bugs. Keep it as a permanent runtime guard.

### Does the frontier close the dashboard gap with no data?

`benchmarks/runs/2026-08-21-remote-dashboard/`:

| Data | Model | Envelope | Rows sent | Result | s | USD |
|---|---|---|---:|---|---:|---:|
| agriculture (public) | Gemini 3.7 Flash (= Antigravity's model) | **schema only**, `__DATA__` injected locally | 0 | 4 KPIs, 2 charts, sortable table, every number correct | 62 | 0.023 |
| agriculture | Gemini 3.7 Flash | full rows (control) | 6 | same class of page | 55 | 0.020 |
| agriculture | Claude Sonnet 5 | schema only | 0 | first run truncated at 16k tokens (10.8k of them reasoning); rerun renders, fails on a 4 px overflow | 45 | 0.062 |
| scholarship (PII, 300 rows) | Gemini 3.7 Flash | schema only | 0 | 5 KPIs (all verified: 300 / 48 approved / 67.17 % / ₹1,29,234 / 15 talukas), 4 charts, table | 55 | 0.021 |
| scholarship | Gemini 3.7 Flash | **20 pseudonymised sample rows + `__DATA__`** | 20 | richest page: status-stacked bars by taluka and category, top-15 table honoured | 47 | 0.018 |
| scholarship | Gemini 3.7 Flash | all 300 pseudonymised rows embedded in output | 300 | truncated at 40k output tokens, empty table | 214 | 0.089 |

Conclusions: the Antigravity-quality gap was a *renderer* gap, not a model
gap. A frontier writing a blind template from the schema produces the same
class of page Antigravity did, for ~2 cents, with zero rows leaving the
laptop. A tokenised 20-row sample makes it better (it learns category
vocabularies). Asking the model to embed data is strictly worse on cost,
latency and privacy — never do it. Offline/console/overflow checks plus
"table has rows" and "not truncated" caught every bad page; the blank Sonnet
page passed the original checks, so keep the stricter ones.

Two hazards found: (a) the model invented a source label ("State Scholarship
Management Portal") when not given the filename — the template must carry a
`__SOURCE__` placeholder filled locally; (b) the raw question was sent as the
intent in schema mode — it must go through `redact_question` first, as the
conversation demo does.

## Recommended sheltered-mode design (feasible on the measured floor)

```text
open mode      : nothing redacted; remote sees rows (consented / public data)
sheltered mode : 
  ingest  -> column classifier (rules + 181 MB GLiNER, CPU) -> proposed redaction
          -> UI shows the sheet with flagged columns tinted + the rule that fired;
             user unticks/adds columns; choice is saved per file hash (never re-asked)
          -> "just do it" option skips the review
  tables  -> pseudonymise locally (stable class tokens; DOB->year; GPS->2 dp)
  text    -> local composed engine (93-100 % recall, over-redacts) with a
             side-by-side preview the user must glance at the first time;
             files too long to review are refused in sheltered mode, or the
             user consents to the trusted 27B redactor (perfect, ~2 min/15 KB)
  query   -> redact_question (known values, partial names, ambiguity -> ask)
          -> low/medium/high model sees schema + tokens only
          -> SQL runs locally in DuckDB; tokens rehydrated on the laptop
  page    -> frontier/27B writes a template from schema + tokenised sample;
             local code injects rows and source; offline/console/overflow/
             rows/truncation checks before showing it
  guard   -> leak assertion against the local map on every outbound payload
```

Human-in-the-loop cost: one column review per new file (4–20 columns, most
pre-ticked correctly), one glance at a redacted text preview, and an
occasional "which Santosh?" — not per-value fatigue.

## Limits and what is not shown

- Development-set numbers: rules were tuned on this corpus. Build a second
  corpus with a different generator/seed (or real consented files) before
  quoting recall. Real Excel layout mess (merged headers, multiple regions)
  was not in scope here and still applies.
- Names in Devanagari/other scripts, transliteration variants ("Kulkarni" vs
  "Kulkarney") and nicknames are untested; the map matches exact/casefolded
  strings only.
- Quasi-identifier re-identification (age + village + school can identify a
  child) is not addressed; sheltered mode hides direct identifiers, it is not
  k-anonymity.
- Latencies are DGX CPU threads, not a real 8 GB Windows laptop.
- Fine-tuning a small Indian-context PII model is not justified yet: the
  off-the-shelf 181 MB model plus generic rules reaches 93–100 %; collect real
  misses first.

## Next

1. Second unseen corpus; measure without touching rules.
2. Serve GLiNER-edge as int8 ONNX (46 MB) inside the local app; time it on a
   real low-RAM laptop.
3. `__SOURCE__` placeholder, question redaction in dashboard mode, and the
   conversation-aware "prefer entities shown last turn" resolver.
4. Re-run the v2 query holdout through the sheltered path to confirm SQL
   accuracy is unchanged when names/places are tokens (it should be: only
   categorical labels change).
5. Then the UI: tinted-column review, per-file memory, "trust and go".
