# Nutrition Screening Coverage Dashboard

A responsive, interactive web application visualizing **Nutrition Screening Coverage by Block and Year** with source provenance, year filtering, dynamic charts, data tables, and an interactive Excel sheet range inspector.

---

## 📊 Source Provenance & Excel Mapping

| Metadata Field | Value |
| :--- | :--- |
| **Workbook File** | `nutrition_review_side_by_side.xlsx` |
| **File Location** | `/workspace/nutrition_review_side_by_side.xlsx` |
| **Source Sheet** | `Quarterly Review` |
| **Table Name** | `Table 1. Nutrition screening by block and year` |
| **Source Cell Range** | `Quarterly Review!A1:C7` |
| **Table Title Range** | `A1:C1` ("Table 1. Nutrition screening by block and year") |
| **Column Headers Range** | `A3:C4` (`A3:A4` Block, `B3:C3` Screening coverage (%), `B4` 2022, `C4` 2023) |
| **Data Rows Range** | `A5:C7` (Gaya, Nalanda, Purnia) |
| **Indicator Definition** | "Share of eligible children screened (%)" (from `Definitions!A2:D2`) |

---

## 🚀 Key Features

1. **Interactive Year Selection**:
   - Select **2023** (Latest), **2022**, or **Compare (2022 vs 2023)**.
   - Real-time reactive updates to KPI stat cards, charts, and breakdown tables.

2. **Block-Level Analytics**:
   - Covers all administrative blocks: **Gaya**, **Nalanda**, and **Purnia**.
   - Year-over-Year (YoY) delta calculation (+6.0 percentage points across all blocks).

3. **Visual Analytics with Chart.js**:
   - Vertical Bar, Horizontal Bar, and Trend Line views.
   - 70% state target benchmark line and percentage labels.

4. **Interactive Excel Grid & Range Visualizer**:
   - Visual representation of the exact Excel spreadsheet grid (`Quarterly Review`, `Definitions`, `Household Visits Raw`).
   - Highlighting for `Table 1 (A1:C7)` and companion `Table 2 (E1:G7)`.
   - Hover tooltips displaying exact cell coordinates (e.g. `B5`, `C5`, `C6`).

5. **Data Export & Reporting**:
   - One-click CSV export with provenance headers.
   - Print-ready clean layout.

---

## 🛠️ How to Run

### Option 1: Using Python Server (Recommended)
```bash
python3 server.py 8080
# Open http://localhost:8080 in your browser
```

### Option 2: Direct File Open
Open `index.html` in any modern web browser.
