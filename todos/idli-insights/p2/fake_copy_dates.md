# Fake copy: keep date order, and read "12-Mar-22" dates

From E1 (2026-11-11, `benchmarks/runs/2026-11-10-idli-pipeline-eval/results/e1/tax_end_before_start.md`).

## The two gaps
1. **"12-Mar-22" (dd-mmm-yy) isn't recognised as a date.** `filekit.classify` calls the column a category, so its
   fake values are random strings from the column, and date checks can't be written from the fake copy.
2. **Order between two date columns isn't kept.** A start and an end date (purchase/sale, sown/germinated) are
   faked independently, so in the fake copy "end before start" appears at random: the tax file's planted
   mistake survived in one version and not the other, by luck.

## What to build (in `lib/filekit.py`, behind `IDLI_MOCK_V2=1` until it is tested)
- Parse dd-mmm-yy and dd-mmm-yyyy as dates in `classify` and the reader.
- When two date columns in a table are in order in most real rows (say 95%+), fake them as a start plus a gap
  drawn from the real gaps, and keep the real share of rows that break the order (so the mistake still shows).

## How to test
Rerun E1 (`harness/e1_fidelity.py`) on the tax file across seeds 1-5: `end_before_start` must survive every time.
Then rerun E2 on the tax file and check false alarms don't rise.
