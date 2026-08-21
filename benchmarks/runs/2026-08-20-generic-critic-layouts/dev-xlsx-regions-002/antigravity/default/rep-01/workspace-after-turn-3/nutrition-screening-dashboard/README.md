# Nutrition Screening & Completed Anaemia Referrals Dashboard

A responsive, interactive web application visualizing **Nutrition Screening Coverage** (Table 1: `A1:C7`) and **Completed Anaemia Referrals** (Table 2: `E1:G7`) by block and year from `nutrition_review_side_by_side.xlsx`.

---

## 📊 Source Provenance & Excel Mapping

| Parameter | Table 1 (Nutrition Screening) | Table 2 (Anaemia Referrals) |
| :--- | :--- | :--- |
| **Workbook File** | `nutrition_review_side_by_side.xlsx` | `nutrition_review_side_by_side.xlsx` |
| **Source Sheet** | `Quarterly Review` | `Quarterly Review` |
| **Table Title** | `"Table 1. Nutrition screening by block and year"` | `"Table 2. Completed anaemia referrals by block and year"` |
| **Full Cell Range** | `Quarterly Review!A1:C7` | `Quarterly Review!E1:G7` |
| **Title Range** | `A1:C1` (Merged) | `E1:G1` (Merged) |
| **Header Range** | `A3:C4` | `E3:G4` |
| **Data Range** | `A5:C7` | `E5:G7` |
| **Indicator** | Screening coverage (%) | Referrals completed |
| **Unit** | Percent (`%`) | Children (count) |
| **Definition** | *"Share of eligible children screened"* (`Definitions!A2:D2`) | *"Children completing an anaemia referral"* (`Definitions!A3:D3`) |

---

## 📈 Data Summary

### Table 1: Nutrition Screening Coverage (`A1:C7`)
- **Gaya (`A5:C5`)**: 2022 = `62%`, 2023 = `68%` (+6.0% YoY)
- **Nalanda (`A6:C6`)**: 2022 = `70%`, 2023 = `76%` (+6.0% YoY)
- **Purnia (`A7:C7`)**: 2022 = `55%`, 2023 = `61%` (+6.0% YoY)
- **Average**: 2022 = `62.3%`, 2023 = `68.3%` (+6.0% YoY)

### Table 2: Completed Anaemia Referrals (`E1:G7`)
- **Gaya (`E5:G5`)**: 2022 = `120`, 2023 = `150` (+30 referrals, +25.0%)
- **Nalanda (`E6:G6`)**: 2022 = `135`, 2023 = `160` (+25 referrals, +18.5%)
- **Purnia (`E7:G7`)**: 2022 = `90`, 2023 = `118` (+28 referrals, +31.1%)
- **Total**: 2022 = `345`, 2023 = `428` (+83 referrals, +24.1%)

---

## 🚀 Key Features

1. **Interactive Year Selection**:
   - Filter by **2023**, **2022**, or **Compare (2022 vs 2023)**.
2. **Dual-Indicator Focus Views**:
   - View both tables side-by-side or zoom into either Screening or Referrals.
3. **Dynamic Interactive Charts**:
   - Visualizes screening percentage benchmarks and referrals counts side-by-side.
4. **Excel Grid Visualizer**:
   - Renders exact Excel grid with Table 1 highlighted in Green (`A1:C7`) and Table 2 in Blue (`E1:G7`).
5. **Combined Export**:
   - One-click CSV export capturing both tables.

---

## 🛠️ How to Run
```bash
python3 server.py 8080
# Open http://localhost:8080 in your browser
```
