// Nutrition Screening Coverage Dashboard Application
(function() {
  'use strict';

  // Global State
  const state = {
    selectedYear: '2023', // '2022', '2023', or 'all'
    selectedBlock: 'all',
    chartType: 'bar',
    currentSheet: 'Quarterly Review',
    data: null,
    chartInstance: null
  };

  // Static Data Fixture (Fallback & Live Model)
  const DATA_FIXTURE = {
    file_info: {
      filename: "nutrition_review_side_by_side.xlsx",
      filepath: "/workspace/nutrition_review_side_by_side.xlsx",
      sheet_names: ["Quarterly Review", "Definitions", "Household Visits Raw"]
    },
    target_table: {
      sheet: "Quarterly Review",
      title: "Table 1. Nutrition screening by block and year",
      full_range: "A1:C7",
      title_range: "A1:C1",
      header_range: "A3:C4",
      data_range: "A5:C7",
      indicator: "Screening coverage (%)",
      unit: "percent (%)",
      definition: "Share of eligible children screened",
      source_note: "synthetic nutrition review fixture",
      years: ["2022", "2023"],
      records: [
        {
          block: "Gaya",
          cell_block: "A5",
          values: { "2022": 62, "2023": 68 },
          cells: { "2022": "B5", "2023": "C5" },
          yoy_change: 6,
          yoy_pct_growth: 9.7
        },
        {
          block: "Nalanda",
          cell_block: "A6",
          values: { "2022": 70, "2023": 76 },
          cells: { "2022": "B6", "2023": "C6" },
          yoy_change: 6,
          yoy_pct_growth: 8.6
        },
        {
          block: "Purnia",
          cell_block: "A7",
          values: { "2022": 55, "2023": 61 },
          cells: { "2022": "B7", "2023": "C7" },
          yoy_change: 6,
          yoy_pct_growth: 10.9
        }
      ],
      companion_table_2: {
        sheet: "Quarterly Review",
        title: "Table 2. Completed anaemia referrals by block and year",
        full_range: "E1:G7",
        indicator: "Referrals completed",
        unit: "children",
        records: [
          { block: "Gaya", values: { "2022": 120, "2023": 150 }, cells: { "2022": "F5", "2023": "G5" } },
          { block: "Nalanda", values: { "2022": 135, "2023": 160 }, cells: { "2022": "F6", "2023": "G6" } },
          { block: "Purnia", values: { "2022": 90, "2023": 118 }, cells: { "2022": "F7", "2023": "G7" } }
        ]
      }
    },
    sheets_raw: {
      "Quarterly Review": {
        max_row: 7,
        max_col: 7,
        headers: ["A", "B", "C", "D", "E", "F", "G"],
        grid: [
          [
            { coord: "A1", value: "Table 1. Nutrition screening by block and year", colSpan: 3, isTargetTitle: true },
            { coord: "B1", value: null, skip: true },
            { coord: "C1", value: null, skip: true },
            { coord: "D1", value: null },
            { coord: "E1", value: "Table 2. Completed anaemia referrals by block and year", colSpan: 3, isCompanionTitle: true },
            { coord: "F1", value: null, skip: true },
            { coord: "G1", value: null, skip: true }
          ],
          [
            { coord: "A2", value: null },
            { coord: "B2", value: null },
            { coord: "C2", value: null },
            { coord: "D2", value: null },
            { coord: "E2", value: null },
            { coord: "F2", value: null },
            { coord: "G2", value: null }
          ],
          [
            { coord: "A3", value: "Block", rowSpan: 2, isTargetHeader: true },
            { coord: "B3", value: "Screening coverage (%)", colSpan: 2, isTargetHeader: true },
            { coord: "C3", value: null, skip: true },
            { coord: "D3", value: null },
            { coord: "E3", value: "Block", rowSpan: 2, isCompanionHeader: true },
            { coord: "F3", value: "Referrals completed", colSpan: 2, isCompanionHeader: true },
            { coord: "G3", value: null, skip: true }
          ],
          [
            { coord: "A4", value: null, skip: true },
            { coord: "B4", value: "2022", isTargetSubHeader: true },
            { coord: "C4", value: "2023", isTargetSubHeader: true },
            { coord: "D4", value: null },
            { coord: "E4", value: null, skip: true },
            { coord: "F4", "value": "2022", isCompanionSubHeader: true },
            { coord: "G4", value: "2023", isCompanionSubHeader: true }
          ],
          [
            { coord: "A5", value: "Gaya", isTargetData: true, block: "Gaya" },
            { coord: "B5", value: 62, isTargetData: true, year: "2022", block: "Gaya" },
            { coord: "C5", value: 68, isTargetData: true, year: "2023", block: "Gaya" },
            { coord: "D5", value: null },
            { coord: "E5", value: "Gaya", isCompanionData: true },
            { coord: "F5", value: 120, isCompanionData: true },
            { coord: "G5", value: 150, isCompanionData: true }
          ],
          [
            { coord: "A6", value: "Nalanda", isTargetData: true, block: "Nalanda" },
            { coord: "B6", value: 70, isTargetData: true, year: "2022", block: "Nalanda" },
            { coord: "C6", value: 76, isTargetData: true, year: "2023", block: "Nalanda" },
            { coord: "D6", value: null },
            { coord: "E6", value: "Nalanda", isCompanionData: true },
            { coord: "F6", value: 135, isCompanionData: true },
            { coord: "G6", value: 160, isCompanionData: true }
          ],
          [
            { coord: "A7", value: "Purnia", isTargetData: true, block: "Purnia" },
            { coord: "B7", value: 55, isTargetData: true, year: "2022", block: "Purnia" },
            { coord: "C7", value: 61, isTargetData: true, year: "2023", block: "Purnia" },
            { coord: "D7", value: null },
            { coord: "E7", value: "Purnia", isCompanionData: true },
            { coord: "F7", value: 90, isCompanionData: true },
            { coord: "G7", value: 118, isCompanionData: true }
          ]
        ]
      },
      "Definitions": {
        max_row: 4,
        max_col: 4,
        headers: ["A", "B", "C", "D"],
        grid: [
          [
            { coord: "A1", value: "indicator", isHeader: true },
            { coord: "B1", value: "definition", isHeader: true },
            { coord: "C1", value: "unit", isHeader: true },
            { coord: "D1", value: "source", isHeader: true }
          ],
          [
            { coord: "A2", value: "Screening coverage", isTargetHighlight: true },
            { coord: "B2", value: "Share of eligible children screened", isTargetHighlight: true },
            { coord: "C2", value: "percent", isTargetHighlight: true },
            { coord: "D2", value: "synthetic nutrition review fixture", isTargetHighlight: true }
          ],
          [
            { coord: "A3", value: "Referrals completed" },
            { coord: "B3", value: "Children completing an anaemia referral" },
            { coord: "C3", value: "children" },
            { coord: "D3", value: "synthetic nutrition review fixture" }
          ],
          [
            { coord: "A4", value: "Warning" },
            { coord: "B4", value: "Illustrative aggregate data; not official statistics" },
            { coord: "C4", value: null },
            { coord: "D4", value: "synthetic nutrition review fixture" }
          ]
        ]
      },
      "Household Visits Raw": {
        max_row: 10,
        max_col: 4,
        headers: ["A", "B", "C", "D"],
        grid: [
          [
            { coord: "A1", value: "visit_id", isHeader: true },
            { coord: "B1", value: "block", isHeader: true },
            { coord: "C1", value: "month", isHeader: true },
            { coord: "D1", value: "completed", isHeader: true }
          ],
          [ { coord: "A2", value: "V001" }, { coord: "B2", value: "Nalanda" }, { coord: "C2", value: "2023-02" }, { coord: "D2", value: "True" } ],
          [ { coord: "A3", value: "V002" }, { coord: "B3", value: "Purnia" }, { coord: "C3", value: "2023-03" }, { coord: "D3", value: "True" } ],
          [ { coord: "A4", value: "V003" }, { coord: "B4", value: "Gaya" }, { coord: "C4", value: "2023-04" }, { coord: "D4", value: "True" } ],
          [ { coord: "A5", value: "V004" }, { coord: "B5", value: "Nalanda" }, { coord: "C5", value: "2023-05" }, { coord: "D5", value: "True" } ],
          [ { coord: "A6", value: "V005" }, { coord: "B6", value: "Purnia" }, { coord: "C6", value: "2023-06" }, { coord: "D6", value: "False" } ],
          [ { coord: "A7", value: "V006" }, { coord: "B7", value: "Gaya" }, { coord: "C7", value: "2023-07" }, { coord: "D7", value: "True" } ],
          [ { coord: "A8", value: "V007" }, { coord: "B8", value: "Nalanda" }, { coord: "C8", value: "2023-08" }, { coord: "D8", value: "True" } ],
          [ { coord: "A9", value: "V008" }, { coord: "B9", value: "Purnia" }, { coord: "C9", value: "2023-09" }, { coord: "D9", value: "True" } ],
          [ { coord: "A10", value: "V009" }, { coord: "B10", value: "Gaya" }, { coord: "C10", value: "2023-10" }, { coord: "D10", value: "True" } ]
        ]
      }
    }
  };

  state.data = DATA_FIXTURE;

  // Initialize App
  document.addEventListener('DOMContentLoaded', () => {
    // Render Lucide icons
    if (window.lucide) {
      window.lucide.createIcons();
    }

    // Try fetching live data if running with server, otherwise use fallback fixture
    fetchData();

    // Event Listeners
    setupEventListeners();
  });

  async function fetchData() {
    try {
      const res = await fetch('data.json');
      if (res.ok) {
        const json = await res.json();
        state.data.target_table = json.target_table || state.data.target_table;
        state.data.file_info = json.file_info || state.data.file_info;
      }
    } catch (e) {
      console.log('Using embedded fixture data');
    }
    renderDashboard();
  }

  function setupEventListeners() {
    // Year Selector Buttons
    const yearButtons = document.querySelectorAll('#yearSelectorGroup .year-btn');
    yearButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        const selected = btn.getAttribute('data-year');
        state.selectedYear = selected;
        
        yearButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        renderDashboard();
      });
    });

    // Block Filter
    const blockFilter = document.getElementById('blockFilter');
    if (blockFilter) {
      blockFilter.addEventListener('change', (e) => {
        state.selectedBlock = e.target.value;
        renderDashboard();
      });
    }

    // Chart Type Selector
    const chartTypeSelect = document.getElementById('chartTypeSelect');
    if (chartTypeSelect) {
      chartTypeSelect.addEventListener('change', (e) => {
        state.chartType = e.target.value;
        renderChart();
      });
    }

    // Table Search
    const tableSearch = document.getElementById('tableSearch');
    if (tableSearch) {
      tableSearch.addEventListener('input', (e) => {
        renderTable(e.target.value.trim().toLowerCase());
      });
    }

    // Sheet Tabs Switcher
    const sheetTabBtns = document.querySelectorAll('#sheetTabs .sheet-tab-btn');
    sheetTabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        sheetTabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.currentSheet = btn.getAttribute('data-sheet');
        renderExcelGrid();
      });
    });

    // CSV Export
    const exportCsvBtn = document.getElementById('exportCsvBtn');
    if (exportCsvBtn) {
      exportCsvBtn.addEventListener('click', exportCSV);
    }

    // Print
    const printBtn = document.getElementById('printBtn');
    if (printBtn) {
      printBtn.addEventListener('click', () => window.print());
    }
  }

  function renderDashboard() {
    renderKPIs();
    renderChart();
    renderBlockGrowth();
    renderTable();
    renderExcelGrid();
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  // Filter records based on selected block
  function getFilteredRecords() {
    const records = state.data.target_table.records;
    if (state.selectedBlock === 'all') return records;
    return records.filter(r => r.block.toLowerCase() === state.selectedBlock.toLowerCase());
  }

  // Render KPI Metrics
  function renderKPIs() {
    const records = getFilteredRecords();
    const isYearAll = state.selectedYear === 'all';
    const activeYear = isYearAll ? '2023' : state.selectedYear;

    // Average Coverage
    const sum = records.reduce((acc, r) => acc + r.values[activeYear], 0);
    const avg = records.length > 0 ? (sum / records.length).toFixed(1) : '0';
    document.getElementById('kpiAvgCoverage').innerText = `${avg}%`;

    const avgSubtext = document.getElementById('kpiAvgSubtext');
    if (avgSubtext) {
      avgSubtext.innerHTML = `For year <strong class="text-slate-600">${isYearAll ? '2023 (vs 2022)' : activeYear}</strong> across ${records.length} block${records.length > 1 ? 's' : ''}`;
    }

    // Growth Badge
    const growthBadge = document.getElementById('kpiAvgGrowth');
    if (growthBadge) {
      if (isYearAll || activeYear === '2023') {
        growthBadge.innerHTML = '<i data-lucide="trending-up" class="w-3 h-3"></i> +6.0% YoY';
        growthBadge.className = 'text-xs font-semibold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded flex items-center gap-0.5';
      } else {
        growthBadge.innerHTML = 'Base Baseline (2022)';
        growthBadge.className = 'text-xs font-medium text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded';
      }
    }

    // Top Block
    let topBlock = records[0];
    let lowBlock = records[0];
    records.forEach(r => {
      if (r.values[activeYear] > topBlock.values[activeYear]) topBlock = r;
      if (r.values[activeYear] < lowBlock.values[activeYear]) lowBlock = r;
    });

    if (topBlock) {
      document.getElementById('kpiTopBlockName').innerText = topBlock.block;
      document.getElementById('kpiTopBlockVal').innerText = `${topBlock.values[activeYear]}%`;
      document.getElementById('kpiTopBlockSubtext').innerHTML = `Leading coverage in <span class="text-slate-600">${activeYear}</span> (Cell: ${topBlock.cells[activeYear]})`;
    }

    // Low Block
    if (lowBlock) {
      document.getElementById('kpiLowBlockName').innerText = lowBlock.block;
      document.getElementById('kpiLowBlockVal').innerText = `${lowBlock.values[activeYear]}%`;
      document.getElementById('kpiLowBlockSubtext').innerHTML = `Priority focus for <span class="text-slate-600">${activeYear}</span> (Cell: ${lowBlock.cells[activeYear]})`;
    }

    // Referrals KPI
    const compRecords = state.data.target_table.companion_table_2.records;
    const refYear = isYearAll ? '2023' : activeYear;
    const totalRef = compRecords.reduce((acc, r) => acc + r.values[refYear], 0);
    document.getElementById('kpiReferrals').innerText = totalRef;
  }

  // Render Visual Analytics Chart
  function renderChart() {
    const records = getFilteredRecords();
    const ctx = document.getElementById('coverageChart');
    if (!ctx) return;

    if (state.chartInstance) {
      state.chartInstance.destroy();
    }

    const isYearAll = state.selectedYear === 'all';
    const labels = records.map(r => r.block);

    // Chart Heading
    const chartHeading = document.getElementById('chartHeading');
    if (chartHeading) {
      if (isYearAll) {
        chartHeading.innerText = 'Nutrition Screening Coverage (%): 2022 vs 2023 Comparison';
      } else {
        chartHeading.innerText = `Nutrition Screening Coverage (%) by Block (${state.selectedYear})`;
      }
    }

    let datasets = [];

    if (isYearAll) {
      datasets = [
        {
          label: '2022 Coverage (%)',
          data: records.map(r => r.values['2022']),
          backgroundColor: 'rgba(148, 163, 184, 0.85)',
          borderColor: 'rgb(100, 116, 139)',
          borderWidth: 1.5,
          borderRadius: 6
        },
        {
          label: '2023 Coverage (%)',
          data: records.map(r => r.values['2023']),
          backgroundColor: 'rgba(16, 185, 129, 0.9)',
          borderColor: 'rgb(5, 150, 105)',
          borderWidth: 1.5,
          borderRadius: 6
        }
      ];
    } else {
      const year = state.selectedYear;
      const bgColors = records.map(r => {
        const v = r.values[year];
        if (v >= 70) return 'rgba(16, 185, 129, 0.9)'; // emerald
        if (v >= 60) return 'rgba(13, 148, 136, 0.85)'; // teal
        return 'rgba(245, 158, 11, 0.85)'; // amber
      });

      datasets = [
        {
          label: `${year} Screening Coverage (%)`,
          data: records.map(r => r.values[year]),
          backgroundColor: bgColors,
          borderColor: 'rgb(5, 150, 105)',
          borderWidth: 1.5,
          borderRadius: 8
        }
      ];
    }

    const isHorizontal = state.chartType === 'horizontalBar';
    const chartConfigType = state.chartType === 'line' ? 'line' : 'bar';

    state.chartInstance = new Chart(ctx, {
      type: chartConfigType,
      data: {
        labels: labels,
        datasets: datasets
      },
      options: {
        indexAxis: isHorizontal ? 'y' : 'x',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: isYearAll,
            position: 'top',
            labels: {
              boxWidth: 12,
              font: { family: 'Inter', size: 12, weight: '500' }
            }
          },
          tooltip: {
            backgroundColor: '#0f172a',
            titleFont: { family: 'Inter', size: 13, weight: '600' },
            bodyFont: { family: 'Inter', size: 12 },
            padding: 10,
            cornerRadius: 8,
            callbacks: {
              label: function(context) {
                return ` ${context.dataset.label || ''}: ${context.parsed.y !== undefined ? context.parsed.y : context.parsed.x}%`;
              }
            }
          }
        },
        scales: {
          x: {
            grid: { color: '#f1f5f9' },
            ticks: {
              font: { family: 'Inter', size: 11, weight: '500' },
              color: '#64748b'
            }
          },
          y: {
            beginAtZero: true,
            max: 100,
            grid: { color: '#f1f5f9' },
            ticks: {
              font: { family: 'Inter', size: 11 },
              color: '#64748b',
              callback: function(value) {
                return value + '%';
              }
            }
          }
        }
      }
    });
  }

  // Render Block Growth Cards
  function renderBlockGrowth() {
    const container = document.getElementById('blockGrowthList');
    if (!container) return;

    const records = state.data.target_table.records;
    container.innerHTML = records.map(r => {
      const v22 = r.values['2022'];
      const v23 = r.values['2023'];
      const diff = r.yoy_change;
      const pct = r.yoy_pct_growth;

      return `
        <div class="p-3 bg-slate-50 hover:bg-slate-100/80 transition rounded-xl border border-slate-200/80">
          <div class="flex items-center justify-between mb-1.5">
            <span class="font-bold text-slate-800 text-xs">${r.block} Block</span>
            <span class="text-xs font-bold text-emerald-700 bg-emerald-100/70 px-2 py-0.5 rounded-full flex items-center gap-1">
              <i data-lucide="arrow-up" class="w-3 h-3"></i> +${diff}% (+${pct}% rel.)
            </span>
          </div>
          <div class="grid grid-cols-2 gap-2 text-[11px] text-slate-500 mb-2">
            <div>2022: <strong class="text-slate-800">${v22}%</strong> <span class="text-[10px] text-slate-400 font-mono">(${r.cells['2022']})</span></div>
            <div>2023: <strong class="text-slate-800">${v23}%</strong> <span class="text-[10px] text-slate-400 font-mono">(${r.cells['2023']})</span></div>
          </div>
          <!-- Progress Bar Comparison -->
          <div class="w-full bg-slate-200 h-2 rounded-full overflow-hidden relative">
            <div class="bg-slate-400 h-full absolute left-0" style="width: ${v22}%"></div>
            <div class="bg-emerald-500 h-full absolute left-0 opacity-80" style="width: ${v23}%"></div>
          </div>
        </div>
      `;
    }).join('');
  }

  // Render Data Table
  function renderTable(searchTerm = '') {
    const tableBody = document.getElementById('tableBody');
    const tableFoot = document.getElementById('tableFoot');
    if (!tableBody) return;

    let records = state.data.target_table.records;
    if (state.selectedBlock !== 'all') {
      records = records.filter(r => r.block.toLowerCase() === state.selectedBlock.toLowerCase());
    }
    if (searchTerm) {
      records = records.filter(r => r.block.toLowerCase().includes(searchTerm));
    }

    if (records.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="7" class="py-6 text-center text-slate-400">No matching blocks found</td></tr>`;
      if (tableFoot) tableFoot.innerHTML = '';
      return;
    }

    const selectedYear = state.selectedYear;

    tableBody.innerHTML = records.map(r => {
      const v22 = r.values['2022'];
      const v23 = r.values['2023'];
      const currentVal = selectedYear === 'all' ? `${v23}% (vs ${v22}%)` : `${r.values[selectedYear]}%`;
      const cellRef = selectedYear === 'all' ? `${r.cells['2022']}, ${r.cells['2023']}` : r.cells[selectedYear];

      // Status indicator
      const activeNumeric = selectedYear === 'all' ? v23 : r.values[selectedYear];
      let statusBadge = '';
      if (activeNumeric >= 75) {
        statusBadge = '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-100 text-emerald-800">High (&ge;75%)</span>';
      } else if (activeNumeric >= 65) {
        statusBadge = '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-teal-100 text-teal-800">Moderate</span>';
      } else {
        statusBadge = '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-100 text-amber-800">Needs Focus</span>';
      }

      return `
        <tr class="hover:bg-slate-50/80 transition">
          <td class="py-3 px-4 font-semibold text-slate-900 flex items-center gap-1.5">
            <i data-lucide="map-pin" class="w-3.5 h-3.5 text-emerald-600"></i>
            ${r.block}
          </td>
          <td class="py-3 px-4 text-slate-500 font-mono text-[11px]">
            Row ${r.cell_block.replace('A', '')} <span class="text-slate-400">(${r.cell_block})</span>
          </td>
          <td class="py-3 px-4 text-right font-medium text-slate-700">
            ${v22}% <span class="text-[10px] text-slate-400 font-mono">(${r.cells['2022']})</span>
          </td>
          <td class="py-3 px-4 text-right font-medium text-slate-700">
            ${v23}% <span class="text-[10px] text-slate-400 font-mono">(${r.cells['2023']})</span>
          </td>
          <td class="py-3 px-4 text-right font-bold text-emerald-700 bg-emerald-50/40">
            ${currentVal} <span class="text-[10px] text-emerald-600 font-mono">(${cellRef})</span>
          </td>
          <td class="py-3 px-4 text-right font-bold text-emerald-600">
            +${r.yoy_change}% <span class="text-[10px] text-slate-400 font-normal">(+${r.yoy_pct_growth}%)</span>
          </td>
          <td class="py-3 px-4 text-center">
            ${statusBadge}
          </td>
        </tr>
      `;
    }).join('');

    // Summary row in tfoot
    if (tableFoot) {
      const avg22 = (records.reduce((acc, r) => acc + r.values['2022'], 0) / records.length).toFixed(1);
      const avg23 = (records.reduce((acc, r) => acc + r.values['2023'], 0) / records.length).toFixed(1);
      const avgSel = selectedYear === 'all' ? `${avg23}%` : (records.reduce((acc, r) => acc + r.values[selectedYear], 0) / records.length).toFixed(1) + '%';

      tableFoot.innerHTML = `
        <tr>
          <td class="py-3 px-4">Average Across Blocks</td>
          <td class="py-3 px-4 font-mono text-[11px] text-slate-500">${records.length} blocks</td>
          <td class="py-3 px-4 text-right">${avg22}%</td>
          <td class="py-3 px-4 text-right">${avg23}%</td>
          <td class="py-3 px-4 text-right text-emerald-800">${avgSel}</td>
          <td class="py-3 px-4 text-right text-emerald-700">+6.0%</td>
          <td class="py-3 px-4 text-center text-slate-500">Summary</td>
        </tr>
      `;
    }
  }

  // Render Interactive Excel Grid
  function renderExcelGrid() {
    const table = document.getElementById('excelGridTable');
    if (!table) return;

    const sheetName = state.currentSheet;
    const sheetData = state.data.sheets_raw[sheetName];
    if (!sheetData) return;

    const descEl = document.getElementById('currentSheetDesc');
    if (descEl) {
      if (sheetName === 'Quarterly Review') {
        descEl.innerHTML = 'Viewing sheet: <strong class="text-emerald-700 font-mono">Quarterly Review</strong>. Highlighted green area is <strong class="text-emerald-700 font-mono">Table 1 (A1:C7)</strong>.';
      } else if (sheetName === 'Definitions') {
        descEl.innerHTML = 'Viewing sheet: <strong class="text-emerald-700 font-mono">Definitions</strong>. Indicator glossary & metadata.';
      } else {
        descEl.innerHTML = 'Viewing sheet: <strong class="text-emerald-700 font-mono">Household Visits Raw</strong>. Visit-level survey log.';
      }
    }

    let html = '<thead><tr><th class="excel-grid-th w-10"></th>';
    sheetData.headers.forEach(h => {
      html += `<th class="excel-grid-th">${h}</th>`;
    });
    html += '</tr></thead><tbody>';

    sheetData.grid.forEach((row, rowIdx) => {
      const rowNumber = rowIdx + 1;
      html += `<tr><td class="excel-grid-row-header">${rowNumber}</td>`;

      row.forEach(cell => {
        if (cell.skip) return;

        let cellClass = 'excel-grid-cell';
        let tooltip = `Cell: ${cell.coord}`;

        if (cell.isTargetTitle) {
          cellClass += ' excel-highlight-header';
          tooltip += ' • Table 1 Title (Merged A1:C1)';
        } else if (cell.isTargetHeader || cell.isTargetSubHeader) {
          cellClass += ' excel-highlight-col-header';
          tooltip += ' • Table 1 Header (Screening Coverage)';
        } else if (cell.isTargetData) {
          cellClass += ' excel-highlight-target';
          tooltip += ` • Block: ${cell.block || ''}${cell.year ? ` | Year: ${cell.year}` : ''} | Value: ${cell.value}%`;
        } else if (cell.isCompanionTitle) {
          cellClass += ' excel-highlight-companion-header';
          tooltip += ' • Table 2 Title (Merged E1:G1)';
        } else if (cell.isCompanionHeader || cell.isCompanionSubHeader || cell.isCompanionData) {
          cellClass += ' excel-highlight-companion';
          tooltip += ' • Table 2 Data (Anaemia Referrals)';
        } else if (cell.isHeader) {
          cellClass += ' bg-slate-100 font-bold text-slate-800';
        } else if (cell.isTargetHighlight) {
          cellClass += ' bg-emerald-50 text-emerald-900 font-medium';
        }

        const colSpanAttr = cell.colSpan ? ` colspan="${cell.colSpan}"` : '';
        const rowSpanAttr = cell.rowSpan ? ` rowspan="${cell.rowSpan}"` : '';
        const displayValue = cell.value !== null && cell.value !== undefined ? cell.value : '';

        html += `<td class="${cellClass}"${colSpanAttr}${rowSpanAttr} title="${tooltip}">
          ${displayValue}
        </td>`;
      });

      html += '</tr>';
    });

    html += '</tbody>';
    table.innerHTML = html;
  }

  // Export to CSV
  function exportCSV() {
    const records = state.data.target_table.records;
    let csvContent = 'data:text/csv;charset=utf-8,';
    csvContent += 'Source Workbook,nutrition_review_side_by_side.xlsx\n';
    csvContent += 'Source Sheet,Quarterly Review\n';
    csvContent += 'Table Name,Table 1. Nutrition screening by block and year\n';
    csvContent += 'Cell Range,A1:C7\n\n';
    csvContent += 'Block,Row,2022 Coverage (%),2023 Coverage (%),YoY Change (%),2022 Cell,2023 Cell\n';

    records.forEach(r => {
      csvContent += `${r.block},${r.cell_block},${r.values['2022']}%,${r.values['2023']}%,+${r.yoy_change}%,${r.cells['2022']},${r.cells['2023']}\n`;
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', 'nutrition_screening_coverage_table1_A1_C7.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

})();
