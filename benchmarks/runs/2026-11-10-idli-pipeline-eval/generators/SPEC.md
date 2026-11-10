# Task: messy spreadsheet generators with a manifest

Write `make_messy.py` in this folder (Python 3, only pandas, numpy, openpyxl; deterministic: fixed seeds).
`python make_messy.py --out ../fixtures --manifests ../manifests` writes one .xlsx per file below into
`../fixtures/`, plus `../manifests/<stem>.json` and `../fixtures/<stem>.doc.md`.

Every file starts clean (a clean table you generate) and then gets **known mess injected**. Every injected
change is recorded in the manifest. Values are entirely invented (no real people, places from a small invented
list are fine: e.g. villages "Kallar", "Pudur", "Mettu", "Anaikatti"; species with Latin names are fine).

## Manifest format (`<stem>.json`)
```json
{"file": "<stem>.xlsx", "data_rows": {"<tab>": <number of real data rows>},
 "items": [
  {"id": "m001", "tab": "Trees", "row": 57, "column": "DBH 2 (cm)", "columns": ["DBH 1 (cm)", "DBH 2 (cm)"],
   "category": "value|layout|cross", "kind": "<kind below>", "expect": "flag|skip",
   "in_doc": true, "original": "<clean value>", "injected": "<messy value>", "fix": "<value a person would type to fix it>"}
 ]}
```
- `row` is the 1-based Excel row number in the written file (after all layout rows are inserted). `column` is the
  header text exactly as written. For a whole-row layout item, `column` is "(whole row)". `columns` (optional)
  lists every column a check could reasonably point at (cross-column items).
- `expect`: "flag" = a person would want it marked as a problem; "skip" = a layout row that must not be counted
  as a record (repeated header, sub-heading, totals, notes row, spacer).
- `in_doc`: true if the file's documentation (below) states the rule this item breaks; false for things a careful
  reader should spot on their own (units in cells, typos, mixed date formats, junk like "n/a").
- `fix`: for value/cross items, the corrected cell value; for layout items, null.

## Documentation (`<stem>.doc.md`)
Half a page, written as the team lead who owns the sheet would explain it to a new analyst: what the file is,
what one row is per tab, what each column means and its unit, and the team's rules ("germination % is 0-100",
"every species code must be in the Species key tab", "DBH 2 is only filled when the tree has a second stem,
so DBH 1 must be filled too", "UKS1 means unidentified species, it's fine"). It must NOT list which cells are
wrong or how many problems there are. It's what a person answering questions about the file knows.

## Mess kinds (use each at least once across the files; 3-10 instances per kind per file where it fits)
- layout: `repeated_header` (sections pasted under each other, each with its own header row),
  `subheading` (a row with only "Transect 3" or "Block B"), `total` (a "Total" row with sums), `notes_row`
  (a row with a sentence in the first cell), `spacer` (fully empty row inside the table), `merged_header`
  (2-3 header rows with merged group cells above the real header), `info_block` (a key/value block above the table:
  "Nursery name: ...").
- value: `unit_in_cell` ("12 cm", "approx 12", "Rs. 1,200"), `na_text` ("n/a", "pending", "-", "NA"),
  `mixed_date_format` (most dd/mm/yyyy, some yyyy-mm-dd or "12 Mar 2024"), `bad_date` ("31/02/2024", "TBD"),
  `future_date`, `code_typo` (a species/village code one letter off: "Cestrm"), `code_not_in_key`
  (a code the key tab doesn't have, NOT a typo), `team_code` (an accepted convention like "UKS1"/"Fern" which the
  doc says is fine: expect "skip"? NO: mark these `expect: "ok"`, they must NOT be flagged), `casing`
  ("CESAUR", "cesaur " with trailing space; expect "flag" only if the doc says codes are lower-case, else "ok"),
  `out_of_range` (germination 140%, DBH 900 cm, negative counts), `duplicate_id` (a tree/household id repeated),
  `required_missing` (a mandatory field blank), `not_a_number` (text in a number column), `bad_phone`, `bad_email`.
- cross: `dbh2_without_dbh1`, `count_mismatch` (a density/summary tab whose count doesn't match the rows in the
  tree tab for that plot), `key_missing_species` (a species used many times, missing from the key tab),
  `total_mismatch` (a totals row or a summary cell that doesn't add up), `end_before_start` (a date pair in the
  wrong order).
`expect` values: "flag", "skip" or "ok" (must not be flagged). Use "ok" for team codes and anything the doc
explicitly accepts.

## Files
1. `tree_plots_transects` (shape of a real field workbook; invent all values). Tabs:
   - `Raw 10x10m Data`: ~900 rows of trees made of sections pasted under each other, one section per transect
     (T1..T8), each section starting with a repeated header row, sometimes a sub-heading "Transect 3". Columns:
     Transect, Plot, Tree No, Species code, DBH 1 (cm), DBH 2 (cm), DBH 3 (cm), Height (m), Canopy (Y/N), Notes,
     Date (dd/mm/yyyy), Recorder.
   - `Density`: one row per transect x plot: Transect, Plot, No. of trees, No. of Cestrum.
   - `Seedlings`: Transect, Plot, Species code, Count, Height class (<10cm / 10-50cm / >50cm).
   - `Species key`: Code, Scientific name, Common name, Native/Alien.
   Mess: repeated_header, subheading, spacer, notes_row, unit_in_cell, na_text, code_typo, code_not_in_key,
   team_code (UKS1, Fern), casing, out_of_range, dbh2_without_dbh1, count_mismatch, key_missing_species,
   mixed_date_format, duplicate_id (Transect+Plot+Tree No).
2. `germination_protocol_filled`: fill this template (layout must match): an `info_block` at the top
   (rows 1-5: "GENERAL INFORMATION", "Nursery Name", "About your nursery, project, organisation",
   "Ecoregion(s) you serve", "Contact Person(s) of nursery, propagation experts (email / phone number)" in column
   B with the answer in column D), then row 6 group headers merged across columns: "SPECIES" (B:C),
   "SEED PROCESSING" (D:F), "GERMINATION" (G:M), "FIRST TRANSPLANT" (N:P); row 7 sub-groups "Procedures" (G:K),
   "Success" (L:M), "Procedures" (N:P); row 8 the real header: No., Scientific Name (Botanical),
   Local / Common name(s), Time of year for seed collection, Processing of fruits/seeds, Seed storage,
   Seed treatment, Seed sowing media, Container (germination), Seed depth, Germination facilities / Nursery Care,
   Duration until germination, % Germination success, Growing media, Container, Watering technique;
   row 9 a long description per column; row 10 MANDATORY/OPTIONAL per column
   (B MANDATORY, C OPTIONAL, D OPTIONAL, E MANDATORY, F OPTIONAL, G-I MANDATORY, J-K OPTIONAL, L-M MANDATORY,
   N-P OPTIONAL). Then ~60 numbered species rows. Mess: required_missing (blank MANDATORY cells),
   unit_in_cell (seed depth "2cm", "approx 1 cm"; duration "3 weeks", "21 days", "2-3 wk"),
   out_of_range (germination 120%, -5), na_text, casing in scientific names, duplicate scientific names,
   bad_email/bad_phone in the contact cell, free text in % column ("good", "70-80%").
3. `tax_missing_info_fake`: a fake of a tax questionnaire workbook (no real person). Tabs and layout:
   - `Missing Information`: rows 3-5 an info block ("Name" "Person A"; "PAN" a fake PAN shaped AAAAA9999A;
     "Period" "01 April 2023 to 31 March 2024"; "Financial Year (FY)" "2023-24"; "Assessment Year (AY)" "2024-25"),
     then a numbered list of questions: columns Sl No, Topic, Our understanding, Your response, Amount (INR).
   - `India Bank Account`: same info block at the top (rows 2-4), title row 6 "Details of all Bank Accounts held in
     India at any time during the FY", header row 7: IFS Code, Name of the Bank, Type of account, Account Number
     (9 digits or more), Savings account interest earned, Closing balance as on 31 March 2024, Refund account (Y/N);
     ~8 rows. Mess: account number shorter than 9 digits, IFSC wrong shape (must be 4 letters, 0, 6 alnum),
     interest with "Rs." and commas, two accounts marked Y for refund (rule: exactly one), na_text.
   - `Capital Gain`: two header rows (row 7 groups "Sale details" over F:L, "Purchase details" over M:Q merged;
     row 8 the real header: Sl No, Particulars, Type of Asset, Date of sale (dd-mmm-yy), Price per unit, Currency,
     No of units, Sale consideration, Expenses on Transfer, Net Sale Consideration (INR), Date of purchase
     (dd-mmm-yy), Purchase price per unit, Cost of acquisition); ~15 rows. Mess: end_before_start (sale before
     purchase), total_mismatch (Net != Sale - Expenses; Sale consideration != price x units), mixed_date_format,
     not_a_number, a `total` row at the bottom.
   - `Travel Calendar`: Month (Apr 2023 .. Mar 2024), Non-work/vacation days in India, Work days in India; mess:
     days > days in month, na_text, a total row that doesn't add up.
4. `household_survey_messy` (village livelihoods; like a totalrecall synthetic table): tabs `Households`
   (~400 rows: Household ID, Village, Ward, Head of household, Phone, Members, Monthly income (INR), Debts (INR),
   Savings (INR), Land (acres), Survey date) and `Members` (Household ID, Name, Age, Sex, Works (Y/N)).
   Mess: duplicate_id, bad_phone, unit_in_cell (income "Rs 8,000", "8k"), na_text, out_of_range (age 140,
   members 0), mixed_date_format, future_date, cross: Members count in Households != rows in Members for that ID,
   a Members row whose Household ID isn't in Households (code_not_in_key), casing in Village, code_typo in Village.
5. `field_visits_messy`: tabs `Visits` (~250 rows: Visit date, Village, Field officer, Households visited,
   Amount disbursed (Rs), Status (Done / Follow-up / Cancelled), Notes) and `Officers` (Name, District, Phone,
   Email). Mess: officer names misspelt vs Officers tab, status variants ("done", "Completed", "cancel"),
   amount with "Rs." and commas, a total row, spacer rows, bad_email, bad_phone, future_date, Cancelled visits
   with an amount > 0 (cross, doc says cancelled visits disburse nothing).

## Also
- `python make_messy.py --check` re-opens every file with openpyxl and verifies every manifest item's cell
  holds the `injected` value (and layout rows are where the manifest says). Print a summary per file:
  data rows, items per category and kind.
- Keep it one file, plain code, ~400-700 lines. No network.
