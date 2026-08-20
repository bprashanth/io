# GPT-OSS 20B planner screening

## Outcome so far

`openai/gpt-oss-20b` at low reasoning effort is the first sub-27B candidate to pass the split pipeline's smoke, five-turn ANC, safety-sensitive programme, clean-XLSX, narrow digital-PDF, bounded Census-connector and one structured irregular-workbook journey. It is not yet the winner: unrestricted web discovery, diverse irregular files, local inference and concurrency remain untested.

The useful result is architectural. A 20B model can plan these bounded analyses when a trusted layer owns filtering, arithmetic, safety checks, HTML, charts and downloads. It should not be asked to calculate values or write an unconstrained application.

## Counted repetitions

| Journey | Requests / repairs | Model time | OpenRouter cost | Result | Antigravity reference |
|---|---:|---:|---:|---|---|
| three-turn CSV smoke | 4 / 1 | 30.694 s | $0.00027114 | all deterministic and browser checks pass; visual 8.8/10 | IDE default: 80.5/100, 594.967 s |
| five-turn ANC CSV | 9 / 4 | 57.782 s | $0.00079874 | all critical checks pass; omits a separate visible 6 pp 2023 gap | CLI default: 84/100, 301.29 s |
| four-turn programme CSV | 6 / 2 | 41.424 s | $0.00064762 | full oracle passes after trusted safety-note rendering | CLI default: 10/100, 238.545 s |
| four-turn clean XLSX | 4 / 0 | 31.870 s | $0.00039448 | all critical checks pass; omits separate visible 7 pp 2023 gap | CLI default: 89/100, 428.938 s |
| four-turn digital PDF | 5 / 1 | 22.670 s | $0.00037850 | full oracle passes | counted PDF run: 0/100 after Google permission failure |
| four-turn bounded Census connector | 6 / 2 | 17.064 s | $0.00131031 | full oracle passes; connector starts after source discovery | CLI default: 78/100; exact values but unrelated citations |
| four-turn merged/stacked XLSX | 5 / 1 | 26.872 s | $0.00047230 | full oracle passes; bounded attendance-layout adapter | CLI default: 57.3/100 counted journey; rescued visual 9.3/10 |

The Antigravity scores are preserved references, not a perfect-answer target. The ANC baseline itself lost durable follow-up details and had a broken control; the programme baseline fabricated data and advice. GPT-OSS is judged against those observed pages while still failing closed on errors that would harm a nontechnical participant.

## What failed before the counted runs

- GPT-OSS low initially confused a within-district time `change` with a same-time cross-district `difference` and exhausted three repairs.
- Medium reasoning repaired that turn but exceeded the 120-second bound on the next turn. Medium is therefore not the event default.
- A later low run calculated the changes but kept three districts that the user had excluded with “compare Gaya and Nalanda.” The page worked, but the oracle correctly failed durable focus.
- The first programme run calculated every value correctly but did not keep the intervention limitation in the page note. The second attempt used safe equivalent wording but failed an overly literal validator that demanded the word “cannot.”
- Human inspection found that the indicator selector changed the chart but left the other indicator visible in a horizontally scrollable table. The automated browser check had missed this.

All failed runs remain under `benchmarks/runs/2026-08-20-split-small-model-screening/`.

## General harness changes

The fixes are model-independent:

- define `change` as one entity across two times and `difference` as two entities at one time;
- reject a named two-entity comparison that retains unrelated entities;
- require a structured causal-limit flag for causal questions;
- let the trusted renderer turn that flag into a standard visible refusal of unsupported causes and interventions;
- make table content follow the selected indicator and make the browser checker verify the selected header.
- compile explicit durable year ranges and named two-entity comparisons into filters before execution, while preserving the model's raw plan and every normalization for audit.

These checks are part of the product architecture, not benchmark answer keys. They prevent plausible-looking bad outputs and allow the user to retry without debugging.

## Smaller Qwen screen

The low-effort Qwen alternatives did not reach promotion:

- Qwen 3.5 9B and Qwen 3.5 35B-A3B timed out on the first smoke turn;
- Qwen 3 8B returned no usable JSON;
- Qwen 3 14B completed turn one, then timed out;
- Qwen 3 30B-A3B completed turn one but collapsed on the follow-up into repeated row limits and ignored the requested year.

The early-stop rule was applied because these candidates were already materially worse than Antigravity in the first one or two easy turns.

## Scope warning: files are not flat tables

These results do not establish arbitrary Excel or PDF ingestion. One added workbook case now covers merged two-row headings, several tabs, blank separators, stacked compatible subtables and the correction “there is another table below.” Its current adapter is intentionally labelled bounded and is still tailored to that layout family. Real NGO files can also have horizontal subtables, deeper or inconsistent headings, formulas, hidden rows, footnotes, cross-tab joins, scanned pages and layout as meaning. Ingestion must preserve sheet, cell range, merged ranges, page, table region and bounding-box provenance before choosing a table; a user correction must be able to add or switch regions without requiring coordinates.

## Next gates

1. Add several structurally different but ordinary workbook/PDF cases; do not tune ingestion to the single attendance workbook.
2. Test a smaller locally runnable candidate now that the 20B boundary is established.
3. Add bounded official connectors without confusing them with open-web research.
4. Run the winning remote configuration locally and measure wall time, memory and bounded-retry rate.
5. Only then estimate laptop versus DGX Spark capacity for 20 event users.
