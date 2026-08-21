# Maternal Health Coverage Dashboard

A simple and interactive web application for analyzing and comparing district maternal health indicators from Excel (`maternal_health.xlsx`).

---

## 📊 Excel Structure (2 Sheets)

1. **Sheet 1: `District Data`**
   - **Columns**: `district`, `year`, `pregnancies_registered`, `institutional_deliveries`, `postnatal_check_48h`
   - **Districts Covered**: Gaya, Nalanda, Purnia
   - **Years Covered**: 2021, 2022, 2023

2. **Sheet 2: `Indicator Notes`**
   - **Columns**: `indicator`, `definition`, `formula`, `unit`, `source`
   - **Formulas Defined**:
     * **Institutional Delivery Coverage**: `(institutional_deliveries / pregnancies_registered) * 100` (%)
     * **Postnatal Check (within 48h) Coverage**: `(postnatal_check_48h / pregnancies_registered) * 100` (%)

---

## 🚀 Key Features

- **Indicator Selector**:
  - 🏥 *Institutional Delivery Coverage*
  - 👶 *Postnatal Check (within 48h) Coverage*
  - ⚖️ *Compare Both Indicators Side-by-Side*
- **Year Selector**:
  - Filter by `2021`, `2022`, `2023`, or `All Years (Trend View)`
- **District Comparison**:
  - Interactive Bar Chart ranking districts with custom tooltips
  - Multi-Year Line Chart tracking 2021–2023 performance trends
  - Executive KPI cards (Top district, lowest district, weighted average, volume)
  - Comprehensive Comparison Table with ranks, status badges, YoY change, and benchmark variance
- **Source Sheet & Formula Presentation**:
  - Clear card displaying source sheet names (`District Data` & `Indicator Notes`), definition, formula, and unit
  - **Live Step-by-Step Calculator**: Inspects any district (e.g. Gaya 2023: `(900 ÷ 1,200) × 100 = 75.0%`)
  - **Raw Sheets Inspector Modal**: Browse the full contents of both Excel sheets
- **Custom Excel Upload & Export**:
  - Drag-and-drop or select any `.xlsx` file for instant client-side analysis via SheetJS
  - Export filtered comparison data as CSV
  - Print / PDF-friendly formatting

---

## 💻 How to Run

### Option 1: Using Python Server (Recommended)
```bash
python3 server.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

### Option 2: Direct File Opening
Open `/workspace/index.html` directly in any web browser.
