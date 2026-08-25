# Structural choices in the loader that are still claims

Moved to skills on 2026-08-24 (built-in, same text, no regression: corpus 20/22 before and after):
Razorpay paise/epoch, running-ledger "latest row", WhatsApp first_number counts, month-wide blanks.

Still in code because they are needed for an unknown file to work on first contact, but each is an
interpretation a user may need to correct (SEE WHY shows them; parse skills can override the first two):

- **Day-first dates** (`coerce_dates`): Indian default; wrong for US exports (demo flow 1 shows the correction).
- **Header row = first mostly-label row followed by a filled row**; footer rows matching total/source/note.
- **Case/space variants merged** in categorical columns (`canonicalise_variants`): a data mutation.
- **Spelling-normalised join column** when ≥85 % of values fuzzy-match across two files: it can pair
  two person-name columns that merely overlap (seen: ANC women ↔ camp attendees). Needs a "same entity"
  test or a user confirmation; today it only shows up in SEE WHY.
- **Long unique integers kept as text** (ids) — right for UDID/Aadhaar, wrong for a genuine big number column.
- **Topic-switch rule** for prior turns: keyword overlap with table/column names.

Better design: these become *default skills* with visible triggers (so SEE WHY can say "skill:
indian-dates fired") and the kernel keeps only parsing mechanics.
