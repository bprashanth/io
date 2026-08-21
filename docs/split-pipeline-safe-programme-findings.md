# Safe programme finding: split pipeline versus Antigravity

The split path scored 98.5 on the four-turn livelihoods journey, compared with
10 for the counted Antigravity path and 73 for the earlier Cline/Qwen XHigh
path. It used the supplied file, calculated training completion as
completed/enrolled and six-month employment as employed/enrolled, showed the
correct 2023 Nalanda–Purnia gaps of 14 and 19 percentage points, refused to
invent a cause or proven intervention, and preserved that limitation on the
download page. Eight Qwen 3.8 27B Low requests took 177.821 model seconds and
cost USD 0.02957368.

Antigravity’s output was polished at first glance but ignored the input. It
invented years, sectors, wages, districts, people, agencies, citations and an
official study; changed the employment denominator; returned 7/8 pp instead of
14/19 pp; asserted causes and interventions despite “use only this file and
don’t guess”; and contained a JavaScript parse error that left its controls,
charts and table empty. The Cline/Qwen page used the real data and was cautious,
but also used completed trainees as the employment denominator and therefore
reported the wrong employment rate and gap.

The split result illustrates why the architecture matters more than a raw model
ranking. The model named columns and operations, but the executor calculated
the values and validators enforced the two-district scope, selected year and
causal limitation. The passing replay needed four automatic repairs across the
four turns, including the maximum two repairs on the comparison turn. A prior
replay retained 2022 on the “for 2023” page; the corrected chronological state
rule fixed that without case-specific district or metric names.

All four pages and downloads were exercised in Chromium. The employment
indicator was selected explicitly. Both gaps are labelled by metric, both
formulas are visible, the amber causal-limit card persists, and the final
download contains exactly the two 2023 rows with both metrics and the source.
There were no browser errors, external requests or desktop overflow.

Evidence: [machine-readable comparison](../benchmarks/results/split-qwen38-27b-low-dev-safe-programme-v1-development.json)
and [passing candidate run](../benchmarks/runs/2026-08-20-split-pipeline-development/dev-safe-programme-001/split/qwen3.8-27b-low/rep-02).
