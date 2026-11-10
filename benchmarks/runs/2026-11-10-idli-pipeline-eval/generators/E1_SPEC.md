# E1 task for Codex: fake-copy fidelity, plus cheap fixes behind a flag

Context: Idli makes a "fake copy" of a spreadsheet (`../2026-11-06-oss-desktop-independent/cowork/lib/filekit.py`,
`make_mock(path, question)` -> (request, mock_path, _); per-column faking in `mock_column`). Claude learns the file
(writes checks) from the fake copy only. Files with planted mistakes: `fixtures/<stem>.xlsx`; each planted mistake
is listed in `manifests/<stem>.json` (`items`: id, tab, row, column, category, kind, expect, injected, original...).
Stems: tree_plots_transects, germination_protocol_filled, household_survey_messy, field_visits_messy,
tax_missing_info_fake. Python with pandas/openpyxl: `../2026-11-06-oss-desktop-independent/cowork/.venv/bin/python`.
Run make_mock with cwd = the cowork dir (it imports `lib`). Do not edit fixtures or manifests.

## Part 1: harness/e1_fidelity.py
`<venv python> harness/e1_fidelity.py [--out results/e1/<label>]` (default label "today"; the env var
IDLI_MOCK_V2=1 selects the fixed fake copy, label "fixed").
For each stem: build the fake copy with make_mock, then compare real vs fake:
1. **Per mistake kind** (from the manifest): does the same KIND of problem still exist somewhere in the same tab and
   column of the fake copy (not the same cell)? Write a detector per kind, applied to both the real file (sanity: it
   must fire on the real file; report kinds where it doesn't as "detector missed") and the fake copy. Kinds present:
   repeated_header, subheading, spacer, notes_row, unit_in_cell, na_text, code_typo, code_not_in_key, team_code,
   casing, out_of_range, mixed_date_format, bad_date, future_date, dbh2_without_dbh1, duplicate_id, count_mismatch,
   key_missing_species, required_missing, info_block, not_a_number, bad_email, bad_phone, merged_header,
   total_mismatch, total, end_before_start. Use the manifest's `injected`/`original`/`column` to define what to look
   for (e.g. out_of_range: the column's plausible range from the clean rows of the REAL file; count_mismatch:
   a count column in one tab vs number of rows per key in another tab — find the pair from the manifest item; for
   the fake copy the question is whether "mismatch rows" are still distinguishable from "matching rows", i.e. report
   the share of fake rows that match and the share that mismatch). Be honest: where detection is ambiguous, say so in
   a `note` field.
2. **Per column**: kind (filekit.classify), share blank, share junk (non-parseable in a number/date column), min/max,
   number of distinct categories — real vs fake.
3. **Per relationship**: blank-when-another-is-blank pairs (columns A,B where in the real file B is blank whenever A
   is blank, >95% of rows): does it hold in fake at the same rate? Count columns vs another tab's row counts; key
   coverage (values of a code column present in a key tab); ID uniqueness (duplicates count).
4. **Template rows**: rows directly under the header whose cells are instructions (long sentences such as "Enter the
   full scientific name") or tokens like MANDATORY/OPTIONAL/REQUIRED: are they kept verbatim in the fake copy?
Write `results/e1/<label>/<stem>.json` and one `results/e1/<label>/summary.md` with a per-file table
(kind -> real/fake survives) plus totals: kinds that survive / kinds present.

## Part 2: cheap fixes in filekit.py behind IDLI_MOCK_V2=1 (default behaviour unchanged)
Only when the env var is set:
a. **Instruction rows kept**: a row (anywhere in the first ~5 rows under the header, or a row repeating a pattern) whose
   non-empty cells are all instruction-like (sentences of >= 5 words starting with an imperative/"If"/"Describe"/
   "Enter"/"List"/"Mention"/"e.g.", or the tokens MANDATORY/OPTIONAL/REQUIRED/Mandatory/Optional) is copied as is.
   It holds no personal data (template text), so that is safe; never keep a row with an email, phone, digits-heavy
   or name-like content.
b. **Blank-when-blank**: already per cell? Verify; if the fake copy breaks the pattern, keep it.
c. **Count columns consistent across tabs**: if a numeric column in tab A equals, for >=80% of rows, the number of
   rows in tab B sharing A's key columns, then in the fake copy set it to the fake count for matching rows and keep the
   real difference (real value - real count) for mismatching rows.
d. **Totals consistent**: a "total" column equal to the sum of other numeric columns in the row (>=80% of rows), or a
   totals row equal to the column sum: recompute in the fake copy, keeping the real difference where it didn't match.
e. **Units/junk kept as quirks**: if a real number cell has a unit or "approx"/"n/a"-like text, the fake cell keeps
   the same kind of quirk (it mostly does already; verify).
Keep the change small and readable; add a short comment per fix. Add a unit test in
`../2026-11-06-oss-desktop-independent/cowork/lib/test_mock_v2.py` (plain asserts, runnable with
`PYTHONPATH=. .venv/bin/python lib/test_mock_v2.py` from the cowork dir) and make sure the existing
`lib/test_formkit.py` and `lib/test_fixkit.py` still pass.

## Then run
`harness/e1_fidelity.py` without and with IDLI_MOCK_V2=1 (labels today, fixed) and leave both summaries.
Finish by printing the two summary tables. Do not commit; do not touch anything outside this eval folder and
cowork/lib/filekit.py + the new test file.
