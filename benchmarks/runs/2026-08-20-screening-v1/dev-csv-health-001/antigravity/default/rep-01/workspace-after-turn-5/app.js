// 4 Antenatal Checkup (ANC4) Coverage Dashboard Application (2021 – 2023)

// Fallback embedded dataset in case of local file:/// execution
const FALLBACK_CSV = `district,year,pregnancies_registered,anc4_completed,source
Gaya,2021,1250,825,synthetic Bihar ANC fixture
Gaya,2022,1300,897,synthetic Bihar ANC fixture
Gaya,2023,1350,999,synthetic Bihar ANC fixture
Nalanda,2021,1100,803,synthetic Bihar ANC fixture
Nalanda,2022,1200,924,synthetic Bihar ANC fixture
Nalanda,2023,1250,1000,synthetic Bihar ANC fixture
Purnia,2021,1500,870,synthetic Bihar ANC fixture
Purnia,2022,1550,992,synthetic Bihar ANC fixture
Purnia,2023,1600,1072,synthetic Bihar ANC fixture
Kishanganj,2021,900,486,synthetic Bihar ANC fixture
Kishanganj,2022,1000,570,synthetic Bihar ANC fixture
Kishanganj,2023,1100,671,synthetic Bihar ANC fixture
Patna,2021,1600,1280,synthetic Bihar ANC fixture
Patna,2022,1700,1411,synthetic Bihar ANC fixture
Patna,2023,1800,1548,synthetic Bihar ANC fixture`;

// State variables
let rawData = [];
let availableYears = [];
let availableDistricts = [];
let selectedYear = '2023'; // default to latest year
let sortOption = 'rate-desc';
let viewMode = 'comparison';
let searchQuery = '';
let compareA = 'Patna';
let compareB = 'Kishanganj';
let chartInstance = null;

// Parse CSV text into array of structured objects
function parseCSV(csvText) {
  const lines = csvText.trim().split(/\r?\n/);
  if (lines.length < 2) return [];

  const headers = lines[0].split(',').map(h => h.trim());
  const records = [];

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    
    // Simple CSV parse
    const cols = line.split(',').map(c => c.trim());
    if (cols.length >= 5) {
      const district = cols[0];
      const year = parseInt(cols[1], 10);
      const reg = parseInt(cols[2], 10);
      const anc4 = parseInt(cols[3], 10);
      const source = cols.slice(4).join(','); // in case of commas in source

      // Rate formula: (anc4_completed / pregnancies_registered) * 100
      const rate = reg > 0 ? (anc4 / reg) * 100 : 0;

      records.push({
        district,
        year,
        pregnancies_registered: reg,
        anc4_completed: anc4,
        coverage_rate: rate,
        coverage_rate_formatted: rate.toFixed(2),
        source
      });
    }
  }

  return records;
}

// Load data from file or fallback
async function loadData() {
  try {
    const res = await fetch('anc4_coverage.csv');
    if (!res.ok) throw new Error('Network response not ok');
    const text = await res.text();
    rawData = parseCSV(text);
  } catch (err) {
    console.warn('Direct fetch failed (likely file:// protocol), using embedded fixture data:', err);
    rawData = parseCSV(FALLBACK_CSV);
  }

  if (rawData.length === 0) {
    rawData = parseCSV(FALLBACK_CSV);
  }

  // Strictly filter dataset to only 2021 to 2023
  rawData = rawData.filter(r => r.year >= 2021 && r.year <= 2023);

  // Extract unique years sorted descending (2023, 2022, 2021)
  const yearsSet = new Set(rawData.map(r => r.year));
  availableYears = Array.from(yearsSet).sort((a, b) => b - a);
  
  // Extract unique districts sorted alphabetically
  const districtSet = new Set(rawData.map(r => r.district));
  availableDistricts = Array.from(districtSet).sort();

  if (availableYears.length > 0 && !availableYears.includes(parseInt(selectedYear, 10)) && selectedYear !== 'all') {
    selectedYear = String(availableYears[0]);
  }

  // Initialize UI components
  setupYearButtons();
  setupDistrictCompareSelectors();
  setupEventListeners();
  renderDashboard();
}

// Setup Year Filter Buttons
function setupYearButtons() {
  const container = document.getElementById('year-buttons-container');
  if (!container) return;
  container.innerHTML = '';

  availableYears.forEach(year => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = year;
    btn.setAttribute('data-year', year);
    btn.className = `px-4 py-2 text-xs font-bold rounded-xl border transition-all ${
      String(year) === String(selectedYear)
        ? 'year-pill-active'
        : 'year-pill-inactive'
    }`;
    btn.addEventListener('click', () => {
      selectedYear = String(year);
      updateYearButtons();
      renderDashboard();
    });
    container.appendChild(btn);
  });

  // "All (2021–2023) Trend" Multi-Year button
  const allBtn = document.createElement('button');
  allBtn.type = 'button';
  allBtn.textContent = 'All (2021–2023) Trend';
  allBtn.setAttribute('data-year', 'all');
  allBtn.className = `px-4 py-2 text-xs font-bold rounded-xl border transition-all ${
    selectedYear === 'all'
      ? 'year-pill-active'
      : 'year-pill-inactive'
  }`;
  allBtn.addEventListener('click', () => {
    selectedYear = 'all';
    viewMode = 'trend';
    const vm = document.getElementById('view-mode-select');
    if (vm) vm.value = 'trend';
    updateYearButtons();
    renderDashboard();
  });
  container.appendChild(allBtn);
}

function updateYearButtons() {
  const buttons = document.querySelectorAll('#year-buttons-container button');
  buttons.forEach(btn => {
    const year = btn.getAttribute('data-year');
    if (year === String(selectedYear)) {
      btn.className = 'px-4 py-2 text-xs font-bold rounded-xl border transition-all year-pill-active';
    } else {
      btn.className = 'px-4 py-2 text-xs font-bold rounded-xl border transition-all year-pill-inactive';
    }
  });
}

// Setup District Compare Selectors
function setupDistrictCompareSelectors() {
  const selectA = document.getElementById('compare-district-a');
  const selectB = document.getElementById('compare-district-b');
  if (!selectA || !selectB) return;

  selectA.innerHTML = '';
  selectB.innerHTML = '';

  availableDistricts.forEach(dist => {
    const optA = document.createElement('option');
    optA.value = dist;
    optA.textContent = dist;
    if (dist === compareA) optA.selected = true;
    selectA.appendChild(optA);

    const optB = document.createElement('option');
    optB.value = dist;
    optB.textContent = dist;
    if (dist === compareB) optB.selected = true;
    selectB.appendChild(optB);
  });

  selectA.addEventListener('change', (e) => {
    compareA = e.target.value;
    renderHeadToHead();
    renderLiveFormulaExample();
  });

  selectB.addEventListener('change', (e) => {
    compareB = e.target.value;
    renderHeadToHead();
  });
}

// Setup Event Listeners
function setupEventListeners() {
  const sortSelect = document.getElementById('sort-select');
  if (sortSelect) {
    sortSelect.addEventListener('change', (e) => {
      sortOption = e.target.value;
      renderTable();
      renderChart();
    });
  }

  const viewModeSelect = document.getElementById('view-mode-select');
  if (viewModeSelect) {
    viewModeSelect.addEventListener('change', (e) => {
      viewMode = e.target.value;
      renderChart();
    });
  }

  const searchInput = document.getElementById('district-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value.toLowerCase().trim();
      renderTable();
    });
  }

  const btnExport = document.getElementById('btn-export-csv');
  if (btnExport) {
    btnExport.addEventListener('click', exportFilteredCSV);
  }

  // Table header sorting
  const sortMap = {
    'th-district': 'name-asc',
    'th-reg': 'reg-desc',
    'th-anc4': 'anc4-desc',
    'th-rate': 'rate-desc'
  };

  Object.entries(sortMap).forEach(([id, sortVal]) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('click', () => {
        if (sortOption === sortVal) {
          // Toggle asc/desc
          if (sortVal === 'rate-desc') sortOption = 'rate-asc';
          else if (sortVal === 'rate-asc') sortOption = 'rate-desc';
          else if (sortVal === 'name-asc') sortOption = 'name-desc';
          else if (sortVal === 'reg-desc') sortOption = 'reg-asc';
          else if (sortVal === 'anc4-desc') sortOption = 'anc4-asc';
        } else {
          sortOption = sortVal;
        }
        if (sortSelect) sortSelect.value = sortOption;
        renderTable();
        renderChart();
      });
    }
  });
}

// Filter and sort data for current selection
function getFilteredData() {
  let records = [];
  if (selectedYear === 'all') {
    records = [...rawData];
  } else {
    const yr = parseInt(selectedYear, 10);
    records = rawData.filter(r => r.year === yr);
  }

  // Search filter
  if (searchQuery) {
    records = records.filter(r => r.district.toLowerCase().includes(searchQuery));
  }

  // Sorting
  records.sort((a, b) => {
    switch (sortOption) {
      case 'rate-desc': return b.coverage_rate - a.coverage_rate;
      case 'rate-asc': return a.coverage_rate - b.coverage_rate;
      case 'name-asc': return a.district.localeCompare(b.district);
      case 'name-desc': return b.district.localeCompare(a.district);
      case 'anc4-desc': return b.anc4_completed - a.anc4_completed;
      case 'anc4-asc': return a.anc4_completed - b.anc4_completed;
      case 'reg-desc': return b.pregnancies_registered - a.pregnancies_registered;
      case 'reg-asc': return a.pregnancies_registered - b.pregnancies_registered;
      default: return b.coverage_rate - a.coverage_rate;
    }
  });

  return records;
}

// Calculate State / Aggregated Totals
function calculateTotals(records) {
  const totalReg = records.reduce((sum, r) => sum + r.pregnancies_registered, 0);
  const totalAnc4 = records.reduce((sum, r) => sum + r.anc4_completed, 0);
  const overallRate = totalReg > 0 ? (totalAnc4 / totalReg) * 100 : 0;

  return {
    totalReg,
    totalAnc4,
    overallRate,
    overallRateFormatted: overallRate.toFixed(2)
  };
}

// Main Render Dispatcher
function renderDashboard() {
  updateYearLabels();
  renderKPIs();
  renderChart();
  renderHeadToHead();
  renderTable();
  renderProgressionMatrix();
  renderLiveFormulaExample();
}

function updateYearLabels() {
  const yrText = selectedYear === 'all' ? 'All (2021-2023)' : selectedYear;
  
  const badge = document.getElementById('kpi-year-badge');
  if (badge) badge.textContent = yrText;

  const chartLabel = document.getElementById('chart-year-label');
  if (chartLabel) chartLabel.textContent = yrText;

  const tableBadge = document.getElementById('table-badge-year');
  if (tableBadge) tableBadge.textContent = `Year: ${yrText}`;

  const h2hYear = document.getElementById('h2h-year-label');
  if (h2hYear) h2hYear.textContent = yrText;
}

// Render Key Performance Indicators
function renderKPIs() {
  const yr = selectedYear === 'all' ? availableYears[0] : parseInt(selectedYear, 10);
  const yearRecords = rawData.filter(r => r.year === yr);
  
  if (yearRecords.length === 0) return;

  const totals = calculateTotals(yearRecords);

  // Highest and Lowest
  const sorted = [...yearRecords].sort((a, b) => b.coverage_rate - a.coverage_rate);
  const top = sorted[0];
  const lowest = sorted[sorted.length - 1];

  // Overall State Rate
  document.getElementById('kpi-avg-rate').textContent = `${totals.overallRateFormatted}%`;
  document.getElementById('kpi-avg-subtext').textContent = `Across ${yearRecords.length} reporting districts (${totals.totalAnc4.toLocaleString()} / ${totals.totalReg.toLocaleString()})`;

  // Top district
  if (top) {
    document.getElementById('kpi-top-district').textContent = top.district;
    document.getElementById('kpi-top-rate').textContent = `${top.coverage_rate_formatted}%`;
    const diff = (top.coverage_rate - totals.overallRate).toFixed(1);
    document.getElementById('kpi-top-subtext').textContent = `+${diff}% above state avg (${top.anc4_completed} / ${top.pregnancies_registered})`;
  }

  // Lowest district
  if (lowest) {
    document.getElementById('kpi-low-district').textContent = lowest.district;
    document.getElementById('kpi-low-rate').textContent = `${lowest.coverage_rate_formatted}%`;
    const gap = (totals.overallRate - lowest.coverage_rate).toFixed(1);
    document.getElementById('kpi-low-subtext').textContent = `-${gap}% below state avg (${lowest.anc4_completed} / ${lowest.pregnancies_registered})`;
  }

  // Beneficiaries
  document.getElementById('kpi-total-completed').textContent = totals.totalAnc4.toLocaleString();
  document.getElementById('kpi-total-registered').textContent = totals.totalReg.toLocaleString();
  document.getElementById('kpi-gap-subtext').textContent = `${(totals.totalReg - totals.totalAnc4).toLocaleString()} missed full 4 checkups`;
}

// Render Main Visual Chart
function renderChart() {
  const ctx = document.getElementById('mainCoverageChart');
  if (!ctx || typeof Chart === 'undefined') return;

  if (chartInstance) {
    chartInstance.destroy();
  }

  const currentYear = selectedYear === 'all' ? availableYears[0] : parseInt(selectedYear, 10);

  if (viewMode === 'trend' || selectedYear === 'all') {
    // Multi-Year Trend Line Chart
    document.getElementById('chart-main-title').textContent = 'District 4-ANC Coverage Trends (2021 – 2023)';
    document.getElementById('chart-main-subtitle').textContent = 'Longitudinal tracking of antenatal coverage improvements across all 5 districts (2021–2023)';

    const years = [...availableYears].sort((a, b) => a - b);
    const colorPalette = [
      { border: '#0d9488', bg: 'rgba(13, 148, 136, 0.1)' },
      { border: '#2563eb', bg: 'rgba(37, 99, 235, 0.1)' },
      { border: '#d97706', bg: 'rgba(217, 119, 6, 0.1)' },
      { border: '#e11d48', bg: 'rgba(225, 29, 72, 0.1)' },
      { border: '#7c3aed', bg: 'rgba(124, 58, 237, 0.1)' },
    ];

    const datasets = availableDistricts.map((district, idx) => {
      const color = colorPalette[idx % colorPalette.length];
      const data = years.map(y => {
        const item = rawData.find(r => r.district === district && r.year === y);
        return item ? parseFloat(item.coverage_rate_formatted) : 0;
      });

      return {
        label: district,
        data: data,
        borderColor: color.border,
        backgroundColor: color.bg,
        borderWidth: 3,
        pointBackgroundColor: color.border,
        pointBorderColor: '#fff',
        pointHoverRadius: 7,
        pointRadius: 5,
        tension: 0.25,
        fill: false
      };
    });

    chartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: years.map(y => `Year ${y}`),
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              boxWidth: 12,
              font: { weight: 'bold', size: 12 }
            }
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                return ` ${context.dataset.label}: ${context.parsed.y}%`;
              }
            }
          }
        },
        scales: {
          y: {
            min: 40,
            max: 100,
            title: {
              display: true,
              text: '4-ANC Coverage Rate (%)',
              font: { weight: 'bold' }
            },
            ticks: {
              callback: val => `${val}%`
            },
            grid: { color: '#f1f5f9' }
          },
          x: {
            grid: { color: '#f8fafc' }
          }
        }
      }
    });

  } else if (viewMode === 'volumes') {
    // Registered vs Completed Volumes
    document.getElementById('chart-main-title').textContent = `Pregnancies Registered vs ANC4 Completed (${currentYear})`;
    document.getElementById('chart-main-subtitle').textContent = 'Raw volume count comparison showing total registered vs mothers completing 4 ANC checkups';

    const filtered = getFilteredData().filter(r => r.year === currentYear);
    const labels = filtered.map(r => r.district);
    const regData = filtered.map(r => r.pregnancies_registered);
    const anc4Data = filtered.map(r => r.anc4_completed);

    chartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'ANC4 Completed',
            data: anc4Data,
            backgroundColor: '#0d9488',
            borderRadius: 6
          },
          {
            label: 'Pregnancies Registered',
            data: regData,
            backgroundColor: '#cbd5e1',
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top' },
          tooltip: {
            callbacks: {
              afterBody: function(context) {
                const index = context[0].dataIndex;
                const rec = filtered[index];
                return `Coverage Rate: ${rec.coverage_rate_formatted}%`;
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: 'Number of Mothers' },
            grid: { color: '#f1f5f9' }
          }
        }
      }
    });

  } else {
    // Standard Coverage Rate Bar Comparison
    document.getElementById('chart-main-title').textContent = `District 4-ANC Coverage Rate Comparison (${currentYear})`;
    document.getElementById('chart-main-subtitle').textContent = `Comparative percentage of registered pregnant women completing 4 checkups in ${currentYear}`;

    const filtered = getFilteredData().filter(r => r.year === currentYear);
    const labels = filtered.map(r => r.district);
    const dataValues = filtered.map(r => parseFloat(r.coverage_rate_formatted));

    // Dynamic color gradient based on rate
    const barColors = dataValues.map(val => {
      if (val >= 80) return '#059669'; // High emerald
      if (val >= 70) return '#0d9488'; // Good teal
      if (val >= 60) return '#0284c7'; // Moderate sky
      return '#d97706'; // Low amber
    });

    chartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: '4-ANC Coverage Rate (%)',
          data: dataValues,
          backgroundColor: barColors,
          borderRadius: 8,
          borderSkipped: false,
          barThickness: 38
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(context) {
                const rec = filtered[context.dataIndex];
                return [
                  ` Coverage: ${rec.coverage_rate_formatted}%`,
                  ` ANC4 Completed: ${rec.anc4_completed.toLocaleString()}`,
                  ` Pregnancies Registered: ${rec.pregnancies_registered.toLocaleString()}`,
                  ` Calculation: (${rec.anc4_completed} / ${rec.pregnancies_registered}) × 100`
                ];
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 100,
            title: {
              display: true,
              text: 'Coverage Rate (%)',
              font: { weight: 'bold' }
            },
            ticks: {
              callback: val => `${val}%`
            },
            grid: { color: '#f1f5f9' }
          },
          x: {
            grid: { display: false }
          }
        }
      }
    });
  }
}

// Render District-to-District Head to Head Comparison
function renderHeadToHead() {
  const container = document.getElementById('h2h-result-box');
  if (!container) return;

  const yr = selectedYear === 'all' ? availableYears[0] : parseInt(selectedYear, 10);
  const recA = rawData.find(r => r.district === compareA && r.year === yr);
  const recB = rawData.find(r => r.district === compareB && r.year === yr);

  if (!recA || !recB) {
    container.innerHTML = '<div class="text-xs text-slate-400 text-center py-2">Select districts to compare</div>';
    return;
  }

  const rateA = recA.coverage_rate;
  const rateB = recB.coverage_rate;
  const diffRate = (rateA - rateB).toFixed(2);
  const absDiff = Math.abs(parseFloat(diffRate)).toFixed(2);
  
  let comparisonText = '';
  if (rateA > rateB) {
    comparisonText = `<strong class="text-emerald-700">${recA.district}</strong> leads <strong class="text-slate-700">${recB.district}</strong> by <span class="font-black text-emerald-700">+${absDiff}%</span> percentage points.`;
  } else if (rateB > rateA) {
    comparisonText = `<strong class="text-slate-700">${recB.district}</strong> leads <strong class="text-amber-700">${recA.district}</strong> by <span class="font-black text-slate-800">+${absDiff}%</span> percentage points.`;
  } else {
    comparisonText = `Both districts have an identical coverage rate of <strong>${rateA.toFixed(2)}%</strong>.`;
  }

  container.innerHTML = `
    <div class="grid grid-cols-2 gap-2 text-center pb-2 border-b border-slate-200/80">
      <div class="bg-white p-2 rounded-lg border border-slate-200/70 shadow-xs">
        <div class="text-xs font-bold text-slate-600 truncate">${recA.district}</div>
        <div class="text-lg font-black text-teal-800">${recA.coverage_rate_formatted}%</div>
        <div class="text-[10px] text-slate-400">${recA.anc4_completed} / ${recA.pregnancies_registered}</div>
      </div>
      <div class="bg-white p-2 rounded-lg border border-slate-200/70 shadow-xs">
        <div class="text-xs font-bold text-slate-600 truncate">${recB.district}</div>
        <div class="text-lg font-black text-teal-800">${recB.coverage_rate_formatted}%</div>
        <div class="text-[10px] text-slate-400">${recB.anc4_completed} / ${recB.pregnancies_registered}</div>
      </div>
    </div>
    
    <div class="text-xs text-slate-700 bg-teal-50/60 p-2.5 rounded-lg border border-teal-100">
      ${comparisonText}
    </div>

    <div class="space-y-1.5 text-xs text-slate-600">
      <div class="flex justify-between items-center">
        <span>Volume Difference:</span>
        <span class="font-semibold text-slate-800">${Math.abs(recA.anc4_completed - recB.anc4_completed).toLocaleString()} completed</span>
      </div>
      <div class="flex justify-between items-center">
        <span>Dropout / Missed Gap:</span>
        <span class="font-semibold text-slate-800">${(recA.pregnancies_registered - recA.anc4_completed).toLocaleString()} vs ${(recB.pregnancies_registered - recB.anc4_completed).toLocaleString()}</span>
      </div>
    </div>
  `;
}

// Render Comparison Data Table
function renderTable() {
  const tbody = document.getElementById('district-table-body');
  const tfoot = document.getElementById('district-table-foot');
  if (!tbody) return;

  const currentYear = selectedYear === 'all' ? null : parseInt(selectedYear, 10);
  let records = getFilteredData();

  if (currentYear) {
    records = records.filter(r => r.year === currentYear);
  }

  tbody.innerHTML = '';

  if (records.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="py-8 text-center text-slate-400">No matching district records found.</td></tr>`;
    if (tfoot) tfoot.innerHTML = '';
    return;
  }

  // Calculate state-level benchmark for comparison column
  const totals = calculateTotals(records);

  records.forEach((row, idx) => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-50/80 transition-colors';

    // Rank styling
    let rankBadgeClass = 'rank-badge-other';
    if (idx === 0) rankBadgeClass = 'rank-badge-1';
    else if (idx === 1) rankBadgeClass = 'rank-badge-2';
    else if (idx === 2) rankBadgeClass = 'rank-badge-3';

    // Difference from average
    const diffFromAvg = (row.coverage_rate - totals.overallRate);
    const diffFormatted = (diffFromAvg >= 0 ? '+' : '') + diffFromAvg.toFixed(2) + ' pp';
    const diffColor = diffFromAvg >= 0 ? 'text-emerald-700 bg-emerald-50' : 'text-amber-700 bg-amber-50';

    // Progress bar color
    let barColor = 'bg-teal-600';
    if (row.coverage_rate >= 80) barColor = 'bg-emerald-600';
    else if (row.coverage_rate < 60) barColor = 'bg-amber-500';

    tr.innerHTML = `
      <td class="py-3.5 px-4">
        <span class="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${rankBadgeClass}">
          ${idx + 1}
        </span>
      </td>
      <td class="py-3.5 px-4 font-semibold text-slate-900">
        ${row.district}
      </td>
      <td class="py-3.5 px-4 text-slate-600">
        ${row.year}
      </td>
      <td class="py-3.5 px-4 text-right font-mono text-slate-700">
        ${row.pregnancies_registered.toLocaleString()}
      </td>
      <td class="py-3.5 px-4 text-right font-mono text-slate-700 font-semibold">
        ${row.anc4_completed.toLocaleString()}
      </td>
      <td class="py-3.5 px-4">
        <div class="flex items-center gap-3">
          <span class="font-mono font-bold text-slate-900 w-14 text-right">${row.coverage_rate_formatted}%</span>
          <div class="flex-1 bg-slate-100 rounded-full h-2.5 overflow-hidden max-w-[120px]">
            <div class="${barColor} h-2.5 rounded-full progress-bar-fill" style="width: ${row.coverage_rate}%"></div>
          </div>
        </div>
      </td>
      <td class="py-3.5 px-4 text-right">
        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${diffColor}">
          ${diffFormatted}
        </span>
      </td>
      <td class="py-3.5 px-4 text-xs text-slate-500 max-w-[180px] truncate" title="${row.source}">
        ${row.source}
      </td>
    `;

    tbody.appendChild(tr);
  });

  // Render Table Footer Summary
  if (tfoot) {
    tfoot.innerHTML = `
      <tr>
        <td class="py-4 px-4 text-slate-800" colspan="3">State Total / Aggregate Rate</td>
        <td class="py-4 px-4 text-right font-mono text-slate-900">${totals.totalReg.toLocaleString()}</td>
        <td class="py-4 px-4 text-right font-mono text-teal-800">${totals.totalAnc4.toLocaleString()}</td>
        <td class="py-4 px-4">
          <div class="flex items-center gap-3">
            <span class="font-mono font-black text-teal-900 w-14 text-right">${totals.overallRateFormatted}%</span>
            <div class="flex-1 bg-slate-200 rounded-full h-3 overflow-hidden max-w-[120px]">
              <div class="bg-teal-700 h-3 rounded-full" style="width: ${totals.overallRate}%"></div>
            </div>
          </div>
        </td>
        <td class="py-4 px-4 text-right text-xs text-slate-500">Benchmark</td>
        <td class="py-4 px-4 text-xs text-slate-500">5 reporting districts</td>
      </tr>
    `;
  }
}

// Render Multi-Year Matrix (2021 - 2023)
function renderProgressionMatrix() {
  const tbody = document.getElementById('matrix-table-body');
  if (!tbody) return;

  tbody.innerHTML = '';
  const years = [...availableYears].sort((a, b) => a - b);

  availableDistricts.forEach(district => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-50/70 transition-colors';

    const rates = years.map(yr => {
      const rec = rawData.find(r => r.district === district && r.year === yr);
      return rec ? rec.coverage_rate : null;
    });

    const firstVal = rates[0];
    const lastVal = rates[rates.length - 1];
    const totalGain = (firstVal !== null && lastVal !== null) ? (lastVal - firstVal).toFixed(2) : 'N/A';

    let cellsHTML = `<td class="py-3 px-4 font-bold text-slate-800">${district}</td>`;
    rates.forEach(r => {
      cellsHTML += `<td class="py-3 px-4 text-center font-mono font-medium text-slate-700">${r !== null ? r.toFixed(2) + '%' : '-'}</td>`;
    });

    cellsHTML += `
      <td class="py-3 px-4 text-center font-mono font-black text-emerald-600">
        +${totalGain} pp
      </td>
      <td class="py-3 px-4">
        <div class="flex items-center gap-1.5 text-xs text-emerald-700 font-medium">
          <svg class="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
          Continuous Growth
        </div>
      </td>
    `;

    tr.innerHTML = cellsHTML;
    tbody.appendChild(tr);
  });
}

// Render Step-by-Step Live Mathematical Calculation Example
function renderLiveFormulaExample() {
  const tag = document.getElementById('calc-example-tag');
  const box = document.getElementById('calc-step-by-step');
  if (!box) return;

  const yr = selectedYear === 'all' ? availableYears[0] : parseInt(selectedYear, 10);
  const sampleDistrict = compareA || (availableDistricts[0] || 'Patna');
  const rec = rawData.find(r => r.district === sampleDistrict && r.year === yr) || rawData[0];

  if (!rec) return;

  if (tag) tag.textContent = `${rec.district} (${rec.year})`;

  const numerator = rec.anc4_completed;
  const denominator = rec.pregnancies_registered;
  const proportion = (numerator / denominator).toFixed(4);
  const rate = ((numerator / denominator) * 100).toFixed(2);

  box.innerHTML = `
    <div class="text-slate-500 font-sans text-xs mb-1 font-semibold">Step-by-step arithmetic for ${rec.district} in year ${rec.year}:</div>
    <div>1. Numerator (ANC4 Completed) = <span class="font-bold text-emerald-600">${numerator.toLocaleString()}</span></div>
    <div>2. Denominator (Pregnancies Registered) = <span class="font-bold text-sky-600">${denominator.toLocaleString()}</span></div>
    <div>3. Proportion = ${numerator} ÷ ${denominator} = <span class="font-bold text-slate-700">${proportion}</span></div>
    <div class="pt-1 border-t border-slate-200 mt-1 font-bold text-teal-800 text-sm">
      4. Coverage Rate (%) = ${proportion} × 100 = ${rate}%
    </div>
  `;
}

// Export Filtered / Computed Dataset to CSV
function exportFilteredCSV() {
  const yr = selectedYear === 'all' ? '2021_2023' : selectedYear;
  let filename = `ANC4_Coverage_Report_${yr}.csv`;
  
  let csvContent = 'district,year,pregnancies_registered,anc4_completed,coverage_rate_percent,source\n';
  
  const records = selectedYear === 'all' ? rawData : rawData.filter(r => r.year === parseInt(selectedYear, 10));

  records.forEach(r => {
    csvContent += `${r.district},${r.year},${r.pregnancies_registered},${r.anc4_completed},${r.coverage_rate_formatted},"${r.source}"\n`;
  });

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.setAttribute('href', url);
  a.setAttribute('download', filename);
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

// Start app on DOMContentLoaded
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', loadData);
}
