

**How the data resolves**

The `beneficiary_master.xlsx` (210 unique beneficiaries) is the per-beneficiary record: 143 rows have a non-null `Assistive Device Issued` with a matching `Device Issue Date` (fully consistent, no orphaned values, no duplicate UDIDs). The `device_inventory.csv` is a stock ledger (IN/OUT quantities); its "Issued to …" references only partially overlap with the master (15 of 166 names), so it can't serve as the beneficiary count — the master is the authoritative source.

**Answer**

| Metric | Count |
|---|---|
| Total beneficiaries in master | 210 |
| Beneficiaries who received an assistive device | **143** |
| Breakdown: Calipers 25, Crutches 24, Wheelchair 23, Tricycle 20, Braille kit 19, Walking stick 18, Hearing aid 14 | — |

**143 beneficiaries** have received an assistive device.