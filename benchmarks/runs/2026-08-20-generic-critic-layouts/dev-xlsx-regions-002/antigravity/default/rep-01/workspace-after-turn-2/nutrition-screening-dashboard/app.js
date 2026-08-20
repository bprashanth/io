// Nutrition Screening & Completed Anaemia Referrals Dashboard
(function() {
  'use strict';

  // Global State
  const state = {
    selectedYear: '2023', // '2022', '2023', or 'all'
    focusView: 'all', // 'all', 'table1', 'table2'
    selectedBlock: 'all',
    chartType: 'bar',
    tableTab: 'sideBySide', // 'sideBySide', 'table1', 'table2'
    currentSheet: 'Quarterly Review',
    data: null,
    chartInstance1: null,
    chartInstance2: null
  };

  // Full Static Fixture Model
  const DATA_FIXTURE = {
    file_info: {
      filename: "nutrition_review_side_by_side.xlsx",
      filepath: "/workspace/nutrition_review_side_by_side.xlsx",
      sheet_names: ["Quarterly Review", "Definitions", "Household Visits Raw"]
    },
    tables: {
      table1_screening: {
        id: "table1",
        sheet: "Quarterly Review",
        title: "Table 1. Nutrition screening by block and year",
        full_range: "A1:C7",
        title_range: "A1:C1",
        header_range: "A3:C4",
        data_range: "A5:C7",
        indicator: "Screening coverage (%)",
        unit: "percent (%)",
        definition: "Share of eligible children screened",
        definition_range: "Definitions!A2:D2",
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
        ]
      },
      table2_referrals: {
        id: "table2",
        sheet: "Quarterly Review",
        title: "Table 2. Completed anaemia referrals by block and year",
        full_range: "E1:G7",
        title_range: "E1:G1",
        header_range: "E3:G4",
        data_range: "E5:G7",
        indicator: "Referrals completed",
        unit: "children (count)",
        definition: "Children completing an anaemia referral",
        definition_range: "Definitions!A3:D3",
        years: ["2022", "2023"],
        records: [
          {
            block: "Gaya",
            cell_block: "E5",
            values: { "2022": 120, "2023": 150 },
            cells: { "2022": "F5", "2023": "G5" },
            yoy_change: 30,
            yoy_pct_growth: 25.0
          },
          {
            block: "Nalanda",
            cell_block: "E6",
            values: { "2022": 135, "2023": 160 },
            cells: { "2022": "F6", "2023": "G6" },
            yoy_change: 25,
            yoy_pct_growth: 18.5
          },
          {
            block: "Purnia",
            cell_block: "E7",
            values: { "2022": 90, "2023": 118 },
            cells: { "2022": "F7", "2023": "G7" },
            yoy_change: 28,
            yoy_pct_growth: 31.1
          }
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
            { coord: "D1", value: null, isColD: true },
            { coord: "E1", value: "Table 2. Completed anaemia referrals by block and year", colSpan: 3, isCompanionTitle: true },
            { coord: "F1", value: null, skip: true },
            { coord: "G1", value: null, skip: true }
          ],
          [
            { coord: "A2", value: null },
            { coord: "B2", value: null },
            { coord: "C2", value: null },
            { coord: "D2", value: null, isColD: true },
            { coord: "E2", value: null },
            { coord: "F2", value: null },
            { coord: "G2", value: null }
          ],
          [
            { coord: "A3", value: "Block", rowSpan: 2, isTargetHeader: true },
            { coord: "B3", value: "Screening coverage (%)", colSpan: 2, isTargetHeader: true },
            { coord: "C3", value: null, skip: true },
            { coord: "D3", value: null, isColD: true },
            { coord: "E3", value: "Block", rowSpan: 2, isCompanionHeader: true },
            { coord: "F3", value: "Referrals completed", colSpan: 2, isCompanionHeader: true },
            { coord: "G3", value: null, skip: true }
          ],
          [
            { coord: "A4", value: null, skip: true },
            { coord: "B4", value: "2022", isTargetSubHeader: true },
            { coord: "C4", value: "2023", isTargetSubHeader: true },
            { coord: "D4", value: null, isColD: true },
            { coord: "E4", value: null, skip: true },
            { coord: "F4", value: "2022", isCompanionSubHeader: true },
            { coord: "G4", value: "2023", isCompanionSubHeader: true }
          ],
          [
            { coord: "A5", value: "Gaya", isTargetData: true, block: "Gaya" },
            { coord: "B5", value: 62, isTargetData: true, year: "2022", block: "Gaya" },
            { coord: "C5", value: 68, isTargetData: true, year: "2023", block: "Gaya" },
            { coord: "D5", value: null, isColD: true },
            { coord: "E5", value: "Gaya", isCompanionData: true, block: "Gaya" },
            { coord: "F5", value: 120, isCompanionData: true, year: "2022", block: "Gaya" },
            { coord: "G5", value: 150, isCompanionData: true, year: "2023", block: "Gaya" }
          ],
          [
            { coord: "A6", value: "Nalanda", isTargetData: true, block: "Nalanda" },
            { coord: "B6", value: 70, isTargetData: true, year: "2022", block: "Nalanda" },
            { coord: "C6", value: 76, isTargetData: true, year: "2023", block: "Nalanda" },
            { coord: "D6", value: null, isColD: true },
            { coord: "E6", value: "Nalanda", isCompanionData: true, block: "Nalanda" },
            { coord: "F6", value: 135, isCompanionData: true, year: "2022", block: "Nalanda" },
            { coord: "G6", value: 160, isCompanionData: true, year: "2023", block: "Nalanda" }
          ],
          [
            { coord: "A7", value: "Purnia", isTargetData: true, block: "Purnia" },
            { coord: "B7", value: 55, isTargetData: true, year: "2022", block: "Purnia" },
            { coord: "C7", value: 61, isTargetData: true, year: "2023", block: "Purnia" },
            { coord: "D7", value: null, isColD: true },
            { coord: "E7", value: "Purnia", isCompanionData: true, block: "Purnia" },
            { coord: "F7", value: 90, isCompanionData: true, year: "2022", block: "Purnia" },
            { coord: "G7", value: 118, isCompanionData: true, year: "2023", block: "Purnia" }
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
            { coord: "A3", value: "Referrals completed", isCompanionHighlight: true },
            { coord: "B3", value: "Children completing an anaemia referral", isCompanionHighlight: true },
            { coord: "C3", value: "children", isCompanionHighlight: true },
            { coord: "D3", value: "synthetic nutrition review fixture", isCompanionHighlight: true }
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
          [ { coord: "A3", value: "V002" }, { coord: "B3", value: "Purnia" }, { coord: "C3", value: "2023-03" }, { coord: "D2", value: "True" } ],
          [ { coord: "A4", value: "V003" }, { coord: "B4", value: "Gaya" }, { coord: "C4", value: "2023-04" }, { coord: "D2", value: "True" } ],
          [ { coord: "A5", value: "V004" }, { coord: "B5", value: "Nalanda" }, { coord: "C5", value: "2023-05" }, { coord: "D2", value: "True" } ],
          [ { coord: "A6", value: "V005" }, { coord: "B6", value: "Purnia" }, { coord: "C6", value: "2023-06" }, { coord: "D2", value: "False" } ],
          [ { coord: "A7", value: "V006" }, { coord: "B7", value: "Gaya" }, { coord: "C7", value: "2023-07" }, { coord: "D2", value: "True" } ],
          [ { coord: "A8", value: "V007" }, { coord: "B8", value: "Nalanda" }, { coord: "C8", value: "2023-08" }, { coord: "D2", value: "True" } ],
          [ { coord: "A9", value: "V008" }, { coord: "B9", value: "Purnia" }, { coord: "C9", value: "2023-09" }, { coord: "D2", value: "True" } ],
          [ { coord: "A10", value: "V009" }, { coord: "B10", value: "Gaya" }, { coord: "C10", value: "2023-10" }, { coord: "D2", value: "True" } ]
        ]
      }
    }
  };

  state.data = DATA_FIXTURE;

  document.addEventListener('DOMContentLoaded', () => {
    if (window.lucide) {
      window.lucide.createIcons();
    }
    fetchData();
    setupEventListeners();
  });

  async function fetchData() {
    try {
      const res = await fetch('data.json');
      if (res.ok) {
        const json = await res.json();
        if (json.tables) state.data.tables = json.tables;
        if (json.file_info) state.data.file_info = json.file_info;
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
      btn.addEventListener('click', () => {
        state.selectedYear = btn.getAttribute('data-year');
        yearButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        renderDashboard();
      });
    });

    // Focus View Selector Buttons (All, Table 1, Table 2)
    const focusButtons = document.querySelectorAll('#focusViewGroup .focus-btn');
    focusButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        state.focusView = btn.getAttribute('data-focus');
        focusButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        updateFocusViewLayout();
        renderCharts();
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

    // Chart Style Selector
    const chartTypeSelect = document.getElementById('chartTypeSelect');
    if (chartTypeSelect) {
      chartTypeSelect.addEventListener('change', (e) => {
        state.chartType = e.target.value;
        renderCharts();
      });
    }

    // Table Tab Selector (Side-by-Side, Table 1, Table 2)
    const tableTabs = document.querySelectorAll('#tableTabGroup .table-tab-btn');
    tableTabs.forEach(btn => {
      btn.addEventListener('click', () => {
        tableTabs.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.tableTab = btn.getAttribute('data-table');
        renderTable();
      });
    });

    // Table Search
    const tableSearch = document.getElementById('tableSearch');
    if (tableSearch) {
      tableSearch.addEventListener('input', (e) => {
        renderTable(e.target.value.trim().toLowerCase());
      });
    }

    // Sheet Tabs
    const sheetTabBtns = document.querySelectorAll('#sheetTabs .sheet-tab-btn');
    sheetTabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        sheetTabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.currentSheet = btn.getAttribute('data-sheet');
        renderExcelGrid();
      });
    });

    // Export CSV
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

  function updateFocusViewLayout() {
    const c1 = document.getElementById('chartContainer1');
    const c2 = document.getElementById('chartContainer2');
    const chartsSec = document.getElementById('chartsSection');
    if (!c1 || !c2 || !chartsSec) return;

    if (state.focusView === 'table1') {
      c1.classList.remove('hidden');
      c2.classList.add('hidden');
      chartsSec.className = 'grid grid-cols-1 gap-6';
    } else if (state.focusView === 'table2') {
      c1.classList.add('hidden');
      c2.classList.remove('hidden');
      chartsSec.className = 'grid grid-cols-1 gap-6';
    } else {
      c1.classList.remove('hidden');
      c2.classList.remove('hidden');
      chartsSec.className = 'grid grid-cols-1 lg:grid-cols-2 gap-6';
    }
  }

  function renderDashboard() {
    updateActiveFilterLabel();
    renderKPIs();
    renderCharts();
    renderBlockCards();
    renderTable();
    renderExcelGrid();
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  function updateActiveFilterLabel() {
    const label = document.getElementById('activeFilterLabel');
    if (!label) return;
    const blockText = state.selectedBlock === 'all' ? 'All Blocks (3)' : `${state.selectedBlock} Block`;
    const yearText = state.selectedYear === 'all' ? '2022 vs 2023 Comparison' : `Year ${state.selectedYear}`;
    label.innerText = `${blockText} • ${yearText}`;
  }

  function getFilteredRecords(tableKey) {
    const records = state.data.tables[tableKey].records;
    if (state.selectedBlock === 'all') return records;
    return records.filter(r => r.block.toLowerCase() === state.selectedBlock.toLowerCase());
  }

  // Render KPI Metrics
  function renderKPIs() {
    const isYearAll = state.selectedYear === 'all';
    const activeYear = isYearAll ? '2023' : state.selectedYear;

    // Table 1 Records (Screening)
    const rec1 = getFilteredRecords('table1_screening');
    const sum1 = rec1.reduce((acc, r) => acc + r.values[activeYear], 0);
    const avg1 = rec1.length > 0 ? (sum1 / rec1.length).toFixed(1) : '0';
    document.getElementById('kpiAvgCoverage').innerText = `${avg1}%`;

    const kpiAvgGrowth = document.getElementById('kpiAvgGrowth');
    if (kpiAvgGrowth) {
      if (isYearAll || activeYear === '2023') {
        kpiAvgGrowth.innerHTML = '<i data-lucide="trending-up" class="w-3 h-3"></i> +6.0% YoY';
        kpiAvgGrowth.className = 'text-xs font-semibold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded flex items-center gap-0.5';
      } else {
        kpiAvgGrowth.innerHTML = 'Baseline (2022)';
        kpiAvgGrowth.className = 'text-xs font-medium text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded';
      }
    }

    // Table 2 Records (Referrals)
    const rec2 = getFilteredRecords('table2_referrals');
    const sum2 = rec2.reduce((acc, r) => acc + r.values[activeYear], 0);
    document.getElementById('kpiTotalReferrals').innerText = sum2;

    const kpiReferralsGrowth = document.getElementById('kpiReferralsGrowth');
    if (kpiReferralsGrowth) {
      if (isYearAll || activeYear === '2023') {
        const sum22 = rec2.reduce((acc, r) => acc + r.values['2022'], 0);
        const growth = sum22 > 0 ? (((sum2 - sum22) / sum22) * 100).toFixed(1) : '0';
        kpiReferralsGrowth.innerHTML = `<i data-lucide="trending-up" class="w-3 h-3"></i> +${growth}% YoY`;
        kpiReferralsGrowth.className = 'text-xs font-semibold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded flex items-center gap-0.5';
      } else {
        kpiReferralsGrowth.innerHTML = 'Baseline (2022)';
        kpiReferralsGrowth.className = 'text-xs font-medium text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded';
      }
    }

    // Top Screening Block
    let top1 = rec1[0];
    rec1.forEach(r => {
      if (r.values[activeYear] > (top1 ? top1.values[activeYear] : -1)) top1 = r;
    });
    if (top1) {
      document.getElementById('kpiTopScreeningName').innerText = top1.block;
      document.getElementById('kpiTopScreeningVal').innerText = `${top1.values[activeYear]}%`;
      document.getElementById('kpiTopScreeningSubtext').innerHTML = `Leading coverage in ${activeYear} (Cell: ${top1.cells[activeYear]})`;
    }

    // Top Referrals Block
    let top2 = rec2[0];
    rec2.forEach(r => {
      if (r.values[activeYear] > (top2 ? top2.values[activeYear] : -1)) top2 = r;
    });
    if (top2) {
      document.getElementById('kpiTopReferralsName').innerText = top2.block;
      document.getElementById('kpiTopReferralsVal').innerText = `${top2.values[activeYear]} children`;
      document.getElementById('kpiTopReferralsSubtext').innerHTML = `Most referrals in ${activeYear} (Cell: ${top2.cells[activeYear]})`;
    }
  }

  // Render Charts for Both Tables
  function renderCharts() {
    renderScreeningChart();
    renderReferralsChart();
  }

  function renderScreeningChart() {
    const records = getFilteredRecords('table1_screening');
    const ctx = document.getElementById('chartScreening');
    if (!ctx) return;

    if (state.chartInstance1) state.chartInstance1.destroy();

    const isYearAll = state.selectedYear === 'all';
    const labels = records.map(r => r.block);

    const titleEl = document.getElementById('chart1Title');
    if (titleEl) {
      titleEl.innerText = isYearAll 
        ? 'Nutrition Screening Coverage (%): 2022 vs 2023 Comparison'
        : `Nutrition Screening Coverage (%) by Block (${state.selectedYear})`;
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
      datasets = [
        {
          label: `${year} Screening Coverage (%)`,
          data: records.map(r => r.values[year]),
          backgroundColor: 'rgba(16, 185, 129, 0.88)',
          borderColor: 'rgb(5, 150, 105)',
          borderWidth: 1.5,
          borderRadius: 8
        }
      ];
    }

    const isHorizontal = state.chartType === 'horizontalBar';
    const chartConfigType = state.chartType === 'line' ? 'line' : 'bar';

    state.chartInstance1 = new Chart(ctx, {
      type: chartConfigType,
      data: { labels, datasets },
      options: {
        indexAxis: isHorizontal ? 'y' : 'x',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: isYearAll, position: 'top' },
          tooltip: {
            callbacks: {
              label: (c) => ` ${c.dataset.label}: ${c.parsed.y !== undefined ? c.parsed.y : c.parsed.x}%`
            }
          }
        },
        scales: {
          x: { grid: { color: '#f1f5f9' } },
          y: {
            beginAtZero: true,
            max: 100,
            grid: { color: '#f1f5f9' },
            ticks: { callback: (v) => v + '%' }
          }
        }
      }
    });
  }

  function renderReferralsChart() {
    const records = getFilteredRecords('table2_referrals');
    const ctx = document.getElementById('chartReferrals');
    if (!ctx) return;

    if (state.chartInstance2) state.chartInstance2.destroy();

    const isYearAll = state.selectedYear === 'all';
    const labels = records.map(r => r.block);

    const titleEl = document.getElementById('chart2Title');
    if (titleEl) {
      titleEl.innerText = isYearAll
        ? 'Completed Anaemia Referrals: 2022 vs 2023 Comparison'
        : `Completed Anaemia Referrals by Block (${state.selectedYear})`;
    }

    let datasets = [];
    if (isYearAll) {
      datasets = [
        {
          label: '2022 Referrals',
          data: records.map(r => r.values['2022']),
          backgroundColor: 'rgba(148, 163, 184, 0.85)',
          borderColor: 'rgb(100, 116, 139)',
          borderWidth: 1.5,
          borderRadius: 6
        },
        {
          label: '2023 Referrals',
          data: records.map(r => r.values['2023']),
          backgroundColor: 'rgba(59, 130, 246, 0.9)',
          borderColor: 'rgb(29, 78, 216)',
          borderWidth: 1.5,
          borderRadius: 6
        }
      ];
    } else {
      const year = state.selectedYear;
      datasets = [
        {
          label: `${year} Completed Referrals`,
          data: records.map(r => r.values[year]),
          backgroundColor: 'rgba(59, 130, 246, 0.88)',
          borderColor: 'rgb(29, 78, 216)',
          borderWidth: 1.5,
          borderRadius: 8
        }
      ];
    }

    const isHorizontal = state.chartType === 'horizontalBar';
    const chartConfigType = state.chartType === 'line' ? 'line' : 'bar';

    state.chartInstance2 = new Chart(ctx, {
      type: chartConfigType,
      data: { labels, datasets },
      options: {
        indexAxis: isHorizontal ? 'y' : 'x',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: isYearAll, position: 'top' },
          tooltip: {
            callbacks: {
              label: (c) => ` ${c.dataset.label}: ${c.parsed.y !== undefined ? c.parsed.y : c.parsed.x} children`
            }
          }
        },
        scales: {
          x: { grid: { color: '#f1f5f9' } },
          y: {
            beginAtZero: true,
            grid: { color: '#f1f5f9' },
            ticks: { callback: (v) => v + ' ch.' }
          }
        }
      }
    });
  }

  // Render Block Summary Cards Comparing Both Tables
  function renderBlockCards() {
    const container = document.getElementById('blockCardsContainer');
    if (!container) return;

    const t1 = state.data.tables.table1_screening.records;
    const t2 = state.data.tables.table2_referrals.records;

    container.innerHTML = t1.map((r1, i) => {
      const r2 = t2[i];
      const s22 = r1.values['2022'];
      const s23 = r1.values['2023'];
      const ref22 = r2.values['2022'];
      const ref23 = r2.values['2023'];

      return `
        <div class="bg-white rounded-xl p-4 border border-slate-200 shadow-sm space-y-3">
          <div class="flex items-center justify-between pb-2 border-b border-slate-100">
            <span class="font-bold text-slate-900 text-sm flex items-center gap-1.5">
              <i data-lucide="map-pin" class="w-4 h-4 text-emerald-600"></i>
              ${r1.block} Block
            </span>
            <span class="text-[11px] font-mono text-slate-400">Rows 5-7</span>
          </div>

          <!-- Table 1 Summary -->
          <div class="p-2.5 bg-emerald-50/70 rounded-lg border border-emerald-100 space-y-1">
            <div class="flex items-center justify-between text-xs">
              <span class="font-semibold text-emerald-900">Screening Coverage (%)</span>
              <span class="font-bold text-emerald-700">+${r1.yoy_change}% YoY</span>
            </div>
            <div class="flex items-center justify-between text-xs text-slate-600">
              <span>2022: <strong>${s22}%</strong> <code class="text-[10px] text-emerald-700">(${r1.cells['2022']})</code></span>
              <span>2023: <strong>${s23}%</strong> <code class="text-[10px] text-emerald-700">(${r1.cells['2023']})</code></span>
            </div>
          </div>

          <!-- Table 2 Summary -->
          <div class="p-2.5 bg-blue-50/70 rounded-lg border border-blue-100 space-y-1">
            <div class="flex items-center justify-between text-xs">
              <span class="font-semibold text-blue-900">Anaemia Referrals</span>
              <span class="font-bold text-blue-700">+${r2.yoy_change} (+${r2.yoy_pct_growth}%)</span>
            </div>
            <div class="flex items-center justify-between text-xs text-slate-600">
              <span>2022: <strong>${ref22}</strong> <code class="text-[10px] text-blue-700">(${r2.cells['2022']})</code></span>
              <span>2023: <strong>${ref23}</strong> <code class="text-[10px] text-blue-700">(${r2.cells['2023']})</code></span>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  // Render Data Table (Side-by-Side, Table 1 only, or Table 2 only)
  function renderTable(searchTerm = '') {
    const container = document.getElementById('tableContainer');
    if (!container) return;

    const t1 = state.data.tables.table1_screening.records;
    const t2 = state.data.tables.table2_referrals.records;
    const year = state.selectedYear;
    const isYearAll = year === 'all';

    let blocks = ['Gaya', 'Nalanda', 'Purnia'];
    if (state.selectedBlock !== 'all') {
      blocks = blocks.filter(b => b.toLowerCase() === state.selectedBlock.toLowerCase());
    }
    if (searchTerm) {
      blocks = blocks.filter(b => b.toLowerCase().includes(searchTerm));
    }

    if (blocks.length === 0) {
      container.innerHTML = `<div class="py-8 text-center text-slate-400 text-xs">No matching block records found</div>`;
      return;
    }

    if (state.tableTab === 'sideBySide') {
      // Full Side-by-Side Table (Replicating Excel sheet layout)
      let html = `
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="bg-slate-100 text-slate-800 font-bold border-b border-slate-200">
              <th colspan="4" class="py-2.5 px-4 bg-emerald-100 text-emerald-900 border-r border-slate-300">
                🟢 Table 1. Nutrition screening by block and year (Range A1:C7)
              </th>
              <th class="w-4 bg-slate-200 border-r border-slate-300"></th>
              <th colspan="4" class="py-2.5 px-4 bg-blue-100 text-blue-900">
                🔵 Table 2. Completed anaemia referrals by block and year (Range E1:G7)
              </th>
            </tr>
            <tr class="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase tracking-wider text-[11px]">
              <th class="py-2 px-3">Block (Col A)</th>
              <th class="py-2 px-3 text-right">2022 (Col B)</th>
              <th class="py-2 px-3 text-right">2023 (Col C)</th>
              <th class="py-2 px-3 text-right border-r border-slate-300">YoY &Delta;</th>
              <th class="bg-slate-200 border-r border-slate-300"></th>
              <th class="py-2 px-3">Block (Col E)</th>
              <th class="py-2 px-3 text-right">2022 (Col F)</th>
              <th class="py-2 px-3 text-right">2023 (Col G)</th>
              <th class="py-2 px-3 text-right">YoY &Delta;</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
      `;

      blocks.forEach(b => {
        const r1 = t1.find(r => r.block === b);
        const r2 = t2.find(r => r.block === b);

        html += `
          <tr class="hover:bg-slate-50 transition">
            <td class="py-3 px-3 font-semibold text-slate-900 flex items-center gap-1">
              <i data-lucide="map-pin" class="w-3.5 h-3.5 text-emerald-600"></i> ${r1.block} <span class="text-slate-400 font-mono text-[10px]">(${r1.cell_block})</span>
            </td>
            <td class="py-3 px-3 text-right font-medium text-slate-700 ${year === '2022' ? 'bg-emerald-50/70 font-bold' : ''}">
              ${r1.values['2022']}% <span class="text-[10px] text-slate-400 font-mono">(${r1.cells['2022']})</span>
            </td>
            <td class="py-3 px-3 text-right font-medium text-slate-700 ${year === '2023' ? 'bg-emerald-50/70 font-bold' : ''}">
              ${r1.values['2023']}% <span class="text-[10px] text-slate-400 font-mono">(${r1.cells['2023']})</span>
            </td>
            <td class="py-3 px-3 text-right font-bold text-emerald-600 border-r border-slate-300">
              +${r1.yoy_change}%
            </td>
            <td class="bg-slate-100 border-r border-slate-300"></td>
            <td class="py-3 px-3 font-semibold text-slate-900">
              ${r2.block} <span class="text-slate-400 font-mono text-[10px]">(${r2.cell_block})</span>
            </td>
            <td class="py-3 px-3 text-right font-medium text-slate-700 ${year === '2022' ? 'bg-blue-50/70 font-bold' : ''}">
              ${r2.values['2022']} <span class="text-[10px] text-slate-400 font-mono">(${r2.cells['2022']})</span>
            </td>
            <td class="py-3 px-3 text-right font-medium text-slate-700 ${year === '2023' ? 'bg-blue-50/70 font-bold' : ''}">
              ${r2.values['2023']} <span class="text-[10px] text-slate-400 font-mono">(${r2.cells['2023']})</span>
            </td>
            <td class="py-3 px-3 text-right font-bold text-blue-600">
              +${r2.yoy_change} <span class="text-[10px] text-slate-400 font-normal">(+${r2.yoy_pct_growth}%)</span>
            </td>
          </tr>
        `;
      });

      html += `
          </tbody>
          <tfoot class="bg-slate-50 font-bold text-slate-900 border-t border-slate-200">
            <tr>
              <td class="py-2.5 px-3">Average / Total</td>
              <td class="py-2.5 px-3 text-right">62.3%</td>
              <td class="py-2.5 px-3 text-right">68.3%</td>
              <td class="py-2.5 px-3 text-right text-emerald-700 border-r border-slate-300">+6.0%</td>
              <td class="bg-slate-100 border-r border-slate-300"></td>
              <td class="py-2.5 px-3">Total Referrals</td>
              <td class="py-2.5 px-3 text-right">345</td>
              <td class="py-2.5 px-3 text-right">428</td>
              <td class="py-2.5 px-3 text-right text-blue-700">+83 (+24.1%)</td>
            </tr>
          </tfoot>
        </table>
      `;
      container.innerHTML = html;

    } else if (state.tableTab === 'table1') {
      // Table 1 only (Screening Coverage)
      let html = `
        <table class="w-full text-left text-xs border-collapse">
          <thead class="bg-emerald-50 text-emerald-950 font-bold border-b border-emerald-200 uppercase tracking-wider">
            <tr>
              <th class="py-3 px-4">Block Name (Col A)</th>
              <th class="py-3 px-4">Cell Block</th>
              <th class="py-3 px-4 text-right">2022 Coverage (%) (Col B)</th>
              <th class="py-3 px-4 text-right">2023 Coverage (%) (Col C)</th>
              <th class="py-3 px-4 text-right">Selected (${year})</th>
              <th class="py-3 px-4 text-right">YoY Difference</th>
              <th class="py-3 px-4 text-center">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
      `;

      blocks.forEach(b => {
        const r1 = t1.find(r => r.block === b);
        const selVal = isYearAll ? `${r1.values['2023']}% (vs ${r1.values['2022']}%)` : `${r1.values[year]}%`;
        const selCell = isYearAll ? `${r1.cells['2022']}, ${r1.cells['2023']}` : r1.cells[year];

        html += `
          <tr class="hover:bg-slate-50 transition">
            <td class="py-3 px-4 font-semibold text-slate-900">${r1.block}</td>
            <td class="py-3 px-4 font-mono text-slate-500">${r1.cell_block}</td>
            <td class="py-3 px-4 text-right">${r1.values['2022']}% <span class="text-[10px] text-slate-400 font-mono">(${r1.cells['2022']})</span></td>
            <td class="py-3 px-4 text-right">${r1.values['2023']}% <span class="text-[10px] text-slate-400 font-mono">(${r1.cells['2023']})</span></td>
            <td class="py-3 px-4 text-right font-bold text-emerald-800 bg-emerald-50/60">${selVal} <span class="text-[10px] text-emerald-700 font-mono">(${selCell})</span></td>
            <td class="py-3 px-4 text-right font-bold text-emerald-600">+${r1.yoy_change}%</td>
            <td class="py-3 px-4 text-center"><span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-100 text-emerald-800">${r1.values['2023'] >= 70 ? 'Target Met' : 'Approaching'}</span></td>
          </tr>
        `;
      });

      html += `</tbody></table>`;
      container.innerHTML = html;

    } else {
      // Table 2 only (Referrals Completed)
      let html = `
        <table class="w-full text-left text-xs border-collapse">
          <thead class="bg-blue-50 text-blue-950 font-bold border-b border-blue-200 uppercase tracking-wider">
            <tr>
              <th class="py-3 px-4">Block Name (Col E)</th>
              <th class="py-3 px-4">Cell Block</th>
              <th class="py-3 px-4 text-right">2022 Referrals (Col F)</th>
              <th class="py-3 px-4 text-right">2023 Referrals (Col G)</th>
              <th class="py-3 px-4 text-right">Selected (${year})</th>
              <th class="py-3 px-4 text-right">YoY Increase</th>
              <th class="py-3 px-4 text-right">Growth Rate</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
      `;

      blocks.forEach(b => {
        const r2 = t2.find(r => r.block === b);
        const selVal = isYearAll ? `${r2.values['2023']} (vs ${r2.values['2022']})` : `${r2.values[year]} children`;
        const selCell = isYearAll ? `${r2.cells['2022']}, ${r2.cells['2023']}` : r2.cells[year];

        html += `
          <tr class="hover:bg-slate-50 transition">
            <td class="py-3 px-4 font-semibold text-slate-900">${r2.block}</td>
            <td class="py-3 px-4 font-mono text-slate-500">${r2.cell_block}</td>
            <td class="py-3 px-4 text-right">${r2.values['2022']} <span class="text-[10px] text-slate-400 font-mono">(${r2.cells['2022']})</span></td>
            <td class="py-3 px-4 text-right">${r2.values['2023']} <span class="text-[10px] text-slate-400 font-mono">(${r2.cells['2023']})</span></td>
            <td class="py-3 px-4 text-right font-bold text-blue-800 bg-blue-50/60">${selVal} <span class="text-[10px] text-blue-700 font-mono">(${selCell})</span></td>
            <td class="py-3 px-4 text-right font-bold text-blue-600">+${r2.yoy_change} children</td>
            <td class="py-3 px-4 text-right font-semibold text-slate-700">+${r2.yoy_pct_growth}%</td>
          </tr>
        `;
      });

      html += `</tbody></table>`;
      container.innerHTML = html;
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
        descEl.innerHTML = 'Viewing sheet: <strong class="text-emerald-700 font-mono">Quarterly Review</strong>. Highlighting Table 1 (<strong class="text-emerald-700 font-mono">A1:C7</strong>) and Table 2 (<strong class="text-blue-700 font-mono">E1:G7</strong>).';
      } else if (sheetName === 'Definitions') {
        descEl.innerHTML = 'Viewing sheet: <strong class="text-emerald-700 font-mono">Definitions</strong>. Indicator glossary & metadata for Screening and Referrals.';
      } else {
        descEl.innerHTML = 'Viewing sheet: <strong class="text-emerald-700 font-mono">Household Visits Raw</strong>. Visit-level survey logs.';
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
          tooltip += ` • Table 1 Data: ${cell.block || ''}${cell.year ? ` | Year: ${cell.year}` : ''} | Value: ${cell.value}%`;
        } else if (cell.isCompanionTitle) {
          cellClass += ' excel-highlight-companion-title';
          tooltip += ' • Table 2 Title (Merged E1:G1)';
        } else if (cell.isCompanionHeader || cell.isCompanionSubHeader) {
          cellClass += ' excel-highlight-companion-col-header';
          tooltip += ' • Table 2 Header (Referrals Completed)';
        } else if (cell.isCompanionData) {
          cellClass += ' excel-highlight-companion-data';
          tooltip += ` • Table 2 Data: ${cell.block || ''}${cell.year ? ` | Year: ${cell.year}` : ''} | Value: ${cell.value} referrals`;
        } else if (cell.isColD) {
          cellClass += ' excel-grid-col-d';
          tooltip += ' • Column D (Separator)';
        } else if (cell.isHeader) {
          cellClass += ' bg-slate-100 font-bold text-slate-800';
        } else if (cell.isTargetHighlight) {
          cellClass += ' bg-emerald-50 text-emerald-900 font-medium';
        } else if (cell.isCompanionHighlight) {
          cellClass += ' bg-blue-50 text-blue-900 font-medium';
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

  // Export Combined CSV
  function exportCSV() {
    const t1 = state.data.tables.table1_screening.records;
    const t2 = state.data.tables.table2_referrals.records;

    let csvContent = 'data:text/csv;charset=utf-8,';
    csvContent += 'Source Workbook,nutrition_review_side_by_side.xlsx\n';
    csvContent += 'Source Sheet,Quarterly Review\n';
    csvContent += 'Table 1,Nutrition screening by block and year (A1:C7)\n';
    csvContent += 'Table 2,Completed anaemia referrals by block and year (E1:G7)\n\n';
    csvContent += 'Block,Table 1 Row,2022 Screening (%),2023 Screening (%),Screening Change (pp),Table 2 Row,2022 Referrals,2023 Referrals,Referrals Change\n';

    t1.forEach((r1, i) => {
      const r2 = t2[i];
      csvContent += `${r1.block},${r1.cell_block},${r1.values['2022']}%,${r1.values['2023']}%,+${r1.yoy_change}%,${r2.cell_block},${r2.values['2022']},${r2.values['2023']},+${r2.yoy_change}\n`;
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', 'nutrition_screening_and_anaemia_referrals_A1_G7.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

})();
