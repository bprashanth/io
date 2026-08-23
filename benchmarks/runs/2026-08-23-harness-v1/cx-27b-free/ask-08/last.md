

The camp register is a general health-camp log (S.No/Name/Age/Gender/Village/Notes) with no ANC visit fields — the ANC1 data lives entirely in the Kobo export, where each of the 327 `visit/anc1=yes` rows is a distinct person (327 unique phones/UUIDs, no duplicates).

**Answer**

| Metric | Count |
|---|---|
| Women with at least ANC1 completed | **327** |

Details:
- Source: `anc_tracking_kobo_export.csv` — 340 total entries, 327 with `visit/anc1 = yes` (13 blank, i.e., no ANC1).
- Dedup check: 327 unique phone numbers and UUIDs, so repeated names (e.g., "Priya Rathod" ×3) are different women, not double-counted.
- `camp_register.xlsx` contributes nothing: it has no ANC visit columns (only S.No, Name, Age, Gender, Village, Notes).

If you want the count restricted to `validation_status_approved` submissions only, it would be 262 (39 are on-hold, 26 have no status) — let me know if that's the definition you need.