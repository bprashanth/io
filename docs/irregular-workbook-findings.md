# Irregular workbook: stacked tables and merged headings

## Result

The new `dev-xlsx-headers-001` case directly tests the overfitting risk that a clean rectangular spreadsheet hides. It contains:

- three tabs;
- a larger irrelevant rectangular enrolment tab that would win a naïve “largest table” heuristic;
- an attendance report with merged table titles and two-row grouped headings;
- a primary table at `Attendance Report!A1:E7`;
- a secondary table below blank separator rows at `Attendance Report!A11:E17`;
- a plain correction turn: “there is another attendance table below for secondary school.”

The values are synthetic aggregate percentages, not official statistics or person-level records.

The GPT-OSS 20B split path passed the full four-turn oracle. Turn 1 showed only primary boys/girls. Turn 2 added both secondary measures without losing primary. Turn 3 selected 2023 secondary girls for Tekari and Wazirganj, showed 73% versus 66% and stated the exact 7 pp gap. Turn 4 preserved that state and downloaded two traceable rows. The footer and table retained workbook, sheet, both table labels and both exact cell ranges.

The counted run used five GPT-OSS 20B Low requests, one automatic repair, 26.872 model seconds and $0.00047230. It used 10,429 prompt, 1,673 completion and 320 reasoning tokens. Browser checks found no page errors, external requests or desktop overflow. Human visual review scored the page 8.7/10: simpler than Antigravity, but complete and readable.

## Why the harness mattered

Five earlier repetitions are retained because they exposed general failure modes:

1. `ne null` produced no SQL rows until the executor mapped it to `IS NOT NULL`.
2. UI placeholders such as `user_selected_year` were treated as data until the constraint compiler removed placeholder filters.
3. A visually passing page contained unfinished “X percentage points” prose until participant text validation rejected placeholders.
4. A later plan averaged already-unique observations, divided one reported percentage by another, invented a ~103% indicator and dropped provenance. The binder now rejects grouping unique keys and percentage derivation from percentage inputs.
5. GPT-OSS repeatedly labelled a subtraction of percentages as `percent`. The trusted binder now assigns change/difference units from the metric type and records the normalization.

These are deliberately deterministic responsibilities. The model chooses the requested measures and view; it does not control literal scope, null semantics, arithmetic units or whether already-reported rates should be recomputed.

## Antigravity comparison

Antigravity CLI 1.1.15 with untouched default `Gemini 3.7 Flash (High)` did understand the workbook. Its generated turn-1 artifact parsed both stacked tables correctly, ignored the decoy as an attendance source, exposed a secondary-school selector and produced a visually excellent page (9.3/10 artifact visual score). Offline Chromium fell back from Chart.js to a working built-in chart.

The product journey nevertheless failed on turn 1. Antigravity recorded an invalid artifact-path permission error, launched its Python server as a blocking foreground tool, and timed out after 613.597 seconds. It consumed 239,543 tokens and never accepted turns 2–4. A manually rescued artifact showed the correct secondary girls values 73/66/63, but it could not select exactly two blocks, invented unsupported Good/Fair performance tiers, and exported all three blocks without sheet/table/range provenance under the wrong filename `primary_attendance_girls_2023.csv`.

Under the same diagnostic rubric, the split path scores 98.7 and the failed Antigravity product journey scores 57.3. The latter gives substantial credit for exact parsing and excellent rescued visuals while heavily penalising the missing handoff and multi-turn journey. This is a CLI/container result, not proof that the Antigravity IDE GUI would fail the same way; a GUI replay remains desirable.

## Scope boundary

This does not prove arbitrary Excel understanding. The adapter handles a bounded but useful pattern: compatible vertically stacked attendance tables with merged two-row headings and year leaves. Future tests must vary heading depth, horizontal subtables, formulas, inconsistent schemas, cross-tab joins, hidden rows, footnotes and corrupted cells. The important architecture rule is preserved: keep cells, merged ranges and candidate regions before choosing a table, and let a plain-language correction select or add a region without requiring cell coordinates from the participant.

