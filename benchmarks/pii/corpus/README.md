# PII corpus ground truth

Synthetic NGO-style fixtures for benchmarking local PII redaction engines.
Everything in this directory is fabricated: names, phone numbers, Aadhaar/PAN
numbers, bank details, villages, GPS points. Aadhaar numbers are structurally
valid (pass the Verhoeff checksum) but are not real allotted numbers. Built by
`../build_pii_corpus.py` with `random.seed(20260821)`; regenerate with the
same interpreter to reproduce byte-for-byte.

## Taxonomy

    person_name, phone, email, aadhaar, pan, bank_account, ifsc, upi_id, dob,
    age, address, village, gps, caste_category, ration_card, voter_id,
    vehicle_number, record_id_non_pii, free_text_with_pii, none

## Ground truth files

For each tabular file `<basename>.{csv,xlsx}`:

- `<basename>.columns.json`: `{column_name: class}`. A column that mixes two
  entity types cell-by-cell (e.g. "Alt Contact" holds either an email or a
  phone number) is given a **list** of classes, e.g. `["email", "phone"]`,
  instead of a single string.
- `<basename>.cells.json`: a flat list of PII spans found inside free-text
  cells (Remarks / Note / Notes / q26_remarks columns), one entry per span:
  `{"sheet": "Baseline"|null, "row": 0-based data row (header excluded),
  "column": name, "start": char offset in the cell string, "end": ...,
  "class": ..., "text": exact substring}`. `sheet` is `null` for CSV files.
  Cells with no embedded PII contribute no entries.

For each narrative `.txt` file:

- `<basename>.spans.json`: a flat list of `{"start", "end", "class", "text"}`
  character offsets into the whole file's content. In the WhatsApp export,
  the sender name in `dd/mm/yy, hh:mm - Sender Name: message` is itself a
  `person_name` span.

All offsets were produced by construction (the generator inserts each PII
value and records its own start/end at insertion time) and were re-verified
after writing: every file was reopened from disk and
`content[start:end] == text` was asserted for every recorded span before the
generator was allowed to report success.

## Files

1. `scholarship_applicants.csv` (300 rows) - Hinglish scholarship register.
2. `donor_transactions.csv` (250 rows) - donation ledger.
3. `child_fitness_scores.xlsx` (200 children x 2 sheets: Baseline, Endline).
4. `household_survey.csv` (150 rows, KoBo-style export with q01..q25
   indicator columns).
5. `field_whatsapp_chat.txt` (~180 lines) - WhatsApp export format.
6. `field_observation_report.txt` (25 paragraphs) - narrative field visit
   report.

## Judgement calls

- `Taluka`, `District`, `City` are marked `none`: the taxonomy only has a
  `village` class for place-level PII, and these broader administrative
  units are shared by thousands of people, so they are not treated as
  identifying on their own.
- `School` (institution name) and `Name of scheme` are `none`: they are not
  personal identifiers, and "Name of scheme" is deliberately a header that
  *looks* like it might be sensitive but is not.
- `Coach` and `enumerator_name` are `person_name` even though they name
  staff rather than beneficiaries - the taxonomy has no separate class for
  staff vs. beneficiary names.
- `gps_lat` and `gps_lon` are each independently labelled `gps`, even though
  a single coordinate alone is less identifying than the pair.
- `start`, `end`, `_submission_time`, and `Date` (donor ledger) are `none`:
  timestamps have no dedicated class in the taxonomy and are not treated as
  PII by themselves here.
- `col_17` (scholarship file) is a deliberately generic header that actually
  holds bank account numbers; `Name of scheme` is a header that looks
  sensitive but is not; `q01..q25` are generic KoBo-style indicator headers
  that hold no PII.
