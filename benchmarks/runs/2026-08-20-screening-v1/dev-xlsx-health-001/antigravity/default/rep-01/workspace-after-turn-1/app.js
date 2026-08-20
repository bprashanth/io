/**
 * Maternal Health Dashboard Application Logic
 * Interactive Indicator Selection, Year Filtering, District Comparisons,
 * Formula & Source Sheet Callouts, Custom SVG Visualizations, and Raw Sheet Viewer.
 */

// Embedded default dataset fallback from /workspace/maternal_health.xlsx
const DEFAULT_DATA = {
  sheets: {
    "District Data": [
      ["district", "year", "pregnancies_registered", "institutional_deliveries", "postnatal_check_48h"],
      ["Gaya", 2021, 1000, 680, 600],
      ["Gaya", 2022, 1100, 792, 693],
      ["Gaya", 2023, 1200, 900, 816],
      ["Nalanda", 2021, 900, 675, 630],
      ["Nalanda", 2022, 1000, 780, 720],
      ["Nalanda", 2023, 1100, 880, 825],
      ["Purnia", 2021, 1200, 720, 660],
      ["Purnia", 2022, 1300, 819, 728],
      ["Purnia", 2023, 1400, 924, 812]
    ],
    "Indicator Notes": [
      ["indicator", "definition", "formula", "unit", "source"],
      ["Institutional delivery coverage", "Share of registered pregnancies with an institutional delivery", "institutional_deliveries / pregnancies_registered * 100", "percent", "synthetic maternal-health workbook fixture"],
      ["Postnatal check within 48 hours coverage", "Share of registered pregnancies with a recorded postnatal check within 48 hours", "postnatal_check_48h / pregnancies_registered * 100", "percent", "synthetic maternal-health workbook fixture"],
      ["Important", "Illustrative benchmark data; not official statistics and not person-level records", null, null, "synthetic maternal-health workbook fixture"]
    ]
  },
  indicators: [
    {
      indicator: "Institutional delivery coverage",
      definition: "Share of registered pregnancies with an institutional delivery",
      formula: "institutional_deliveries / pregnancies_registered * 100",
      unit: "percent",
      source: "synthetic maternal-health workbook fixture"
    },
    {
      indicator: "Postnatal check within 48 hours coverage",
      definition: "Share of registered pregnancies with a recorded postnatal check within 48 hours",
      formula: "postnatal_check_48h / pregnancies_registered * 100",
      unit: "percent",
      source: "synthetic maternal-health workbook fixture"
    }
  ],
  district_data: [
    { district: "Gaya", year: 2021, pregnancies_registered: 1000, institutional_deliveries: 680, postnatal_check_48h: 600 },
    { district: "Gaya", year: 2022, pregnancies_registered: 1100, institutional_deliveries: 792, postnatal_check_48h: 693 },
    { district: "Gaya", year: 2023, pregnancies_registered: 1200, institutional_deliveries: 900, postnatal_check_48h: 816 },
    { district: "Nalanda", year: 2021, pregnancies_registered: 900, institutional_deliveries: 675, postnatal_check_48h: 630 },
    { district: "Nalanda", year: 2022, pregnancies_registered: 1000, institutional_deliveries: 780, postnatal_check_48h: 720 },
    { district: "Nalanda", year: 2023, pregnancies_registered: 1100, institutional_deliveries: 880, postnatal_check_48h: 825 },
    { district: "Purnia", year: 2021, pregnancies_registered: 1200, institutional_deliveries: 720, postnatal_check_48h: 660 },
    { district: "Purnia", year: 2022, pregnancies_registered: 1300, institutional_deliveries: 819, postnatal_check_48h: 728 },
    { district: "Purnia", year: 2023, pregnancies_registered: 1400, institutional_deliveries: 924, postnatal_check_48h: 812 }
  ],
  years: [2021, 2022, 2023],
  districts: ["Gaya", "Nalanda", "Purnia"],
  disclaimer: "Illustrative benchmark data; not official statistics and not person-level records"
};

// Global App State
const state = {
  data: JSON.parse(JSON.stringify(DEFAULT_DATA)),
  selectedIndicator: "institutional_delivery", // 'institutional_delivery', 'postnatal_check', 'both'
  selectedYear: "2023", // '2021', '2022', '2023', 'all'
  selectedDistricts: ["Gaya", "Nalanda", "Purnia"],
  activeSheetTab: "District Data",
  searchQuery: "",
  fileName: "maternal_health.xlsx"
};

// Indicator Configurations
const INDICATOR_MAP = {
  institutional_delivery: {
    key: "institutional_delivery",
    name: "Institutional delivery coverage",
    shortName: "Institutional Delivery",
    definition: "Share of registered pregnancies with an institutional delivery",
    numeratorField: "institutional_deliveries",
    numeratorLabel: "Institutional Deliveries",
    denominatorField: "pregnancies_registered",
    denominatorLabel: "Pregnancies Registered",
    formula: "institutional_deliveries / pregnancies_registered * 100",
    color: "#2563eb",
    secondaryColor: "#93c5fd"
  },
  postnatal_check: {
    key: "postnatal_check",
    name: "Postnatal check within 48 hours coverage",
    shortName: "Postnatal Check (48h)",
    definition: "Share of registered pregnancies with a recorded postnatal check within 48 hours",
    numeratorField: "postnatal_check_48h",
    numeratorLabel: "Postnatal Checks (within 48h)",
    denominatorField: "pregnancies_registered",
    denominatorLabel: "Pregnancies Registered",
    formula: "postnatal_check_48h / pregnancies_registered * 100",
    color: "#0d9488",
    secondaryColor: "#99f6e4"
  }
};

// Initialize Application
document.addEventListener("DOMContentLoaded", async () => {
  initEventListeners();
  await loadDataFromBackend();
  renderAll();
});

// Fetch backend data if available, or fall back to embedded data
async function loadDataFromBackend() {
  try {
    const response = await fetch("/api/data");
    if (response.ok) {
      const json = await response.json();
      if (json && json.district_data && json.district_data.length > 0) {
        state.data = json;
        state.districts = [...json.districts];
        state.selectedDistricts = [...json.districts];
        console.log("Loaded dataset from backend API:", json);
      }
    }
  } catch (err) {
    console.warn("Backend API not reachable; running in standalone mode with embedded fixture data.");
  }
}

// Bind UI Listeners
function initEventListeners() {
  // Indicator Select
  const indicatorSelect = document.getElementById("indicator-select");
  if (indicatorSelect) {
    indicatorSelect.addEventListener("change", (e) => {
      state.selectedIndicator = e.target.value;
      renderAll();
    });
  }

  // Year Buttons
  const yearGroup = document.getElementById("year-buttons-group");
  if (yearGroup) {
    yearGroup.addEventListener("click", (e) => {
      const btn = e.target.closest(".year-btn");
      if (btn) {
        yearGroup.querySelectorAll(".year-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        state.selectedYear = btn.dataset.year;
        renderAll();
      }
    });
  }

  // Quick District Selection Buttons
  const btnSelectAll = document.getElementById("btn-select-all-districts");
  if (btnSelectAll) {
    btnSelectAll.addEventListener("click", () => {
      state.selectedDistricts = [...state.data.districts];
      renderDistrictChips();
      renderAll();
    });
  }

  const btnClearDistricts = document.getElementById("btn-clear-districts");
  if (btnClearDistricts) {
    btnClearDistricts.addEventListener("click", () => {
      if (state.data.districts.length > 0) {
        state.selectedDistricts = [state.data.districts[0]]; // keep at least one
      }
      renderDistrictChips();
      renderAll();
    });
  }

  // Search input in table
  const searchInput = document.getElementById("table-search-input");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      state.searchQuery = e.target.value.toLowerCase().trim();
      renderComparisonTable();
    });
  }

  // Main Tabs navigation
  document.querySelectorAll(".main-tabs .tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".main-tabs .tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      const targetId = btn.dataset.tab;
      const targetEl = document.getElementById(targetId);
      if (targetEl) targetEl.classList.add("active");

      if (targetId === "tab-multiyear") {
        renderMultiYearTab();
      } else if (targetId === "tab-sheets") {
        renderSheetExplorer();
      }
    });
  });

  // Sheet Tabs navigation inside Explorer
  const sheetTabsNav = document.getElementById("sheet-tabs-nav");
  if (sheetTabsNav) {
    sheetTabsNav.addEventListener("click", (e) => {
      const btn = e.target.closest(".sheet-nav-btn");
      if (btn) {
        sheetTabsNav.querySelectorAll(".sheet-nav-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        state.activeSheetTab = btn.dataset.sheet;
        renderSheetExplorer();
      }
    });
  }

  // CSV Export Button
  const btnExport = document.getElementById("btn-export-csv");
  if (btnExport) {
    btnExport.addEventListener("click", exportComparisonToCSV);
  }

  // Excel Upload Input
  const fileInput = document.getElementById("excel-upload-input");
  if (fileInput) {
    fileInput.addEventListener("change", handleFileUpload);
  }
}

// Master Render Function
function renderAll() {
  renderDistrictChips();
  renderFormulaSourceBox();
  renderSummaryStats();
  renderDistrictCharts();
  renderDistrictCards();
  renderComparisonTable();
  renderMultiYearTab();
  renderSheetExplorer();
}

// Render District Filter Chips
function renderDistrictChips() {
  const container = document.getElementById("district-chips-container");
  if (!container) return;

  container.innerHTML = "";
  const allDistricts = state.data.districts || [];

  allDistricts.forEach(district => {
    const isSelected = state.selectedDistricts.includes(district);
    const chip = document.createElement("label");
    chip.className = `district-chip ${isSelected ? "selected" : ""}`;
    chip.innerHTML = `
      <input type="checkbox" value="${district}" ${isSelected ? "checked" : ""}>
      <span>${district}</span>
    `;

    chip.addEventListener("change", (e) => {
      if (e.target.checked) {
        if (!state.selectedDistricts.includes(district)) {
          state.selectedDistricts.push(district);
        }
      } else {
        if (state.selectedDistricts.length > 1) {
          state.selectedDistricts = state.selectedDistricts.filter(d => d !== district);
        } else {
          e.target.checked = true; // Prevent deselecting all
        }
      }
      renderDistrictChips();
      renderAll();
    });

    container.appendChild(chip);
  });
}

// Render Formula & Source Sheet Info Callout
function renderFormulaSourceBox() {
  const isBoth = state.selectedIndicator === "both";
  const indKey = isBoth ? "institutional_delivery" : state.selectedIndicator;
  const cfg = INDICATOR_MAP[indKey] || INDICATOR_MAP.institutional_delivery;

  const metaNameEl = document.getElementById("meta-indicator-name");
  const metaDefEl = document.getElementById("meta-indicator-def");
  const formulaNumEl = document.getElementById("formula-numerator-text");
  const formulaDenEl = document.getElementById("formula-denominator-text");
  const excelFormulaEl = document.getElementById("excel-formula-text");
  const srcFieldsEl = document.getElementById("src-fields-list");
  const disclaimerEl = document.getElementById("meta-disclaimer-text");

  if (isBoth) {
    metaNameEl.textContent = "Institutional Delivery & Postnatal Care Coverage (Dual Comparison)";
    metaDefEl.textContent = "Comparing share of institutional deliveries alongside postnatal checks (within 48h) per registered pregnancy.";
    formulaNumEl.textContent = "institutional_deliveries | postnatal_check_48h";
    formulaDenEl.textContent = "pregnancies_registered";
    excelFormulaEl.textContent = "= institutional_deliveries / pregnancies_registered * 100 AND = postnatal_check_48h / pregnancies_registered * 100";
    srcFieldsEl.textContent = "pregnancies_registered, institutional_deliveries, postnatal_check_48h";
  } else {
    metaNameEl.textContent = cfg.name;
    metaDefEl.textContent = cfg.definition;
    formulaNumEl.textContent = cfg.numeratorField;
    formulaDenEl.textContent = cfg.denominatorField;
    excelFormulaEl.textContent = `= ${cfg.formula}`;
    srcFieldsEl.textContent = `${cfg.denominatorField}, ${cfg.numeratorField}`;
  }

  if (state.data.disclaimer) {
    disclaimerEl.textContent = `${state.data.disclaimer} (Source: synthetic maternal-health workbook fixture)`;
  }
}

// Calculate Filtered District Rows
function getFilteredRows(indicatorKey) {
  let rows = state.data.district_data || [];

  // Filter Year
  if (state.selectedYear !== "all") {
    const yr = parseInt(state.selectedYear, 10);
    rows = rows.filter(r => r.year === yr);
  }

  // Filter District
  rows = rows.filter(r => state.selectedDistricts.includes(r.district));

  // Compute calculated values
  const cfg = INDICATOR_MAP[indicatorKey];
  return rows.map(r => {
    const num = r[cfg.numeratorField];
    const den = r[cfg.denominatorField];
    const coverage = (num != null && den != null && den > 0) ? (num / den) * 100 : null;
    const calcStr = (num != null && den != null) ? `${num.toLocaleString()} / ${den.toLocaleString()} × 100 = ${coverage.toFixed(2)}%` : "N/A";
    return {
      district: r.district,
      year: r.year,
      numerator: num,
      denominator: den,
      coverage: coverage,
      calcString: calcStr,
      cfg: cfg,
      rawRow: r
    };
  });
}

// Render Summary KPI Statistics
function renderSummaryStats() {
  const isBoth = state.selectedIndicator === "both";
  const indKey = isBoth ? "institutional_delivery" : state.selectedIndicator;
  const rows = getFilteredRows(indKey);

  const avgEl = document.getElementById("kpi-avg-coverage");
  const yrLabelEl = document.getElementById("kpi-year-label");
  const aggMathEl = document.getElementById("kpi-aggregate-math");
  const topDistEl = document.getElementById("kpi-top-district");
  const topCovEl = document.getElementById("kpi-top-coverage");
  const topFormulaEl = document.getElementById("kpi-top-formula");
  const totalPregEl = document.getElementById("kpi-total-pregnancies");
  const totalDelivEl = document.getElementById("kpi-total-deliveries");

  yrLabelEl.textContent = state.selectedYear === "all" ? "across all years" : `in ${state.selectedYear}`;

  if (rows.length === 0) {
    avgEl.textContent = "0.0%";
    aggMathEl.textContent = "No data selected";
    topDistEl.textContent = "-";
    topCovEl.textContent = "0%";
    totalPregEl.textContent = "0";
    totalDelivEl.textContent = "0";
    return;
  }

  const totalNum = rows.reduce((sum, r) => sum + (r.numerator || 0), 0);
  const totalDen = rows.reduce((sum, r) => sum + (r.denominator || 0), 0);
  const aggCoverage = totalDen > 0 ? (totalNum / totalDen) * 100 : 0;

  avgEl.textContent = `${aggCoverage.toFixed(1)}%`;
  aggMathEl.textContent = `Aggregate: ${totalNum.toLocaleString()} / ${totalDen.toLocaleString()}`;

  totalPregEl.textContent = totalDen.toLocaleString();
  totalDelivEl.textContent = totalNum.toLocaleString();

  // Find top district
  const sorted = [...rows].sort((a, b) => (b.coverage || 0) - (a.coverage || 0));
  const top = sorted[0];
  if (top) {
    topDistEl.textContent = `${top.district} ${state.selectedYear === "all" ? `('${top.year})` : ""}`;
    topCovEl.textContent = `${top.coverage.toFixed(1)}%`;
    topFormulaEl.textContent = `${top.numerator.toLocaleString()} / ${top.denominator.toLocaleString()} recorded`;
  }
}

// Render Custom Interactive SVG District Comparison Charts
function renderDistrictCharts() {
  const container = document.getElementById("chart-svg-wrapper");
  const subtitleEl = document.getElementById("chart-subtitle-text");
  if (!container) return;

  const isBoth = state.selectedIndicator === "both";
  const yearText = state.selectedYear === "all" ? "All Years (2021-2023)" : `Year ${state.selectedYear}`;

  if (isBoth) {
    subtitleEl.textContent = `Side-by-Side: Institutional Delivery vs Postnatal Care (${yearText})`;
    renderDualIndicatorChart(container);
  } else {
    const cfg = INDICATOR_MAP[state.selectedIndicator];
    subtitleEl.textContent = `Comparing ${cfg.name} across selected districts (${yearText})`;
    renderSingleIndicatorChart(container, cfg);
  }
}

// Single Indicator SVG Bar Chart
function renderSingleIndicatorChart(container, cfg) {
  const rows = getFilteredRows(cfg.key);
  if (rows.length === 0) {
    container.innerHTML = `<div style="text-align:center; padding: 3rem; color: #64748b;">No district data selected</div>`;
    return;
  }

  // Calculate Average Benchmark
  const totalNum = rows.reduce((sum, r) => sum + (r.numerator || 0), 0);
  const totalDen = rows.reduce((sum, r) => sum + (r.denominator || 0), 0);
  const avgCoverage = totalDen > 0 ? (totalNum / totalDen) * 100 : 0;

  const width = container.clientWidth || 800;
  const height = 300;
  const padding = { top: 30, right: 30, bottom: 50, left: 60 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const barCount = rows.length;
  const barSlotWidth = chartWidth / barCount;
  const barWidth = Math.min(65, barSlotWidth * 0.55);

  let svg = `
    <svg class="chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
      <!-- Grid lines -->
      <line x1="${padding.left}" y1="${padding.top}" x2="${width - padding.right}" y2="${padding.top}" class="chart-grid-line" />
      <line x1="${padding.left}" y1="${padding.top + chartHeight * 0.25}" x2="${width - padding.right}" y2="${padding.top + chartHeight * 0.25}" class="chart-grid-line" />
      <line x1="${padding.left}" y1="${padding.top + chartHeight * 0.5}" x2="${width - padding.right}" y2="${padding.top + chartHeight * 0.5}" class="chart-grid-line" />
      <line x1="${padding.left}" y1="${padding.top + chartHeight * 0.75}" x2="${width - padding.right}" y2="${padding.top + chartHeight * 0.75}" class="chart-grid-line" />
      <line x1="${padding.left}" y1="${padding.top + chartHeight}" x2="${width - padding.right}" y2="${padding.top + chartHeight}" stroke="#cbd5e1" stroke-width="1.5" />

      <!-- Y Axis Labels -->
      <text x="${padding.left - 10}" y="${padding.top + 4}" text-anchor="end" class="chart-text">100%</text>
      <text x="${padding.left - 10}" y="${padding.top + chartHeight * 0.25 + 4}" text-anchor="end" class="chart-text">75%</text>
      <text x="${padding.left - 10}" y="${padding.top + chartHeight * 0.5 + 4}" text-anchor="end" class="chart-text">50%</text>
      <text x="${padding.left - 10}" y="${padding.top + chartHeight * 0.75 + 4}" text-anchor="end" class="chart-text">25%</text>
      <text x="${padding.left - 10}" y="${padding.top + chartHeight + 4}" text-anchor="end" class="chart-text">0%</text>
  `;

  // Benchmark Average Line
  const avgY = padding.top + chartHeight - (avgCoverage / 100) * chartHeight;
  svg += `
    <line x1="${padding.left}" y1="${avgY}" x2="${width - padding.right}" y2="${avgY}" class="chart-avg-line" />
    <text x="${width - padding.right}" y="${avgY - 6}" text-anchor="end" font-size="11" font-weight="600" fill="#d97706">Avg: ${avgCoverage.toFixed(1)}%</text>
  `;

  // Bars
  rows.forEach((r, idx) => {
    const cov = r.coverage || 0;
    const barH = (cov / 100) * chartHeight;
    const x = padding.left + idx * barSlotWidth + (barSlotWidth - barWidth) / 2;
    const y = padding.top + chartHeight - barH;
    const label = state.selectedYear === "all" ? `${r.district} ('${r.year.toString().slice(-2)})` : r.district;

    svg += `
      <g class="chart-bar-group" data-district="${r.district}" data-cov="${cov.toFixed(2)}" data-math="${r.calcString}">
        <rect x="${x}" y="${y}" width="${barWidth}" height="${barH}" rx="6" ry="6" fill="${cfg.color}" class="chart-bar-rect">
          <title>${r.district} (${r.year}): ${cov.toFixed(2)}% (${r.numerator} / ${r.denominator})</title>
        </rect>
        <text x="${x + barWidth / 2}" y="${y - 8}" text-anchor="middle" class="chart-text-value">${cov.toFixed(1)}%</text>
        <text x="${x + barWidth / 2}" y="${padding.top + chartHeight + 20}" text-anchor="middle" class="chart-text" font-weight="600">${label}</text>
      </g>
    `;
  });

  svg += `</svg>`;
  container.innerHTML = svg;
}

// Dual Indicator SVG Grouped Bar Chart
function renderDualIndicatorChart(container) {
  const instRows = getFilteredRows("institutional_delivery");
  const postRows = getFilteredRows("postnatal_check");

  if (instRows.length === 0) {
    container.innerHTML = `<div style="text-align:center; padding: 3rem; color: #64748b;">No district data selected</div>`;
    return;
  }

  const width = container.clientWidth || 800;
  const height = 300;
  const padding = { top: 30, right: 30, bottom: 50, left: 60 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const groupCount = instRows.length;
  const groupSlotWidth = chartWidth / groupCount;
  const barWidth = Math.min(32, groupSlotWidth * 0.35);

  let svg = `
    <svg class="chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
      <!-- Grid lines -->
      <line x1="${padding.left}" y1="${padding.top}" x2="${width - padding.right}" y2="${padding.top}" class="chart-grid-line" />
      <line x1="${padding.left}" y1="${padding.top + chartHeight * 0.5}" x2="${width - padding.right}" y2="${padding.top + chartHeight * 0.5}" class="chart-grid-line" />
      <line x1="${padding.left}" y1="${padding.top + chartHeight}" x2="${width - padding.right}" y2="${padding.top + chartHeight}" stroke="#cbd5e1" stroke-width="1.5" />

      <!-- Y Axis -->
      <text x="${padding.left - 10}" y="${padding.top + 4}" text-anchor="end" class="chart-text">100%</text>
      <text x="${padding.left - 10}" y="${padding.top + chartHeight * 0.5 + 4}" text-anchor="end" class="chart-text">50%</text>
      <text x="${padding.left - 10}" y="${padding.top + chartHeight + 4}" text-anchor="end" class="chart-text">0%</text>
  `;

  instRows.forEach((inst, idx) => {
    const post = postRows[idx] || { coverage: 0, numerator: 0, denominator: 0 };
    const instCov = inst.coverage || 0;
    const postCov = post.coverage || 0;

    const instH = (instCov / 100) * chartHeight;
    const postH = (postCov / 100) * chartHeight;

    const groupCenterX = padding.left + idx * groupSlotWidth + groupSlotWidth / 2;
    const x1 = groupCenterX - barWidth - 3;
    const x2 = groupCenterX + 3;
    const y1 = padding.top + chartHeight - instH;
    const y2 = padding.top + chartHeight - postH;

    const label = state.selectedYear === "all" ? `${inst.district} ('${inst.year.toString().slice(-2)})` : inst.district;

    svg += `
      <!-- Inst Delivery Bar -->
      <rect x="${x1}" y="${y1}" width="${barWidth}" height="${instH}" rx="4" ry="4" fill="#2563eb" class="chart-bar-rect">
        <title>Institutional: ${instCov.toFixed(1)}%</title>
      </rect>
      <text x="${x1 + barWidth / 2}" y="${y1 - 6}" text-anchor="middle" font-size="11" font-weight="700" fill="#2563eb">${instCov.toFixed(0)}%</text>

      <!-- Postnatal Check Bar -->
      <rect x="${x2}" y="${y2}" width="${barWidth}" height="${postH}" rx="4" ry="4" fill="#0d9488" class="chart-bar-rect">
        <title>Postnatal (48h): ${postCov.toFixed(1)}%</title>
      </rect>
      <text x="${x2 + barWidth / 2}" y="${y2 - 6}" text-anchor="middle" font-size="11" font-weight="700" fill="#0d9488">${postCov.toFixed(0)}%</text>

      <!-- X Label -->
      <text x="${groupCenterX}" y="${padding.top + chartHeight + 20}" text-anchor="middle" class="chart-text" font-weight="600">${label}</text>
    `;
  });

  svg += `</svg>`;
  container.innerHTML = svg;
}

// Render District Scorecards with Math Breakdown
function renderDistrictCards() {
  const container = document.getElementById("district-cards-grid");
  if (!container) return;

  const isBoth = state.selectedIndicator === "both";
  const indKey = isBoth ? "institutional_delivery" : state.selectedIndicator;
  const rows = getFilteredRows(indKey);

  // Sort by coverage descending to assign ranks
  const sorted = [...rows].sort((a, b) => (b.coverage || 0) - (a.coverage || 0));

  container.innerHTML = "";

  if (sorted.length === 0) {
    container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 2rem;">No districts match current filter.</div>`;
    return;
  }

  sorted.forEach((r, idx) => {
    const rankClass = idx === 0 ? "rank-1" : idx === 1 ? "rank-2" : "rank-3";
    const rankLabel = idx === 0 ? "Rank #1 (Highest)" : `Rank #${idx + 1}`;
    const cov = r.coverage != null ? r.coverage.toFixed(1) : "0.0";
    const fillPercent = Math.min(100, Math.max(0, r.coverage || 0));

    const card = document.createElement("div");
    card.className = "district-metric-card";
    card.innerHTML = `
      <div class="district-card-top">
        <div>
          <div class="district-name-title">${r.district}</div>
          <span style="font-size: 0.775rem; color: var(--text-muted);">Reporting Year: ${r.year}</span>
        </div>
        <span class="rank-badge ${rankClass}">${rankLabel}</span>
      </div>

      <div class="district-coverage-display">
        <span class="coverage-big-pct">${cov}</span>
        <span class="coverage-unit">% Coverage</span>
      </div>

      <div class="progress-track">
        <div class="progress-fill" style="width: ${fillPercent}%;"></div>
      </div>

      <div class="district-counts-row">
        <span class="count-label">${r.cfg.numeratorLabel}:</span>
        <span class="count-val">${(r.numerator || 0).toLocaleString()}</span>
      </div>

      <div class="district-counts-row">
        <span class="count-label">Registered Pregnancies:</span>
        <span class="count-val">${(r.denominator || 0).toLocaleString()}</span>
      </div>

      <div class="formula-eval-callout">
        <span>Formula: (${r.numerator} / ${r.denominator}) × 100</span>
        <strong style="color: var(--primary);">${cov}%</strong>
      </div>
    `;
    container.appendChild(card);
  });
}

// Render Comparison Data Table
function renderComparisonTable() {
  const tbody = document.getElementById("comparison-tbody");
  const tfoot = document.getElementById("comparison-tfoot");
  const thNum = document.getElementById("th-numerator");
  if (!tbody) return;

  const isBoth = state.selectedIndicator === "both";
  const indKey = isBoth ? "institutional_delivery" : state.selectedIndicator;
  const cfg = INDICATOR_MAP[indKey];

  if (thNum) thNum.textContent = cfg.numeratorLabel;

  let rows = getFilteredRows(indKey);

  // Apply search query
  if (state.searchQuery) {
    rows = rows.filter(r => r.district.toLowerCase().includes(state.searchQuery));
  }

  // Sort descending by coverage
  rows.sort((a, b) => (b.coverage || 0) - (a.coverage || 0));

  tbody.innerHTML = "";

  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 2rem;">No matching district records found.</td></tr>`;
    if (tfoot) tfoot.innerHTML = "";
    return;
  }

  rows.forEach((r, idx) => {
    const cov = r.coverage != null ? r.coverage.toFixed(2) : "0.00";
    let tierBadge = `<span class="badge badge-green">High (≥75%)</span>`;
    if (r.coverage < 65) {
      tierBadge = `<span class="badge badge-amber">Needs Attention (&lt;65%)</span>`;
    } else if (r.coverage < 75) {
      tierBadge = `<span class="badge badge-blue">Moderate (65-74%)</span>`;
    }

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>#${idx + 1}</strong></td>
      <td><strong>${r.district}</strong></td>
      <td><span class="badge badge-purple">${r.year}</span></td>
      <td>${(r.numerator || 0).toLocaleString()}</td>
      <td>${(r.denominator || 0).toLocaleString()}</td>
      <td><code class="calc-snippet">${r.calcString}</code></td>
      <td><strong style="color: var(--primary); font-size: 1rem;">${cov}%</strong></td>
      <td>${tierBadge}</td>
      <td><span class="cell-ref">District Data (Row ${idx + 2})</span></td>
    `;
    tbody.appendChild(tr);
  });

  // Calculate totals for tfoot
  const totalNum = rows.reduce((sum, r) => sum + (r.numerator || 0), 0);
  const totalDen = rows.reduce((sum, r) => sum + (r.denominator || 0), 0);
  const aggCov = totalDen > 0 ? ((totalNum / totalDen) * 100).toFixed(2) : "0.00";

  if (tfoot) {
    tfoot.innerHTML = `
      <tr>
        <td colspan="3"><strong>Total / Aggregate (${rows.length} records)</strong></td>
        <td><strong>${totalNum.toLocaleString()}</strong></td>
        <td><strong>${totalDen.toLocaleString()}</strong></td>
        <td><code class="calc-snippet">${totalNum.toLocaleString()} / ${totalDen.toLocaleString()} × 100</code></td>
        <td><strong style="color: var(--emerald); font-size: 1.05rem;">${aggCov}%</strong></td>
        <td><span class="badge badge-teal">Combined Average</span></td>
        <td><span class="cell-ref">Calculated Aggregate</span></td>
      </tr>
    `;
  }
}

// Render Multi-Year Tab (2021-2023 Trends)
function renderMultiYearTab() {
  const chartInst = document.getElementById("trend-chart-institutional");
  const chartPost = document.getElementById("trend-chart-postnatal");
  const tbody = document.getElementById("multiyear-matrix-tbody");

  if (!chartInst || !chartPost || !tbody) return;

  // Draw trend charts for both indicators
  drawTrendSVG(chartInst, "institutional_delivery");
  drawTrendSVG(chartPost, "postnatal_check");

  // Build matrix rows
  tbody.innerHTML = "";
  const districts = state.data.districts || [];
  const rawData = state.data.district_data || [];

  const indicatorsToMatrix = [
    INDICATOR_MAP.institutional_delivery,
    INDICATOR_MAP.postnatal_check
  ];

  districts.forEach(dist => {
    indicatorsToMatrix.forEach(ind => {
      const d2021 = rawData.find(r => r.district === dist && r.year === 2021);
      const d2022 = rawData.find(r => r.district === dist && r.year === 2022);
      const d2023 = rawData.find(r => r.district === dist && r.year === 2023);

      const c2021 = d2021 && d2021[ind.denominatorField] ? (d2021[ind.numeratorField] / d2021[ind.denominatorField]) * 100 : 0;
      const c2022 = d2022 && d2022[ind.denominatorField] ? (d2022[ind.numeratorField] / d2022[ind.denominatorField]) * 100 : 0;
      const c2023 = d2023 && d2023[ind.denominatorField] ? (d2023[ind.numeratorField] / d2023[ind.denominatorField]) * 100 : 0;

      const diff = c2023 - c2021;
      const sign = diff >= 0 ? "+" : "";

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${dist}</strong></td>
        <td><span class="badge ${ind.key === "institutional_delivery" ? "badge-blue" : "badge-teal"}">${ind.shortName}</span></td>
        <td>${c2021.toFixed(1)}%</td>
        <td>${c2022.toFixed(1)}%</td>
        <td><strong style="color: var(--primary);">${c2023.toFixed(1)}%</strong></td>
        <td><strong style="color: ${diff >= 0 ? "var(--emerald)" : "var(--rose)"};">${sign}${diff.toFixed(1)} pp</strong></td>
        <td><span class="badge badge-green">▲ Continuous Growth</span></td>
        <td><code class="calc-snippet">${ind.formula}</code></td>
      `;
      tbody.appendChild(tr);
    });
  });
}

// Draw Multi-Year Line Chart SVG
function drawTrendSVG(container, indicatorKey) {
  const cfg = INDICATOR_MAP[indicatorKey];
  const rawData = state.data.district_data || [];
  const districts = state.data.districts || [];
  const years = [2021, 2022, 2023];

  const colors = {
    Gaya: "#2563eb",
    Nalanda: "#059669",
    Purnia: "#d97706"
  };

  const width = container.clientWidth || 450;
  const height = 220;
  const padding = { top: 20, right: 30, bottom: 40, left: 45 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  let svg = `
    <svg class="chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
      <!-- Grid -->
      <line x1="${padding.left}" y1="${padding.top}" x2="${width - padding.right}" y2="${padding.top}" class="chart-grid-line" />
      <line x1="${padding.left}" y1="${padding.top + chartHeight * 0.5}" x2="${width - padding.right}" y2="${padding.top + chartHeight * 0.5}" class="chart-grid-line" />
      <line x1="${padding.left}" y1="${padding.top + chartHeight}" x2="${width - padding.right}" y2="${padding.top + chartHeight}" stroke="#cbd5e1" />

      <text x="${padding.left - 8}" y="${padding.top + 4}" text-anchor="end" class="chart-text">100%</text>
      <text x="${padding.left - 8}" y="${padding.top + chartHeight * 0.5 + 4}" text-anchor="end" class="chart-text">50%</text>
      <text x="${padding.left - 8}" y="${padding.top + chartHeight + 4}" text-anchor="end" class="chart-text">0%</text>
  `;

  // X Axis year ticks
  years.forEach((yr, idx) => {
    const x = padding.left + (idx / (years.length - 1)) * chartWidth;
    svg += `<text x="${x}" y="${padding.top + chartHeight + 20}" text-anchor="middle" class="chart-text" font-weight="600">${yr}</text>`;
  });

  // Plot line for each district
  districts.forEach(dist => {
    const distColor = colors[dist] || "#7c3aed";
    const points = [];

    years.forEach((yr, idx) => {
      const match = rawData.find(r => r.district === dist && r.year === yr);
      const cov = match && match[cfg.denominatorField] ? (match[cfg.numeratorField] / match[cfg.denominatorField]) * 100 : 0;
      const x = padding.left + (idx / (years.length - 1)) * chartWidth;
      const y = padding.top + chartHeight - (cov / 100) * chartHeight;
      points.push({ x, y, cov, yr });
    });

    // Draw line path
    const pathD = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
    svg += `<path d="${pathD}" fill="none" stroke="${distColor}" stroke-width="2.5" stroke-linecap="round" />`;

    // Draw dots and text
    points.forEach(p => {
      svg += `
        <circle cx="${p.x}" cy="${p.y}" r="4" fill="${distColor}" stroke="#ffffff" stroke-width="2">
          <title>${dist} (${p.yr}): ${p.cov.toFixed(1)}%</title>
        </circle>
        <text x="${p.x}" y="${p.y - 8}" text-anchor="middle" font-size="11" font-weight="700" fill="${distColor}">${p.cov.toFixed(0)}%</text>
      `;
    });
  });

  svg += `</svg>`;
  container.innerHTML = svg;
}

// Render Raw Sheet Explorer
function renderSheetExplorer() {
  const table = document.getElementById("raw-sheet-table");
  const metaInfo = document.getElementById("sheet-meta-info");
  if (!table || !metaInfo) return;

  const currentSheetName = state.activeSheetTab;
  const sheetRows = state.data.sheets[currentSheetName] || [];

  if (sheetRows.length === 0) {
    metaInfo.innerHTML = `<span>Sheet <strong>${currentSheetName}</strong> is empty.</span>`;
    table.innerHTML = "";
    return;
  }

  const rowCount = sheetRows.length - 1; // minus header
  const colCount = sheetRows[0].length;
  metaInfo.innerHTML = `
    <span><strong>Active Sheet:</strong> ${currentSheetName}</span>
    <span><strong>Rows:</strong> ${rowCount} rows</span>
    <span><strong>Columns:</strong> ${colCount} columns</span>
    <span><strong>Source Workbook:</strong> <code>${state.fileName}</code></span>
  `;

  const headers = sheetRows[0];
  let theadHtml = `<thead><tr><th>#</th>${headers.map(h => `<th>${h || ""}</th>`).join("")}</tr></thead>`;

  let tbodyHtml = "<tbody>";
  for (let i = 1; i < sheetRows.length; i++) {
    const row = sheetRows[i];
    tbodyHtml += `<tr><td><span class="cell-ref">${i}</span></td>${row.map(val => `<td>${val != null ? val : '<span style="color:#94a3b8;">null</span>'}</td>`).join("")}</tr>`;
  }
  tbodyHtml += "</tbody>";

  table.innerHTML = theadHtml + tbodyHtml;
}

// Handle Custom Excel Upload
function handleFileUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  state.fileName = file.name;
  const fileNameDisplay = document.getElementById("source-workbook-name");
  if (fileNameDisplay) fileNameDisplay.textContent = file.name;

  const reader = new FileReader();
  reader.onload = (event) => {
    try {
      if (typeof XLSX === "undefined") {
        alert("Excel parser library is initializing. Please try again in a moment.");
        return;
      }
      const data = new Uint8Array(event.target.result);
      const workbook = XLSX.read(data, { type: "array" });

      const parsedData = {
        sheets: {},
        indicators: [],
        district_data: [],
        years: [],
        districts: []
      };

      workbook.SheetNames.forEach(name => {
        const sheet = workbook.Sheets[name];
        const jsonRows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: null });
        parsedData.sheets[name] = jsonRows;
      });

      // Parse Indicator Notes
      if (parsedData.sheets["Indicator Notes"]) {
        const rows = parsedData.sheets["Indicator Notes"];
        const headers = rows[0].map(h => String(h || "").toLowerCase().trim());
        for (let i = 1; i < rows.length; i++) {
          const item = {};
          rows[i].forEach((v, idx) => {
            if (headers[idx]) item[headers[idx]] = v;
          });
          if (item.indicator && item.indicator !== "Important") {
            parsedData.indicators.push(item);
          } else if (item.indicator === "Important") {
            parsedData.disclaimer = item.definition;
          }
        }
      }

      // Parse District Data
      if (parsedData.sheets["District Data"]) {
        const rows = parsedData.sheets["District Data"];
        const headers = rows[0].map(h => String(h || "").toLowerCase().trim());
        for (let i = 1; i < rows.length; i++) {
          const item = {};
          rows[i].forEach((v, idx) => {
            if (headers[idx]) item[headers[idx]] = v;
          });
          if (item.district && item.year) {
            item.year = parseInt(item.year, 10);
            parsedData.district_data.push(item);
          }
        }
      }

      parsedData.years = [...new Set(parsedData.district_data.map(d => d.year))].sort();
      parsedData.districts = [...new Set(parsedData.district_data.map(d => d.district))].sort();

      state.data = parsedData;
      state.districts = [...parsedData.districts];
      state.selectedDistricts = [...parsedData.districts];

      alert(`Successfully loaded workbook "${file.name}" with ${workbook.SheetNames.length} sheets!`);
      renderAll();
    } catch (err) {
      console.error("Error parsing uploaded Excel:", err);
      alert(`Error reading Excel file: ${err.message}`);
    }
  };
  reader.readAsArrayBuffer(file);
}

// Export Comparison Summary to CSV
function exportComparisonToCSV() {
  const isBoth = state.selectedIndicator === "both";
  const indKey = isBoth ? "institutional_delivery" : state.selectedIndicator;
  const cfg = INDICATOR_MAP[indKey];
  const rows = getFilteredRows(indKey);

  let csv = "District,Year,Numerator,Denominator,Formula,Coverage_Percent,Source_Sheet\n";
  rows.forEach(r => {
    csv += `"${r.district}",${r.year},${r.numerator},${r.denominator},"${r.calcString}",${(r.coverage || 0).toFixed(2)},"District Data"\n`;
  });

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  link.setAttribute("download", `maternal_health_comparison_${state.selectedYear}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
