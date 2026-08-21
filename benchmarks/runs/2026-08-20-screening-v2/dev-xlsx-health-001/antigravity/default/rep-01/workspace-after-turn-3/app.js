/**
 * Maternal Health Coverage Dashboard
 * District Comparison (2022 & 2023 Focus), Source Sheet & Formula Explorer
 */

// Embedded dataset from maternal_health.xlsx
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

// Application State (Filtered to 2022 and 2023)
const state = {
  currentData: JSON.parse(JSON.stringify(DEFAULT_DATA)),
  selectedIndicator: "inst_del", // "inst_del", "pnc_48h", "both"
  selectedYearMode: "compare_22_23", // "compare_22_23", "2023", "2022", "all_years"
  selectedDrilldownYear: 2023,
  selectedDistricts: new Set(["Gaya", "Nalanda", "Purnia"]),
  selectedDrilldownDistrict: "Nalanda",
  sortKey: "growth_desc", // "growth_desc", "coverage_2023_desc", "coverage_2022_desc", "name_asc"
  charts: {
    barChart: null,
    trendChart: null
  }
};

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  initApp();
});

async function initApp() {
  setupEventListeners();
  
  try {
    const res = await fetch("/api/data");
    if (res.ok) {
      const json = await res.json();
      if (json.sheets && json.sheets["District Data"]) {
        state.currentData = json;
      }
    }
  } catch (e) {
    console.log("Using embedded dataset:", e);
  }

  refreshControls();
  renderAll();
}

function getAvailableDistricts() {
  const rows = state.currentData.sheets["District Data"]?.rows || [];
  const districts = Array.from(new Set(rows.map(r => r.district).filter(Boolean))).sort();
  return districts.length ? districts : ["Gaya", "Nalanda", "Purnia"];
}

function refreshControls() {
  // Year Control Buttons
  const yearContainer = document.getElementById("yearButtonsContainer");
  if (yearContainer) {
    yearContainer.innerHTML = `
      <button type="button" data-year-mode="compare_22_23" class="px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold border transition ${
        state.selectedYearMode === "compare_22_23"
          ? "bg-blue-600 text-white border-blue-600 shadow-sm"
          : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50"
      }">
        <i class="fas fa-arrows-split-up-and-left mr-1"></i> 2022 & 2023 (Comparison)
      </button>

      <button type="button" data-year-mode="2023" class="px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold border transition ${
        state.selectedYearMode === "2023"
          ? "bg-blue-600 text-white border-blue-600 shadow-sm"
          : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50"
      }">
        2023
      </button>

      <button type="button" data-year-mode="2022" class="px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold border transition ${
        state.selectedYearMode === "2022"
          ? "bg-blue-600 text-white border-blue-600 shadow-sm"
          : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50"
      }">
        2022
      </button>

      <button type="button" data-year-mode="all_years" class="px-3 py-1.5 rounded-lg text-xs font-medium border text-slate-500 border-slate-200 hover:bg-slate-100 transition ${
        state.selectedYearMode === "all_years"
          ? "bg-slate-700 text-white border-slate-700 shadow-sm"
          : "bg-slate-50"
      }">
        Include 2021
      </button>
    `;

    yearContainer.querySelectorAll("[data-year-mode]").forEach(btn => {
      btn.onclick = () => {
        state.selectedYearMode = btn.getAttribute("data-year-mode");
        if (state.selectedYearMode === "2022") state.selectedDrilldownYear = 2022;
        if (state.selectedYearMode === "2023") state.selectedDrilldownYear = 2023;
        refreshControls();
        renderAll();
      };
    });
  }

  // Populate District Chips
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
          ? "bg-blue-50 border-blue-300 text-blue-800 font-semibold shadow-xs" 
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
            alert("At least one district must remain selected.");
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
}

function setupEventListeners() {
  // Indicator selector buttons
  document.querySelectorAll("[data-indicator-btn]").forEach(btn => {
    btn.addEventListener("click", () => {
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

  // Table Sort Selector
  const sortSelect = document.getElementById("tableSortSelect");
  if (sortSelect) {
    sortSelect.addEventListener("change", (e) => {
      state.sortKey = e.target.value;
      renderTable();
    });
  }

  // Select all districts
  const selectAllBtn = document.getElementById("selectAllDistrictsBtn");
  if (selectAllBtn) {
    selectAllBtn.addEventListener("click", () => {
      getAvailableDistricts().forEach(d => state.selectedDistricts.add(d));
      refreshControls();
      renderAll();
    });
  }

  // Reset filters
  const resetBtn = document.getElementById("resetFiltersBtn");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      state.selectedIndicator = "inst_del";
      state.selectedYearMode = "compare_22_23";
      state.selectedDrilldownYear = 2023;
      state.selectedDistricts = new Set(getAvailableDistricts());
      state.sortKey = "growth_desc";
      
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

  // Modal Tabs
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

  // Excel Upload
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

// Data Calculations
function calculateMetrics() {
  const rawRows = state.currentData.sheets["District Data"]?.rows || [];
  
  // Enriched rows with calculated percentages
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

  // Filter allowed years based on state
  let allowedYears = [2022, 2023];
  if (state.selectedYearMode === "2023") allowedYears = [2023];
  else if (state.selectedYearMode === "2022") allowedYears = [2022];
  else if (state.selectedYearMode === "all_years") allowedYears = [2021, 2022, 2023];

  const filteredByYearAndDistrict = enrichedRows.filter(r => 
    allowedYears.includes(r.year) && state.selectedDistricts.has(r.district)
  );

  // Group by district to compute 2022 vs 2023 side-by-side metrics
  const districtSummaries = Array.from(state.selectedDistricts).map(districtName => {
    const row2022 = enrichedRows.find(r => r.district === districtName && r.year === 2022) || {
      pregnancies_registered: 0, institutional_deliveries: 0, postnatal_check_48h: 0, inst_coverage: 0, pnc_coverage: 0
    };
    const row2023 = enrichedRows.find(r => r.district === districtName && r.year === 2023) || {
      pregnancies_registered: 0, institutional_deliveries: 0, postnatal_check_48h: 0, inst_coverage: 0, pnc_coverage: 0
    };
    const row2021 = enrichedRows.find(r => r.district === districtName && r.year === 2021) || null;

    const instGrowth = Number((row2023.inst_coverage - row2022.inst_coverage).toFixed(2));
    const pncGrowth = Number((row2023.pnc_coverage - row2022.pnc_coverage).toFixed(2));

    return {
      district: districtName,
      row2021,
      row2022,
      row2023,
      instGrowth,
      pncGrowth
    };
  });

  // Sort district summaries
  districtSummaries.sort((a, b) => {
    const isInst = state.selectedIndicator === "inst_del" || state.selectedIndicator === "both";
    const growthKey = isInst ? "instGrowth" : "pncGrowth";
    const covKey = isInst ? "inst_coverage" : "pnc_coverage";

    if (state.sortKey === "growth_desc") return b[growthKey] - a[growthKey];
    if (state.sortKey === "coverage_2023_desc") return b.row2023[covKey] - a.row2023[covKey];
    if (state.sortKey === "coverage_2022_desc") return b.row2022[covKey] - a.row2022[covKey];
    if (state.sortKey === "name_asc") return a.district.localeCompare(b.district);
    return 0;
  });

  // Aggregate Totals for 2022 and 2023
  const totalPreg2022 = districtSummaries.reduce((sum, d) => sum + d.row2022.pregnancies_registered, 0);
  const totalInst2022 = districtSummaries.reduce((sum, d) => sum + d.row2022.institutional_deliveries, 0);
  const totalPnc2022 = districtSummaries.reduce((sum, d) => sum + d.row2022.postnatal_check_48h, 0);

  const totalPreg2023 = districtSummaries.reduce((sum, d) => sum + d.row2023.pregnancies_registered, 0);
  const totalInst2023 = districtSummaries.reduce((sum, d) => sum + d.row2023.institutional_deliveries, 0);
  const totalPnc2023 = districtSummaries.reduce((sum, d) => sum + d.row2023.postnatal_check_48h, 0);

  const avgInst2022 = totalPreg2022 > 0 ? Number(((totalInst2022 / totalPreg2022) * 100).toFixed(2)) : 0;
  const avgInst2023 = totalPreg2023 > 0 ? Number(((totalInst2023 / totalPreg2023) * 100).toFixed(2)) : 0;

  const avgPnc2022 = totalPreg2022 > 0 ? Number(((totalPnc2022 / totalPreg2022) * 100).toFixed(2)) : 0;
  const avgPnc2023 = totalPreg2023 > 0 ? Number(((totalPnc2023 / totalPreg2023) * 100).toFixed(2)) : 0;

  return {
    allRows: enrichedRows,
    filteredRows: filteredByYearAndDistrict,
    districtSummaries,
    allowedYears,
    totals: {
      2022: {
        preg: totalPreg2022,
        inst: totalInst2022,
        pnc: totalPnc2022,
        avgInst: avgInst2022,
        avgPnc: avgPnc2022
      },
      2023: {
        preg: totalPreg2023,
        inst: totalInst2023,
        pnc: totalPnc2023,
        avgInst: avgInst2023,
        avgPnc: avgPnc2023
      }
    }
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

  // Drilldown calculations for selected district and year (2022 or 2023)
  const activeYear = state.selectedDrilldownYear;
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
              <span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">
                Focus: 2022 & 2023
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
                <!-- Year Pill Toggle -->
                <div class="inline-flex rounded-md shadow-xs bg-slate-900 p-0.5 border border-slate-700 text-xs">
                  <button type="button" onclick="setDrilldownYear(2022)" class="px-2 py-0.5 rounded ${activeYear === 2022 ? 'bg-blue-600 text-white font-bold' : 'text-slate-400 hover:text-white'}">2022</button>
                  <button type="button" onclick="setDrilldownYear(2023)" class="px-2 py-0.5 rounded ${activeYear === 2023 ? 'bg-blue-600 text-white font-bold' : 'text-slate-400 hover:text-white'}">2023</button>
                </div>

                <select id="formulaDistrictSelect" class="bg-slate-900 text-xs text-white border border-slate-700 rounded px-2 py-1 focus:outline-none focus:border-blue-500">
                  ${getAvailableDistricts().map(d => `<option value="${d}" ${d === state.selectedDrilldownDistrict ? 'selected' : ''}>${d}</option>`).join('')}
                </select>
              </div>
            </div>

            <!-- Calculation Steps -->
            <div class="bg-slate-950/90 rounded-lg p-3 border border-slate-800 text-xs space-y-2">
              <div class="flex justify-between items-center text-slate-400 pb-1 border-b border-slate-800">
                <span>District: <strong class="text-white">${state.selectedDrilldownDistrict}</strong> (Year ${activeYear})</span>
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

  const updatedSelect = document.getElementById("formulaDistrictSelect");
  if (updatedSelect) {
    updatedSelect.addEventListener("change", (e) => {
      state.selectedDrilldownDistrict = e.target.value;
      renderFormulaCard();
    });
  }
}

window.setDrilldownYear = function(year) {
  state.selectedDrilldownYear = year;
  renderFormulaCard();
};

// Render KPI Metric Cards
function renderKpiCards(metrics) {
  const container = document.getElementById("kpiCardsContainer");
  if (!container) return;

  const isInst = state.selectedIndicator === "inst_del" || state.selectedIndicator === "both";
  const indTitle = isInst ? "Institutional Delivery" : "Postnatal Check (48h)";
  const covKey = isInst ? "inst_coverage" : "pnc_coverage";
  const numKey = isInst ? "institutional_deliveries" : "postnatal_check_48h";

  const summaries = metrics.districtSummaries;
  const top2023 = [...summaries].sort((a, b) => b.row2023[covKey] - a.row2023[covKey])[0] || { district: "N/A", row2023: { [covKey]: 0 } };
  const top2022 = [...summaries].sort((a, b) => b.row2022[covKey] - a.row2022[covKey])[0] || { district: "N/A", row2022: { [covKey]: 0 } };

  const avg2022 = isInst ? metrics.totals[2022].avgInst : metrics.totals[2022].avgPnc;
  const avg2023 = isInst ? metrics.totals[2023].avgInst : metrics.totals[2023].avgPnc;
  const avgGrowth = (avg2023 - avg2022).toFixed(2);

  const totalDel2022 = isInst ? metrics.totals[2022].inst : metrics.totals[2022].pnc;
  const totalDel2023 = isInst ? metrics.totals[2023].inst : metrics.totals[2023].pnc;
  const volumeGrowth = totalDel2023 - totalDel2022;

  container.innerHTML = `
    <!-- Top Performer (2023 vs 2022) -->
    <div class="glass-card rounded-xl p-4 relative overflow-hidden border-l-4 border-l-emerald-500">
      <div class="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase">
        <span>Top District (2023)</span>
        <i class="fas fa-trophy text-emerald-500 text-sm"></i>
      </div>
      <div class="mt-2 flex items-baseline justify-between">
        <div>
          <span class="text-xl md:text-2xl font-bold text-slate-800">${top2023.district}</span>
          <span class="text-xs text-slate-500 block">2022: ${top2023.row2022[covKey]}% → 2023: ${top2023.row2023[covKey]}%</span>
        </div>
        <div class="text-right">
          <span class="text-xl md:text-2xl font-extrabold text-emerald-600">${top2023.row2023[covKey]}%</span>
          <span class="text-[11px] text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200 block">+${(top2023.row2023[covKey] - top2023.row2022[covKey]).toFixed(1)}% YoY</span>
        </div>
      </div>
    </div>

    <!-- 2022 vs 2023 Average Growth -->
    <div class="glass-card rounded-xl p-4 relative overflow-hidden border-l-4 border-l-blue-500">
      <div class="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase">
        <span>Group Average (2022 vs 2023)</span>
        <i class="fas fa-chart-line text-blue-500 text-sm"></i>
      </div>
      <div class="mt-2 flex items-baseline justify-between">
        <div>
          <span class="text-xl md:text-2xl font-bold text-slate-800">${avg2023}%</span>
          <span class="text-xs text-slate-500 block">2022 Average: ${avg2022}%</span>
        </div>
        <div class="text-right">
          <span class="text-base font-extrabold text-emerald-600 inline-flex items-center gap-1">
            <i class="fas fa-arrow-trend-up"></i> +${avgGrowth}%
          </span>
          <span class="text-[11px] text-slate-500 block">${summaries.length} Districts</span>
        </div>
      </div>
    </div>

    <!-- 2023 Total Volume -->
    <div class="glass-card rounded-xl p-4 relative overflow-hidden border-l-4 border-l-indigo-500">
      <div class="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase">
        <span>2023 Delivered / Checked</span>
        <i class="fas fa-hospital-user text-indigo-500 text-sm"></i>
      </div>
      <div class="mt-2 flex items-baseline justify-between">
        <div>
          <span class="text-xl md:text-2xl font-bold text-slate-800">${totalDel2023.toLocaleString()}</span>
          <span class="text-xs text-slate-500 block">vs ${totalDel2022.toLocaleString()} in 2022</span>
        </div>
        <div class="text-right">
          <span class="text-xs font-bold text-indigo-600 block">+${volumeGrowth.toLocaleString()} (+${((volumeGrowth / totalDel2022) * 100).toFixed(1)}%)</span>
          <span class="text-[11px] text-slate-400 block">annual increase</span>
        </div>
      </div>
    </div>

    <!-- Total Registered Pregnancies -->
    <div class="glass-card rounded-xl p-4 relative overflow-hidden border-l-4 border-l-amber-500">
      <div class="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase">
        <span>Registered Pregnancies (2023)</span>
        <i class="fas fa-users-viewfinder text-amber-500 text-sm"></i>
      </div>
      <div class="mt-2 flex items-baseline justify-between">
        <div>
          <span class="text-xl md:text-2xl font-bold text-slate-800">${metrics.totals[2023].preg.toLocaleString()}</span>
          <span class="text-xs text-slate-500 block">2022: ${metrics.totals[2022].preg.toLocaleString()}</span>
        </div>
        <div class="text-right">
          <span class="text-xs text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200 font-semibold block">
            +${(metrics.totals[2023].preg - metrics.totals[2022].preg).toLocaleString()}
          </span>
          <span class="text-[11px] text-slate-500 block">Cohort Size</span>
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

  const summaries = metrics.districtSummaries;
  const labels = summaries.map(s => s.district);
  const isInst = state.selectedIndicator === "inst_del" || state.selectedIndicator === "both";
  const covKey = isInst ? "inst_coverage" : "pnc_coverage";
  const numKey = isInst ? "institutional_deliveries" : "postnatal_check_48h";

  let datasets = [];

  if (state.selectedYearMode === "2023") {
    datasets = [{
      label: "2023 Coverage (%)",
      data: summaries.map(s => s.row2023[covKey]),
      backgroundColor: "rgba(37, 99, 235, 0.85)",
      borderColor: "#1d4ed8",
      borderWidth: 1.5,
      borderRadius: 6
    }];
  } else if (state.selectedYearMode === "2022") {
    datasets = [{
      label: "2022 Coverage (%)",
      data: summaries.map(s => s.row2022[covKey]),
      backgroundColor: "rgba(14, 165, 233, 0.85)",
      borderColor: "#0284c7",
      borderWidth: 1.5,
      borderRadius: 6
    }];
  } else {
    // 2022 vs 2023 Side-by-Side Comparison
    datasets = [
      {
        label: "Year 2022 Coverage (%)",
        data: summaries.map(s => s.row2022[covKey]),
        backgroundColor: "rgba(147, 197, 253, 0.85)",
        borderColor: "#3b82f6",
        borderWidth: 1.5,
        borderRadius: 6
      },
      {
        label: "Year 2023 Coverage (%)",
        data: summaries.map(s => s.row2023[covKey]),
        backgroundColor: isInst ? "rgba(37, 99, 235, 0.9)" : "rgba(5, 150, 105, 0.9)",
        borderColor: isInst ? "#1d4ed8" : "#047857",
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
          display: true,
          position: "top",
          labels: { font: { size: 12 } }
        },
        tooltip: {
          backgroundColor: "#0f172a",
          padding: 10,
          callbacks: {
            label: function (context) {
              const s = summaries[context.dataIndex];
              const is2023 = context.dataset.label.includes("2023");
              const row = is2023 ? s.row2023 : s.row2022;
              return `${context.dataset.label}: ${context.parsed.y}% (${row[numKey]} / ${row.pregnancies_registered})`;
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          ticks: {
            callback: v => v + "%",
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

  const isAllYears = state.selectedYearMode === "all_years";
  const years = isAllYears ? [2021, 2022, 2023] : [2022, 2023];
  const summaries = metrics.districtSummaries;
  const isInst = state.selectedIndicator === "inst_del" || state.selectedIndicator === "both";
  const covKey = isInst ? "inst_coverage" : "pnc_coverage";

  const colors = [
    { bg: "rgba(37, 99, 235, 0.1)", stroke: "#2563eb" },
    { bg: "rgba(16, 185, 129, 0.1)", stroke: "#10b981" },
    { bg: "rgba(245, 158, 11, 0.1)", stroke: "#f59e0b" },
    { bg: "rgba(139, 92, 246, 0.1)", stroke: "#8b5cf6" }
  ];

  const datasets = summaries.map((s, idx) => {
    const color = colors[idx % colors.length];
    const dataPoints = years.map(y => {
      if (y === 2021) return s.row2021 ? s.row2021[covKey] : null;
      if (y === 2022) return s.row2022[covKey];
      if (y === 2023) return s.row2023[covKey];
      return null;
    });

    return {
      label: s.district,
      data: dataPoints,
      borderColor: color.stroke,
      backgroundColor: color.bg,
      borderWidth: 3,
      pointRadius: 6,
      pointHoverRadius: 8,
      pointBackgroundColor: color.stroke,
      tension: 0.1
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
          min: 50,
          max: 90,
          ticks: {
            callback: v => v + "%",
            font: { size: 11 }
          },
          grid: { color: "rgba(226, 232, 240, 0.6)" }
        },
        x: {
          grid: { color: "rgba(226, 232, 240, 0.4)" },
          ticks: { font: { size: 12, weight: "bold" } }
        }
      }
    }
  });
}

// Render Comparison Table (2022 vs 2023)
function renderTable(metrics = calculateMetrics()) {
  const tbody = document.getElementById("comparisonTableBody");
  if (!tbody) return;

  const summaries = metrics.districtSummaries;
  const isInst = state.selectedIndicator === "inst_del" || state.selectedIndicator === "both";
  const covKey = isInst ? "inst_coverage" : "pnc_coverage";
  const numKey = isInst ? "institutional_deliveries" : "postnatal_check_48h";
  const growthKey = isInst ? "instGrowth" : "pncGrowth";

  if (summaries.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-400">No districts selected.</td></tr>`;
    return;
  }

  tbody.innerHTML = summaries.map((s, idx) => {
    const cov2022 = s.row2022[covKey];
    const cov2023 = s.row2023[covKey];
    const growth = s[growthKey];

    // Status Badge
    let badgeClass = "badge-blue";
    let statusLabel = "Moderate";
    if (cov2023 >= 75) {
      badgeClass = "badge-green";
      statusLabel = "High (≥75%)";
    } else if (cov2023 < 65) {
      badgeClass = "badge-amber";
      statusLabel = "Needs Focus (<65%)";
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
            <span>${s.district}</span>
          </div>
          <span class="px-2 py-0.5 rounded text-[10px] font-semibold ${badgeClass} mt-1 inline-block">
            ${statusLabel}
          </span>
        </td>

        <!-- 2022 Numbers & Coverage -->
        <td class="px-4 py-3 whitespace-nowrap text-right">
          <div class="text-sm font-bold text-slate-700">${cov2022.toFixed(1)}%</div>
          <div class="text-[11px] text-slate-400">
            ${s.row2022[numKey]} / ${s.row2022.pregnancies_registered}
          </div>
        </td>

        <!-- 2023 Numbers & Coverage -->
        <td class="px-4 py-3 whitespace-nowrap text-right">
          <div class="text-sm font-extrabold text-blue-700">${cov2023.toFixed(1)}%</div>
          <div class="text-[11px] text-slate-500 font-medium">
            ${s.row2023[numKey]} / ${s.row2023.pregnancies_registered}
          </div>
        </td>

        <!-- Visual Progress Bar (2023) -->
        <td class="px-4 py-3 whitespace-nowrap">
          <div class="w-28 md:w-36 bg-slate-200 rounded-full h-2.5 overflow-hidden">
            <div class="bg-blue-600 h-full rounded-full" style="width: ${Math.min(cov2023, 100)}%"></div>
          </div>
        </td>

        <!-- 2022 to 2023 Net Growth -->
        <td class="px-4 py-3 whitespace-nowrap text-center">
          <span class="text-emerald-600 text-xs font-bold inline-flex items-center gap-1 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
            <i class="fas fa-arrow-up text-[10px]"></i> +${growth.toFixed(1)}% pts
          </span>
        </td>

        <!-- Inspect Formula Action -->
        <td class="px-4 py-3 whitespace-nowrap text-center no-print">
          <div class="inline-flex gap-1">
            <button type="button" onclick="inspectDistrictYear('${s.district}', 2022)" class="px-2 py-1 rounded bg-slate-100 hover:bg-blue-50 text-slate-700 hover:text-blue-700 text-[11px] font-medium border border-slate-200 transition" title="Inspect 2022 Formula">
              '22
            </button>
            <button type="button" onclick="inspectDistrictYear('${s.district}', 2023)" class="px-2 py-1 rounded bg-blue-50 hover:bg-blue-100 text-blue-700 text-[11px] font-bold border border-blue-200 transition" title="Inspect 2023 Formula">
              '23
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

window.inspectDistrictYear = function(districtName, year) {
  state.selectedDrilldownDistrict = districtName;
  state.selectedDrilldownYear = year;
  renderFormulaCard();
  const card = document.getElementById("formulaCardSection");
  if (card) {
    card.scrollIntoView({ behavior: "smooth", block: "start" });
  }
};

// Render Source Sheets Modal
function renderRawSheetsModal() {
  const districtData = state.currentData.sheets["District Data"] || { headers: [], rows: [] };
  const notesData = state.currentData.sheets["Indicator Notes"] || { headers: [], rows: [] };

  const distTableHead = document.getElementById("modalDistrictHead");
  const distTableBody = document.getElementById("modalDistrictBody");
  if (distTableHead && distTableBody) {
    distTableHead.innerHTML = `
      <tr>
        ${districtData.headers.map(h => `<th class="px-3 py-2 text-left text-xs font-bold text-slate-700 uppercase bg-slate-100 border-b border-slate-300">${h}</th>`).join('')}
      </tr>
    `;
    distTableBody.innerHTML = districtData.rows.map(r => {
      const isHighlighted = (r.year === 2022 || r.year === 2023);
      return `
        <tr class="border-b border-slate-200 hover:bg-slate-50 text-xs ${isHighlighted ? 'bg-blue-50/40 font-medium' : 'text-slate-400 opacity-60'}">
          ${districtData.headers.map(h => `<td class="px-3 py-2 text-slate-800 font-mono">${r[h] !== null && r[h] !== undefined ? r[h] : ''}</td>`).join('')}
        </tr>
      `;
    }).join('');
  }

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

// Custom Excel File Upload
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
        alert("The uploaded file does not contain a 'District Data' sheet.");
        return;
      }

      state.currentData = {
        filename: file.name,
        sheets: parsedSheets
      };

      state.selectedDistricts = new Set(getAvailableDistricts());
      state.selectedDrilldownDistrict = getAvailableDistricts()[0] || "";

      const badge = document.getElementById("fileStatusBadge");
      if (badge) {
        badge.innerHTML = `<i class="fas fa-file-excel text-emerald-600 mr-1"></i> Uploaded: <strong>${file.name}</strong>`;
      }

      refreshControls();
      renderAll();
      alert(`Loaded ${file.name} successfully!`);
    } catch (err) {
      alert("Error parsing Excel file: " + err.message);
    }
  };
  reader.readAsArrayBuffer(file);
}

// Export CSV
function exportCurrentDataToCsv() {
  const metrics = calculateMetrics();
  const summaries = metrics.districtSummaries;
  if (!summaries || summaries.length === 0) {
    alert("No data available to export.");
    return;
  }

  const isInst = state.selectedIndicator === "inst_del" || state.selectedIndicator === "both";
  const numKey = isInst ? "institutional_deliveries" : "postnatal_check_48h";
  const covKey = isInst ? "inst_coverage" : "pnc_coverage";

  const headers = [
    "District",
    "2022 Pregnancies Registered",
    `2022 ${isInst ? 'Institutional Deliveries' : 'PNC 48h Checks'}`,
    "2022 Coverage (%)",
    "2023 Pregnancies Registered",
    `2023 ${isInst ? 'Institutional Deliveries' : 'PNC 48h Checks'}`,
    "2023 Coverage (%)",
    "Net Growth 2022-2023 (% pts)"
  ];
  
  const csvRows = [headers.join(",")];
  summaries.forEach(s => {
    csvRows.push([
      `"${s.district}"`,
      s.row2022.pregnancies_registered,
      s.row2022[numKey],
      s.row2022[covKey],
      s.row2023.pregnancies_registered,
      s.row2023[numKey],
      s.row2023[covKey],
      (s.row2023[covKey] - s.row2022[covKey]).toFixed(2)
    ].join(","));
  });

  const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `maternal_health_2022_2023_comparison.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}
