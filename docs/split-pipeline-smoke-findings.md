# Split insight pipeline versus Antigravity: first smoke finding

The corrected split pipeline is competitive with Antigravity on the same
three-turn synthetic CSV smoke. It is not yet a replacement claim.

| System | Diagnostic score | Visual /10 | Model time | Durable 2023 page | Traceable export | External assets |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| Antigravity IDE / Gemini 3.6 Flash High | 80.5 | 7.5 | 595 s total | No | Yes | 3 |
| Qwen 3.8 27B Low plan + DuckDB + fixed renderer | 95.3 | 8.8 | 124 s | Yes | Yes | 0 |

These numbers are diagnostic single repetitions. The candidate score applies
the existing weighted rubric to the completed insight journey; it is not an
official-product score. Its model only produced a constrained plan. Local code
profiled the CSV, validated column and user-intent constraints, calculated the
values, rendered the page and produced the export. Windows installation,
arbitrary-file ingest and IDE integration were not in this run.

## What the comparison actually says

Antigravity's page is more visually elaborate. It has KPI cards, two charts,
district cards and a dramatic dark theme. That is the useful visual target.
But its durable page ignored the request to show only 2023, kept 2022 rows,
did not surface Purnia as the requested lowest district, invented performance
bands and labelled percentage-point changes as percentages. It also depended
on three remote assets.

The split page is simpler: one suitable chart, one insight area, a table,
filters, download and source. It looks finished rather than experimental. The
2023 follow-up changed the durable page, named Purnia at 76%, removed 2022,
kept the non-causal caveat and downloaded exactly the three visible rows with
year and source. Every page was opened in Chromium. There were no console/page
errors, external requests or desktop overflow.

This is enough to advance the split architecture. It is not enough to say it
matches Antigravity for arbitrary NGO data. The next fair comparison must use
the routine CSV, Excel, PDF, official-web and safe-interpretation cases. The
renderer also needs several audited visual families so different datasets do
not all look like the same template. Visual variety should be judged against
Antigravity, not perfected in isolation.

## Why the development failures matter

The passing run was the fourth development replay, not a lucky first draft.
Earlier runs exposed and retained:

- a fake year-selector placeholder passed as a data value;
- a 9B plan that grouped away a column and two hosted 9B requests that did not
  finish inside their time budgets;
- a plan that ran but ignored “show only 2023”;
- insight cards that stayed stale after a client-side filter;
- a line chart connecting unordered districts;
- a page that made Purnia the shortest bar but failed to name it as lowest;
- schema chart modes the renderer did not implement; and
- spreadsheet-formula risk in exported text cells.

Each was turned into a validator, renderer or export guard before the final
replay. The result demonstrates the main architectural advantage: constrained
plans can fail closed and repair cheaply before a nontechnical participant sees
a broken or misleading page.

## Evidence

- [machine-readable comparison](../benchmarks/results/split-qwen38-27b-low-smoke-v1-development.json)
- [passing split run](../benchmarks/runs/2026-08-20-split-pipeline-development/smoke-001/split/qwen3.8-27b-low/rep-04)
- [Antigravity paired product smoke](../benchmarks/results/product-gui-smoke-v1-diagnostic.json)
