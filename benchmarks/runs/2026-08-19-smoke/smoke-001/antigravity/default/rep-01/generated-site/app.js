// Raw CSV Fallback in case fetch is blocked by file:// CORS
const FALLBACK_CSV = `district,year,children_due,children_fully_immunised,source
Gaya,2022,1000,780,synthetic smoke fixture
Nalanda,2022,800,680,synthetic smoke fixture
Purnia,2022,900,630,synthetic smoke fixture
Gaya,2023,1100,935,synthetic smoke fixture
Nalanda,2023,850,765,synthetic smoke fixture
Purnia,2023,1000,760,synthetic smoke fixture`;

// Color palette for district indicators
const DISTRICT_COLORS = [
  '#3b82f6', // blue
  '#10b981', // emerald
  '#f59e0b', // amber
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f97316'  // orange
];

// Application State
const state = {
  rawRecords: [],
  districts: [],
  years: [],
  selectedYear: '2023',
  selectedDistricts: new Set(),
  chartMode: 'rate', // 'rate' or 'counts'
  sortColumn: 'rate',
  sortAsc: false,
  sources: new Set()
};

// District color mapping
const districtColorMap = new Map();

/**
 * Parse CSV text into array of objects
 */
function parseCSV(csvText) {
  const lines = csvText.trim().split('\n');
  if (lines.length < 2) return [];

  const headers = lines[0].split(',').map(h => h.trim());
  const records = [];

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    const values = line.split(',').map(v => v.trim());
    const row = {};
    headers.forEach((h, idx) => {
      row[h] = values[idx];
    });

    const due = parseFloat(row.children_due) || 0;
    const immunised = parseFloat(row.children_fully_immunised) || 0;
    const rate = due > 0 ? (immunised / due) * 100 : 0;

    records.push({
      district: row.district || 'Unknown',
      year: row.year || 'Unknown',
      children_due: due,
      children_fully_immunised: immunised,
      rate: rate,
      source: row.source || 'N/A'
    });
  }

  return records;
}

/**
 * Initialize Application Data
 */
async function loadData() {
  let csvText = '';
  try {
    const res = await fetch('district_immunisation.csv');
    if (res.ok) {
      csvText = await res.text();
    } else {
      csvText = FALLBACK_CSV;
    }
  } catch (err) {
    console.warn('Direct fetch failed (likely local file:// protocol), using fallback dataset:', err);
    csvText = FALLBACK_CSV;
  }

  state.rawRecords = parseCSV(csvText);

  // Extract unique districts, years, sources
  const distSet = new Set();
  const yearSet = new Set();
  state.sources.clear();

  state.rawRecords.forEach(r => {
    distSet.add(r.district);
    yearSet.add(r.year);
    if (r.source) state.sources.add(r.source);
  });

  state.districts = Array.from(distSet).sort();
  state.years = Array.from(yearSet).sort();

  // Assign distinct colors to districts
  state.districts.forEach((d, i) => {
    districtColorMap.set(d, DISTRICT_COLORS[i % DISTRICT_COLORS.length]);
  });

  // Default selections
  state.selectedDistricts = new Set(state.districts);
  if (state.years.length > 0) {
    // Select latest year by default
    state.selectedYear = state.years[state.years.length - 1];
  }

  // Update source text everywhere
  const sourceString = Array.from(state.sources).join(', ') || 'synthetic smoke fixture';
  document.getElementById('sourceText').textContent = sourceString;
  document.getElementById('footerSourceText').textContent = sourceString;
  document.getElementById('footerSourceInline').textContent = sourceString;

  setupControls();
  render();
}

/**
 * Setup Controls (Years, District Chips, Toggles)
 */
function setupControls() {
  // Setup Year Buttons
  const yearContainer = document.getElementById('yearButtonsContainer');
  const yearSelect = document.getElementById('yearSelect');
  yearContainer.innerHTML = '';
  yearSelect.innerHTML = '';

  // All years option
  const allBtn = document.createElement('button');
  allBtn.type = 'button';
  allBtn.className = `year-btn ${state.selectedYear === 'all' ? 'active' : ''}`;
  allBtn.textContent = 'All Years';
  allBtn.addEventListener('click', () => {
    state.selectedYear = 'all';
    updateYearUI();
    render();
  });
  yearContainer.appendChild(allBtn);

  const allOpt = document.createElement('option');
  allOpt.value = 'all';
  allOpt.textContent = 'All Years';
  yearSelect.appendChild(allOpt);

  state.years.forEach(yr => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `year-btn ${state.selectedYear === yr ? 'active' : ''}`;
    btn.textContent = yr;
    btn.addEventListener('click', () => {
      state.selectedYear = yr;
      updateYearUI();
      render();
    });
    yearContainer.appendChild(btn);

    const opt = document.createElement('option');
    opt.value = yr;
    opt.textContent = yr;
    if (state.selectedYear === yr) opt.selected = true;
    yearSelect.appendChild(opt);
  });

  yearSelect.addEventListener('change', (e) => {
    state.selectedYear = e.target.value;
    updateYearUI();
    render();
  });

  // Setup District Checkboxes
  renderDistrictChips();

  // Select all / Clear buttons
  document.getElementById('selectAllDistricts').addEventListener('click', () => {
    state.selectedDistricts = new Set(state.districts);
    renderDistrictChips();
    render();
  });

  document.getElementById('clearDistricts').addEventListener('click', () => {
    state.selectedDistricts = new Set();
    renderDistrictChips();
    render();
  });

  // Chart Mode Toggles
  document.querySelectorAll('.chart-toggles .toggle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.chart-toggles .toggle-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.chartMode = btn.dataset.mode;
      renderChart();
    });
  });

  // Table Column Sort Handlers
  document.querySelectorAll('#immunisationTable th').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.dataset.sort;
      if (!col) return;

      if (state.sortColumn === col) {
        state.sortAsc = !state.sortAsc;
      } else {
        state.sortColumn = col;
        state.sortAsc = col === 'district' || col === 'year';
      }
      renderTable();
    });
  });

  // Download Table CSV Handler
  const downloadBtn = document.getElementById('downloadTableBtn');
  if (downloadBtn) {
    downloadBtn.addEventListener('click', downloadTableCSV);
  }
}

/**
 * Download currently filtered table data as CSV
 */
function downloadTableCSV() {
  const records = getFilteredRecords();
  if (records.length === 0) {
    alert('No data available to download for the current selection.');
    return;
  }

  // Sort records according to current table sort
  const sorted = [...records].sort((a, b) => {
    let valA = a[state.sortColumn];
    let valB = b[state.sortColumn];

    if (typeof valA === 'string') {
      return state.sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }
    return state.sortAsc ? valA - valB : valB - valA;
  });

  const headers = ['district', 'year', 'children_due', 'children_fully_immunised', 'immunisation_rate_pct', 'source'];
  const csvRows = [headers.join(',')];

  sorted.forEach(r => {
    const row = [
      `"${r.district.replace(/"/g, '""')}"`,
      r.year,
      r.children_due,
      r.children_fully_immunised,
      r.rate.toFixed(2),
      `"${r.source.replace(/"/g, '""')}"`
    ];
    csvRows.push(row.join(','));
  });

  const csvContent = csvRows.join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  
  const filename = state.selectedYear === 'all' 
    ? 'district_immunisation_all_years.csv' 
    : `district_immunisation_${state.selectedYear}.csv`;

  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function updateYearUI() {
  const buttons = document.querySelectorAll('.year-btn');
  buttons.forEach(btn => {
    if (btn.textContent === 'All Years' && state.selectedYear === 'all') {
      btn.classList.add('active');
    } else if (btn.textContent === state.selectedYear) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
  document.getElementById('yearSelect').value = state.selectedYear;
}

function renderDistrictChips() {
  const container = document.getElementById('districtCheckboxes');
  container.innerHTML = '';

  state.districts.forEach(dist => {
    const isSelected = state.selectedDistricts.has(dist);
    const color = districtColorMap.get(dist) || '#3b82f6';

    const chip = document.createElement('label');
    chip.className = `district-chip ${isSelected ? 'selected' : ''}`;

    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = isSelected;
    cb.value = dist;

    cb.addEventListener('change', () => {
      if (cb.checked) {
        state.selectedDistricts.add(dist);
      } else {
        state.selectedDistricts.delete(dist);
      }
      chip.classList.toggle('selected', cb.checked);
      render();
    });

    const dot = document.createElement('span');
    dot.className = 'district-color-dot';
    dot.style.backgroundColor = color;

    const span = document.createElement('span');
    span.textContent = dist;

    chip.appendChild(cb);
    chip.appendChild(dot);
    chip.appendChild(span);
    container.appendChild(chip);
  });
}

/**
 * Filter and sort records based on current state
 */
function getFilteredRecords() {
  return state.rawRecords.filter(r => {
    const matchYear = state.selectedYear === 'all' || r.year === state.selectedYear;
    const matchDistrict = state.selectedDistricts.has(r.district);
    return matchYear && matchDistrict;
  });
}

/**
 * Render All Components
 */
function render() {
  renderSummary();
  renderChart();
  renderTable();
  renderTrends();
}

/**
 * Render Summary Metric Cards
 */
function renderSummary() {
  const records = getFilteredRecords();

  if (records.length === 0) {
    document.getElementById('overallRate').textContent = '0.0%';
    document.getElementById('totalDue').textContent = '0';
    document.getElementById('totalImmunised').textContent = '0';
    document.getElementById('topDistrict').textContent = 'None';
    document.getElementById('topDistrictRate').textContent = 'No district selected';
    return;
  }

  const totalDue = records.reduce((sum, r) => sum + r.children_due, 0);
  const totalImmunised = records.reduce((sum, r) => sum + r.children_fully_immunised, 0);
  const overallRate = totalDue > 0 ? ((totalImmunised / totalDue) * 100).toFixed(1) : '0.0';

  // Find top district by coverage rate
  // Group by district if "all" years selected
  const districtMap = new Map();
  records.forEach(r => {
    if (!districtMap.has(r.district)) {
      districtMap.set(r.district, { due: 0, immunised: 0 });
    }
    const d = districtMap.get(r.district);
    d.due += r.children_due;
    d.immunised += r.children_fully_immunised;
  });

  let bestDistrict = '';
  let bestRate = -1;

  districtMap.forEach((val, name) => {
    const rate = val.due > 0 ? (val.immunised / val.due) * 100 : 0;
    if (rate > bestRate) {
      bestRate = rate;
      bestDistrict = name;
    }
  });

  document.getElementById('overallRate').textContent = `${overallRate}%`;
  document.getElementById('rateSubtext').textContent = `For ${state.selectedYear === 'all' ? 'all recorded years' : 'Year ' + state.selectedYear}`;
  document.getElementById('totalDue').textContent = totalDue.toLocaleString();
  document.getElementById('totalImmunised').textContent = totalImmunised.toLocaleString();

  if (bestDistrict) {
    document.getElementById('topDistrict').textContent = bestDistrict;
    document.getElementById('topDistrictRate').textContent = `${bestRate.toFixed(1)}% coverage rate`;
  } else {
    document.getElementById('topDistrict').textContent = '--';
    document.getElementById('topDistrictRate').textContent = '';
  }
}

/**
 * Render Interactive Bar Chart
 */
function renderChart() {
  const container = document.getElementById('chartContainer');
  container.innerHTML = '';

  const records = getFilteredRecords();

  if (records.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        <p>No districts selected. Please select at least one district above to compare.</p>
      </div>
    `;
    return;
  }

  // Aggregate by district if 'all' years or single year
  const districtData = [];
  const grouped = new Map();

  records.forEach(r => {
    const key = state.selectedYear === 'all' ? `${r.district} (${r.year})` : r.district;
    if (!grouped.has(key)) {
      grouped.set(key, {
        label: key,
        district: r.district,
        year: r.year,
        due: 0,
        immunised: 0
      });
    }
    const item = grouped.get(key);
    item.due += r.children_due;
    item.immunised += r.children_fully_immunised;
  });

  grouped.forEach(item => {
    item.rate = item.due > 0 ? (item.immunised / item.due) * 100 : 0;
    districtData.push(item);
  });

  // Sort by rate descending for clear comparison
  districtData.sort((a, b) => b.rate - a.rate);

  // Maximum value for scaling absolute counts
  const maxDue = Math.max(...districtData.map(d => d.due), 1);

  districtData.forEach(item => {
    const row = document.createElement('div');
    row.className = 'bar-chart-row';

    const color = districtColorMap.get(item.district) || '#3b82f6';

    if (state.chartMode === 'rate') {
      // Coverage Rate % Mode
      row.innerHTML = `
        <div class="bar-label-group">
          <span class="district-color-dot" style="background-color: ${color}"></span>
          <span class="bar-label" title="${item.label}">${item.label}</span>
        </div>
        <div class="bar-track">
          <div class="bar-fill" style="width: ${item.rate.toFixed(1)}%; background: linear-gradient(90deg, ${color} 0%, ${adjustColor(color, -20)} 100%);">
            ${item.rate.toFixed(1)}%
          </div>
        </div>
        <div class="bar-val-text">
          <span>${item.rate.toFixed(1)}%</span>
          <span class="bar-sub-val">${item.immunised.toLocaleString()} / ${item.due.toLocaleString()}</span>
        </div>
      `;
    } else {
      // Absolute Counts Mode
      const duePct = (item.due / maxDue) * 100;
      const immPct = (item.immunised / maxDue) * 100;

      row.innerHTML = `
        <div class="bar-label-group">
          <span class="district-color-dot" style="background-color: ${color}"></span>
          <span class="bar-label" title="${item.label}">${item.label}</span>
        </div>
        <div class="bar-track">
          <div class="bar-fill-due" style="width: ${duePct.toFixed(1)}%;" title="Due: ${item.due}"></div>
          <div class="bar-fill-immunised" style="width: ${immPct.toFixed(1)}%; background: ${color};" title="Immunised: ${item.immunised}"></div>
        </div>
        <div class="bar-val-text">
          <span>${item.immunised.toLocaleString()}</span>
          <span class="bar-sub-val">of ${item.due.toLocaleString()} due</span>
        </div>
      `;
    }

    container.appendChild(row);
  });
}

/**
 * Render Data Table
 */
function renderTable() {
  const tbody = document.getElementById('tableBody');
  const countEl = document.getElementById('recordCount');
  tbody.innerHTML = '';

  const records = getFilteredRecords();
  countEl.textContent = `${records.length} ${records.length === 1 ? 'record' : 'records'}`;

  if (records.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; color: var(--slate-500); padding: 32px;">
          No matching records for current filters.
        </td>
      </tr>
    `;
    return;
  }

  // Sort records
  const sorted = [...records].sort((a, b) => {
    let valA = a[state.sortColumn];
    let valB = b[state.sortColumn];

    if (typeof valA === 'string') {
      return state.sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }
    return state.sortAsc ? valA - valB : valB - valA;
  });

  sorted.forEach(r => {
    const tr = document.createElement('tr');
    const color = districtColorMap.get(r.district) || '#3b82f6';

    let badgeClass = 'medium';
    if (r.rate >= 85) badgeClass = 'high';
    else if (r.rate < 70) badgeClass = 'low';

    tr.innerHTML = `
      <td>
        <div class="district-cell">
          <span class="district-color-dot" style="background-color: ${color}"></span>
          <span>${r.district}</span>
        </div>
      </td>
      <td><strong>${r.year}</strong></td>
      <td>${r.children_due.toLocaleString()}</td>
      <td><strong>${r.children_fully_immunised.toLocaleString()}</strong></td>
      <td>
        <span class="rate-badge ${badgeClass}">
          ${r.rate.toFixed(1)}%
        </span>
      </td>
      <td>
        <span class="source-cell-badge">${r.source}</span>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

/**
 * Render Year-over-Year District Trend Cards
 */
function renderTrends() {
  const container = document.getElementById('trendGrid');
  container.innerHTML = '';

  const trendDistricts = state.districts.filter(d => state.selectedDistricts.has(d));

  if (trendDistricts.length === 0) {
    container.innerHTML = '<p style="color: var(--slate-500); grid-column: 1/-1;">Select districts to view multi-year comparisons.</p>';
    return;
  }

  trendDistricts.forEach(dist => {
    const distRecords = state.rawRecords
      .filter(r => r.district === dist)
      .sort((a, b) => a.year.localeCompare(b.year));

    if (distRecords.length < 2) return;

    const r2022 = distRecords[0];
    const r2023 = distRecords[1];
    const diff = r2023.rate - r2022.rate;
    const diffSign = diff >= 0 ? '+' : '';
    const diffClass = diff >= 0 ? 'positive' : 'negative';
    const color = districtColorMap.get(dist) || '#3b82f6';

    const card = document.createElement('div');
    card.className = 'trend-card';
    card.innerHTML = `
      <div class="trend-card-title">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span class="district-color-dot" style="background-color: ${color}"></span>
          <span>${dist}</span>
        </div>
        <span class="trend-diff ${diffClass}">${diffSign}${diff.toFixed(1)}% YoY</span>
      </div>
      <div class="trend-years-flow">
        <div class="trend-year-item">
          <div class="trend-year-label">${r2022.year}</div>
          <div class="trend-year-pct">${r2022.rate.toFixed(1)}%</div>
          <div style="font-size: 0.75rem; color: var(--slate-500);">${r2022.children_fully_immunised}/${r2022.children_due}</div>
        </div>
        <div class="trend-arrow">&rarr;</div>
        <div class="trend-year-item">
          <div class="trend-year-label">${r2023.year}</div>
          <div class="trend-year-pct" style="color: ${color};">${r2023.rate.toFixed(1)}%</div>
          <div style="font-size: 0.75rem; color: var(--slate-500);">${r2023.children_fully_immunised}/${r2023.children_due}</div>
        </div>
      </div>
    `;
    container.appendChild(card);
  });
}

/**
 * Utility function to lighten/darken hex colors for gradients
 */
function adjustColor(hex, lum) {
  hex = String(hex).replace(/[^0-9a-f]/gi, '');
  if (hex.length < 6) {
    hex = hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2];
  }
  lum = lum || 0;
  let rgb = '#', c, i;
  for (i = 0; i < 3; i++) {
    c = parseInt(hex.substr(i * 2, 2), 16);
    c = Math.round(Math.min(Math.max(0, c + (c * lum / 100)), 255)).toString(16);
    rgb += ('00' + c).substr(c.length);
  }
  return rgb;
}

// Start application when DOM is ready
document.addEventListener('DOMContentLoaded', loadData);
