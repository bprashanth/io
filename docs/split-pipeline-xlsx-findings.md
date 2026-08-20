# Clean workbook finding: split pipeline versus Antigravity

On the same four-turn maternal-health workbook journey, Qwen 3.8 27B Low as a
constrained planner plus local calculation and rendering scored 95.5 versus the
preserved Antigravity score of 89. The candidate used four first-pass model
requests totalling 114.527 seconds and USD 0.01289775. This is a development
comparison, not a general Excel or editor-product equivalence claim.

Both systems calculated the requested coverage rates correctly. Antigravity
also explicitly stated the seven-point 2023 Nalanda–Gaya gap and produced a
more visually varied dashboard. Its final durable page, however, remained on
institutional delivery rather than the requested postnatal comparison, retained
a confusing 2021 control, invented performance labels, required external web
assets, and took 428.938 seconds including a recorded preview intervention.

The split path retained only 2022 and 2023, then retained postnatal coverage and
the Gaya/Nalanda comparison through the download turn. It visibly showed the
correct +5 pp and +3 pp changes, source workbook, both sheet names, formulas and
the not-official caveat. All four pages were opened in Chromium. Their exports
matched the visible rows; there were no browser errors, external requests, or
desktop overflow. The page showed the two 2023 values but did not separately
state their seven-point gap, which remains a scored noncritical shortfall.

This fixture is deliberately narrow: it has one clean rectangular data sheet
and one notes sheet. The current adapter chooses an apparent observation sheet
and would not reliably handle merged headings, vertically stacked subtables, or
measures split across tabs. Those shapes now have explicit development and
holdout cases, including ordinary recovery prompts such as “there is another
table below.” Both systems must be tested on the same files and correction
turns before any wider Excel claim.

Evidence: [machine-readable comparison](../benchmarks/results/split-qwen38-27b-low-dev-xlsx-health-v1-development.json)
and [candidate run](../benchmarks/runs/2026-08-20-split-pipeline-development/dev-xlsx-health-001/split/qwen3.8-27b-low/rep-02).
