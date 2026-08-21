/**
 * District Immunisation Dashboard
 * Highly interactive, zero-dependency analytics application
 */

// Fallback dataset matching district_immunisation.csv
const DEFAULT_CSV_DATA = `district,year,children_due,children_fully_immunised,source
Gaya,2022,1000,780,synthetic smoke fixture
Nalanda,2022,800,680,synthetic smoke fixture
Purnia,2022,900,630,synthetic smoke fixture
Gaya,2023,1100,935,synthetic smoke fixture
Nalanda,2023,850,765,synthetic smoke fixture
Purnia,2023,1000,760,synthetic smoke fixture`;

// App State
const state = {
  rawData: [],
  years: [],
  districts: [],
  sources: [],
  selectedYear: '2023',
  selectedDistricts: new Set(),
  h2hA: '',
  h2hB: '',
  searchQuery: '',
  sortCol: 'district',
  sortAsc: true,
  theme: localStorage.getItem('agy_theme') || 'light'
};

// Apply theme on load
document.documentElement.setAttribute('data-theme', state.theme);

// CSV Parser Helper
function parseCSV(csvText) {
  const lines = csvText.trim().split(/\r?\n/).filter(line => line.trim().length > 0);
  if (lines.length < 2) return [];

  const headers = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/['"]+/g, ''));
  const rows = [];

  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(',').map(v => v.trim().replace(/['"]+/g, ''));
    if (values.length < headers.length) continue;

    const rowObj = {};
    headers.forEach((header, index) => {
      rowObj[header] = values[index];
    });

    const district = rowObj['district'] || 'Unknown';
    const year = parseInt(rowObj['year'], 10) || 0;
    const due = parseFloat(rowObj['children_due'] || rowObj['due'] || 0);
    const immunised = parseFloat(rowObj['children_fully_immunised'] || rowObj['fully_immunised'] || rowObj['immunised'] || 0);
    const source = rowObj['source'] || 'Unknown Source';

    const rate = due > 0 ? (immunised / due) * 100 : 0;
    const gap = Math.max(0, due - immunised);

    rows.push({
      district,
      year: year.toString(),
      children_due: due,
      children_fully_immunised: immunised,
      source,
      rate,
      gap
    });
  }

  return rows;
}

// Data Initialization
async function loadData() {
  let csvText = DEFAULT_CSV_DATA;
  try {
    const response = await fetch('district_immunisation.csv');
    if (response.ok) {
      csvText = await response.text();
    }
  } catch (err) {
    console.info('Loaded embedded fallback data:', err);
  }

  state.rawData = parseCSV(csvText);
  extractMetadata();
  initUI();
}

function extractMetadata() {
  const yearsSet = new Set();
  const districtsSet = new Set();
  const sourcesSet = new Set();

  state.rawData.forEach(row => {
    yearsSet.add(row.year);
    districtsSet.add(row.district);
    sourcesSet.add(row.source);
  });

  state.years = Array.from(yearsSet).sort();
  state.districts = Array.from(districtsSet).sort();
  state.sources = Array.from(sourcesSet);

  // Set default selected year to latest available
  if (state.years.length > 0) {
    state.selectedYear = state.years[state.years.length - 1];
  }

  // Select all districts initially
  state.selectedDistricts = new Set(state.districts);

  // Setup initial head to head comparison
  if (state.districts.length >= 2) {
    state.h2hA = state.districts[0];
    state.h2hB = state.districts[1];
  } else if (state.districts.length === 1) {
    state.h2hA = state.districts[0];
    state.h2hB = state.districts[0];
  }
}

// Get Filtered Data
function getFilteredData() {
  return state.rawData.filter(row => {
    const matchesYear = state.selectedYear === 'ALL' || row.year === state.selectedYear;
    const matchesDistrict = state.selectedDistricts.has(row.district);
    const matchesSearch = state.searchQuery === '' || 
      row.district.toLowerCase().includes(state.searchQuery.toLowerCase()) ||
      row.source.toLowerCase().includes(state.searchQuery.toLowerCase()) ||
      row.year.includes(state.searchQuery);
    return matchesYear && matchesDistrict && matchesSearch;
  });
}

// Helper: Format Numbers & Percents
function fmtNum(n) {
  return new Intl.NumberFormat().format(Math.round(n));
}

function fmtPct(n) {
  return n.toFixed(1) + '%';
}

function getPerformanceBadge(rate) {
  if (rate >= 85) {
    return `<span class="badge badge-success">✓ High (≥85%)</span>`;
  } else if (rate >= 75) {
    return `<span class="badge badge-warning">⚡ Moderate (75-84%)</span>`;
  } else {
    return `<span class="badge badge-danger">⚠ Priority (<75%)</span>`;
  }
}

function getRateColor(rate) {
  if (rate >= 85) return 'var(--success)';
  if (rate >= 75) return 'var(--warning)';
  return 'var(--danger)';
}

// Render Functions
function initUI() {
  renderHeaderSource();
  renderYearPills();
  renderDistrictChips();
  renderHeadToHeadSelectors();
  updateDashboard();
}

function renderHeaderSource() {
  const sourceBadge = document.getElementById('headerSourceBadge');
  if (sourceBadge) {
    const uniqueSources = state.sources.join(', ') || 'N/A';
    sourceBadge.innerHTML = `<span>Source:</span> <code>${uniqueSources}</code>`;
  }
}

function renderYearPills() {
  const container = document.getElementById('yearPillGroup');
  if (!container) return;

  let html = '';
  state.years.forEach(year => {
    const active = state.selectedYear === year ? 'active' : '';
    html += `<button type="button" class="pill-btn ${active}" data-year="${year}">${year}</button>`;
  });
  
  const allActive = state.selectedYear === 'ALL' ? 'active' : '';
  html += `<button type="button" class="pill-btn ${allActive}" data-year="ALL">All Years / Trend</button>`;

  container.innerHTML = html;

  container.querySelectorAll('.pill-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      state.selectedYear = btn.getAttribute('data-year');
      container.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      updateDashboard();
    });
  });
}

function renderDistrictChips() {
  const container = document.getElementById('districtBadgesContainer');
  if (!container) return;

  let html = '';
  state.districts.forEach(d => {
    const active = state.selectedDistricts.has(d) ? 'active' : '';
    html += `
      <div class="district-chip ${active}" data-district="${d}">
        <span class="chip-dot"></span>
        <span>${d}</span>
      </div>
    `;
  });

  container.innerHTML = html;

  container.querySelectorAll('.district-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const d = chip.getAttribute('data-district');
      if (state.selectedDistricts.has(d)) {
        if (state.selectedDistricts.size > 1) {
          state.selectedDistricts.delete(d);
          chip.classList.remove('active');
        }
      } else {
        state.selectedDistricts.add(d);
        chip.classList.add('active');
      }
      updateDashboard();
    });
  });
}

function renderHeadToHeadSelectors() {
  const selectA = document.getElementById('h2hSelectA');
  const selectB = document.getElementById('h2hSelectB');
  if (!selectA || !selectB) return;

  const buildOptions = (selected) => {
    return state.districts.map(d => 
      `<option value="${d}" ${d === selected ? 'selected' : ''}>${d}</option>`
    ).join('');
  };

  selectA.innerHTML = buildOptions(state.h2hA);
  selectB.innerHTML = buildOptions(state.h2hB);

  selectA.addEventListener('change', (e) => {
    state.h2hA = e.target.value;
    renderHeadToHead();
  });

  selectB.addEventListener('change', (e) => {
    state.h2hB = e.target.value;
    renderHeadToHead();
  });
}

function updateDashboard() {
  renderKPIs();
  renderRateChart();
  renderVolumeChart();
  renderYearOverYearProgress();
  renderHeadToHead();
  renderTable();
  renderSourceBreakdown();
}

// 1. KPI Cards
function renderKPIs() {
  const filtered = getFilteredData();
  
  let totalDue = 0;
  let totalImmunised = 0;

  filtered.forEach(r => {
    totalDue += r.children_due;
    totalImmunised += r.children_fully_immunised;
  });

  const overallRate = totalDue > 0 ? (totalImmunised / totalDue) * 100 : 0;
  const totalGap = Math.max(0, totalDue - totalImmunised);

  // Highest and lowest performing districts in selection
  let highest = null;
  let lowest = null;

  filtered.forEach(r => {
    if (!highest || r.rate > highest.rate) highest = r;
    if (!lowest || r.rate < lowest.rate) lowest = r;
  });

  document.getElementById('kpiTotalDue').textContent = fmtNum(totalDue);
  document.getElementById('kpiTotalImmunised').textContent = fmtNum(totalImmunised);
  
  const rateElem = document.getElementById('kpiRate');
  rateElem.textContent = fmtPct(overallRate);
  
  const progressBar = document.getElementById('kpiRateProgressBar');
  if (progressBar) {
    progressBar.style.width = `${Math.min(100, overallRate)}%`;
    progressBar.style.backgroundColor = getRateColor(overallRate);
  }

  const topDistrictElem = document.getElementById('kpiTopDistrict');
  if (highest) {
    topDistrictElem.innerHTML = `<strong>${highest.district}</strong> (${fmtPct(highest.rate)})`;
  } else {
    topDistrictElem.textContent = 'N/A';
  }

  const gapDistrictElem = document.getElementById('kpiGapSummary');
  if (lowest) {
    gapDistrictElem.innerHTML = `Total Unimmunised Gap: <strong>${fmtNum(totalGap)}</strong> (${lowest.district} lowest at ${fmtPct(lowest.rate)})`;
  } else {
    gapDistrictElem.textContent = `Total Unimmunised Gap: ${fmtNum(totalGap)}`;
  }
}

// 2. District Immunisation Rate Bar Chart
function renderRateChart() {
  const container = document.getElementById('rateBarChartContainer');
  if (!container) return;

  const filtered = getFilteredData();
  if (filtered.length === 0) {
    container.innerHTML = `<div class="empty-state">No data available for the current selection.</div>`;
    return;
  }

  // Group by district (if year is ALL, compute average rate or per-district breakdown)
  const districtMap = new Map();
  filtered.forEach(r => {
    if (!districtMap.has(r.district)) {
      districtMap.set(r.district, { district: r.district, due: 0, immunised: 0, years: [] });
    }
    const item = districtMap.get(r.district);
    item.due += r.children_due;
    item.immunised += r.children_fully_immunised;
    item.years.push(r.year);
  });

  const districtList = Array.from(districtMap.values()).map(d => ({
    district: d.district,
    rate: d.due > 0 ? (d.immunised / d.due) * 100 : 0,
    due: d.due,
    immunised: d.immunised,
    gap: d.due - d.immunised
  })).sort((a, b) => b.rate - a.rate);

  let html = `<div class="district-bar-list">`;
  districtList.forEach(item => {
    const colorClass = item.rate >= 85 ? 'success' : item.rate >= 75 ? 'warning' : '';
    html += `
      <div class="district-bar-item">
        <div class="bar-meta">
          <span class="bar-district-name">
            <strong>${item.district}</strong>
            ${getPerformanceBadge(item.rate)}
          </span>
          <span class="bar-stat-val" style="color: ${getRateColor(item.rate)}">
            ${fmtPct(item.rate)} (${fmtNum(item.immunised)} / ${fmtNum(item.due)})
          </span>
        </div>
        <div class="bar-track-wrapper">
          <div class="bar-track" title="${item.district}: ${fmtPct(item.rate)} (${fmtNum(item.immunised)} of ${fmtNum(item.due)} immunised)">
            <div class="bar-fill-immunised ${colorClass}" style="width: ${item.rate}%">
              ${fmtPct(item.rate)}
            </div>
            <div class="bar-fill-gap" style="width: ${100 - item.rate}%" title="Gap: ${fmtNum(item.gap)} children unimmunised">
              ${item.gap > 0 ? `Gap: ${fmtNum(item.gap)}` : ''}
            </div>
          </div>
        </div>
      </div>
    `;
  });
  html += `</div>`;

  container.innerHTML = html;
}

// 3. Volume Breakdown Chart
function renderVolumeChart() {
  const container = document.getElementById('volumeChartContainer');
  if (!container) return;

  const filtered = getFilteredData();
  if (filtered.length === 0) {
    container.innerHTML = `<div class="empty-state">No data available.</div>`;
    return;
  }

  const districtMap = new Map();
  filtered.forEach(r => {
    if (!districtMap.has(r.district)) {
      districtMap.set(r.district, { district: r.district, due: 0, immunised: 0 });
    }
    const item = districtMap.get(r.district);
    item.due += r.children_due;
    item.immunised += r.children_fully_immunised;
  });

  const list = Array.from(districtMap.values());
  const maxDue = Math.max(...list.map(l => l.due), 100);

  let html = `<div class="district-bar-list">`;
  list.forEach(item => {
    const duePct = (item.due / maxDue) * 100;
    const immPct = (item.immunised / maxDue) * 100;
    const gap = item.due - item.immunised;

    html += `
      <div class="district-bar-item">
        <div class="bar-meta">
          <span class="bar-district-name"><strong>${item.district}</strong></span>
          <span class="bar-stat-val">${fmtNum(item.immunised)} immunised / ${fmtNum(item.due)} due (Gap: ${fmtNum(gap)})</span>
        </div>
        <div class="bar-track" style="height: 20px;">
          <div style="background: var(--primary); width: ${immPct}%; height: 100%;" title="Immunised: ${fmtNum(item.immunised)}"></div>
          <div style="background: rgba(239, 68, 68, 0.35); width: ${duePct - immPct}%; height: 100%; border-left: 1px dashed red;" title="Unimmunised Gap: ${fmtNum(gap)}"></div>
        </div>
      </div>
    `;
  });
  html += `</div>`;

  container.innerHTML = html;
}

// 4. Multi-Year Progression (YoY Comparison)
function renderYearOverYearProgress() {
  const container = document.getElementById('yoyContainer');
  if (!container) return;

  if (state.years.length < 2) {
    container.innerHTML = `<p class="source-detail-val" style="color: var(--text-muted)">Requires multiple years of data for trend comparison.</p>`;
    return;
  }

  const y1 = state.years[0];
  const y2 = state.years[1];

  let html = `
    <div style="display: flex; flex-direction: column; gap: 0.75rem;">
      <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.25rem;">
        Comparing progress from <strong>${y1}</strong> to <strong>${y2}</strong> across districts:
      </div>
  `;

  state.districts.forEach(district => {
    const r1 = state.rawData.find(r => r.district === district && r.year === y1);
    const r2 = state.rawData.find(r => r.district === district && r.year === y2);

    if (r1 && r2) {
      const deltaRate = r2.rate - r1.rate;
      const deltaImmunised = r2.children_fully_immunised - r1.children_fully_immunised;
      const isPositive = deltaRate >= 0;
      const badgeColor = isPositive ? 'var(--success)' : 'var(--danger)';
      const sign = isPositive ? '+' : '';

      html += `
        <div style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-input); padding: 0.75rem 1rem; border-radius: var(--radius-md); border: 1px solid var(--border-color);">
          <div>
            <strong>${district}</strong>:
            <span style="color: var(--text-secondary); margin-left: 0.5rem;">${y1} (${fmtPct(r1.rate)}) ➔ ${y2} (${fmtPct(r2.rate)})</span>
          </div>
          <div style="font-weight: 700; color: ${badgeColor}; display: flex; align-items: center; gap: 0.5rem;">
            <span>${sign}${fmtPct(deltaRate)}</span>
            <span style="font-size: 0.75rem; font-weight: normal; color: var(--text-secondary);">(${sign}${fmtNum(deltaImmunised)} children)</span>
          </div>
        </div>
      `;
    }
  });

  html += `</div>`;
  container.innerHTML = html;
}

// 5. Head to Head District Comparison
function renderHeadToHead() {
  const container = document.getElementById('h2hResultContainer');
  if (!container) return;

  const targetYear = state.selectedYear === 'ALL' ? (state.years[state.years.length - 1] || '2023') : state.selectedYear;

  const rowA = state.rawData.find(r => r.district === state.h2hA && r.year === targetYear);
  const rowB = state.rawData.find(r => r.district === state.h2hB && r.year === targetYear);

  if (!rowA || !rowB) {
    container.innerHTML = `<div class="empty-state">Select two districts to compare.</div>`;
    return;
  }

  const rateDiff = rowA.rate - rowB.rate;
  const rateDiffText = Math.abs(rateDiff).toFixed(1) + '%';
  const leadingDistrict = rateDiff > 0 ? rowA.district : rateDiff < 0 ? rowB.district : 'Tied';

  container.innerHTML = `
    <div class="h2h-grid">
      <!-- District A -->
      <div class="h2h-card">
        <div class="h2h-district">
          <span>${rowA.district}</span>
          <span style="font-size: 0.8rem; color: var(--text-muted);">${targetYear}</span>
        </div>
        <div class="h2h-metric-row">
          <span>Immunisation Rate</span>
          <strong style="color: ${getRateColor(rowA.rate)}">${fmtPct(rowA.rate)}</strong>
        </div>
        <div class="h2h-metric-row">
          <span>Fully Immunised</span>
          <strong>${fmtNum(rowA.children_fully_immunised)}</strong>
        </div>
        <div class="h2h-metric-row">
          <span>Children Due</span>
          <strong>${fmtNum(rowA.children_due)}</strong>
        </div>
        <div class="h2h-metric-row">
          <span>Unimmunised Gap</span>
          <strong style="color: var(--danger-text)">${fmtNum(rowA.gap)}</strong>
        </div>
      </div>

      <!-- VS Badge -->
      <div class="h2h-vs">
        <div>VS</div>
        <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.25rem;">
          ${rateDiff !== 0 ? `<strong>${leadingDistrict}</strong> +${rateDiffText}` : 'Equal Rate'}
        </div>
      </div>

      <!-- District B -->
      <div class="h2h-card">
        <div class="h2h-district">
          <span>${rowB.district}</span>
          <span style="font-size: 0.8rem; color: var(--text-muted);">${targetYear}</span>
        </div>
        <div class="h2h-metric-row">
          <span>Immunisation Rate</span>
          <strong style="color: ${getRateColor(rowB.rate)}">${fmtPct(rowB.rate)}</strong>
        </div>
        <div class="h2h-metric-row">
          <span>Fully Immunised</span>
          <strong>${fmtNum(rowB.children_fully_immunised)}</strong>
        </div>
        <div class="h2h-metric-row">
          <span>Children Due</span>
          <strong>${fmtNum(rowB.children_due)}</strong>
        </div>
        <div class="h2h-metric-row">
          <span>Unimmunised Gap</span>
          <strong style="color: var(--danger-text)">${fmtNum(rowB.gap)}</strong>
        </div>
      </div>
    </div>
  `;
}

// 6. Data Table
function renderTable() {
  const tbody = document.getElementById('tableBody');
  if (!tbody) return;

  const data = getFilteredData();

  // Sorting
  data.sort((a, b) => {
    let valA = a[state.sortCol];
    let valB = b[state.sortCol];

    if (typeof valA === 'string') {
      return state.sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }
    return state.sortAsc ? valA - valB : valB - valA;
  });

  if (data.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No matching district records found.</td></tr>`;
    return;
  }

  let html = '';
  data.forEach(row => {
    html += `
      <tr>
        <td><strong>${row.district}</strong></td>
        <td><span class="badge" style="background: var(--bg-input); border: 1px solid var(--border-color);">${row.year}</span></td>
        <td>${fmtNum(row.children_due)}</td>
        <td><strong style="color: var(--primary)">${fmtNum(row.children_fully_immunised)}</strong></td>
        <td><span style="color: var(--danger-text)">${fmtNum(row.gap)}</span></td>
        <td>
          <div class="rate-cell">
            <div class="rate-cell-bar">
              <div class="rate-cell-fill" style="width: ${row.rate}%; background-color: ${getRateColor(row.rate)}"></div>
            </div>
            <strong>${fmtPct(row.rate)}</strong>
          </div>
        </td>
        <td>${getPerformanceBadge(row.rate)}</td>
        <td><span class="badge badge-source">${row.source}</span></td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
}

// 7. Source & Metadata Breakdown Section
function renderSourceBreakdown() {
  const container = document.getElementById('sourceBreakdownGrid');
  if (!container) return;

  const uniqueSources = Array.from(new Set(state.rawData.map(r => r.source))).join(', ') || 'synthetic smoke fixture';
  const totalRows = state.rawData.length;
  const uniqueDistricts = state.districts.join(', ');
  const yearsTracked = state.years.join(', ');

  container.innerHTML = `
    <div class="source-detail-item">
      <span class="source-detail-label">Dataset Source</span>
      <span class="source-detail-val" style="color: var(--info-text); font-family: monospace;">${uniqueSources}</span>
    </div>
    <div class="source-detail-item">
      <span class="source-detail-label">Source File</span>
      <span class="source-detail-val" style="font-family: monospace;">district_immunisation.csv</span>
    </div>
    <div class="source-detail-item">
      <span class="source-detail-label">Districts Covered (${state.districts.length})</span>
      <span class="source-detail-val">${uniqueDistricts}</span>
    </div>
    <div class="source-detail-item">
      <span class="source-detail-label">Years Available (${state.years.length})</span>
      <span class="source-detail-val">${yearsTracked}</span>
    </div>
  `;
}

// 8. Event Listeners Setup
document.addEventListener('DOMContentLoaded', () => {
  loadData();

  // District Quick Selectors
  const selectAllBtn = document.getElementById('selectAllDistrictsBtn');
  if (selectAllBtn) {
    selectAllBtn.addEventListener('click', () => {
      state.selectedDistricts = new Set(state.districts);
      document.querySelectorAll('.district-chip').forEach(c => c.classList.add('active'));
      updateDashboard();
    });
  }

  const clearAllBtn = document.getElementById('clearDistrictsBtn');
  if (clearAllBtn) {
    clearAllBtn.addEventListener('click', () => {
      if (state.districts.length > 0) {
        state.selectedDistricts = new Set([state.districts[0]]);
        document.querySelectorAll('.district-chip').forEach((c, idx) => {
          if (idx === 0) c.classList.add('active');
          else c.classList.remove('active');
        });
        updateDashboard();
      }
    });
  }

  // Search input
  const searchInput = document.getElementById('tableSearch');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      state.searchQuery = e.target.value;
      renderTable();
    });
  }

  // Table Sorting
  document.querySelectorAll('.data-table th[data-col]').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.getAttribute('data-col');
      if (state.sortCol === col) {
        state.sortAsc = !state.sortAsc;
      } else {
        state.sortCol = col;
        state.sortAsc = true;
      }

      document.querySelectorAll('.data-table th').forEach(h => {
        h.classList.remove('sorted');
        const arrow = h.querySelector('.sort-arrow');
        if (arrow) arrow.textContent = '⇅';
      });

      th.classList.add('sorted');
      const arrow = th.querySelector('.sort-arrow');
      if (arrow) arrow.textContent = state.sortAsc ? '▲' : '▼';

      renderTable();
    });
  });

  // Download 2023 Table Specifically
  const download2023Data = () => {
    const data2023 = state.rawData.filter(r => r.year === '2023');
    let csvContent = 'district,year,children_due,children_fully_immunised,immunisation_rate_pct,unimmunised_gap,source\n';
    data2023.forEach(r => {
      csvContent += `"${r.district}",${r.year},${r.children_due},${r.children_fully_immunised},${r.rate.toFixed(2)},${r.gap},"${r.source}"\n`;
    });

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', 'district_immunisation_2023.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const d2023Btn = document.getElementById('download2023Btn');
  if (d2023Btn) d2023Btn.addEventListener('click', download2023Data);

  const d2023TopBtn = document.getElementById('download2023TopBtn');
  if (d2023TopBtn) d2023TopBtn.addEventListener('click', download2023Data);

  // Export Current View CSV button
  const triggerExport = () => {
    const data = getFilteredData();
    let csvContent = 'district,year,children_due,children_fully_immunised,immunisation_rate_pct,unimmunised_gap,source\n';
    data.forEach(r => {
      csvContent += `"${r.district}",${r.year},${r.children_due},${r.children_fully_immunised},${r.rate.toFixed(2)},${r.gap},"${r.source}"\n`;
    });

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `district_immunisation_${state.selectedYear}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportBtn = document.getElementById('exportCsvBtn');
  if (exportBtn) exportBtn.addEventListener('click', triggerExport);

  const exportTopBtn = document.getElementById('exportCsvBtnTop');
  if (exportTopBtn) exportTopBtn.addEventListener('click', triggerExport);

  // Theme Toggle
  const themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      state.theme = state.theme === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', state.theme);
      localStorage.setItem('agy_theme', state.theme);
      themeToggle.textContent = state.theme === 'dark' ? '☀️' : '🌙';
    });
    themeToggle.textContent = state.theme === 'dark' ? '☀️' : '🌙';
  }

  // Custom CSV Upload
  const fileInput = document.getElementById('csvFileInput');
  const uploadBtn = document.getElementById('uploadCsvBtn');
  if (uploadBtn && fileInput) {
    uploadBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (event) => {
        const text = event.target.result;
        state.rawData = parseCSV(text);
        extractMetadata();
        initUI();
      };
      reader.readAsText(file);
    });
  }
});
