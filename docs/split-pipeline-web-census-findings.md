# Official Census finding: connector and split pipeline

After an official source URL is known, the split path is fast, correct and much
safer than free-form citation generation. A bounded Census A‑01 connector
re-downloaded the official workbook, retained its bytes and SHA‑256, selected
district-total rows, and passed a traceable three-row table to Qwen 3.8 27B Low.
Four first-pass plans took 95.797 model seconds and USD 0.01495195. The resulting
page and download have the exact Patna, Gaya and Nalanda populations, Patna as
largest, the exact 1,447,047-person gap, two-decimal lakh values, 2011 vintage,
publisher, table, catalog URL and direct workbook URL.

This is not a general web-search win. The connector was given catalog 42526 and
its direct download URL, originally found by the earlier measured DeepSeek Web
run and revalidated live in this experiment. The candidate’s 98.5 score applies
after discovery. It must not be compared as though it independently performed
the same open search as Antigravity.

The complete references show the useful routing decision. Antigravity took
214.448 seconds and scored 78: its numbers and visuals were good, but its three
exported “official” district record URLs led to unrelated 1961 monographs. The
DeepSeek Web plus Qwen guardrail run genuinely discovered and cross-checked the
official workbooks and scored 91 with no critical failure, but used 830.346
model seconds plus 101.464 tool seconds. The practical architecture is therefore
an allowlisted connector for common official sources, the split planner for
analysis and rendering, and a bounded web-capable fallback for unknown sources.

The first split replay also taught two generic lessons: a population difference
is a count, not a percent, and a turn asking both “which is largest?” and an A/B
gap must retain the full ranking set. Human page inspection then caught clipped
lakh-axis labels that browser error checks missed. The chart gutter was widened,
all pages were recaptured, and the final page displays 58.38, 43.91 and 28.78
lakh while retaining exact counts in the table.

Evidence: [machine-readable ablation](../benchmarks/results/split-qwen38-27b-low-dev-web-census-v1-development.json),
[passing split run](../benchmarks/runs/2026-08-20-split-pipeline-development/dev-web-census-001/split/qwen3.8-27b-low/rep-02),
and [connector handoff](../benchmarks/runs/2026-08-20-split-pipeline-development/dev-web-census-001/prepared-case/discovery-manifest.json).
