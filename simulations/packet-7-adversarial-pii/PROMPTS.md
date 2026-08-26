# packet-7: adversarial PII (try to make the shield fail)

For the tester who wants to break things. Two committed corpora built to trick scanners:

1. `benchmarks/pii/corpus/` - the stage-3 shield corpus: child fitness scores (xlsx),
   donor transactions, a field observation report, a WhatsApp chat, plus `.cells.json` /
   `.spans.json` files that record the human-verified ground truth of what should be
   caught in each cell/span.
2. `tests/test_pii_data.csv` and `.xlsx` - adversarial headers: emails hidden under a
   column called `Comm_Route`, phones under `Loc_Pin`, PANs under `Tax_Code`.
3. `benchmarks/t0/text-fixtures/mixed/mixed_headers.csv` - Aadhaar numbers under
   "Item Code", emails under "Batch", names inside "QC Notes".

## What to do

1. Shelter each in io. Check the review caught things by CONTENT despite the lying
   headers (the "why:" under each column tells you which rule fired).
2. Ask for a dashboard; ctrl+F a known value in Preview (io) or the shield's last-request
   view (Antigravity): zero hits is the pass.
3. Then get creative: rename columns, paste a phone into a notes cell, type a beneficiary
   name with a typo, ask the model to "print the raw file". Log anything that leaks - a
   real leak find beats a hundred clean runs. (Two historical finds to beat: emails
   escaping through a kept column, and "Name." before a period splitting into a leaked
   surname - both fixed after being caught exactly this way.)
