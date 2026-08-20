# Planned case bank

This is the pre-fixture case matrix, not a frozen benchmark. The six screening
cases are built and piloted first. Only after their inputs, hashes, prompts,
oracles and graders work do we build the rest and freeze the split.

The bank deliberately favours ordinary NGO work. Four cases are moderately
messy because real spreadsheets and PDFs are messy; none is intended as a
coding puzzle or adversarial trap.

## Development set (13)

| ID | Screen | Input | Routine request and follow-ups | Level |
| --- | :---: | --- | --- | --- |
| `dev-csv-health-001` | yes | clean CSV | immunisation dashboard; select year; compare districts; lowest district; download | routine |
| `dev-xlsx-health-001` | yes | two-sheet Excel | maternal-health dashboard; choose indicator/year; compare two districts; download | routine |
| `dev-pdf-health-001` | yes | digital PDF table | facility delivery dashboard; filter year; show source page/table; download | routine |
| `dev-web-census-001` | yes | official web discovery | find an official district population source; preserve source; dashboard; compare districts | routine |
| `dev-safe-programme-001` | yes | clean CSV | show programme outcomes; ask why one district is lower; do not invent a cause | routine |
| `dev-csv-missing-001` | no | CSV with blanks/`NA` | nutrition coverage dashboard; show missing data honestly; compare years | routine |
| `dev-xlsx-headers-001` | yes | three-tab Excel with merged headers, two vertically stacked subtables and a larger irrelevant rectangular tab | primary school-attendance dashboard; say “there is another table below” to add secondary; compare blocks; cite sheet/table/range; download | moderate |
| `dev-xlsx-regions-002` | yes | three-tab Excel with two horizontally adjacent mixed-unit tables and a larger irrelevant rectangular tab | screening dashboard; say “there is one more table on the right”; compare two measures using a paraphrased gap request; cite ranges; download | moderate |
| `dev-xlsx-formulas-001` | no | Excel with formulas | budget/spend dashboard; compare planned and spent; explain units | routine |
| `dev-pdf-scan-001` | no | scanned PDF with repeated headings and two candidate tables | extract the water-access table; after an incomplete result say “use the second table”; cite page/region; flag unreadable cells | moderate |
| `dev-join-health-pop-001` | no | two CSVs | join service counts with population; calculate per-1,000 rate; compare districts | moderate |
| `dev-names-001` | no | two small files | combine district names with harmless spelling variants; show unresolved matches | routine |
| `dev-dates-001` | no | monthly CSV | show financial-year trend; select date range; compare two blocks; download | routine |

## Holdout set (8)

| ID | Input | Routine request and follow-ups | Level |
| --- | --- | --- | --- |
| `hold-csv-livelihood-001` | clean CSV | livelihoods dashboard; year filter; district comparison; download | routine |
| `hold-xlsx-school-001` | multi-sheet Excel with the requested measures split across tabs and repeated headings | enrolment/attendance dashboard; sex and year filter; cite cells/sheets; redirect with “use the table on the attendance tab” if needed | moderate |
| `hold-pdf-water-001` | digital PDF with two relevant tables on different pages | water-point dashboard; compare blocks across the named table; cite page/table | moderate |
| `hold-web-official-001` | official web discovery | find official public health data; preserve source; simple dashboard | routine |
| `hold-join-budget-output-001` | two files | join spend and output; compare districts without causal claims | moderate |
| `hold-missing-suppressed-001` | CSV with suppressed values | show rates without treating suppression as zero; download | routine |
| `hold-pdf-scan-001` | short scanned PDF | extract a small table; flag uncertain OCR; cite page | routine |
| `hold-csv-boundary-001` | CSV with boundary note | compare only compatible years; explain why one series should not be joined | routine |

## Conversation shape

Most cases use four short messages:

1. make a simple webpage dashboard from the supplied file, or find the named
   kind of official data;
2. filter a year/range and compare districts or blocks;
3. ask one plain-language interpretation or source question;
4. download the currently filtered table.

Prompts should say what the user wants, not which library, framework, command or
chart implementation to use. Every turn is replayed in the same conversation.

Excel coverage must not silently assume that a workbook is one rectangular
table. At least one development and one holdout workbook retain cell positions,
merged ranges, blank separator rows, repeated headings, stacked subtables and
cross-sheet provenance. The recovery turn is part of the measured journey:
plain guidance such as “there is another table below” or “use the second tab”
must cause a new extraction and durable page, without asking the participant to
name cell ranges or debug parsing code. A clean two-sheet success is reported
only as that narrow case, never as general Excel support.
