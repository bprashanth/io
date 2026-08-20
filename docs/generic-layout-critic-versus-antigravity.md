# Generic planner/critic on a second workbook layout

## What this gate changes

`dev-xlsx-regions-002` is a second development layout family, not a new sector-specific flow. Its workbook has two horizontally adjacent tables with different units, merged headings, three tabs and a larger irrelevant rectangular sheet. The follow-up says only that another table is “on the right,” and asks “how much higher” rather than reusing the earlier benchmark's gap wording.

The production extractor was rewritten to use merged-cell bounds, header geometry, year leaves, categorical row labels, numeric bodies, compatible category sets and exact cell ranges. The old code that named attendance, boys/girls and primary/secondary was removed. Metric words come from the workbook itself. The trusted computation layer is unchanged.

The rule-assisted English constraint compiler is not used in the counted run. GPT-OSS 20B Low produces a generic plan; Gemini 3.7 Flash Low independently reviews whether that executable plan satisfies the conversation. The critic receives the conversation, workbook geometry and column metadata, the previous and proposed plans, and the executed result's column metadata. It receives no raw rows, min/max summaries, enumerated values or benchmark answers. The exact redacted critic request is retained with every call. Deterministic checks cover mechanics, not sector meaning.

## Counted split result

The GPT-OSS planner plus metadata-only Gemini critic passed every oracle and browser check. Turn 2 added the right-hand referrals table without losing screening. Turn 3 retained only Gaya and Nalanda in 2023 and stated both requested answers: 8 percentage points for screening coverage and 10 completed referrals. Turn 4 retained the scope and downloaded two rows with both measures, the sheet, both table labels and both ranges.

The reproducible counted run used five planner calls and four critic calls, 35.259 recorded model seconds and $0.004125425. One malformed first plan on turn 3 was rejected mechanically before the critic; the bounded repair succeeded. There were no timeouts. The desktop page has no browser errors, external runtime requests or page-level overflow. Human visual review scores it 8.8/10: clear, complete and restrained, though less rich than Antigravity, reliant on an indicator switch for the two unlike units, and with an internally scrolling provenance table.

A self-critic ablation failed. GPT-OSS reviewed its own turn-3 plan as complete even though it showed only the screening gap and omitted the referral gap. Another self-critic call timed out at 120 seconds. Merely calling the same small model twice is therefore not a sufficient independent check.

Qwen 3.8 27B worked as an independent critic but was not a good always-on event path: its successful earlier run took 141.572 recorded model seconds and cost $0.02545797 for this four-turn journey. Gemini is therefore a temporary semantic-review baseline and possible escalation path, not evidence that the final system is local. The next model-search stage should replay the same redacted critic decisions against smaller open reviewers and invoke a frontier critic only when they reject or are uncertain.

## Antigravity comparison

Antigravity CLI 1.1.15 with untouched default Gemini 3.7 Flash (High) completed four agent invocations in 267.386 seconds and showed strong workbook understanding. Its rescued page is visually excellent (9.5/10), has separate charts for the unlike units, exact source-grid inspection and a correct two-block Excel download. Its textual turn-3 response also gives the exact 8 pp and 10-referral answers.

The product returned an artifact-path permission `ERROR` on every turn. The final webpage does not state either requested cross-block gap, invents an unsupported 70% state target and “Target Met/Approaching” status, retains a Purnia detail card under the Gaya/Nalanda filter, and its CSV export contains all three blocks. It depends on external Tailwind, Chart.js, fonts and icons; with those blocked, the page raises `tailwind is not defined` and `Chart is not defined`. The separately generated two-block Excel file is correct and receives credit.

Under the same diagnostic rubric, the generic split path scores 98.8 and Antigravity 81.5. Antigravity remains the stronger visual designer by 0.7 points; the split path wins correctness of the requested webpage state, safety, offline operation, download consistency, time and clean handoff.

This is still development evidence. Because the new layout was visible while the generic extractor was built, it cannot be a generalization claim. The next meaningful gate is frozen code against untouched, cross-sector holdouts and layout perturbations.

Evidence: [paired result](../benchmarks/results/generic-layout-critic-versus-antigravity-v1-development.json), [split screenshot](../benchmarks/runs/2026-08-20-generic-critic-layouts/dev-xlsx-regions-002/split/gpt-oss-20b-low-gemini37-flash-low-critic/rep-04/turn-3/browser/desktop-initial.png), [selected count screenshot](../benchmarks/runs/2026-08-20-generic-critic-layouts/dev-xlsx-regions-002/split/gpt-oss-20b-low-gemini37-flash-low-critic/rep-04/turn-3/browser/desktop-metric-selected.png), [Antigravity screenshot](../benchmarks/runs/2026-08-20-generic-critic-layouts/dev-xlsx-regions-002/antigravity/default/rep-01/browser/desktop-final-online.png), and [Antigravity inspection](../benchmarks/runs/2026-08-20-generic-critic-layouts/dev-xlsx-regions-002/antigravity/default/rep-01/browser/inspection.json).
