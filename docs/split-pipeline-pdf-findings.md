# Digital PDF finding: split pipeline versus Antigravity

The validated split path completed the four-turn facility-delivery PDF journey
with a diagnostic score of 98.5. It extracted the correct table from page 2,
retained Table 1 and the exact source label on every row, showed the correct
2022–2023 values for Purnia and Kishanganj, stated the six-percentage-point 2023
gap, and downloaded the matching four rows. Five Qwen 3.8 27B Low requests took
109.007 model seconds and cost USD 0.01657679. Every page and download was
exercised in Chromium with no browser errors, external requests or desktop
overflow.

The counted Antigravity CLI result is 0 because its Google model call returned
`PERMISSION_DENIED` before it produced an answer or page. That is a real
failure of the product path available on this server, but it is not evidence
that Gemini lacks the task capability. There is no paired GUI PDF replay from
the laptop. To avoid an artificially easy conclusion, the result also compares
the prior Cline/Qwen XHigh run: that system scored 95 and produced a strong
page, but used 50 model calls, 826.295 model seconds and USD 1.1053471.

The passing replay was the fourth development attempt. The first lost the
previously selected 2022 rows after a 2023 comparison. The second kept the
scope but divided a percentage column by itself, displaying 100% and a zero
gap. The third fixed the arithmetic but initially left all four districts in a
two-district comparison. Those failures produced generic durable-year,
already-percent and two-entity-scope guards. The fourth run needed one bounded
repair and then passed the independent oracle.

The scope remains narrow. `pdftotext -layout` found one clean digital table with
simple year columns. This does not establish scanned-PDF, nested-table,
spanning-header or multiple-region extraction. Planned development and holdout
PDFs now contain multiple candidate tables and ordinary recovery turns such as
“use the second table,” and must be compared with Antigravity on the same files.

Evidence: [machine-readable comparison](../benchmarks/results/split-qwen38-27b-low-dev-pdf-health-v1-development.json)
and [passing candidate run](../benchmarks/runs/2026-08-20-split-pipeline-development/dev-pdf-health-001/split/qwen3.8-27b-low/rep-04).
