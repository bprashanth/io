# Digital PDF split journey versus Antigravity

A narrow PDF adapter was added for digital, text-bearing reports with one
district-by-year percentage table. It preserves document page, table label and
source label on every extracted observation and explicitly labels its limited
scope. It does not attempt OCR or silently claim multiple-region support.

Four development replays were needed. `rep-01` produced correct extracted data
but interpreted “compare Purnia and Kishanganj in 2023” as permission to discard
2022, so its final export had two rows rather than the frozen four-row oracle.
A generic durable-state rule was added: a comparison at one time sets the
insight time but does not narrow an earlier explicit time selection unless the
participant says show, filter or only that time.

`rep-02` then revealed a more serious arithmetic failure. The plan divided the
already-percent coverage column by itself and rendered 100% for every district,
with a zero gap. The plan prompt and binder were changed so percentage
derivation requires distinct count columns and an existing percentage field is
used directly. `rep-03` calculated the correct values and six-point gap but its
comparison page initially showed all four districts. A generic validator now
requires a two-entity difference result to focus on exactly those two entities.

`rep-04` passed after one automatic repair on that scope check. It used five
Qwen 3.8 27B Low calls, 109.007 model seconds, USD 0.01657679, 7,994 prompt,
4,001 completion and 2,503 reasoning tokens. The page retained Purnia 61/66%
and Kishanganj 56/60% for 2022/2023, showed the six-percentage-point 2023 gap,
and exported all four rows with page 2, Table 1 and the exact source label.
Chromium checks found no page/console errors, external requests or desktop
overflow. Human visual review found the result clear and finished.

The Antigravity reference remains the counted CLI product failure: it found the
PDF, then received a Google `PERMISSION_DENIED` response before producing any
answer or page, for a score of 0. This is recorded as product-path reliability,
not a Gemini capability conclusion, because no paired GUI PDF replay is
available. The stronger context is the earlier Cline/Qwen XHigh run, which
scored 95 but needed 50 calls, 826.295 model seconds and USD 1.1053471. The
split diagnostic score is 98.5.

This result is restricted to one simple digital table. The case bank was
updated so scanned and holdout PDFs include multiple candidate tables and a
plain-language region-correction turn. No broad PDF equivalence claim is made.
