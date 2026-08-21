# GPT-OSS 20B passes clean XLSX and narrow digital PDF gates

The clean two-sheet rectangular XLSX journey passed every critical check with four first-pass model calls: 31.870 seconds and $0.00039448. The page preserved both workbook sheets, formulas, exact values, durable 2022–2023 and Gaya/Nalanda scope, +5/+3 percentage-point changes and a traceable download. It retained the same noncritical miss as the Qwen 27B run: the visible 2023 values imply a 7 pp district gap but the page does not state it separately. Human inspection led us to move the active chart metric beside district/year in the visible table so a wide source field cannot hide the key value.

The first two PDF repetitions failed on the third turn even though extraction was correct. GPT-OSS repaired one fault at a time—x/series duplication, unit, entity scope, durable year scope—and exhausted the three-attempt bound. This led to a general architecture change: literal user constraints such as “only 2022 and 2023” and “compare Purnia and Kishanganj” are now compiled into filters deterministically before semantic validation. Both the raw model plan and normalized plan are retained.

With that constraint compiler, the counted digital-PDF run passed its full oracle with five calls and one repair: 22.670 seconds and $0.00037850. Browser and human checks confirmed an unclipped offline page, correct 61/66 versus 56/60 values, the 6 pp 2023 gap, page 2/Table 1 provenance and a four-row download.

The preserved Antigravity comparisons are 89/100 for clean XLSX and 0/100 for the counted PDF run, where Antigravity stopped at a Google permission error. The latter is an operational comparison, not evidence that Gemini cannot read PDFs. These are still narrow adapters: merged headers, stacked subtables, multiple candidate regions and scanned PDFs remain untested.

