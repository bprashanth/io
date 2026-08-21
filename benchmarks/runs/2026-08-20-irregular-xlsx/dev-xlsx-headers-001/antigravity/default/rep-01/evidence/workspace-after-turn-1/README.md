# Primary School Attendance Portal

A simple and interactive web portal for exploring block-level primary school attendance by sex (boys/girls), year, and indicator, based on `school_attendance_nested.xlsx`.

## Features

1. **Indicator & Year Selectors**:
   - **Indicators**:
     - All Indicators (Boys & Girls side-by-side)
     - Boys Attendance (%)
     - Girls Attendance (%)
     - Boys vs Girls Comparison
     - Average Attendance `(Boys + Girls) / 2`
     - Gender Attendance Gap `(Boys - Girls %)`
   - **Years**:
     - All Years (2022 & 2023 with YoY growth rates)
     - 2022
     - 2023
   - **Block Filters**: All Blocks, Tekari, Wazirganj, Atri.
   - **School Level**: Primary School (Table 1), Secondary School (Table 2), or Both.

2. **Attendance Dashboard**:
   - Dynamic KPI Summary Cards (Boys Avg, Girls Avg, Top Performing Block, Gender Gap).
   - Filtered attendance table with visual progress indicators and YoY growth badges.
   - Interactive charts (Block Comparison Bar Chart, YoY Trend, Gender Gap analysis).

3. **Source Sheet & Raw Table Explorer**:
   - **Attendance Report**: View exact Excel spreadsheet grid replica with nested headers, row/column indices (1-17, A-E), and merged cells.
   - **Read Me**: Workbook metadata and benchmark documentation.
   - **Enrolment Raw**: 30 school enrolment records with search filter and block roll-up summary.
   - Multiple view modes: **Excel Grid View**, **Structured Tables**, and **Raw JSON**.

4. **Export & Utility**:
   - One-click **Export to CSV**.
   - One-click **Copy Table** to clipboard.
   - Dark / Light mode toggle.
   - Live data refresh and reload.

## Running the Portal

```bash
# Start server
python3 /workspace/server.py

# Access in browser at
http://localhost:8000
```
