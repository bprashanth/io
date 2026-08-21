# 4 Antenatal Checkup (ANC4) Coverage Dashboard (2021 – 2023)

Interactive maternal health dashboard to visualize and compare **4 Antenatal Checkup (ANC4) coverage rates** across districts for reporting years **2021, 2022, and 2023**.

---

## 🌟 Key Features

1. **Year Selection (2021 – 2023)**:
   - Toggle between single reporting years (`2021`, `2022`, `2023`) or view the complete `All (2021–2023) Trend`.
2. **Interactive Visualizations (Chart.js)**:
   - **District Comparison (Bar Chart)**: Color-coded bars showing district-by-district completion rates against health targets.
   - **Multi-Year Trend (Line Chart)**: Tracks coverage growth trajectories across all 5 districts from 2021 to 2023.
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
   - Shows 3-year gains from 2021 to 2023 for every district.
7. **Source & Methodology Section**:
   - Highlights the dataset source (`synthetic Bihar ANC fixture`).
   - Explains the mathematical formula with variable definitions and a live step-by-step arithmetic calculator.
8. **Export Capability**:
   - Export filtered or complete 2021–2023 dataset with calculated rates to CSV.

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
python3 -m http.server 8080 --directory /workspace
```
Then open [http://localhost:8080](http://localhost:8080) in your browser.

### Option 2: Using Node / npx
```bash
npx serve /workspace
```

### Option 3: Direct File Opening
Open [`index.html`](file:///workspace/index.html) directly in any web browser.
