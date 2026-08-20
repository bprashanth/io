/**
 * Maternal Health Coverage Dashboard
 * District Comparison, Source Sheet & Formula Explorer
 */

// Embedded initial dataset from maternal_health.xlsx as fallback and fast startup
const DEFAULT_DATA = {
  filename: "maternal_health.xlsx",
  sheets: {
    "District Data": {
      headers: [
        "district",
        "year",
        "pregnancies_registered",
        "institutional_deliveries",
        "postnatal_check_48h"
      ],
      rows: [
        { district: "Gaya", year: 2021, pregnancies_registered: 1000, institutional_deliveries: 680, postnatal_check_48h: 600 },
        { district: "Gaya", year: 2022, pregnancies_registered: 1100, institutional_deliveries: 792, postnatal_check_48h: 693 },
        { district: "Gaya", year: 2023, pregnancies_registered: 1200, institutional_deliveries: 900, postnatal_check_48h: 816 },
        { district: "Nalanda", year: 2021, pregnancies_registered: 900, institutional_deliveries: 675, postnatal_check_48h: 630 },
        { district: "Nalanda", year: 2022, pregnancies_registered: 1000, institutional_deliveries: 780, postnatal_check_48h: 720 },
        { district: "Nalanda", year: 2023, pregnancies_registered: 1100, institutional_deliveries: 880, postnatal_check_48h: 825 },
        { district: "Purnia", year: 2021, pregnancies_registered: 1200, institutional_deliveries: 720, postnatal_check_48h: 660 },
        { district: "Purnia", year: 2022, pregnancies_registered: 1300, institutional_deliveries: 819, postnatal_check_48h: 728 },
        { district: "Purnia", year: 2023, pregnancies_registered: 1400, institutional_deliveries: 924, postnatal_check_48h: 812 }
      ]
    },
    "Indicator Notes": {
      headers: ["indicator", "definition", "formula", "unit", "source"],
      rows: [
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
        },
        {
          indicator: "Important",
          definition: "Illustrative benchmark data; not official statistics and not person-level records",
          formula: null,
          unit: null,
          source: "synthetic maternal-health workbook fixture"
        }
      ]
    }
  }
};

// Indicator Registry Configurations
const INDICATORS = {
  inst_del: {
    id: "inst_del",
    title: "Institutional Delivery Coverage",
    shortTitle: "Inst. Delivery Coverage",
    icon: "fa-hospital",
    numeratorCol: "institutional_deliveries",
    numeratorLabel: "Institutional Deliveries",
    denominatorCol: "pregnancies_registered",
    denominatorLabel: "Registered Pregnancies",
    formulaRaw: "institutional_deliveries / pregnancies_registered * 100",
    formulaHuman: "institutional_deliveries ÷ pregnancies_registered × 100",
    unit: "%",
    sourceSheetData: "District Data",
    sourceSheetMeta: "Indicator Notes",
    metaRowIndex: 0,
    themeColor: "#2563eb",
    themeBg: "#eff6ff",
    chartColor: "rgba(37, 99, 235, 0.85)",
    chartBorder: "#1d4ed8"
  },
  pnc_48h: {
    id: "pnc_48h",
    title: "Postnatal Check (within 48h) Coverage",
    shortTitle: "PNC 48h Coverage",
    icon: "fa-baby",
    numeratorCol: "postnatal_check_48h",
    numeratorLabel: "Postnatal Checks (48h)",
    denominatorCol: "pregnancies_registered",
    denominatorLabel: "Registered Pregnancies",
    formulaRaw: "postnatal_check_48h / pregnancies_registered * 100",
    formulaHuman: "postnatal_check_48h ÷ pregnancies_registered × 100",
    unit: "%",
    sourceSheetData: "District Data",
    sourceSheetMeta: "Indicator Notes",
    metaRowIndex: 1,
    themeColor: "#059669",
    themeBg: "#ecfdf5",
    chartColor: "rgba(5, 150, 105, 0.85)",
    chartBorder: "#047857"
  }
};

// Application State
const state = {
  currentData: JSON.parse(JSON.stringify(DEFAULT_DATA)),
  selectedIndicator: "inst_del", // "inst_del", "pnc_48h", "both"
  selectedYear: 2023,            // 2021, 2022, 2023, or "all"
  selectedDistricts: new Set(["Gaya", "Nalanda", "Purnia"]),
  selectedDrilldownDistrict: "Nalanda",
  sortKey: "coverage_desc",      // coverage_desc, coverage_asc, name_asc, numerator_desc
  charts: {
    barChart: null,
    trendChart: null,
    dualChart: null
  }
};

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  initApp();
});

async function initApp() {
  setupEventListeners();
  
  // Try fetching latest live data from server API if available
  try {
    const res = await fetch("/api/data");
    if (res.ok) {
      const json = await res.json();
      if (json.sheets && json.sheets["District Data"]) {
        state.currentData = json;
        console.log("Loaded dataset from backend server API:", json);
      }
    }
  } catch (e) {
    console.log("Using embedded default dataset:", e);
  }

  // Populate dynamic controls (years, districts, indicators)
  refreshControls();
  renderAll();
}

function getAvailableYears() {
  const rows = state.currentData.sheets["District Data"]?.rows || [];
  const years = Array.from(new Set(rows.map(r => Number(r.year)).filter(Boolean))).sort((a, b) => a - b);
  return years.length ? years : [2021, 2022, 2023];
}

function getAvailableDistricts() {
  const rows = state.currentData.sheets["District Data"]?.rows || [];
  const districts = Array.from(new Set(rows.map(r => r.district).filter(Boolean))).sort();
  return districts.length ? districts : ["Gaya", "Nalanda", "Purnia"];
}

function refreshControls() {
  // Populate Years
  const years = getAvailableYears();
  const yearContainer = document.getElementById("yearButtonsContainer");
  if (yearContainer) {
    yearContainer.innerHTML = "";
    
    years.forEach(year => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold border transition ${
        state.selectedYear === year 
          ? "bg-blue-600 text-white border-blue-600 shadow-sm" 
          : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50"
      }`;
      btn.textContent = year;
      btn.onclick = () => {
        state.selectedYear = year;
        refreshControls();
        renderAll();
      };
      yearContainer.appendChild(btn);
    });

    // "All Years" option
    const allBtn = document.createElement("button");
    allBtn.type = "button";
    allBtn.className = `px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold border transition ${
      state.selectedYear === "all"
        ? "bg-blue-600 text-white border-blue-600 shadow-sm"
        : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50"
    }`;
    allBtn.textContent = "All Years (Trend)";
    allBtn.onclick = () => {
      state.selectedYear = "all";
      refreshControls();
      renderAll();
    };
    yearContainer.appendChild(allBtn);
  }

  // Populate Districts
  const districts = getAvailableDistricts();
  if (state.selectedDistricts.size === 0) {
    districts.forEach(d => state.selectedDistricts.add(d));
  }
  if (!districts.includes(state.selectedDrilldownDistrict) && districts.length > 0) {
    state.selectedDrilldownDistrict = districts[0];
  }

  const districtContainer = document.getElementById("districtChipsContainer");
  if (districtContainer) {
    districtContainer.innerHTML = "";
    districts.forEach(d => {
      const isSelected = state.selectedDistricts.has(d);
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = `px-2.5 py-1 rounded-full text-xs font-medium border flex items-center gap-1.5 transition ${
        isSelected 
          ? "bg-blue-50 border-blue-300 text-blue-800 font-semibold" 
          : "bg-slate-100 border-slate-200 text-slate-500 opacity-60 hover:opacity-100"
      }`;
      chip.innerHTML = `
        <span class="w-2 h-2 rounded-full ${isSelected ? 'bg-blue-600' : 'bg-slate-400'}"></span>
        ${d}
      `;
      chip.onclick = () => {
        if (state.selectedDistricts.has(d)) {
          if (state.selectedDistricts.size > 1) {
            state.selectedDistricts.delete(d);
          } else {
            alert("At least one district must be selected.");
            return;
          }
        } else {
          state.selectedDistricts.add(d);
        }
        refreshControls();
        renderAll();
      };
      districtContainer.appendChild(chip);
    });
  }

  // Populate Drilldown District Dropdown
  const drilldownSelect = document.getElementById("formulaDistrictSelect");
  if (drilldownSelect) {
    drilldownSelect.innerHTML = "";
    districts.forEach(d => {
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d;
      opt.selected = (d === state.selectedDrilldownDistrict);
      drilldownSelect.appendChild(opt);
    });
  }
}

function setupEventListeners() {
  // Indicator selector tabs
  document.querySelectorAll("[data-indicator-btn]").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const target = btn.getAttribute("data-indicator-btn");
      state.selectedIndicator = target;
      
      document.querySelectorAll("[data-indicator-btn]").forEach(b => {
        b.classList.remove("active", "bg-blue-600", "text-white", "border-blue-600", "shadow-sm");
        b.classList.add("bg-white", "text-slate-700", "border-slate-300");
      });
      btn.classList.add("active", "bg-blue-600", "text-white", "border-blue-600", "shadow-sm");
      btn.classList.remove("bg-white", "text-slate-700", "border-slate-300");

      renderAll();
    });
  });

  // Sort selector
  const sortSelect = document.getElementById("tableSortSelect");
  if (sortSelect) {
    sortSelect.addEventListener("change", (e) => {
      state.sortKey = e.target.value;
      renderTable();
    });
  }

  // Drilldown district change
  const drilldownSelect = document.getElementById("formulaDistrictSelect");
  if (drilldownSelect) {
    drilldownSelect.addEventListener("change", (e) => {
      state.selectedDrilldownDistrict = e.target.value;
      renderFormulaCard();
    });
  }

  // Select all districts button
  const selectAllBtn = document.getElementById("selectAllDistrictsBtn");
  if (selectAllBtn) {
    selectAllBtn.addEventListener("click", () => {
      const all = getAvailableDistricts();
      all.forEach(d => state.selectedDistricts.add(d));
      refreshControls();
      renderAll();
    });
  }

  // Reset filter button
  const resetBtn = document.getElementById("resetFiltersBtn");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      state.selectedIndicator = "inst_del";
      state.selectedYear = 2023;
      state.selectedDistricts = new Set(getAvailableDistricts());
      state.sortKey = "coverage_desc";
      
      // Update UI buttons
      document.querySelectorAll("[data-indicator-btn]").forEach(b => {
        if (b.getAttribute("data-indicator-btn") === "inst_del") {
          b.classList.add("active", "bg-blue-600", "text-white", "border-blue-600", "shadow-sm");
          b.classList.remove("bg-white", "text-slate-700", "border-slate-300");
        } else {
          b.classList.remove("active", "bg-blue-600", "text-white", "border-blue-600", "shadow-sm");
          b.classList.add("bg-white", "text-slate-700", "border-slate-300");
        }
      });
      
      refreshControls();
      renderAll();
    });
  }

  // Modal triggers
  const viewSheetsBtn = document.getElementById("viewSheetsBtn");
  const modalCloseBtn = document.getElementById("modalCloseBtn");
  const sheetsModal = document.getElementById("sheetsModal");
  if (viewSheetsBtn && sheetsModal) {
    viewSheetsBtn.addEventListener("click", () => {
      renderRawSheetsModal();
      sheetsModal.classList.remove("hidden");
    });
  }
  if (modalCloseBtn && sheetsModal) {
    modalCloseBtn.addEventListener("click", () => {
      sheetsModal.classList.add("hidden");
    });
  }

  // Modal Sheet Tab Switching
  document.querySelectorAll("[data-sheet-tab]").forEach(tab => {
    tab.addEventListener("click", () => {
      const sheetName = tab.getAttribute("data-sheet-tab");
      document.querySelectorAll("[data-sheet-tab]").forEach(t => {
        t.classList.remove("border-blue-600", "text-blue-600", "font-bold");
        t.classList.add("border-transparent", "text-slate-500", "font-medium");
      });
      tab.classList.add("border-blue-600", "text-blue-600", "font-bold");
      tab.classList.remove("border-transparent", "text-slate-500", "font-medium");

      document.querySelectorAll(".sheet-table-pane").forEach(pane => {
        pane.classList.add("hidden");
      });
      const targetPane = document.getElementById(`pane_${sheetName.replace(/\s+/g, "_")}`);
      if (targetPane) targetPane.classList.remove("hidden");
    });
  });

  // Excel File Upload Handler (Drag & Drop + File Input)
  const excelFileInput = document.getElementById("excelFileInput");
  const uploadTriggerBtn = document.getElementById("uploadTriggerBtn");
  if (uploadTriggerBtn && excelFileInput) {
    uploadTriggerBtn.addEventListener("click", () => excelFileInput.click());
  }
  if (excelFileInput) {
    excelFileInput.addEventListener("change", handleFileUpload);
  }

  // Export CSV
  const exportCsvBtn = document.getElementById("exportCsvBtn");
  if (exportCsvBtn) {
    exportCsvBtn.addEventListener("click", exportCurrentDataToCsv);
  }

  // Print
  const printBtn = document.getElementById("printBtn");
  if (printBtn) {
    printBtn.addEventListener("click", () => window.print());
  }
}

// Data Processing & Calculations
function calculateMetrics() {
  const rawRows = state.currentData.sheets["District Data"]?.rows || [];
  const years = getAvailableYears();
  const latestYear = state.selectedYear === "all" ? Math.max(...years) : state.selectedYear;
  
  // Calculate row metrics
  const enrichedRows = rawRows.map(r => {
    const preg = Number(r.pregnancies_registered) || 0;
    const inst = Number(r.institutional_deliveries) || 0;
    const pnc = Number(r.postnatal_check_48h) || 0;
    
    const instCoverage = preg > 0 ? (inst / preg) * 100 : 0;
    const pncCoverage = preg > 0 ? (pnc / preg) * 100 : 0;
    
    return {
      district: r.district,
      year: Number(r.year),
      pregnancies_registered: preg,
      institutional_deliveries: inst,
      postnatal_check_48h: pnc,
      inst_coverage: Number(instCoverage.toFixed(2)),
      pnc_coverage: Number(pncCoverage.toFixed(2))
    };
  });

  // Filter by selected year and districts
  let currentFiltered = enrichedRows.filter(r => {
    const matchYear = (state.selectedYear === "all") ? (r.year === latestYear) : (r.year === state.selectedYear);
    const matchDist = state.selectedDistricts.has(r.district);
    return matchYear && matchDist;
  });

  // Calculate YoY growth for each row
  currentFiltered = currentFiltered.map(row => {
    const prevYearRow = enrichedRows.find(r => r.district === row.district && r.year === (row.year - 1));
    let yoyInst = null;
    let yoyPnc = null;
    if (prevYearRow) {
      yoyInst = Number((row.inst_coverage - prevYearRow.inst_coverage).toFixed(2));
      yoyPnc = Number((row.pnc_coverage - prevYearRow.pnc_coverage).toFixed(2));
    }
    return {
      ...row,
      prevYear: prevYearRow ? prevYearRow.year : null,
      yoyInst,
      yoyPnc
    };
  });

  // Sort rows based on state.sortKey
  currentFiltered.sort((a, b) => {
    const ind = state.selectedIndicator === "pnc_48h" ? "pnc_coverage" : "inst_coverage";
    const num = state.selectedIndicator === "pnc_48h" ? "postnatal_check_48h" : "institutional_deliveries";
    
    if (state.sortKey === "coverage_desc") return b[ind] - a[ind];
    if (state.sortKey === "coverage_asc") return a[ind] - b[ind];
    if (state.sortKey === "name_asc") return a.district.localeCompare(b.district);
    if (state.sortKey === "numerator_desc") return b[num] - a[num];
    return 0;
  });

  // Overall totals across filtered set
  const totalPreg = currentFiltered.reduce((sum, r) => sum + r.pregnancies_registered, 0);
  const totalInst = currentFiltered.reduce((sum, r) => sum + r.institutional_deliveries, 0);
  const totalPnc = currentFiltered.reduce((sum, r) => sum + r.postnatal_check_48h, 0);

  const aggregateInstCoverage = totalPreg > 0 ? Number(((totalInst / totalPreg) * 100).toFixed(2)) : 0;
  const aggregatePncCoverage = totalPreg > 0 ? Number(((totalPnc / totalPreg) * 100).toFixed(2)) : 0;

  return {
    allRows: enrichedRows,
    filteredRows: currentFiltered,
    totalPreg,
    totalInst,
    totalPnc,
    aggregateInstCoverage,
    aggregatePncCoverage,
    activeYear: latestYear
  };
}

// Master Render
function renderAll() {
  const metrics = calculateMetrics();
  renderFormulaCard();
  renderKpiCards(metrics);
  renderCharts(metrics);
  renderTable(metrics);
}

// Render Formula & Source Sheet Card
function renderFormulaCard() {
  const cardContainer = document.getElementById("formulaCardContent");
  if (!cardContainer) return;

  const isBoth = state.selectedIndicator === "both";
  const indKey = isBoth ? "inst_del" : state.selectedIndicator;
  const indConfig = INDICATORS[indKey];

  // Get notes metadata from sheet
  const notesSheet = state.currentData.sheets["Indicator Notes"]?.rows || [];
  const noteRow = notesSheet[indConfig.metaRowIndex] || {};
  const definition = noteRow.definition || (indKey === "inst_del" 
    ? "Share of registered pregnancies with an institutional delivery" 
    : "Share of registered pregnancies with a recorded postnatal check within 48 hours");
  const formulaRaw = noteRow.formula || indConfig.formulaRaw;
  const unit = noteRow.unit || indConfig.unit;
  const sourceCitation = noteRow.source || "synthetic maternal-health workbook fixture";

  // Drilldown calculations for selected district
  const years = getAvailableYears();
  const activeYear = (state.selectedYear === "all") ? Math.max(...years) : state.selectedYear;
  const rawRows = state.currentData.sheets["District Data"]?.rows || [];
  const matchRow = rawRows.find(r => r.district === state.selectedDrilldownDistrict && Number(r.year) === activeYear)
    || rawRows.find(r => r.district === state.selectedDrilldownDistrict)
    || rawRows[0] || {};

  const preg = Number(matchRow.pregnancies_registered) || 0;
  const numVal = indKey === "inst_del" 
    ? Number(matchRow.institutional_deliveries) || 0 
    : Number(matchRow.postnatal_check_48h) || 0;
  const calcRate = preg > 0 ? ((numVal / preg) * 100).toFixed(2) : "0.00";

  cardContainer.innerHTML = `
    <div class="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl p-5 md:p-6 text-white shadow-xl border border-slate-700/60">
      
      <!-- Top Badges & Header -->
      <div class="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-700/70">
        <div class="flex items-center gap-2.5">
          <span class="p-2 rounded-lg bg-blue-500/20 text-blue-400 border border-blue-500/30 text-base">
            <i class="fas ${indConfig.icon}"></i>
          </span>
          <div>
            <div class="flex items-center gap-2">
              <h3 class="text-lg md:text-xl font-bold tracking-tight text-white">
                ${isBoth ? "Institutional Delivery & PNC 48h Coverage Formulas" : indConfig.title}
              </h3>
              <span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-500/30 text-blue-300 border border-blue-400/40">
                Unit: ${unit}
              </span>
            </div>
            <p class="text-xs md:text-sm text-slate-300 mt-0.5">
              ${definition}
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <button type="button" onclick="document.getElementById('viewSheetsBtn').click()" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 transition">
            <i class="fas fa-table text-blue-400"></i>
            <span>View Source Sheets</span>
          </button>
        </div>
      </div>

      <!-- Formula Grid & Sources -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-5 mt-5">
        
        <!-- Left: Source Sheets & General Formula -->
        <div class="lg:col-span-6 space-y-4">
          <div>
            <div class="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
              <i class="fas fa-file-excel text-emerald-400"></i> Source Sheets in Excel
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <div class="bg-slate-800/80 rounded-lg p-2.5 border border-slate-700">
                <span class="text-xs text-blue-300 font-semibold block">Sheet 1: District Data</span>
                <span class="text-[11px] text-slate-400">Provides raw counts: <code class="text-slate-200 bg-slate-900 px-1 py-0.5 rounded">${indConfig.numeratorCol}</code> and <code class="text-slate-200 bg-slate-900 px-1 py-0.5 rounded">${indConfig.denominatorCol}</code></span>
              </div>
              <div class="bg-slate-800/80 rounded-lg p-2.5 border border-slate-700">
                <span class="text-xs text-emerald-300 font-semibold block">Sheet 2: Indicator Notes</span>
                <span class="text-[11px] text-slate-400">Provides indicator definition, official formula string, and unit metadata</span>
              </div>
            </div>
          </div>

          <div>
            <div class="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
              <i class="fas fa-square-root-variable text-blue-400"></i> Mathematical Expression
            </div>
            <div class="bg-slate-950/80 rounded-xl p-4 border border-slate-800 flex items-center justify-center font-mono text-sm md:text-base">
              <span class="text-blue-300 font-semibold mr-2">Coverage (%) = </span>
              <span class="inline-flex flex-col items-center mx-1 text-center">
                <span class="text-emerald-300 border-b border-slate-500 pb-1 px-2 font-medium">${indConfig.numeratorCol}</span>
                <span class="text-amber-300 pt-1 px-2 font-medium">${indConfig.denominatorCol}</span>
              </span>
              <span class="text-slate-300 ml-2 font-semibold">× 100</span>
            </div>
            <div class="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
              <i class="fas fa-circle-info text-blue-400"></i>
              <span>Excel Formula String: <code class="text-blue-200 bg-slate-900 px-1.5 py-0.5 rounded text-[11px]">${formulaRaw}</code></span>
            </div>
          </div>
        </div>

        <!-- Right: Live Step-by-Step Drilldown Calculator -->
        <div class="lg:col-span-6 bg-slate-800/60 rounded-xl p-4 border border-slate-700/80 flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between gap-2 mb-3">
              <div class="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <i class="fas fa-calculator text-amber-400"></i> Live Calculation Inspector
              </div>
              <div class="flex items-center gap-2">
                <label for="formulaDistrictSelect" class="text-xs text-slate-400">District:</label>
                <select id="formulaDistrictSelect" class="bg-slate-900 text-xs text-white border border-slate-700 rounded px-2 py-1 focus:outline-none focus:border-blue-500">
                  ${getAvailableDistricts().map(d => `<option value="${d}" ${d === state.selectedDrilldownDistrict ? 'selected' : ''}>${d}</option>`).join('')}
                </select>
              </div>
            </div>

            <!-- Calculation Steps -->
            <div class="bg-slate-950/90 rounded-lg p-3 border border-slate-800 text-xs space-y-2">
              <div class="flex justify-between items-center text-slate-400 pb-1 border-b border-slate-800">
                <span>District: <strong class="text-white">${state.selectedDrilldownDistrict}</strong> (${matchRow.year || activeYear})</span>
                <span class="text-slate-400">Source: <span class="text-blue-300 font-mono">District Data</span></span>
              </div>
              
              <div class="grid grid-cols-2 gap-2 text-slate-300 pt-1">
                <div class="bg-slate-900/80 p-2 rounded border border-slate-800">
                  <div class="text-[10px] text-slate-400 uppercase">${indConfig.numeratorLabel} (Numerator)</div>
                  <div class="text-base font-bold text-emerald-400">${numVal.toLocaleString()}</div>
                </div>
                <div class="bg-slate-900/80 p-2 rounded border border-slate-800">
                  <div class="text-[10px] text-slate-400 uppercase">${indConfig.denominatorLabel} (Denominator)</div>
                  <div class="text-base font-bold text-amber-400">${preg.toLocaleString()}</div>
                </div>
              </div>

              <!-- Computed Arithmetic -->
              <div class="p-2.5 rounded bg-blue-950/40 border border-blue-900/60 mt-2">
                <div class="text-[11px] text-blue-200 flex items-center justify-between">
                  <span>Step: (${numVal} ÷ ${preg}) × 100</span>
                  <span class="text-sm font-extrabold text-blue-300 font-mono">${calcRate}%</span>
                </div>
              </div>
            </div>
          </div>

          <div class="text-[11px] text-slate-400 mt-2 flex items-center justify-between">
            <span>Citation: <em>${sourceCitation}</em></span>
            <span class="text-emerald-400 font-mono text-[10px]">Verified ✓</span>
          </div>
        </div>

      </div>

    </div>
  `;

  // Bind change handler on newly created select
  const updatedSelect = document.getElementById("formulaDistrictSelect");
  if (updatedSelect) {
    updatedSelect.addEventListener("change", (e) => {
      state.selectedDrilldownDistrict = e.target.value;
      renderFormulaCard();
    });
  }
}

// Render KPI Metric Cards
function renderKpiCards(metrics) {
  const container = document.getElementById("kpiCardsContainer");
  if (!container) return;

  const isInst = state.selectedIndicator === "inst_del" || state.selectedIndicator === "both";
  const indKey = isInst ? "inst_coverage" : "pnc_coverage";
  const indTitle = isInst ? "Institutional Delivery" : "Postnatal Check (48h)";
  const numKey = isInst ? "institutional_deliveries" : "postnatal_check_48h";
  const totalNum = isInst ? metrics.totalInst : metrics.totalPnc;
  const avgCoverage = isInst ? metrics.aggregateInstCoverage : metrics.aggregatePncCoverage;

  const sortedRows = [...metrics.filteredRows].sort((a, b) => b[indKey] - a[indKey]);
  const topDistrict = sortedRows[0] || { district: "N/A", [indKey]: 0 };
  const lowestDistrict = sortedRows[sortedRows.length - 1] || { district: "N/A", [indKey]: 0 };
  const gap = (topDistrict[indKey] - lowestDistrict[indKey]).toFixed(1);

  container.innerHTML = `
    <!-- Top Performer -->
    <div class="glass-card rounded-xl p-4 relative overflow-hidden border-l-4 border-l-emerald-500">
      <div class="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase">
        <span>Top Performing District</span>
        <i class="fas fa-trophy text-emerald-500 text-sm"></i>
      </div>
      <div class="mt-2 flex items-baseline justify-between">
        <div>
          <span class="text-xl md:text-2xl font-bold text-slate-800">${topDistrict.district}</span>
          <span class="text-xs text-slate-500 block">Year ${metrics.activeYear}</span>
        </div>
        <div class="text-right">
          <span class="text-xl md:text-2xl font-extrabold text-emerald-600">${topDistrict[indKey]}%</span>
          <span class="text-[11px] text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200 block">Rank #1</span>
        </div>
      </div>
    </div>

    <!-- Lowest Performer / Improvement Opportunity -->
    <div class="glass-card rounded-xl p-4 relative overflow-hidden border-l-4 border-l-amber-500">
      <div class="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase">
        <span>Lowest Performing District</span>
        <i class="fas fa-triangle-exclamation text-amber-500 text-sm"></i>
      </div>
      <div class="mt-2 flex items-baseline justify-between">
        <div>
          <span class="text-xl md:text-2xl font-bold text-slate-800">${lowestDistrict.district}</span>
          <span class="text-xs text-slate-500 block">Gap vs Top: -${gap}% pts</span>
        </div>
        <div class="text-right">
          <span class="text-xl md:text-2xl font-extrabold text-amber-600">${lowestDistrict[indKey]}%</span>
          <span class="text-[11px] text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200 block">Focus Area</span>
        </div>
      </div>
    </div>

    <!-- Weighted Average Coverage -->
    <div class="glass-card rounded-xl p-4 relative overflow-hidden border-l-4 border-l-blue-500">
      <div class="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase">
        <span>Selected Group Average</span>
        <i class="fas fa-chart-pie text-blue-500 text-sm"></i>
      </div>
      <div class="mt-2 flex items-baseline justify-between">
        <div>
          <span class="text-xl md:text-2xl font-bold text-slate-800">${avgCoverage}%</span>
          <span class="text-xs text-slate-500 block">Weighted average</span>
        </div>
        <div class="text-right">
          <span class="text-xs text-blue-600 font-semibold">${metrics.filteredRows.length} Districts</span>
          <span class="text-[11px] text-slate-500 block">Year ${metrics.activeYear}</span>
        </div>
      </div>
    </div>

    <!-- Total Denominator & Numerator Volumes -->
    <div class="glass-card rounded-xl p-4 relative overflow-hidden border-l-4 border-l-indigo-500">
      <div class="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase">
        <span>Total Coverage Volume</span>
        <i class="fas fa-users-viewfinder text-indigo-500 text-sm"></i>
      </div>
      <div class="mt-2 flex items-baseline justify-between">
        <div>
          <span class="text-xl md:text-2xl font-bold text-slate-800">${totalNum.toLocaleString()}</span>
          <span class="text-xs text-slate-500 block">Total numerator</span>
        </div>
        <div class="text-right">
          <span class="text-xs text-slate-600 font-medium">out of ${metrics.totalPreg.toLocaleString()}</span>
          <span class="text-[11px] text-slate-500 block">pregnancies</span>
        </div>
      </div>
    </div>
  `;
}

// Render Charts
function renderCharts(metrics) {
  renderDistrictBarChart(metrics);
  renderTrendLineChart(metrics);
}

function renderDistrictBarChart(metrics) {
  const canvas = document.getElementById("districtBarChart");
  if (!canvas) return;

  if (state.charts.barChart) {
    state.charts.barChart.destroy();
  }

  const isBoth = state.selectedIndicator === "both";
  const rows = [...metrics.filteredRows];
  const labels = rows.map(r => r.district);

  let datasets = [];

  if (isBoth) {
    datasets = [
      {
        label: "Institutional Delivery Coverage (%)",
        data: rows.map(r => r.inst_coverage),
        backgroundColor: "rgba(37, 99, 235, 0.8)",
        borderColor: "#1d4ed8",
        borderWidth: 1.5,
        borderRadius: 6
      },
      {
        label: "Postnatal Check (48h) Coverage (%)",
        data: rows.map(r => r.pnc_coverage),
        backgroundColor: "rgba(5, 150, 105, 0.8)",
        borderColor: "#047857",
        borderWidth: 1.5,
        borderRadius: 6
      }
    ];
  } else {
    const isInst = state.selectedIndicator === "inst_del";
    const key = isInst ? "inst_coverage" : "pnc_coverage";
    const color = isInst ? "rgba(37, 99, 235, 0.85)" : "rgba(5, 150, 105, 0.85)";
    const border = isInst ? "#1d4ed8" : "#047857";
    const label = isInst ? "Institutional Delivery Coverage (%)" : "Postnatal Check (48h) Coverage (%)";

    datasets = [
      {
        label: label,
        data: rows.map(r => r[key]),
        backgroundColor: color,
        borderColor: border,
        borderWidth: 1.5,
        borderRadius: 6
      }
    ];
  }

  const ctx = canvas.getContext("2d");
  state.charts.barChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: isBoth,
          position: "top",
          labels: { font: { size: 12, family: "sans-serif" } }
        },
        tooltip: {
          backgroundColor: "#0f172a",
          padding: 10,
          titleFont: { size: 13, weight: "bold" },
          callbacks: {
            label: function (context) {
              const row = rows[context.dataIndex];
              const val = context.parsed.y;
              if (isBoth) {
                const label = context.dataset.label.includes("Institutional") ? "Inst. Deliveries" : "PNC (48h)";
                const num = context.dataset.label.includes("Institutional") ? row.institutional_deliveries : row.postnatal_check_48h;
                return `${label}: ${val}% (${num} / ${row.pregnancies_registered})`;
              } else {
                const isInst = state.selectedIndicator === "inst_del";
                const num = isInst ? row.institutional_deliveries : row.postnatal_check_48h;
                return `Coverage: ${val}% (${num} / ${row.pregnancies_registered} pregnancies)`;
              }
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          ticks: {
            callback: value => value + "%",
            font: { size: 11 }
          },
          grid: { color: "rgba(226, 232, 240, 0.6)" }
        },
        x: {
          grid: { display: false },
          ticks: { font: { size: 12, weight: "bold" } }
        }
      }
    }
  });
}

function renderTrendLineChart(metrics) {
  const canvas = document.getElementById("trendLineChart");
  if (!canvas) return;

  if (state.charts.trendChart) {
    state.charts.trendChart.destroy();
  }

  const years = getAvailableYears();
  const rawRows = metrics.allRows;
  const districts = Array.from(state.selectedDistricts);

  const colors = [
    { bg: "rgba(37, 99, 235, 0.1)", stroke: "#2563eb" },
    { bg: "rgba(16, 185, 129, 0.1)", stroke: "#10b981" },
    { bg: "rgba(245, 158, 11, 0.1)", stroke: "#f59e0b" },
    { bg: "rgba(139, 92, 246, 0.1)", stroke: "#8b5cf6" },
    { bg: "rgba(236, 72, 153, 0.1)", stroke: "#ec4899" }
  ];

  const indKey = state.selectedIndicator === "pnc_48h" ? "pnc_coverage" : "inst_coverage";

  const datasets = districts.map((district, idx) => {
    const color = colors[idx % colors.length];
    const dataPoints = years.map(y => {
      const match = rawRows.find(r => r.district === district && r.year === y);
      return match ? match[indKey] : null;
    });

    return {
      label: district,
      data: dataPoints,
      borderColor: color.stroke,
      backgroundColor: color.bg,
      borderWidth: 2.5,
      pointRadius: 4,
      pointHoverRadius: 6,
      pointBackgroundColor: color.stroke,
      tension: 0.2
    };
  });

  const ctx = canvas.getContext("2d");
  state.charts.trendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: years.map(y => `Year ${y}`),
      datasets: datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "top",
          labels: { font: { size: 12 } }
        },
        tooltip: {
          backgroundColor: "#0f172a",
          padding: 10,
          callbacks: {
            label: context => `${context.dataset.label}: ${context.parsed.y}%`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: false,
          min: 40,
          max: 100,
          ticks: {
            callback: val => val + "%",
            font: { size: 11 }
          },
          grid: { color: "rgba(226, 232, 240, 0.6)" }
        },
        x: {
          grid: { color: "rgba(226, 232, 240, 0.4)" },
          ticks: { font: { size: 11 } }
        }
      }
    }
  });
}

// Render Comparison Table
function renderTable(metrics = calculateMetrics()) {
  const tbody = document.getElementById("comparisonTableBody");
  if (!tbody) return;

  const rows = metrics.filteredRows;
  const isInst = state.selectedIndicator === "inst_del" || state.selectedIndicator === "both";
  const indKey = isInst ? "inst_coverage" : "pnc_coverage";
  const numKey = isInst ? "institutional_deliveries" : "postnatal_check_48h";
  const avgCoverage = isInst ? metrics.aggregateInstCoverage : metrics.aggregatePncCoverage;

  if (rows.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="text-center py-8 text-slate-400">
          No records match the selected filters.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = rows.map((row, idx) => {
    const coverage = row[indKey];
    const yoy = isInst ? row.yoyInst : row.yoyPnc;
    const diffAvg = (coverage - avgCoverage).toFixed(1);
    
    // Status color badge
    let badgeClass = "badge-blue";
    let statusLabel = "Moderate";
    let progressColor = "bg-blue-600";
    if (coverage >= 75) {
      badgeClass = "badge-green";
      statusLabel = "High (≥75%)";
      progressColor = "bg-emerald-600";
    } else if (coverage < 65) {
      badgeClass = "badge-amber";
      statusLabel = "Needs Focus (<65%)";
      progressColor = "bg-amber-600";
    }

    // YoY tag
    let yoyHtml = `<span class="text-slate-400 text-xs">-</span>`;
    if (yoy !== null) {
      if (yoy > 0) {
        yoyHtml = `<span class="text-emerald-600 text-xs font-semibold inline-flex items-center"><i class="fas fa-arrow-up text-[10px] mr-1"></i>+${yoy}%</span>`;
      } else if (yoy < 0) {
        yoyHtml = `<span class="text-rose-600 text-xs font-semibold inline-flex items-center"><i class="fas fa-arrow-down text-[10px] mr-1"></i>${yoy}%</span>`;
      } else {
        yoyHtml = `<span class="text-slate-500 text-xs font-medium">0.0%</span>`;
      }
    }

    // Rank Medal
    let rankHtml = `<span class="font-bold text-slate-600 text-sm">#${idx + 1}</span>`;
    if (idx === 0) {
      rankHtml = `<span class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-amber-100 text-amber-800 text-xs font-bold border border-amber-300">🥇 1</span>`;
    } else if (idx === 1) {
      rankHtml = `<span class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-slate-200 text-slate-800 text-xs font-bold border border-slate-300">🥈 2</span>`;
    } else if (idx === 2) {
      rankHtml = `<span class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-amber-50 text-amber-900 text-xs font-bold border border-amber-200">🥉 3</span>`;
    }

    return `
      <tr class="hover:bg-slate-50/80 transition border-b border-slate-200/80">
        <td class="px-4 py-3 text-center whitespace-nowrap">${rankHtml}</td>
        
        <td class="px-4 py-3 whitespace-nowrap">
          <div class="font-bold text-slate-900 text-sm flex items-center gap-1.5">
            <i class="fas fa-location-dot text-blue-500 text-xs"></i>
            <span>${row.district}</span>
          </div>
          <div class="text-[11px] text-slate-400">Year ${row.year}</div>
        </td>

        <td class="px-4 py-3 whitespace-nowrap text-right text-xs md:text-sm font-semibold text-slate-700">
          ${row[numKey].toLocaleString()}
        </td>

        <td class="px-4 py-3 whitespace-nowrap text-right text-xs md:text-sm text-slate-600">
          ${row.pregnancies_registered.toLocaleString()}
        </td>

        <td class="px-4 py-3 whitespace-nowrap">
          <div class="flex items-center gap-3">
            <span class="text-sm font-extrabold text-slate-900 w-12 text-right">${coverage.toFixed(1)}%</span>
            <div class="w-24 md:w-32 bg-slate-200 rounded-full h-2 overflow-hidden">
              <div class="${progressColor} h-full rounded-full" style="width: ${Math.min(coverage, 100)}%"></div>
            </div>
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold ${badgeClass}">
              ${statusLabel}
            </span>
          </div>
        </td>

        <td class="px-4 py-3 whitespace-nowrap text-center">
          ${yoyHtml}
        </td>

        <td class="px-4 py-3 whitespace-nowrap text-center">
          <button type="button" onclick="inspectDistrict('${row.district}')" class="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-100 hover:bg-blue-50 text-slate-700 hover:text-blue-700 text-xs font-medium border border-slate-200 hover:border-blue-300 transition">
            <i class="fas fa-calculator text-[10px]"></i>
            <span>Formula</span>
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

// Quick trigger to inspect a district calculation
window.inspectDistrict = function(districtName) {
  state.selectedDrilldownDistrict = districtName;
  renderFormulaCard();
  const card = document.getElementById("formulaCardSection");
  if (card) {
    card.scrollIntoView({ behavior: "smooth", block: "start" });
  }
};

// Render Source Sheets Explorer Modal
function renderRawSheetsModal() {
  const districtData = state.currentData.sheets["District Data"] || { headers: [], rows: [] };
  const notesData = state.currentData.sheets["Indicator Notes"] || { headers: [], rows: [] };

  // Render District Data table
  const distTableHead = document.getElementById("modalDistrictHead");
  const distTableBody = document.getElementById("modalDistrictBody");
  if (distTableHead && distTableBody) {
    distTableHead.innerHTML = `
      <tr>
        ${districtData.headers.map(h => `<th class="px-3 py-2 text-left text-xs font-bold text-slate-700 uppercase bg-slate-100 border-b border-slate-300">${h}</th>`).join('')}
      </tr>
    `;
    distTableBody.innerHTML = districtData.rows.map(r => `
      <tr class="border-b border-slate-200 hover:bg-slate-50 text-xs">
        ${districtData.headers.map(h => `<td class="px-3 py-2 text-slate-800 font-mono">${r[h] !== null && r[h] !== undefined ? r[h] : ''}</td>`).join('')}
      </tr>
    `).join('');
  }

  // Render Indicator Notes table
  const notesTableHead = document.getElementById("modalNotesHead");
  const notesTableBody = document.getElementById("modalNotesBody");
  if (notesTableHead && notesTableBody) {
    notesTableHead.innerHTML = `
      <tr>
        ${notesData.headers.map(h => `<th class="px-3 py-2 text-left text-xs font-bold text-slate-700 uppercase bg-slate-100 border-b border-slate-300">${h}</th>`).join('')}
      </tr>
    `;
    notesTableBody.innerHTML = notesData.rows.map(r => `
      <tr class="border-b border-slate-200 hover:bg-slate-50 text-xs">
        ${notesData.headers.map(h => `<td class="px-3 py-2 text-slate-800 ${h === 'formula' ? 'font-mono text-blue-700 bg-blue-50/50' : ''}">${r[h] !== null && r[h] !== undefined ? r[h] : '<span class="text-slate-400 italic">null</span>'}</td>`).join('')}
      </tr>
    `).join('');
  }
}

// Handle Custom Excel File Upload with SheetJS
function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function (e) {
    try {
      const data = new Uint8Array(e.target.result);
      const workbook = XLSX.read(data, { type: "array" });

      const parsedSheets = {};
      workbook.SheetNames.forEach(sheetName => {
        const worksheet = workbook.Sheets[sheetName];
        const rawJson = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
        if (rawJson.length > 0) {
          const headers = rawJson[0].map(h => String(h || "").trim());
          const rows = [];
          for (let i = 1; i < rawJson.length; i++) {
            const rowArr = rawJson[i];
            if (rowArr && rowArr.length > 0 && rowArr.some(c => c !== undefined && c !== null && c !== "")) {
              const rowObj = {};
              headers.forEach((h, idx) => {
                rowObj[h] = rowArr[idx] !== undefined ? rowArr[idx] : null;
              });
              rows.push(rowObj);
            }
          }
          parsedSheets[sheetName] = {
            headers: headers,
            rows: rows,
            total_rows: rows.length
          };
        }
      });

      if (!parsedSheets["District Data"]) {
        alert("The uploaded file does not contain a 'District Data' sheet. Please verify sheet names.");
        return;
      }

      state.currentData = {
        filename: file.name,
        sheets: parsedSheets
      };

      // Reset filter sets
      state.selectedDistricts = new Set(getAvailableDistricts());
      const years = getAvailableYears();
      state.selectedYear = years[years.length - 1] || 2023;
      state.selectedDrilldownDistrict = getAvailableDistricts()[0] || "";

      // Update filename badge
      const badge = document.getElementById("fileStatusBadge");
      if (badge) {
        badge.innerHTML = `<i class="fas fa-file-excel text-emerald-600 mr-1"></i> Uploaded: <strong>${file.name}</strong> (${workbook.SheetNames.length} Sheets)`;
      }

      refreshControls();
      renderAll();
      alert(`Successfully loaded ${file.name} with ${workbook.SheetNames.join(", ")}!`);
    } catch (err) {
      console.error("Excel parse error:", err);
      alert("Error parsing Excel file: " + err.message);
    }
  };
  reader.readAsArrayBuffer(file);
}

// Export Filtered Comparison to CSV
function exportCurrentDataToCsv() {
  const metrics = calculateMetrics();
  const rows = metrics.filteredRows;
  if (!rows || rows.length === 0) {
    alert("No data available to export.");
    return;
  }

  const isInst = state.selectedIndicator === "inst_del" || state.selectedIndicator === "both";
  const headers = ["District", "Year", "Registered Pregnancies", "Institutional Deliveries", "Inst Delivery Coverage (%)", "Postnatal Checks 48h", "PNC 48h Coverage (%)"];
  
  const csvRows = [headers.join(",")];
  rows.forEach(r => {
    csvRows.push([
      `"${r.district}"`,
      r.year,
      r.pregnancies_registered,
      r.institutional_deliveries,
      r.inst_coverage,
      r.postnatal_check_48h,
      r.pnc_coverage
    ].join(","));
  });

  const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `maternal_health_district_comparison_${state.selectedYear}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}
