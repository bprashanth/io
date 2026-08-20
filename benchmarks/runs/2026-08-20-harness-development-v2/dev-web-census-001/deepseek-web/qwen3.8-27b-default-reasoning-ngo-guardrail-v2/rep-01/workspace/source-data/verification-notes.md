# Verification notes — 2011 district populations (Patna, Gaya, Nalanda, Bihar)

Retrieved and verified: 2026-08-20, from official government sources only (no blogs).

## Official figures (Census of India, Census year 2011)

| District | Total | Males | Females |
|---|---|---|---|
| Patna   | 5,838,465 | 3,078,512 | 2,759,953 |
| Gaya    | 4,391,418 | 2,266,566 | 2,124,852 |
| Nalanda | 2,877,653 | 1,497,060 | 1,380,593 |

Context (same sources): Bihar state total 2011 = 104,099,452; India total 2011 = 1,210,854,977.

## Sources

1. **A-01 table (2011)** — "Number of villages, towns, households, population and area (India, states/UTs, districts and Sub-districts) - 2011"
   - Publisher: Registrar General & Census Commissioner of India, hosted on NADA (National Data Archive of India), censusindia.gov.in
   - Catalog page (live, title verified): https://censusindia.gov.in/nada/index.php/catalog/42526
   - File: https://censusindia.gov.in/nada/index.php/catalog/42526/download/46152/A-1_NO_OF_VILLAGES_TOWNS_HOUSEHOLDS_POPULATION_AND_AREA.xlsx
   - Local copy: `source-data/A01_2011.xlsx`
   - Rows used: state code 10 (Bihar), district code 230 (Patna), 236 (Gaya), 229 (Nalanda), column "DISTRICT / Total", columns K (persons), L (males), M (females).

2. **Basic Population Figures 2011 (Primary Census Abstract)** — "Basic Population Figures of India/State/District/Sub-District/Village - 2011"
   - Publisher: Registrar General & Census Commissioner of India, hosted on NADA
   - Catalog page (live, title verified): https://censusindia.gov.in/nada/index.php/catalog/42557
   - File: https://censusindia.gov.in/nada/index.php/catalog/42557/download/46183/2011-IndiaStateDist-0000.xlsx
   - Local copy: `source-data/PCA_2011_State_District.xlsx`
   - Linked from the official Population Finder page: https://www.censusindia.gov.in/census.website/data/population-finder
   - Rows used: state 10, district level "Total", column K = TOT_P, L = TOT_M, M = TOT_F.

## Cross-checks performed

- Both official files agree **exactly** for all three districts (total, male, female).
- Sum of all 38 Bihar district totals in both files = 104,099,452 = official Bihar state total.
- India total in the PCA file = 1,210,854,977 = official 2011 India total (confirms the file is genuinely the 2011 census, not a projection).
- Decadal growth against the official 2001 A-01 table (NADA catalog 20028, file PC01_A01.xls):
  Patna 4,718,592 → 5,838,465 (+23.7%); Gaya 3,473,428 → 4,391,418 (+26.4%);
  Nalanda 2,370,528 → 2,877,653 (+21.4%). All within Bihar's 2001–2011 state growth of 25.06%, i.e. plausible.

## Derived values shown on the page (formulas)

- Share of Bihar total = district total ÷ 104,099,452:
  Patna 5,838,465/104,099,452 = 5.608% → 5.6%; Gaya 4,391,418/104,099,452 = 4.219% → 4.2%; Nalanda 2,877,653/104,099,452 = 2.764% → 2.8%.
- Differences: Patna − Gaya = 1,447,047; Gaya − Nalanda = 1,513,765; Patna − Nalanda = 2,960,812.
- Three-district sum = 13,107,536.
- Population in lakhs (exact: persons ÷ 100,000, 1 lakh = 100,000):
  Patna 58.38465 lakh; Gaya 43.91418 lakh; Nalanda 28.77653 lakh;
  Patna − Gaya = 14.47047 lakh; three-district sum = 131.07536 lakh.
- Bar widths: Gaya 4,391,418/5,838,465 = 75.2%; Nalanda 2,877,653/5,838,465 = 49.3%.
