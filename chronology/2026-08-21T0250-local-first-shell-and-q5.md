# Local-first event shell, Q5 rejection, Excel and PDF checks

`benchmarks/scripts/run_local_first_insight.py` is the first executable event
shell assembled from the measured components. It accepts one or more local
CSV/XLSX/PDF files and a plain-language question, keeps prior questions and SQL
in a session, and uses the small model only to propose one read-only DuckDB
query. Local code validates and executes the query, builds the result bundle,
renders a self-contained dashboard, and writes the filtered download. A
rejected result is hidden and may be sent to the declared Qwen 3.8 27B tier.

The shell always writes an optional frontier-layout envelope for audit but does
not send it when deterministic rendering succeeds. The envelope constructor
accepts only the user question and result column name/type/role plus the fixed
layout contract; it has no parameter for rows or statistics.

The first three-turn agriculture run with Q4 demonstrated routing behavior:
turns 1 and 3 stayed local, while a wide turn-2 representation was initially
escalated. Browser inspection then found a silent unit problem in another run:
Q4 used a `percentage_point_change` alias for a tonnes-per-hectare difference,
causing a polished but wrong percent display. The product guard now rejects a
computed percentage alias when the user did not request a percentage and the
expression has no percent-typed input. Existing percent columns remain valid.

Several evaluator proxies were corrected while exercising the shell:

- multiple years may be represented by a long `year` column or by separate
  year-suffixed metric columns;
- selecting an existing numeric metric is valid and no longer requires a
  computed expression;
- structured provenance may use `source_sheet`, `source_table` or
  `source_page`, not only a literal `source` column;
- a saved non-executable SQL query is routed upward rather than crashing the
  offline router;
- dense line charts no longer label every point, which had caused visible text
  collisions for three or four close series.

Arctic Q5_K_M was downloaded and replayed locally. The file is 5,444,831,840
bytes with SHA-256
`157cc3e1caafb02a7e4c7abc6e23fbe1bb1b75ef1623fc54885bd17b1a8c0c5d`.
It scored **24/30 (80.0%)** in 484.796 seconds and is rejected. Its six counted
failures included two final execution failures and four semantic mismatches;
the old frozen router silently accepted three of the semantic misses. One join
question is itself ambiguous about the employment-rate denominator, but even
removing that item cannot make Q5 reach 85%.

The structure-preserving local adapters were then exercised independently of
Q5's model qualification:

- A merged-heading, vertically stacked Excel workbook was converted to six
  correct primary-school district-year rows with percent metrics and
  sheet/table provenance. The final self-contained page passed Chromium checks
  with a line chart, indicator/block/year controls and a working six-row
  download.
- A two-page digital PDF was converted to twelve correct district-year
  facility-delivery percentages with page 2/Table 1 provenance. Its final page
  passed the same checks with year/district controls and a twelve-row download.

Both pages were opened and inspected as images. Their initial dense point
labels were visibly cluttered, so the generic renderer was changed to omit
point values when more than two series are present. Exact values remain in the
table and insight cards.

Q8_0 is the final bounded quantization experiment. No smaller or additional
quant will be promoted if Q8 does not preserve the BF16 gate.
