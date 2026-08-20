/**
 * Women's Vocational Training & Employment Tracker
 * Application Logic, Math Formulas, Comparisons & Dynamic Charts
 */

// Application State
const state = {
  data: typeof INITIAL_DATA !== "undefined" ? [...INITIAL_DATA] : [],
  activeTab: "overview", // "overview" | "compare" | "trends"
  selectedYear: 2025,
  compareYearA: 2021,
  compareYearB: 2025,
  selectedDistrict: "all",
  selectedSector: "all",
  searchQuery: "",
  sortColumn: "completionRate",
  sortOrder: "desc",
  charts: {}
};

// Math Formula Calculations
function calculateMetrics(records) {
  if (!records || records.length === 0) {
    return {
      enrolled: 0,
      completed: 0,
      employed6m: 0,
      completionRate: 0,
      employmentRate: 0,
      placementYield: 0,
      avgWage: 0,
      recordCount: 0
    };
  }

  const enrolled = records.reduce((sum, r) => sum + (Number(r.enrolled) || 0), 0);
  const completed = records.reduce((sum, r) => sum + (Number(r.completed) || 0), 0);
  const employed6m = records.reduce((sum, r) => sum + (Number(r.employed6m) || 0), 0);
  const totalWage = records.reduce((sum, r) => sum + ((Number(r.avgWage) || 0) * (Number(r.employed6m) || 0)), 0);

  // Formula 1: Training Completion Rate = (Completed / Enrolled) * 100
  const completionRate = enrolled > 0 ? (completed / enrolled) * 100 : 0;

  // Formula 2: 6-Month Employment Rate = (Employed at 6 Months / Completed) * 100
  const employmentRate = completed > 0 ? (employed6m / completed) * 100 : 0;

  // Overall Placement Yield = (Employed at 6 Months / Enrolled) * 100
  const placementYield = enrolled > 0 ? (employed6m / enrolled) * 100 : 0;

  const avgWage = employed6m > 0 ? totalWage / employed6m : 0;

  return {
    enrolled,
    completed,
    employed6m,
    completionRate: Number(completionRate.toFixed(1)),
    employmentRate: Number(employmentRate.toFixed(1)),
    placementYield: Number(placementYield.toFixed(1)),
    avgWage: Math.round(avgWage),
    recordCount: records.length
  };
}

// Compute individual record augmented metrics
function augmentRecord(r) {
  const completionRate = r.enrolled > 0 ? (r.completed / r.enrolled) * 100 : 0;
  const employmentRate = r.completed > 0 ? (r.employed6m / r.completed) * 100 : 0;
  const placementYield = r.enrolled > 0 ? (r.employed6m / r.enrolled) * 100 : 0;

  return {
    ...r,
    completionRate: Number(completionRate.toFixed(1)),
    employmentRate: Number(employmentRate.toFixed(1)),
    placementYield: Number(placementYield.toFixed(1))
  };
}

// Filter dataset based on current state
function getFilteredData() {
  return state.data
    .filter(r => {
      if (state.activeTab === "overview") {
        if (state.selectedYear !== "all" && r.year !== Number(state.selectedYear)) return false;
      }
      if (state.selectedDistrict !== "all" && r.district !== state.selectedDistrict) return false;
      if (state.selectedSector !== "all" && r.sector !== state.selectedSector) return false;
      if (state.searchQuery) {
        const q = state.searchQuery.toLowerCase();
        return r.district.toLowerCase().includes(q) || (r.sector && r.sector.toLowerCase().includes(q));
      }
      return true;
    })
    .map(augmentRecord);
}

// Initialize Dropdowns
function populateFilters() {
  const years = [...new Set(state.data.map(d => d.year))].sort((a, b) => b - a);
  const districts = [...new Set(state.data.map(d => d.district))].sort();
  const sectors = [...new Set(state.data.map(d => d.sector).filter(Boolean))].sort();

  // Year filter (Single Overview)
  const yearSelect = document.getElementById("filter-year");
  if (yearSelect) {
    yearSelect.innerHTML = years.map(y => `<option value="${y}" ${y === state.selectedYear ? "selected" : ""}>${y}</option>`).join("");
  }

  // Compare Year Selectors
  const compareA = document.getElementById("compare-year-a");
  const compareB = document.getElementById("compare-year-b");
  if (compareA && compareB) {
    compareA.innerHTML = years.map(y => `<option value="${y}" ${y === state.compareYearA ? "selected" : ""}>${y}</option>`).join("");
    compareB.innerHTML = years.map(y => `<option value="${y}" ${y === state.compareYearB ? "selected" : ""}>${y}</option>`).join("");
  }

  // District filter
  const districtSelect = document.getElementById("filter-district");
  if (districtSelect) {
    districtSelect.innerHTML = `<option value="all">All Districts (${districts.length})</option>` +
      districts.map(d => `<option value="${d}" ${d === state.selectedDistrict ? "selected" : ""}>${d}</option>`).join("");
  }

  // Sector filter
  const sectorSelect = document.getElementById("filter-sector");
  if (sectorSelect) {
    sectorSelect.innerHTML = `<option value="all">All Sectors (${sectors.length})</option>` +
      sectors.map(s => `<option value="${s}" ${s === state.selectedSector ? "selected" : ""}>${s}</option>`).join("");
  }

  // Form modal district options
  const formDistrict = document.getElementById("new-district");
  if (formDistrict) {
    formDistrict.innerHTML = districts.map(d => `<option value="${d}">${d}</option>`).join("") +
      `<option value="__custom__">+ Add New District...</option>`;
  }
}

// Render Formula Banner with live plugged-in values
function renderFormulaCard(metrics) {
  const formula1Live = document.getElementById("formula1-live-values");
  const formula2Live = document.getElementById("formula2-live-values");
  const formulaYieldLive = document.getElementById("formula-yield-live-values");

  if (formula1Live) {
    formula1Live.innerHTML = `
      <div class="flex items-center justify-between text-xs text-blue-700 dark:text-blue-300 font-mono bg-blue-50 dark:bg-blue-900/30 p-2.5 rounded-lg border border-blue-200 dark:border-blue-800">
        <span>Completed: <strong>${metrics.completed.toLocaleString()}</strong> ÷ Enrolled: <strong>${metrics.enrolled.toLocaleString()}</strong></span>
        <span class="text-sm font-bold bg-blue-600 text-white px-2 py-0.5 rounded shadow-sm">= ${metrics.completionRate}%</span>
      </div>
    `;
  }

  if (formula2Live) {
    formula2Live.innerHTML = `
      <div class="flex items-center justify-between text-xs text-emerald-700 dark:text-emerald-300 font-mono bg-emerald-50 dark:bg-emerald-900/30 p-2.5 rounded-lg border border-emerald-200 dark:border-emerald-800">
        <span>Employed (6M): <strong>${metrics.employed6m.toLocaleString()}</strong> ÷ Completed: <strong>${metrics.completed.toLocaleString()}</strong></span>
        <span class="text-sm font-bold bg-emerald-600 text-white px-2 py-0.5 rounded shadow-sm">= ${metrics.employmentRate}%</span>
      </div>
    `;
  }

  if (formulaYieldLive) {
    formulaYieldLive.innerHTML = `
      <div class="flex items-center justify-between text-xs text-purple-700 dark:text-purple-300 font-mono bg-purple-50 dark:bg-purple-900/30 p-2.5 rounded-lg border border-purple-200 dark:border-purple-800">
        <span>Employed (6M): <strong>${metrics.employed6m.toLocaleString()}</strong> ÷ Enrolled: <strong>${metrics.enrolled.toLocaleString()}</strong></span>
        <span class="text-sm font-bold bg-purple-600 text-white px-2 py-0.5 rounded shadow-sm">= ${metrics.placementYield}%</span>
      </div>
    `;
  }
}

// Render KPI Summary Cards
function renderKPIs() {
  const kpiContainer = document.getElementById("kpi-container");
  if (!kpiContainer) return;

  if (state.activeTab === "compare") {
    renderComparisonKPIs(kpiContainer);
  } else {
    renderStandardKPIs(kpiContainer);
  }
}

function renderStandardKPIs(container) {
  const filtered = getFilteredData();
  const metrics = calculateMetrics(filtered);
  renderFormulaCard(metrics);

  const currentYearNum = Number(state.selectedYear);
  const priorYearData = state.data.filter(r => r.year === currentYearNum - 1);
  const priorMetrics = calculateMetrics(priorYearData);

  const deltaCompletion = priorMetrics.recordCount > 0 ? (metrics.completionRate - priorMetrics.completionRate).toFixed(1) : null;
  const deltaEmployment = priorMetrics.recordCount > 0 ? (metrics.employmentRate - priorMetrics.employmentRate).toFixed(1) : null;

  container.innerHTML = `
    <!-- Card 1: Total Enrolled -->
    <div class="kpi-card bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm relative overflow-hidden">
      <div class="flex items-center justify-between">
        <span class="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Total Enrolled Women</span>
        <span class="p-2 bg-indigo-50 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400 rounded-lg">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
        </span>
      </div>
      <div class="mt-3">
        <div class="text-3xl font-extrabold text-slate-900 dark:text-white">${metrics.enrolled.toLocaleString()}</div>
        <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Across ${metrics.recordCount} district units in ${state.selectedYear}</p>
      </div>
    </div>

    <!-- Card 2: Training Completed & Rate -->
    <div class="kpi-card bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm relative overflow-hidden">
      <div class="flex items-center justify-between">
        <span class="text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">Completion Rate (Formula 1)</span>
        <span class="p-2 bg-blue-50 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 rounded-lg">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        </span>
      </div>
      <div class="mt-3 flex items-baseline justify-between">
        <div class="text-3xl font-extrabold text-blue-600 dark:text-blue-400">${metrics.completionRate}%</div>
        ${deltaCompletion !== null ? `
          <span class="inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded-full ${Number(deltaCompletion) >= 0 ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300" : "bg-rose-100 text-rose-800 dark:bg-rose-900/50 dark:text-rose-300"}">
            ${Number(deltaCompletion) >= 0 ? "▲ +" : "▼ "}${deltaCompletion}% vs ${currentYearNum - 1}
          </span>
        ` : ""}
      </div>
      <p class="text-xs text-slate-500 dark:text-slate-400 mt-1"><strong>${metrics.completed.toLocaleString()}</strong> women successfully completed training</p>
    </div>

    <!-- Card 3: 6-Month Employment & Rate -->
    <div class="kpi-card bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm relative overflow-hidden">
      <div class="flex items-center justify-between">
        <span class="text-xs font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">6-Month Employment (Formula 2)</span>
        <span class="p-2 bg-emerald-50 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400 rounded-lg">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
        </span>
      </div>
      <div class="mt-3 flex items-baseline justify-between">
        <div class="text-3xl font-extrabold text-emerald-600 dark:text-emerald-400">${metrics.employmentRate}%</div>
        ${deltaEmployment !== null ? `
          <span class="inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded-full ${Number(deltaEmployment) >= 0 ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300" : "bg-rose-100 text-rose-800 dark:bg-rose-900/50 dark:text-rose-300"}">
            ${Number(deltaEmployment) >= 0 ? "▲ +" : "▼ "}${deltaEmployment}% vs ${currentYearNum - 1}
          </span>
        ` : ""}
      </div>
      <p class="text-xs text-slate-500 dark:text-slate-400 mt-1"><strong>${metrics.employed6m.toLocaleString()}</strong> women employed after 6 months</p>
    </div>

    <!-- Card 4: Overall Pipeline Yield & Avg Wage -->
    <div class="kpi-card bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm relative overflow-hidden">
      <div class="flex items-center justify-between">
        <span class="text-xs font-semibold uppercase tracking-wider text-purple-600 dark:text-purple-400">Total Placement Yield</span>
        <span class="p-2 bg-purple-50 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400 rounded-lg">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>
        </span>
      </div>
      <div class="mt-3 flex items-baseline justify-between">
        <div class="text-3xl font-extrabold text-purple-600 dark:text-purple-400">${metrics.placementYield}%</div>
        <span class="text-xs font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded">
          Avg Wage: $${metrics.avgWage}/mo
        </span>
      </div>
      <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Employed Women ÷ All Initially Enrolled</p>
    </div>
  `;
}

function renderComparisonKPIs(container) {
  const yearA = Number(state.compareYearA);
  const yearB = Number(state.compareYearB);

  const dataA = state.data.filter(r => r.year === yearA);
  const dataB = state.data.filter(r => r.year === yearB);

  const metricsA = calculateMetrics(dataA);
  const metricsB = calculateMetrics(dataB);

  const deltaCompletion = (metricsB.completionRate - metricsA.completionRate).toFixed(1);
  const deltaEmployment = (metricsB.employmentRate - metricsA.employmentRate).toFixed(1);
  const deltaEnrolled = metricsB.enrolled - metricsA.enrolled;
  const deltaEmployed = metricsB.employed6m - metricsA.employed6m;

  renderFormulaCard(metricsB);

  container.innerHTML = `
    <!-- Card 1: Enrolled Comparison -->
    <div class="kpi-card bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm">
      <div class="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Total Enrolled (${yearA} → ${yearB})</div>
      <div class="mt-2 flex items-baseline justify-between">
        <div class="text-2xl font-bold text-slate-900 dark:text-white">${metricsA.enrolled.toLocaleString()} <span class="text-sm font-normal text-slate-400">→</span> ${metricsB.enrolled.toLocaleString()}</div>
        <span class="inline-flex items-center text-xs font-bold px-2 py-0.5 rounded-full ${deltaEnrolled >= 0 ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300" : "bg-rose-100 text-rose-800"}">
          ${deltaEnrolled >= 0 ? "+" : ""}${deltaEnrolled.toLocaleString()} women
        </span>
      </div>
      <p class="text-xs text-slate-500 mt-1">Net change in female trainee admissions</p>
    </div>

    <!-- Card 2: Completion Rate Comparison -->
    <div class="kpi-card bg-white dark:bg-slate-800 rounded-xl p-5 border border-blue-200 dark:border-blue-800/60 shadow-sm bg-gradient-to-br from-blue-50/40 dark:from-blue-950/20 to-transparent">
      <div class="text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">Completion Rate (${yearA} vs ${yearB})</div>
      <div class="mt-2 flex items-baseline justify-between">
        <div class="text-2xl font-bold text-blue-600 dark:text-blue-400">${metricsA.completionRate}% <span class="text-sm font-normal text-slate-400">→</span> ${metricsB.completionRate}%</div>
        <span class="inline-flex items-center text-xs font-bold px-2 py-0.5 rounded-full ${Number(deltaCompletion) >= 0 ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300" : "bg-rose-100 text-rose-800"}">
          ${Number(deltaCompletion) >= 0 ? "▲ +" : "▼ "}${deltaCompletion}% pts
        </span>
      </div>
      <p class="text-xs text-slate-500 mt-1">Completed: ${metricsA.completed.toLocaleString()} vs ${metricsB.completed.toLocaleString()}</p>
    </div>

    <!-- Card 3: 6-Month Employment Comparison -->
    <div class="kpi-card bg-white dark:bg-slate-800 rounded-xl p-5 border border-emerald-200 dark:border-emerald-800/60 shadow-sm bg-gradient-to-br from-emerald-50/40 dark:from-emerald-950/20 to-transparent">
      <div class="text-xs font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">6-Month Employment (${yearA} vs ${yearB})</div>
      <div class="mt-2 flex items-baseline justify-between">
        <div class="text-2xl font-bold text-emerald-600 dark:text-emerald-400">${metricsA.employmentRate}% <span class="text-sm font-normal text-slate-400">→</span> ${metricsB.employmentRate}%</div>
        <span class="inline-flex items-center text-xs font-bold px-2 py-0.5 rounded-full ${Number(deltaEmployment) >= 0 ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300" : "bg-rose-100 text-rose-800"}">
          ${Number(deltaEmployment) >= 0 ? "▲ +" : "▼ "}${deltaEmployment}% pts
        </span>
      </div>
      <p class="text-xs text-slate-500 mt-1">Employed: ${metricsA.employed6m.toLocaleString()} vs ${metricsB.employed6m.toLocaleString()} (${deltaEmployed >= 0 ? "+" : ""}${deltaEmployed.toLocaleString()})</p>
    </div>

    <!-- Card 4: Net Placement Yield -->
    <div class="kpi-card bg-white dark:bg-slate-800 rounded-xl p-5 border border-purple-200 dark:border-purple-800/60 shadow-sm bg-gradient-to-br from-purple-50/40 dark:from-purple-950/20 to-transparent">
      <div class="text-xs font-semibold uppercase tracking-wider text-purple-600 dark:text-purple-400">Overall Placement Yield</div>
      <div class="mt-2 flex items-baseline justify-between">
        <div class="text-2xl font-bold text-purple-600 dark:text-purple-400">${metricsA.placementYield}% <span class="text-sm font-normal text-slate-400">→</span> ${metricsB.placementYield}%</div>
        <span class="text-xs font-semibold text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded">
          Wage: $${metricsA.avgWage} → $${metricsB.avgWage}
        </span>
      </div>
      <p class="text-xs text-slate-500 mt-1">Net efficiency gain: +${(metricsB.placementYield - metricsA.placementYield).toFixed(1)}%</p>
    </div>
  `;
}

// Chart Rendering Logic
function renderCharts() {
  if (state.activeTab === "compare") {
    renderComparisonCharts();
  } else if (state.activeTab === "trends") {
    renderTrendCharts();
  } else {
    renderOverviewCharts();
  }
}

function renderOverviewCharts() {
  const chartWrapper1 = document.getElementById("chart-container-1");
  const chartWrapper2 = document.getElementById("chart-container-2");
  if (!chartWrapper1 || !chartWrapper2) return;

  chartWrapper1.innerHTML = `<canvas id="mainDistrictChart" class="w-full h-80"></canvas>`;
  chartWrapper2.innerHTML = `<canvas id="sectorChart" class="w-full h-80"></canvas>`;

  const filtered = getFilteredData();
  const sortedByDistrict = [...filtered].sort((a, b) => a.district.localeCompare(b.district));

  const labels = sortedByDistrict.map(d => d.district);
  const completionRates = sortedByDistrict.map(d => d.completionRate);
  const employmentRates = sortedByDistrict.map(d => d.employmentRate);

  // Chart 1: District Bar Chart (Completion vs Employment)
  const ctx1 = document.getElementById("mainDistrictChart").getContext("2d");
  if (state.charts.district) state.charts.district.destroy();
  state.charts.district = new Chart(ctx1, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Training Completion Rate (%)",
          data: completionRates,
          backgroundColor: "rgba(59, 130, 246, 0.85)",
          borderColor: "rgb(37, 99, 235)",
          borderWidth: 1,
          borderRadius: 6
        },
        {
          label: "6-Month Employment Rate (%)",
          data: employmentRates,
          backgroundColor: "rgba(16, 185, 129, 0.85)",
          borderColor: "rgb(5, 150, 105)",
          borderWidth: 1,
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "top" },
        tooltip: {
          callbacks: {
            label: function (context) {
              return `${context.dataset.label}: ${context.parsed.y}%`;
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          ticks: { callback: v => v + "%" },
          title: { display: true, text: "Percentage (%)" }
        },
        x: {
          ticks: { maxRotation: 45, minRotation: 0 }
        }
      }
    }
  });

  // Chart 2: Sector Breakdown
  const sectorGroups = {};
  filtered.forEach(item => {
    const s = item.sector || "General";
    if (!sectorGroups[s]) sectorGroups[s] = { enrolled: 0, completed: 0, employed6m: 0 };
    sectorGroups[s].enrolled += item.enrolled;
    sectorGroups[s].completed += item.completed;
    sectorGroups[s].employed6m += item.employed6m;
  });

  const sectorLabels = Object.keys(sectorGroups);
  const sectorCompletion = sectorLabels.map(s => Number(((sectorGroups[s].completed / sectorGroups[s].enrolled) * 100).toFixed(1)));
  const sectorEmployment = sectorLabels.map(s => Number(((sectorGroups[s].employed6m / sectorGroups[s].completed) * 100).toFixed(1)));

  const ctx2 = document.getElementById("sectorChart").getContext("2d");
  if (state.charts.sector) state.charts.sector.destroy();
  state.charts.sector = new Chart(ctx2, {
    type: "bar",
    data: {
      labels: sectorLabels,
      datasets: [
        {
          label: "Completion Rate (%)",
          data: sectorCompletion,
          backgroundColor: "rgba(99, 102, 241, 0.8)",
          borderRadius: 4
        },
        {
          label: "6M Employment Rate (%)",
          data: sectorEmployment,
          backgroundColor: "rgba(244, 63, 94, 0.8)",
          borderRadius: 4
        }
      ]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top" },
        tooltip: {
          callbacks: {
            label: context => `${context.dataset.label}: ${context.parsed.x}%`
          }
        }
      },
      scales: {
        x: {
          beginAtZero: true,
          max: 100,
          ticks: { callback: v => v + "%" }
        }
      }
    }
  });
}

function renderComparisonCharts() {
  const chartWrapper1 = document.getElementById("chart-container-1");
  const chartWrapper2 = document.getElementById("chart-container-2");
  if (!chartWrapper1 || !chartWrapper2) return;

  const yearA = Number(state.compareYearA);
  const yearB = Number(state.compareYearB);

  chartWrapper1.innerHTML = `<canvas id="compareCompletionChart" class="w-full h-80"></canvas>`;
  chartWrapper2.innerHTML = `<canvas id="compareEmploymentChart" class="w-full h-80"></canvas>`;

  const districts = [...new Set(state.data.map(d => d.district))].sort();

  const compRatesA = [];
  const compRatesB = [];
  const empRatesA = [];
  const empRatesB = [];

  districts.forEach(dist => {
    const recA = state.data.find(d => d.district === dist && d.year === yearA);
    const recB = state.data.find(d => d.district === dist && d.year === yearB);

    compRatesA.push(recA ? Number(((recA.completed / recA.enrolled) * 100).toFixed(1)) : 0);
    compRatesB.push(recB ? Number(((recB.completed / recB.enrolled) * 100).toFixed(1)) : 0);
    empRatesA.push(recA ? Number(((recA.employed6m / recA.completed) * 100).toFixed(1)) : 0);
    empRatesB.push(recB ? Number(((recB.employed6m / recB.completed) * 100).toFixed(1)) : 0);
  });

  // Comparison Chart 1: Completion Rate Year A vs Year B
  const ctx1 = document.getElementById("compareCompletionChart").getContext("2d");
  if (state.charts.comp1) state.charts.comp1.destroy();
  state.charts.comp1 = new Chart(ctx1, {
    type: "bar",
    data: {
      labels: districts,
      datasets: [
        {
          label: `${yearA} Completion Rate (%)`,
          data: compRatesA,
          backgroundColor: "rgba(148, 163, 184, 0.8)",
          borderRadius: 4
        },
        {
          label: `${yearB} Completion Rate (%)`,
          data: compRatesB,
          backgroundColor: "rgba(37, 99, 235, 0.85)",
          borderRadius: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `Formula 1: Training Completion Rate Comparison (${yearA} vs ${yearB})`, font: { size: 14, weight: "bold" } },
        tooltip: { callbacks: { label: c => `${c.dataset.label}: ${c.parsed.y}%` } }
      },
      scales: {
        y: { beginAtZero: true, max: 100, ticks: { callback: v => v + "%" } },
        x: { ticks: { maxRotation: 45 } }
      }
    }
  });

  // Comparison Chart 2: 6-Month Employment Rate Year A vs Year B
  const ctx2 = document.getElementById("compareEmploymentChart").getContext("2d");
  if (state.charts.comp2) state.charts.comp2.destroy();
  state.charts.comp2 = new Chart(ctx2, {
    type: "bar",
    data: {
      labels: districts,
      datasets: [
        {
          label: `${yearA} 6M Employment Rate (%)`,
          data: empRatesA,
          backgroundColor: "rgba(203, 213, 225, 0.8)",
          borderRadius: 4
        },
        {
          label: `${yearB} 6M Employment Rate (%)`,
          data: empRatesB,
          backgroundColor: "rgba(16, 185, 129, 0.85)",
          borderRadius: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: `Formula 2: 6-Month Employment Rate Comparison (${yearA} vs ${yearB})`, font: { size: 14, weight: "bold" } },
        tooltip: { callbacks: { label: c => `${c.dataset.label}: ${c.parsed.y}%` } }
      },
      scales: {
        y: { beginAtZero: true, max: 100, ticks: { callback: v => v + "%" } },
        x: { ticks: { maxRotation: 45 } }
      }
    }
  });
}

function renderTrendCharts() {
  const chartWrapper1 = document.getElementById("chart-container-1");
  const chartWrapper2 = document.getElementById("chart-container-2");
  if (!chartWrapper1 || !chartWrapper2) return;

  chartWrapper1.innerHTML = `<canvas id="trendRateChart" class="w-full h-80"></canvas>`;
  chartWrapper2.innerHTML = `<canvas id="trendVolumeChart" class="w-full h-80"></canvas>`;

  const years = [...new Set(state.data.map(d => d.year))].sort((a, b) => a - b);
  const yearlyMetrics = years.map(y => {
    const recs = state.data.filter(d => d.year === y);
    return { year: y, ...calculateMetrics(recs) };
  });

  // Line Chart: Rate Trends Over Time
  const ctx1 = document.getElementById("trendRateChart").getContext("2d");
  if (state.charts.trend1) state.charts.trend1.destroy();
  state.charts.trend1 = new Chart(ctx1, {
    type: "line",
    data: {
      labels: years,
      datasets: [
        {
          label: "Training Completion Rate (%)",
          data: yearlyMetrics.map(m => m.completionRate),
          borderColor: "rgb(37, 99, 235)",
          backgroundColor: "rgba(37, 99, 235, 0.1)",
          fill: true,
          tension: 0.3,
          borderWidth: 3,
          pointRadius: 6,
          pointHoverRadius: 8
        },
        {
          label: "6-Month Employment Rate (%)",
          data: yearlyMetrics.map(m => m.employmentRate),
          borderColor: "rgb(16, 185, 129)",
          backgroundColor: "rgba(16, 185, 129, 0.1)",
          fill: true,
          tension: 0.3,
          borderWidth: 3,
          pointRadius: 6,
          pointHoverRadius: 8
        },
        {
          label: "Overall Placement Yield (%)",
          data: yearlyMetrics.map(m => m.placementYield),
          borderColor: "rgb(168, 85, 247)",
          borderDash: [5, 5],
          tension: 0.3,
          borderWidth: 2,
          pointRadius: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: "5-Year Trajectory: Completion & Employment Rates (2021–2025)", font: { size: 14, weight: "bold" } },
        tooltip: { callbacks: { label: c => `${c.dataset.label}: ${c.parsed.y}%` } }
      },
      scales: {
        y: { beginAtZero: false, min: 40, max: 100, ticks: { callback: v => v + "%" } }
      }
    }
  });

  // Volume Bar Chart: Total Women Enrolled, Completed, Employed
  const ctx2 = document.getElementById("trendVolumeChart").getContext("2d");
  if (state.charts.trend2) state.charts.trend2.destroy();
  state.charts.trend2 = new Chart(ctx2, {
    type: "bar",
    data: {
      labels: years,
      datasets: [
        {
          label: "Total Enrolled",
          data: yearlyMetrics.map(m => m.enrolled),
          backgroundColor: "rgba(99, 102, 241, 0.75)",
          borderRadius: 4
        },
        {
          label: "Training Completed",
          data: yearlyMetrics.map(m => m.completed),
          backgroundColor: "rgba(59, 130, 246, 0.85)",
          borderRadius: 4
        },
        {
          label: "Employed at 6 Months",
          data: yearlyMetrics.map(m => m.employed6m),
          backgroundColor: "rgba(16, 185, 129, 0.85)",
          borderRadius: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: "Longitudinal Participation & Placement Volume Growth", font: { size: 14, weight: "bold" } },
        tooltip: { callbacks: { label: c => `${c.dataset.label}: ${c.parsed.y.toLocaleString()} women` } }
      },
      scales: {
        y: { beginAtZero: true, ticks: { callback: v => v.toLocaleString() } }
      }
    }
  });
}

// Render Interactive District Table
function renderTable() {
  const tableHead = document.getElementById("table-head");
  const tableBody = document.getElementById("table-body");
  const tableCount = document.getElementById("table-row-count");
  if (!tableHead || !tableBody) return;

  if (state.activeTab === "compare") {
    renderComparisonTable(tableHead, tableBody, tableCount);
  } else {
    renderStandardTable(tableHead, tableBody, tableCount);
  }
}

function renderStandardTable(thead, tbody, countSpan) {
  let records = getFilteredData();

  records.sort((a, b) => {
    let valA = a[state.sortColumn];
    let valB = b[state.sortColumn];
    if (typeof valA === "string") {
      return state.sortOrder === "asc" ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }
    return state.sortOrder === "asc" ? valA - valB : valB - valA;
  });

  if (countSpan) countSpan.textContent = `Showing ${records.length} records`;

  const getSortIcon = col => {
    if (state.sortColumn !== col) return "↕";
    return state.sortOrder === "asc" ? "▲" : "▼";
  };

  thead.innerHTML = `
    <tr>
      <th class="sortable px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider" onclick="handleSort('district')">District ${getSortIcon("district")}</th>
      <th class="sortable px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider" onclick="handleSort('year')">Year ${getSortIcon("year")}</th>
      <th class="sortable px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider" onclick="handleSort('sector')">Sector ${getSortIcon("sector")}</th>
      <th class="sortable px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider" onclick="handleSort('enrolled')">Enrolled ${getSortIcon("enrolled")}</th>
      <th class="sortable px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider" onclick="handleSort('completed')">Completed ${getSortIcon("completed")}</th>
      <th class="sortable px-4 py-3 text-right text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider bg-blue-50/50 dark:bg-blue-900/20" onclick="handleSort('completionRate')">Completion Rate (%) ${getSortIcon("completionRate")}</th>
      <th class="sortable px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider" onclick="handleSort('employed6m')">Employed (6M) ${getSortIcon("employed6m")}</th>
      <th class="sortable px-4 py-3 text-right text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider bg-emerald-50/50 dark:bg-emerald-900/20" onclick="handleSort('employmentRate')">6M Employment Rate (%) ${getSortIcon("employmentRate")}</th>
      <th class="sortable px-4 py-3 text-right text-xs font-semibold text-purple-600 dark:text-purple-400 uppercase tracking-wider" onclick="handleSort('placementYield')">Placement Yield (%) ${getSortIcon("placementYield")}</th>
      <th class="sortable px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider" onclick="handleSort('avgWage')">Avg Wage ($) ${getSortIcon("avgWage")}</th>
    </tr>
  `;

  if (records.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="10" class="text-center py-8 text-slate-400">No matching district records found. Try adjusting your filters.</td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = records.map(r => `
    <tr class="hover:bg-slate-50 dark:hover:bg-slate-700/50 border-b border-slate-200 dark:border-slate-700">
      <td class="px-4 py-3 font-semibold text-slate-900 dark:text-white flex items-center gap-2">
        <span>${r.district}</span>
        ${r.completionRate >= 90 && r.employmentRate >= 85 ? "<span class="text-[10px] bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300 px-1.5 py-0.5 rounded font-medium">★ Top Performer</span>" : ""}
      </td>
      <td class="px-4 py-3 text-slate-600 dark:text-slate-300 font-mono text-sm">${r.year}</td>
      <td class="px-4 py-3 text-slate-600 dark:text-slate-300 text-xs">${r.sector || "General Track"}</td>
      <td class="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-200">${r.enrolled.toLocaleString()}</td>
      <td class="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-200">${r.completed.toLocaleString()}</td>
      <td class="px-4 py-3 text-right bg-blue-50/40 dark:bg-blue-900/10">
        <div class="flex items-center justify-end gap-2">
          <div class="w-12 bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 hidden sm:block">
            <div class="bg-blue-600 h-1.5 rounded-full" style="width: ${Math.min(100, r.completionRate)}%"></div>
          </div>
          <span class="font-bold text-blue-600 dark:text-blue-400">${r.completionRate}%</span>
        </div>
      </td>
      <td class="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-200">${r.employed6m.toLocaleString()}</td>
      <td class="px-4 py-3 text-right bg-emerald-50/40 dark:bg-emerald-900/10">
        <div class="flex items-center justify-end gap-2">
          <div class="w-12 bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 hidden sm:block">
            <div class="bg-emerald-600 h-1.5 rounded-full" style="width: ${Math.min(100, r.employmentRate)}%"></div>
          </div>
          <span class="font-bold text-emerald-600 dark:text-emerald-400">${r.employmentRate}%</span>
        </div>
      </td>
      <td class="px-4 py-3 text-right font-semibold text-purple-600 dark:text-purple-400">${r.placementYield}%</td>
      <td class="px-4 py-3 text-right font-mono text-sm text-slate-700 dark:text-slate-300">$${r.avgWage || 0}</td>
    </tr>
  `).join("");
}

function renderComparisonTable(thead, tbody, countSpan) {
  const yearA = Number(state.compareYearA);
  const yearB = Number(state.compareYearB);

  const districts = [...new Set(state.data.map(d => d.district))].sort();

  let rows = districts.map(dist => {
    const recA = state.data.find(d => d.district === dist && d.year === yearA);
    const recB = state.data.find(d => d.district === dist && d.year === yearB);

    const compA = recA ? (recA.completed / recA.enrolled) * 100 : 0;
    const compB = recB ? (recB.completed / recB.enrolled) * 100 : 0;
    const deltaComp = compB - compA;

    const empA = recA ? (recA.employed6m / recA.completed) * 100 : 0;
    const empB = recB ? (recB.employed6m / recB.completed) * 100 : 0;
    const deltaEmp = empB - empA;

    const jobsA = recA ? recA.employed6m : 0;
    const jobsB = recB ? recB.employed6m : 0;
    const deltaJobs = jobsB - jobsA;

    return {
      district: dist,
      sector: recB ? recB.sector : (recA ? recA.sector : "General"),
      compA: Number(compA.toFixed(1)),
      compB: Number(compB.toFixed(1)),
      deltaComp: Number(deltaComp.toFixed(1)),
      empA: Number(empA.toFixed(1)),
      empB: Number(empB.toFixed(1)),
      deltaEmp: Number(deltaEmp.toFixed(1)),
      jobsA,
      jobsB,
      deltaJobs
    };
  });

  if (state.searchQuery) {
    const q = state.searchQuery.toLowerCase();
    rows = rows.filter(r => r.district.toLowerCase().includes(q) || r.sector.toLowerCase().includes(q));
  }

  rows.sort((a, b) => {
    let valA = a[state.sortColumn] !== undefined ? a[state.sortColumn] : a.district;
    let valB = b[state.sortColumn] !== undefined ? b[state.sortColumn] : b.district;
    if (typeof valA === "string") {
      return state.sortOrder === "asc" ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }
    return state.sortOrder === "asc" ? valA - valB : valB - valA;
  });

  if (countSpan) countSpan.textContent = `Comparing ${rows.length} districts between ${yearA} and ${yearB}`;

  const getSortIcon = col => {
    if (state.sortColumn !== col) return "↕";
    return state.sortOrder === "asc" ? "▲" : "▼";
  };

  thead.innerHTML = `
    <tr>
      <th class="sortable px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider" onclick="handleSort('district')">District ${getSortIcon("district")}</th>
      <th class="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Sector</th>
      <th class="sortable px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider" onclick="handleSort('compA')">${yearA} Completion ${getSortIcon("compA")}</th>
      <th class="sortable px-4 py-3 text-right text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider" onclick="handleSort('compB')">${yearB} Completion ${getSortIcon("compB")}</th>
      <th class="sortable px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider" onclick="handleSort('deltaComp')">Δ Completion ${getSortIcon("deltaComp")}</th>
      <th class="sortable px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider" onclick="handleSort('empA')">${yearA} Employment (6M) ${getSortIcon("empA")}</th>
      <th class="sortable px-4 py-3 text-right text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider" onclick="handleSort('empB')">${yearB} Employment (6M) ${getSortIcon("empB")}</th>
      <th class="sortable px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider" onclick="handleSort('deltaEmp')">Δ Employment ${getSortIcon("deltaEmp")}</th>
      <th class="sortable px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider" onclick="handleSort('deltaJobs')">Net Jobs Added ${getSortIcon("deltaJobs")}</th>
    </tr>
  `;

  tbody.innerHTML = rows.map(r => `
    <tr class="hover:bg-slate-50 dark:hover:bg-slate-700/50 border-b border-slate-200 dark:border-slate-700">
      <td class="px-4 py-3 font-semibold text-slate-900 dark:text-white">${r.district}</td>
      <td class="px-4 py-3 text-xs text-slate-500 dark:text-slate-400">${r.sector}</td>
      <td class="px-4 py-3 text-right font-mono text-sm text-slate-600 dark:text-slate-300">${r.compA}%</td>
      <td class="px-4 py-3 text-right font-mono font-bold text-blue-600 dark:text-blue-400">${r.compB}%</td>
      <td class="px-4 py-3 text-right font-mono text-xs">
        <span class="inline-block px-1.5 py-0.5 rounded font-semibold ${r.deltaComp >= 0 ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300" : "bg-rose-100 text-rose-800 dark:bg-rose-900/50 dark:text-rose-300"}">
          ${r.deltaComp >= 0 ? "+" : ""}${r.deltaComp}%
        </span>
      </td>
      <td class="px-4 py-3 text-right font-mono text-sm text-slate-600 dark:text-slate-300">${r.empA}%</td>
      <td class="px-4 py-3 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">${r.empB}%</td>
      <td class="px-4 py-3 text-right font-mono text-xs">
        <span class="inline-block px-1.5 py-0.5 rounded font-semibold ${r.deltaEmp >= 0 ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300" : "bg-rose-100 text-rose-800 dark:bg-rose-900/50 dark:text-rose-300"}">
          ${r.deltaEmp >= 0 ? "+" : ""}${r.deltaEmp}%
        </span>
      </td>
      <td class="px-4 py-3 text-right font-mono font-bold ${r.deltaJobs >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}">
        ${r.deltaJobs >= 0 ? "+" : ""}${r.deltaJobs.toLocaleString()}
      </td>
    </tr>
  `).join("");
}

// Global Sorting Handler
window.handleSort = function (col) {
  if (state.sortColumn === col) {
    state.sortOrder = state.sortOrder === "asc" ? "desc" : "asc";
  } else {
    state.sortColumn = col;
    state.sortOrder = "desc";
  }
  renderTable();
};

// Tab Switching
function setTab(tab) {
  state.activeTab = tab;

  document.querySelectorAll(".tab-btn").forEach(btn => {
    if (btn.dataset.tab === tab) {
      btn.className = "tab-btn px-4 py-2 text-sm font-semibold rounded-lg bg-blue-600 text-white shadow-sm";
    } else {
      btn.className = "tab-btn px-4 py-2 text-sm font-medium rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800";
    }
  });

  const singleYearControl = document.getElementById("single-year-control");
  const compareYearControl = document.getElementById("compare-year-control");

  if (singleYearControl && compareYearControl) {
    if (tab === "compare") {
      singleYearControl.classList.add("hidden");
      compareYearControl.classList.remove("hidden");
    } else if (tab === "trends") {
      singleYearControl.classList.add("hidden");
      compareYearControl.classList.add("hidden");
    } else {
      singleYearControl.classList.remove("hidden");
      compareYearControl.classList.add("hidden");
    }
  }

  state.sortColumn = tab === "compare" ? "deltaEmp" : "completionRate";
  state.sortOrder = "desc";

  renderKPIs();
  renderCharts();
  renderTable();
}

// CSV Export Utility
function exportCSV() {
  let csvContent = "data:text/csv;charset=utf-8,";

  if (state.activeTab === "compare") {
    const yearA = Number(state.compareYearA);
    const yearB = Number(state.compareYearB);
    const districts = [...new Set(state.data.map(d => d.district))].sort();

    csvContent += `District,Sector,${yearA} Completion Rate (%),${yearB} Completion Rate (%),Delta Completion (%),${yearA} 6M Employment Rate (%),${yearB} 6M Employment Rate (%),Delta Employment (%),Net Jobs Added
`;

    districts.forEach(dist => {
      const recA = state.data.find(d => d.district === dist && d.year === yearA);
      const recB = state.data.find(d => d.district === dist && d.year === yearB);

      const compA = recA ? ((recA.completed / recA.enrolled) * 100).toFixed(1) : "0";
      const compB = recB ? ((recB.completed / recB.enrolled) * 100).toFixed(1) : "0";
      const deltaComp = (Number(compB) - Number(compA)).toFixed(1);

      const empA = recA ? ((recA.employed6m / recA.completed) * 100).toFixed(1) : "0";
      const empB = recB ? ((recB.employed6m / recB.completed) * 100).toFixed(1) : "0";
      const deltaEmp = (Number(empB) - Number(empA)).toFixed(1);

      const deltaJobs = (recB ? recB.employed6m : 0) - (recA ? recA.employed6m : 0);
      const sector = recB ? recB.sector : (recA ? recA.sector : "General");

      csvContent += `"${dist}","${sector}",${compA},${compB},${deltaComp},${empA},${empB},${deltaEmp},${deltaJobs}
`;
    });
  } else {
    const records = getFilteredData();
    csvContent += "District,Year,Sector,Enrolled,Completed,Training Completion Rate (%),Employed (6M),6-Month Employment Rate (%),Overall Placement Yield (%),Avg Starting Wage ($)
";

    records.forEach(r => {
      csvContent += `"${r.district}",${r.year},"${r.sector || "General"}",${r.enrolled},${r.completed},${r.completionRate},${r.employed6m},${r.employmentRate},${r.placementYield},${r.avgWage || 0}
`;
    });
  }

  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `women_training_employment_${state.activeTab}_${new Date().toISOString().slice(0, 10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// Add New District / Record Modal Logic
function setupModal() {
  const modal = document.getElementById("add-record-modal");
  const openBtn = document.getElementById("open-add-modal-btn");
  const closeBtn = document.getElementById("close-modal-btn");
  const cancelBtn = document.getElementById("cancel-modal-btn");
  const form = document.getElementById("add-record-form");
  const districtSelect = document.getElementById("new-district");
  const customDistrictGroup = document.getElementById("custom-district-group");

  if (!modal || !form) return;

  const showModal = () => modal.classList.remove("hidden");
  const hideModal = () => modal.classList.add("hidden");

  if (openBtn) openBtn.addEventListener("click", showModal);
  if (closeBtn) closeBtn.addEventListener("click", hideModal);
  if (cancelBtn) cancelBtn.addEventListener("click", hideModal);

  if (districtSelect) {
    districtSelect.addEventListener("change", (e) => {
      if (e.target.value === "__custom__") {
        customDistrictGroup.classList.remove("hidden");
      } else {
        customDistrictGroup.classList.add("hidden");
      }
    });
  }

  const inputEnrolled = document.getElementById("new-enrolled");
  const inputCompleted = document.getElementById("new-completed");
  const inputEmployed = document.getElementById("new-employed");
  const previewBox = document.getElementById("new-record-preview");

  const updateFormPreview = () => {
    const enrolled = Number(inputEnrolled.value) || 0;
    const completed = Number(inputCompleted.value) || 0;
    const employed = Number(inputEmployed.value) || 0;

    if (completed > enrolled) {
      previewBox.innerHTML = `<span class="text-rose-500 font-semibold">⚠️ Completed cannot exceed Enrolled</span>`;
      return;
    }
    if (employed > completed) {
      previewBox.innerHTML = `<span class="text-rose-500 font-semibold">⚠️ Employed (6M) cannot exceed Completed</span>`;
      return;
    }

    const compRate = enrolled > 0 ? ((completed / enrolled) * 100).toFixed(1) : 0;
    const empRate = completed > 0 ? ((employed / completed) * 100).toFixed(1) : 0;

    previewBox.innerHTML = `
      <div class="grid grid-cols-2 gap-2 text-xs">
        <div class="bg-blue-50 dark:bg-blue-900/30 p-2 rounded border border-blue-200 dark:border-blue-800">
          <span class="text-slate-500 dark:text-slate-400">Formula 1 (Completion):</span>
          <span class="font-bold text-blue-600 dark:text-blue-400 ml-1">${compRate}%</span>
        </div>
        <div class="bg-emerald-50 dark:bg-emerald-900/30 p-2 rounded border border-emerald-200 dark:border-emerald-800">
          <span class="text-slate-500 dark:text-slate-400">Formula 2 (6M Employed):</span>
          <span class="font-bold text-emerald-600 dark:text-emerald-400 ml-1">${empRate}%</span>
        </div>
      </div>
    `;
  };

  [inputEnrolled, inputCompleted, inputEmployed].forEach(el => {
    if (el) el.addEventListener("input", updateFormPreview);
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();

    let district = districtSelect.value;
    if (district === "__custom__") {
      district = document.getElementById("custom-district-name").value.trim();
      if (!district) {
        alert("Please specify a district name.");
        return;
      }
    }

    const year = Number(document.getElementById("new-year").value);
    const sector = document.getElementById("new-sector").value;
    const enrolled = Number(document.getElementById("new-enrolled").value);
    const completed = Number(document.getElementById("new-completed").value);
    const employed6m = Number(document.getElementById("new-employed").value);
    const avgWage = Number(document.getElementById("new-wage").value) || 500;

    if (completed > enrolled) {
      alert("Error: Completed trainees cannot exceed total enrolled trainees.");
      return;
    }
    if (employed6m > completed) {
      alert("Error: Employed trainees cannot exceed completed trainees.");
      return;
    }

    const existingIndex = state.data.findIndex(d => d.district.toLowerCase() === district.toLowerCase() && d.year === year);
    if (existingIndex >= 0) {
      state.data[existingIndex] = { id: state.data[existingIndex].id, district, year, sector, enrolled, completed, employed6m, avgWage };
    } else {
      state.data.push({
        id: Date.now(),
        district,
        year,
        sector,
        enrolled,
        completed,
        employed6m,
        avgWage
      });
    }

    form.reset();
    hideModal();
    populateFilters();
    renderKPIs();
    renderCharts();
    renderTable();
  });
}

// Setup Event Listeners
function setupEvents() {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => setTab(btn.dataset.tab));
  });

  const filterYear = document.getElementById("filter-year");
  if (filterYear) {
    filterYear.addEventListener("change", (e) => {
      state.selectedYear = Number(e.target.value);
      renderKPIs();
      renderCharts();
      renderTable();
    });
  }

  const compA = document.getElementById("compare-year-a");
  const compB = document.getElementById("compare-year-b");
  const swapBtn = document.getElementById("swap-compare-years");

  if (compA && compB) {
    compA.addEventListener("change", (e) => {
      state.compareYearA = Number(e.target.value);
      renderKPIs();
      renderCharts();
      renderTable();
    });
    compB.addEventListener("change", (e) => {
      state.compareYearB = Number(e.target.value);
      renderKPIs();
      renderCharts();
      renderTable();
    });
  }

  if (swapBtn && compA && compB) {
    swapBtn.addEventListener("click", () => {
      const temp = state.compareYearA;
      state.compareYearA = state.compareYearB;
      state.compareYearB = temp;
      compA.value = state.compareYearA;
      compB.value = state.compareYearB;
      renderKPIs();
      renderCharts();
      renderTable();
    });
  }

  const filterDist = document.getElementById("filter-district");
  if (filterDist) {
    filterDist.addEventListener("change", (e) => {
      state.selectedDistrict = e.target.value;
      renderKPIs();
      renderCharts();
      renderTable();
    });
  }

  const filterSector = document.getElementById("filter-sector");
  if (filterSector) {
    filterSector.addEventListener("change", (e) => {
      state.selectedSector = e.target.value;
      renderKPIs();
      renderCharts();
      renderTable();
    });
  }

  const searchBox = document.getElementById("search-district");
  if (searchBox) {
    searchBox.addEventListener("input", (e) => {
      state.searchQuery = e.target.value.trim();
      renderTable();
    });
  }

  const exportBtn = document.getElementById("export-csv-btn");
  if (exportBtn) {
    exportBtn.addEventListener("click", exportCSV);
  }

  const resetBtn = document.getElementById("reset-filters-btn");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      state.selectedYear = 2025;
      state.compareYearA = 2021;
      state.compareYearB = 2025;
      state.selectedDistrict = "all";
      state.selectedSector = "all";
      state.searchQuery = "";
      if (document.getElementById("search-district")) document.getElementById("search-district").value = "";
      populateFilters();
      renderKPIs();
      renderCharts();
      renderTable();
    });
  }

  const themeToggle = document.getElementById("theme-toggle-btn");
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      document.documentElement.classList.toggle("dark");
      const isDark = document.documentElement.classList.contains("dark");
      localStorage.setItem("theme", isDark ? "dark" : "light");
      renderCharts();
    });
  }

  if (localStorage.getItem("theme") === "dark" || (!("theme" in localStorage) && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }

  const sourceAgency = document.getElementById("source-agency");
  const sourcePublication = document.getElementById("source-publication");
  const sourceMethodology = document.getElementById("source-methodology");
  const sourceCitation = document.getElementById("source-citation");

  if (sourceAgency && typeof SOURCE_METADATA !== "undefined") {
    sourceAgency.textContent = SOURCE_METADATA.agency;
    sourcePublication.textContent = SOURCE_METADATA.publication;
    sourceMethodology.textContent = SOURCE_METADATA.methodology;
    sourceCitation.textContent = SOURCE_METADATA.citation;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  populateFilters();
  setupEvents();
  setupModal();
  renderKPIs();
  renderCharts();
  renderTable();
});
