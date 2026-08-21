/**
 * District Immunisation Analytics Dashboard Engine
 */

// Embedded fallback data matching district_immunisation.csv exactly
const FALLBACK_CSV = `district,year,children_due,children_fully_immunised,source
Gaya,2022,1000,780,synthetic smoke fixture
Nalanda,2022,800,680,synthetic smoke fixture
Purnia,2022,900,630,synthetic smoke fixture
Gaya,2023,1100,935,synthetic smoke fixture
Nalanda,2023,850,765,synthetic smoke fixture
Purnia,2023,1000,760,synthetic smoke fixture`;

// App State
let rawData = [];
let availableYears = [];
let availableDistricts = [];
let activeYear = '2023'; // Default to latest year
let selectedDistricts = new Set();
let primarySource = 'synthetic smoke fixture';

// Chart Instances
let compareChartInstance = null;
let rateChartInstance = null;
let trendChartInstance = null;

// Helper: Parse CSV text into array of objects
function parseCSV(csvText) {
  const lines = csvText.trim().split('\n');
  if (lines.length < 2) return [];
  
  const headers = lines[0].split(',').map(h => h.trim());
  const results = [];
  
  for (let i = 1; i < lines.length; i++) {
    const currentLine = lines[i].split(',').map(item => item.trim());
    if (currentLine.length === headers.length) {
      const entry = {
        district: currentLine[0],
        year: currentLine[1],
        children_due: parseInt(currentLine[2], 10) || 0,
        children_fully_immunised: parseInt(currentLine[3], 10) || 0,
        source: currentLine[4] || 'synthetic smoke fixture'
      };
      // Calculate coverage percentage
      entry.coverage_pct = entry.children_due > 0 
        ? parseFloat(((entry.children_fully_immunised / entry.children_due) * 100).toFixed(1))
        : 0;
      results.push(entry);
    }
  }
  return results;
}

// Load Dataset
async function initData() {
  try {
    const response = await fetch('district_immunisation.csv');
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const text = await response.text();
    rawData = parseCSV(text);
  } catch (err) {
    console.warn('Fetching district_immunisation.csv via HTTP failed, using fallback CSV content:', err);
    rawData = parseCSV(FALLBACK_CSV);
  }

  // Extract metadata
  availableYears = [...new Set(rawData.map(d => d.year))].sort();
  availableDistricts = [...new Set(rawData.map(d => d.district))].sort();
  selectedDistricts = new Set(availableDistricts); // Select all by default
  
  if (rawData.length > 0) {
    primarySource = rawData[0].source;
  }

  // Render UI controls & components
  renderSourceBadges();
  renderYearControls();
  renderDistrictChips();
  renderTable();
  setupDownloadButton();
  updateDashboard();
}

// Download CSV function
function downloadCSV() {
  const dataToExport = activeYear === 'YoY' 
    ? rawData 
    : rawData.filter(d => d.year === activeYear);

  let csvRows = ["district,year,children_due,children_fully_immunised,coverage_rate_pct,source"];
  dataToExport.forEach(row => {
    csvRows.push(`${row.district},${row.year},${row.children_due},${row.children_fully_immunised},${row.coverage_pct}%,${row.source}`);
  });

  const blob = new Blob([csvRows.join("\n")], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  const filename = activeYear === 'YoY' ? 'district_immunisation_all_years.csv' : `district_immunisation_${activeYear}.csv`;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function setupDownloadButton() {
  const btn = document.getElementById('downloadCsvBtn');
  if (btn) {
    btn.onclick = downloadCSV;
  }
}

// Render Source Attribution Tags
function renderSourceBadges() {
  const badgeText = `Source: ${primarySource}`;
  document.querySelectorAll('.source-name').forEach(el => {
    el.textContent = badgeText;
  });
}

// Render Year Selection Buttons
function renderYearControls() {
  const container = document.getElementById('yearControl');
  if (!container) return;
  container.innerHTML = '';

  availableYears.forEach(year => {
    const btn = document.createElement('button');
    btn.className = `segmented-btn ${year === activeYear ? 'active' : ''}`;
    btn.textContent = year;
    btn.onclick = () => {
      activeYear = year;
      document.querySelectorAll('#yearControl .segmented-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      updateDashboard();
    };
    container.appendChild(btn);
  });

  // Add YoY All-Years Option
  const yoyBtn = document.createElement('button');
  yoyBtn.className = `segmented-btn ${activeYear === 'YoY' ? 'active' : ''}`;
  yoyBtn.textContent = 'All Years (YoY)';
  yoyBtn.onclick = () => {
    activeYear = 'YoY';
    document.querySelectorAll('#yearControl .segmented-btn').forEach(b => b.classList.remove('active'));
    yoyBtn.classList.add('active');
    updateDashboard();
  };
  container.appendChild(yoyBtn);
}

// Render District Filter Chips
function renderDistrictChips() {
  const container = document.getElementById('districtChips');
  if (!container) return;
  container.innerHTML = '';

  availableDistricts.forEach(district => {
    const chip = document.createElement('button');
    chip.className = `chip-btn ${selectedDistricts.has(district) ? 'selected' : ''}`;
    chip.innerHTML = `<span>${selectedDistricts.has(district) ? '✓' : '+'}</span> ${district}`;
    chip.onclick = () => {
      if (selectedDistricts.has(district)) {
        if (selectedDistricts.size > 1) { // Keep at least one selected
          selectedDistricts.delete(district);
        }
      } else {
        selectedDistricts.add(district);
      }
      renderDistrictChips();
      updateDashboard();
    };
    container.appendChild(chip);
  });
}

// Core Dashboard Update
function updateDashboard() {
  let filteredData = [];

  if (activeYear === 'YoY') {
    filteredData = rawData.filter(d => selectedDistricts.has(d.district));
  } else {
    filteredData = rawData.filter(d => d.year === activeYear && selectedDistricts.has(d.district));
  }

  const dlBtn = document.getElementById('downloadCsvBtn');
  if (dlBtn) {
    dlBtn.innerHTML = `📥 Download ${activeYear === 'YoY' ? 'All Years' : activeYear} CSV Table`;
  }

  updateStats(filteredData);
  renderCharts(filteredData);
  renderDistrictCards(filteredData);
}

// Update Top KPI Cards
function updateStats(data) {
  let totalDue = 0;
  let totalImmunised = 0;
  let topDistrict = '-';
  let topRate = -1;

  data.forEach(d => {
    totalDue += d.children_due;
    totalImmunised += d.children_fully_immunised;
    if (d.coverage_pct > topRate) {
      topRate = d.coverage_pct;
      topDistrict = `${d.district} (${d.coverage_pct}%)`;
    }
  });

  const overallRate = totalDue > 0 ? ((totalImmunised / totalDue) * 100).toFixed(1) : 0;

  document.getElementById('statTotalDue').textContent = totalDue.toLocaleString();
  document.getElementById('statTotalImmunised').textContent = totalImmunised.toLocaleString();
  document.getElementById('statOverallRate').textContent = `${overallRate}%`;
  document.getElementById('statTopDistrict').textContent = topDistrict;

  // View title description
  const label = activeYear === 'YoY' ? 'All Years Combined' : `Year ${activeYear}`;
  document.getElementById('viewSubtitle').textContent = `Showing data for ${label} across ${selectedDistricts.size} district(s)`;
}

// Render Charts
function renderCharts(data) {
  renderCompareChart(data);
  renderRateChart(data);
}

// Chart 1: District Comparison Bar Chart (Due vs Fully Immunised)
function renderCompareChart(data) {
  const ctx = document.getElementById('compareChart').getContext('2d');
  if (compareChartInstance) compareChartInstance.destroy();

  // Group by district
  const labels = [...selectedDistricts];
  const dueValues = [];
  const immunisedValues = [];

  labels.forEach(dist => {
    const distData = data.filter(d => d.district === dist);
    const totalDue = distData.reduce((sum, d) => sum + d.children_due, 0);
    const totalImm = distData.reduce((sum, d) => sum + d.children_fully_immunised, 0);
    dueValues.push(totalDue);
    immunisedValues.push(totalImm);
  });

  compareChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Children Due',
          data: dueValues,
          backgroundColor: 'rgba(6, 182, 212, 0.5)',
          borderColor: '#06b6d4',
          borderWidth: 1.5,
          borderRadius: 6
        },
        {
          label: 'Fully Immunised',
          data: immunisedValues,
          backgroundColor: 'rgba(16, 185, 129, 0.7)',
          borderColor: '#10b981',
          borderWidth: 1.5,
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: '#9ca3af', font: { family: 'Inter', size: 12 } }
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          padding: 12,
          backgroundColor: '#131b2e',
          titleColor: '#fff',
          bodyColor: '#9ca3af',
          borderColor: 'rgba(255, 255, 255, 0.1)',
          borderWidth: 1
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#9ca3af' }
        },
        y: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#9ca3af' },
          beginAtZero: true
        }
      }
    }
  });
}

// Chart 2: Immunisation Rate (%) Ranking Chart
function renderRateChart(data) {
  const ctx = document.getElementById('rateChart').getContext('2d');
  if (rateChartInstance) rateChartInstance.destroy();

  const labels = [...selectedDistricts];
  const rateValues = labels.map(dist => {
    const distData = data.filter(d => d.district === dist);
    const due = distData.reduce((sum, d) => sum + d.children_due, 0);
    const imm = distData.reduce((sum, d) => sum + d.children_fully_immunised, 0);
    return due > 0 ? parseFloat(((imm / due) * 100).toFixed(1)) : 0;
  });

  const barColors = rateValues.map(r => r >= 80 ? 'rgba(16, 185, 129, 0.8)' : r >= 75 ? 'rgba(245, 158, 11, 0.8)' : 'rgba(244, 63, 94, 0.8)');

  rateChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Immunisation Rate (%)',
        data: rateValues,
        backgroundColor: barColors,
        borderRadius: 6,
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y', // Horizontal bars
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` Coverage Rate: ${ctx.raw}%`
          }
        }
      },
      scales: {
        x: {
          max: 100,
          min: 50,
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#9ca3af', callback: v => v + '%' }
        },
        y: {
          grid: { display: false },
          ticks: { color: '#fff', font: { weight: 'bold' } }
        }
      }
    }
  });
}

// District Compare Side-by-Side Cards
function renderDistrictCards(data) {
  const container = document.getElementById('districtCardsGrid');
  if (!container) return;
  container.innerHTML = '';

  const districtsToRender = [...selectedDistricts];

  districtsToRender.forEach(distName => {
    // Get 2022 and 2023 records for YoY comparison
    const rec2022 = rawData.find(d => d.district === distName && d.year === '2022');
    const rec2023 = rawData.find(d => d.district === distName && d.year === '2023');

    let currentRec = activeYear === '2022' ? rec2022 : rec2023;
    if (activeYear === 'YoY' || !currentRec) {
      currentRec = rec2023 || rec2022; // default to latest available
    }

    if (!currentRec) return;

    // Calculate YoY growth percentage
    let yoyGrowth = null;
    if (rec2022 && rec2023) {
      yoyGrowth = (rec2023.coverage_pct - rec2022.coverage_pct).toFixed(1);
    }

    // Status Badge
    let statusClass = 'status-high';
    let statusText = 'HIGH COVERAGE (≥85%)';
    if (currentRec.coverage_pct < 75) {
      statusClass = 'status-low';
      statusText = 'ATTENTION NEEDED (<75%)';
    } else if (currentRec.coverage_pct < 85) {
      statusClass = 'status-medium';
      statusText = 'MODERATE COVERAGE (75-84%)';
    }

    const card = document.createElement('div');
    card.className = 'district-card';
    card.innerHTML = `
      <div class="district-card-header">
        <span class="district-name">${distName}</span>
        <span class="district-status ${statusClass}">${statusText}</span>
      </div>
      
      <div class="metric-row">
        <span class="metric-label">Target Children Due:</span>
        <span class="metric-val">${currentRec.children_due.toLocaleString()}</span>
      </div>
      <div class="metric-row">
        <span class="metric-label">Fully Immunised:</span>
        <span class="metric-val" style="color: var(--accent-emerald)">${currentRec.children_fully_immunised.toLocaleString()}</span>
      </div>
      <div class="metric-row">
        <span class="metric-label">Immunisation Rate:</span>
        <span class="metric-val" style="font-size: 1.05rem">${currentRec.coverage_pct}%</span>
      </div>

      <div class="progress-bar-bg">
        <div class="progress-bar-fill" style="width: ${currentRec.coverage_pct}%"></div>
      </div>

      ${yoyGrowth !== null ? `
        <div class="metric-row" style="margin-top: 0.5rem; font-size: 0.8rem; border-top: 1px dashed rgba(255,255,255,0.08); padding-top: 0.5rem;">
          <span class="metric-label">YoY Change (2022 → 2023):</span>
          <span class="metric-val" style="color: ${yoyGrowth >= 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)'}">
            ${yoyGrowth >= 0 ? '+' : ''}${yoyGrowth}%
          </span>
        </div>
      ` : ''}
    `;
    container.appendChild(card);
  });
}

// Render Raw CSV Data Table
function renderTable() {
  const tbody = document.getElementById('tableBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  rawData.forEach(row => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${row.district}</strong></td>
      <td><span class="stat-badge" style="background: rgba(255,255,255,0.1); color: #fff">${row.year}</span></td>
      <td>${row.children_due.toLocaleString()}</td>
      <td>${row.children_fully_immunised.toLocaleString()}</td>
      <td><strong style="color: var(--accent-cyan)">${row.coverage_pct}%</strong></td>
      <td><span style="color: var(--accent-emerald)">${row.source}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', initData);
