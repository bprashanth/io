# 4 Antenatal Checkup (ANC4) Coverage Dashboard

Interactive maternal health dashboard to visualize and compare **4 Antenatal Checkup (ANC4) coverage rates** across districts and years (2020–2023).

---

## 🌟 Key Features

1. **Year Selection & Multi-Year Mode**:
   - Easily toggle between single reporting years (`2020`, `2021`, `2022`, `2023`) or view the complete `All Years Trend`.
2. **Interactive Visualizations (Chart.js)**:
   - **District Comparison (Bar Chart)**: Color-coded bars showing district-by-district completion rates against health targets.
   - **Multi-Year Trend (Line Chart)**: Tracks coverage growth trajectories across all 5 districts.
   - **Volumes View**: Directly compares raw registered pregnancies against 4-ANC completed.
3. **Key Performance Indicator (KPI) Cards**:
   - Aggregated State Average Coverage Rate.
   - Top Performing District and Needs Focus / Priority District.
   - Total Beneficiary counts and dropout gap.
4. **Detailed Comparison Table**:
   - Ranks, raw counts, formatted coverage percentages, visual progress bars, and difference from state average (`+ / - pp`).
   - Search filter and multi-column sorting (by coverage rate, district name, registered, completed).
5. **Head-to-Head District Comparison Tool**:
   - Compare any two districts side-by-side with immediate gap analysis and drop-out calculations.
6. **Multi-Year Progression Matrix**:
   - Shows 4-year gains from 2020 to 2023 for every district.
7. **Source & Methodology Section**:
   - Highlights the dataset source (`synthetic Bihar ANC fixture`).
   - Clearly explains the mathematical formula with variable definitions and a live step-by-step arithmetic calculator.
8. **Export Capability**:
   - Export filtered or complete dataset with calculated rates to CSV.

---

## 📐 Rate Calculation Formula

$$\text{ANC 4 Coverage Rate (\%)} = \left( \frac{\text{ANC 4 Completed}}{\text{Pregnancies Registered}} \right) \times 100$$

- **Numerator (`anc4_completed`)**: Number of pregnant women who attended $\ge 4$ antenatal checkups.
- **Denominator (`pregnancies_registered`)**: Total number of pregnant women registered for antenatal care.
- **Multiplier (`100`)**: Converts ratio to percentage.

---

## 🚀 How to Run the Website

### Option 1: Using Python
```bash
python3 -m http.server 8080
```
Then open [http://localhost:8080](http://localhost:8080) in your browser.

### Option 2: Using Node / npx
```bash
npx serve .
```

### Option 3: Direct File Opening
Open `index.html` directly in any web browser. The app includes a built-in fallback parser that works offline even without a local web server.
