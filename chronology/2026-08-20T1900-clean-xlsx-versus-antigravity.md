# Clean XLSX journey versus Antigravity, with scope correction

The split pipeline was extended from CSV to XLSX for the four-turn synthetic
maternal-health case. It enumerated both workbook tabs, selected `District Data`
as the rectangular observation table, retained `Indicator Notes`, and exposed
the definitions, formulas and source-sheet fields to the report layer.

The first run exposed an evaluator error: the durable-filter check interpreted
“only 2022 and 2023” as “only 2022.” The run was stopped after its allowed
repairs failed for that incorrect reason. The validator was corrected to
distinguish a year set from a single year. This was benchmark plumbing, not
scored as a model failure, and the failed run remains under `rep-01`.

The counted `rep-02` completed all four plans on their first attempt: 9 rows,
then 6 for 2022–2023, then 4 for Gaya/Nalanda postnatal coverage, retained in
the download turn. Four Qwen 3.8 27B Low calls took 114.527 model seconds, cost
USD 0.01289775, and used 5,894 prompt, 3,300 completion and 1,739 reasoning
tokens. Exact values, +5 pp/+3 pp changes, formula definitions, sheet names,
the four-row source-bearing download and the non-official caveat passed the
deterministic oracle. The seven-point 2023 district gap is visually available
but not separately stated, so it remains a noncritical deduction.

Every page was served and opened in Chromium at 1440 by 1000. Downloads and row
counts were exercised. There were no console/page errors, external requests or
desktop document overflow. Human review found a finished, clear page, though
Antigravity's visual treatment is richer. The scored development comparison is
95.5 for the split candidate versus the preserved Antigravity CLI score of 89.
The candidate advantage comes mainly from durable state, offline reliability
and speed; Antigravity gets credit for the explicit gap and richer treatment.

The user then identified a major scope hazard: real NGO workbooks often encode
structure visually through merged headings, repeated headers, blank separators,
stacked subtables and multiple relevant tabs. The present adapter does not solve
that problem. Documentation and the case bank were corrected so this result is
reported only as a clean two-sheet check. The next workbook evidence must retain
cell coordinates and visual structure, and test plain-language recovery such as
“there is another table below” against Antigravity on the same workbook.
