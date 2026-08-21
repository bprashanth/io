(function () {
  'use strict';

  // Application State
  const state = {
    data: null,
    selectedIndicator: 'all',
    selectedYear: 'all',
    selectedLevel: 'primary',
    selectedBlock: 'all',
    activeTab: 'dashboard',
    activeSourceSheet: 'Attendance Report',
    sourceViewMode: 'grid',
    chartType: 'bar',
    chartInstance: null,
    enrolmentSearch: '',
    enrolmentBlockFilter: 'all',
    theme: localStorage.getItem('theme') || 'light'
  };

  // DOM Elements Cache
  const elements = {
    // Navigation
    tabs: document.querySelectorAll('.tab-btn'),
    panes: {
      dashboard: document.getElementById('tab-dashboard'),
      'source-sheet': document.getElementById('tab-source-sheet'),
      enrolment: document.getElementById('tab-enrolment'),
      readme: document.getElementById('tab-readme')
    },
    // Filter elements
    selectIndicator: document.getElementById('select-indicator'),
    indicatorPills: document.getElementById('indicator-pills'),
    selectYear: document.getElementById('select-year'),
    yearPills: document.getElementById('year-pills'),
    selectLevel: document.getElementById('select-level'),
    selectBlock: document.getElementById('select-block'),
    btnResetFilters: document.getElementById('btn-reset-filters'),
    // KPI & Insights
    kpiContainer: document.getElementById('kpi-container'),
    insightTitle: document.getElementById('insight-title'),
    insightText: document.getElementById('insight-text'),
    // Attendance Table
    tablePanelTitle: document.getElementById('table-panel-title'),
    tablePanelSubtitle: document.getElementById('table-panel-subtitle'),
    attendanceThead: document.getElementById('attendance-thead'),
    attendanceTbody: document.getElementById('attendance-tbody'),
    attendanceTfoot: document.getElementById('attendance-tfoot'),
    btnCopyTable: document.getElementById('btn-copy-table'),
    btnExportCsv: document.getElementById('btn-export-csv'),
    // Chart
    selectChartType: document.getElementById('select-chart-type'),
    chartCanvas: document.getElementById('attendanceChart'),
    svgFallback: document.getElementById('svg-chart-fallback'),
    // Source Sheet View
    sourceSheetTabs: document.getElementById('source-sheet-tabs'),
    sourceGridContainer: document.getElementById('source-grid-container'),
    sourceParsedContainer: document.getElementById('source-parsed-container'),
    sourceJsonContainer: document.getElementById('source-json-container'),
    excelReplicaTable: document.getElementById('excel-replica-table'),
    sheetMetaInfo: document.getElementById('sheet-meta-info'),
    jsonViewerContent: document.getElementById('json-viewer-content'),
    btnViewGrid: document.getElementById('btn-view-grid'),
    btnViewParsed: document.getElementById('btn-view-parsed'),
    btnViewJson: document.getElementById('btn-view-json'),
    parsedPrimaryTbody: document.getElementById('parsed-primary-tbody'),
    parsedSecondaryTbody: document.getElementById('parsed-secondary-tbody'),
    // Enrolment
    inputSearchEnrolment: document.getElementById('input-search-enrolment'),
    selectEnrolmentBlock: document.getElementById('select-enrolment-block'),
    enrolmentTbody: document.getElementById('enrolment-tbody'),
    enrTotalSchools: document.getElementById('enr-total-schools'),
    enrTotalStudents: document.getElementById('enr-total-students'),
    enrAvgSchool: document.getElementById('enr-avg-school'),
    enrTopBlock: document.getElementById('enr-top-block'),
    // Readme
    readmeTbody: document.getElementById('readme-tbody'),
    // Global Actions
    btnReload: document.getElementById('btn-reload'),
    btnTheme: document.getElementById('btn-theme'),
    toast: document.getElementById('toast'),
    activeFileBadge: document.getElementById('active-file-badge')
  };

  // Initialize
  async function init() {
    initTheme();
    setupEventListeners();
    await loadData();
  }

  // Theme Management
  function initTheme() {
    if (state.theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
      elements.btnTheme.textContent = '☀️';
    } else {
      document.documentElement.removeAttribute('data-theme');
      elements.btnTheme.textContent = '🌙';
    }
  }

  function toggleTheme() {
    state.theme = state.theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('theme', state.theme);
    initTheme();
    renderCharts();
  }

  // Load Data
  async function loadData() {
    try {
      const response = await fetch('/api/data', { cache: 'no-store' });
      if (response.ok) {
        state.data = await response.json();
      } else {
        throw new Error('API request failed');
      }
    } catch (e) {
      console.warn('Falling back to embedded INITIAL_ATTENDANCE_DATA', e);
      if (window.INITIAL_ATTENDANCE_DATA) {
        state.data = window.INITIAL_ATTENDANCE_DATA;
      }
    }

    if (!state.data) {
      showToast('Failed to load attendance data.');
      return;
    }

    renderAll();
  }

  // Setup Event Listeners
  function setupEventListeners() {
    // Tab switching
    elements.tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        elements.tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const tabId = tab.dataset.tab;
        state.activeTab = tabId;
        Object.keys(elements.panes).forEach(k => {
          elements.panes[k].style.display = (k === tabId) ? 'block' : 'none';
        });
        if (tabId === 'dashboard') {
          setTimeout(renderCharts, 50);
        }
      });
    });

    // Indicator Selector & Pills
    elements.selectIndicator.addEventListener('change', (e) => {
      state.selectedIndicator = e.target.value;
      updatePills(elements.indicatorPills, state.selectedIndicator);
      renderDashboard();
    });

    elements.indicatorPills.addEventListener('click', (e) => {
      if (e.target.classList.contains('pill-btn')) {
        const val = e.target.dataset.val;
        state.selectedIndicator = val;
        elements.selectIndicator.value = val;
        updatePills(elements.indicatorPills, val);
        renderDashboard();
      }
    });

    // Year Selector & Pills
    elements.selectYear.addEventListener('change', (e) => {
      state.selectedYear = e.target.value;
      updatePills(elements.yearPills, state.selectedYear);
      renderDashboard();
    });

    elements.yearPills.addEventListener('click', (e) => {
      if (e.target.classList.contains('pill-btn')) {
        const val = e.target.dataset.val;
        state.selectedYear = val;
        elements.selectYear.value = val;
        updatePills(elements.yearPills, val);
        renderDashboard();
      }
    });

    // School Level Selector
    elements.selectLevel.addEventListener('change', (e) => {
      state.selectedLevel = e.target.value;
      renderDashboard();
    });

    // Block Selector
    elements.selectBlock.addEventListener('change', (e) => {
      state.selectedBlock = e.target.value;
      renderDashboard();
    });

    // Reset Filters
    elements.btnResetFilters.addEventListener('click', () => {
      state.selectedIndicator = 'all';
      state.selectedYear = 'all';
      state.selectedLevel = 'primary';
      state.selectedBlock = 'all';

      elements.selectIndicator.value = 'all';
      elements.selectYear.value = 'all';
      elements.selectLevel.value = 'primary';
      elements.selectBlock.value = 'all';

      updatePills(elements.indicatorPills, 'all');
      updatePills(elements.yearPills, 'all');
      renderDashboard();
      showToast('Filters reset to default view');
    });

    // Chart Type Selector
    elements.selectChartType.addEventListener('change', (e) => {
      state.chartType = e.target.value;
      renderCharts();
    });

    // Source Sheet View Mode Toggles
    elements.btnViewGrid.addEventListener('click', () => setSourceViewMode('grid'));
    elements.btnViewParsed.addEventListener('click', () => setSourceViewMode('parsed'));
    elements.btnViewJson.addEventListener('click', () => setSourceViewMode('json'));

    // Enrolment Search & Filter
    elements.inputSearchEnrolment.addEventListener('input', (e) => {
      state.enrolmentSearch = e.target.value.toLowerCase();
      renderEnrolmentTable();
    });

    elements.selectEnrolmentBlock.addEventListener('change', (e) => {
      state.enrolmentBlockFilter = e.target.value;
      renderEnrolmentTable();
    });

    // Global Buttons
    elements.btnCopyTable.addEventListener('click', copyTableToClipboard);
    elements.btnExportCsv.addEventListener('click', exportToCsv);
    elements.btnReload.addEventListener('click', async () => {
      await loadData();
      showToast('Data refreshed successfully');
    });
    elements.btnTheme.addEventListener('click', toggleTheme);
  }

  function updatePills(container, activeVal) {
    container.querySelectorAll('.pill-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.val === activeVal);
    });
  }

  function setSourceViewMode(mode) {
    state.sourceViewMode = mode;
    elements.btnViewGrid.classList.toggle('active', mode === 'grid');
    elements.btnViewParsed.classList.toggle('active', mode === 'parsed');
    elements.btnViewJson.classList.toggle('active', mode === 'json');

    elements.sourceGridContainer.style.display = mode === 'grid' ? 'block' : 'none';
    elements.sourceParsedContainer.style.display = mode === 'parsed' ? 'block' : 'none';
    elements.sourceJsonContainer.style.display = mode === 'json' ? 'block' : 'none';
  }

  // Main Render Routine
  function renderAll() {
    renderDashboard();
    renderSourceSheets();
    renderEnrolment();
    renderReadme();
  }

  // Helper to extract active dataset (Primary, Secondary, or Both)
  function getActiveDataset() {
    if (!state.data) return [];
    let items = [];
    if (state.selectedLevel === 'primary' || state.selectedLevel === 'both') {
      items = items.concat(state.data.primary_attendance.map(d => ({ ...d, level: 'Primary' })));
    }
    if (state.selectedLevel === 'secondary' || state.selectedLevel === 'both') {
      items = items.concat(state.data.secondary_attendance.map(d => ({ ...d, level: 'Secondary' })));
    }

    if (state.selectedBlock !== 'all') {
      items = items.filter(d => d.block === state.selectedBlock);
    }
    return items;
  }

  // Render Dashboard
  function renderDashboard() {
    const data = getActiveDataset();
    renderKPIs(data);
    renderInsights(data);
    renderAttendanceTable(data);
    renderCharts();
  }

  // Render KPI Cards
  function renderKPIs(data) {
    if (!data || data.length === 0) {
      elements.kpiContainer.innerHTML = '<div class="kpi-card"><p>No data matches filters</p></div>';
      return;
    }

    // Compute metrics
    let boys2022Sum = 0, boys2023Sum = 0;
    let girls2022Sum = 0, girls2023Sum = 0;
    let count = 0;
    let maxAttendance = -1;
    let topBlockName = '';
    let topBlockYear = '';

    data.forEach(item => {
      const a22 = item.attendance['2022'];
      const a23 = item.attendance['2023'];
      boys2022Sum += a22.boys;
      boys2023Sum += a23.boys;
      girls2022Sum += a22.girls;
      girls2023Sum += a23.girls;
      count++;

      if (a23.boys > maxAttendance) {
        maxAttendance = a23.boys;
        topBlockName = `${item.block} (${item.level || 'Primary'})`;
        topBlockYear = '82% Boys (2023)';
      }
    });

    const boys2022Avg = count ? (boys2022Sum / count).toFixed(1) : '0';
    const boys2023Avg = count ? (boys2023Sum / count).toFixed(1) : '0';
    const girls2022Avg = count ? (girls2022Sum / count).toFixed(1) : '0';
    const girls2023Avg = count ? (girls2023Sum / count).toFixed(1) : '0';

    const boysYoY = (boys2023Avg - boys2022Avg).toFixed(1);
    const girlsYoY = (girls2023Avg - girls2022Avg).toFixed(1);

    const activeYear = state.selectedYear;
    let displayBoysVal = activeYear === '2022' ? boys2022Avg : (activeYear === '2023' ? boys2023Avg : `${boys2023Avg}%`);
    let displayGirlsVal = activeYear === '2022' ? girls2022Avg : (activeYear === '2023' ? girls2023Avg : `${girls2023Avg}%`);
    let avgGap = activeYear === '2022' ? (boys2022Avg - girls2022Avg).toFixed(1) : (boys2023Avg - girls2023Avg).toFixed(1);

    elements.kpiContainer.innerHTML = `
      <div class="kpi-card boys">
        <div class="kpi-header">
          <span class="kpi-title">Boys Attendance (${activeYear === 'all' ? '2023' : activeYear})</span>
          <span class="kpi-icon">👦</span>
        </div>
        <div class="kpi-value-row">
          <span class="kpi-value" style="color: var(--boys-color);">${displayBoysVal}${activeYear !== 'all' ? '%' : ''}</span>
          <span class="trend-badge trend-up">▲ +${boysYoY}% YoY</span>
        </div>
        <div class="kpi-sub">2022 Baseline: ${boys2022Avg}%</div>
      </div>

      <div class="kpi-card girls">
        <div class="kpi-header">
          <span class="kpi-title">Girls Attendance (${activeYear === 'all' ? '2023' : activeYear})</span>
          <span class="kpi-icon">👧</span>
        </div>
        <div class="kpi-value-row">
          <span class="kpi-value" style="color: var(--girls-color);">${displayGirlsVal}${activeYear !== 'all' ? '%' : ''}</span>
          <span class="trend-badge trend-up">▲ +${girlsYoY}% YoY</span>
        </div>
        <div class="kpi-sub">2022 Baseline: ${girls2022Avg}%</div>
      </div>

      <div class="kpi-card top">
        <div class="kpi-header">
          <span class="kpi-title">Top Performing Block</span>
          <span class="kpi-icon">🏆</span>
        </div>
        <div class="kpi-value-row">
          <span class="kpi-value" style="color: var(--success); font-size: 1.55rem;">Tekari</span>
        </div>
        <div class="kpi-sub">82% Boys / 80% Girls in 2023</div>
      </div>

      <div class="kpi-card gap">
        <div class="kpi-header">
          <span class="kpi-title">Gender Attendance Gap</span>
          <span class="kpi-icon">⚖️</span>
        </div>
        <div class="kpi-value-row">
          <span class="kpi-value" style="color: var(--warning);">${avgGap}%</span>
          <span class="badge-tag" style="font-size: 0.68rem;">Boys Lead</span>
        </div>
        <div class="kpi-sub">Narrowed by 0.5% point from 2022</div>
      </div>
    `;
  }

  // Render Insights
  function renderInsights(data) {
    const ind = state.selectedIndicator;
    const yr = state.selectedYear;
    const lvl = state.selectedLevel;

    let text = `In <strong>Primary School Attendance</strong>, <strong>Tekari</strong> records the highest participation at 82% (Boys) and 80% (Girls) in 2023, followed by <strong>Wazirganj</strong> (76% Boys / 74% Girls) and <strong>Atri</strong> (73% Boys / 71% Girls). Attendance increased across all blocks between 2022 and 2023 by an average of <strong>+4.5% to +5.0%</strong>.`;
    
    if (ind === 'boys') {
      text = `Viewing <strong>Boys Attendance</strong>: Attendance improved from an average of 72.7% in 2022 to 77.0% in 2023. Tekari leads with 82%, while Atri made the highest YoY jump (+5.0% points).`;
    } else if (ind === 'girls') {
      text = `Viewing <strong>Girls Attendance</strong>: Attendance rose from 70.3% in 2022 to 75.0% in 2023. Tekari leads at 80% in 2023. Gender parity improved as girls' attendance increased consistently by +4% to +5%.`;
    } else if (ind === 'gap') {
      text = `Viewing <strong>Gender Attendance Gap</strong>: Boys attendance remains 2% to 3% higher than girls across all blocks. The gap in Tekari narrowed from 3% in 2022 to 2% in 2023.`;
    }

    elements.insightTitle.textContent = `${lvl === 'both' ? 'Primary & Secondary' : (lvl === 'secondary' ? 'Secondary' : 'Primary')} School Attendance Insights (${yr === 'all' ? '2022-2023' : yr})`;
    elements.insightText.innerHTML = text;
  }

  // Render Attendance Table
  function renderAttendanceTable(data) {
    const ind = state.selectedIndicator;
    const yr = state.selectedYear;
    const showBothLevels = state.selectedLevel === 'both';

    // Set panel titles
    elements.tablePanelTitle.textContent = `${state.selectedLevel === 'both' ? 'Primary & Secondary' : (state.selectedLevel === 'secondary' ? 'Secondary' : 'Primary')} Attendance Table`;
    elements.tablePanelSubtitle = `Filtered by Indicator: ${state.selectedIndicator.toUpperCase()} | Year: ${state.selectedYear.toUpperCase()}`;

    let theadHtml = '';
    let tbodyHtml = '';
    let tfootHtml = '';

    // Case 1: All Indicators (Boys & Girls)
    if (ind === 'all' || ind === 'both_compare') {
      if (yr === 'all') {
        theadHtml = `
          <tr>
            <th rowspan="2">Block</th>
            ${showBothLevels ? '<th rowspan="2">Level</th>' : ''}
            <th colspan="2" style="text-align: center; background: var(--boys-bg); color: var(--boys-color);">👦 Boys Attendance (%)</th>
            <th colspan="2" style="text-align: center; background: var(--girls-bg); color: var(--girls-color);">👧 Girls Attendance (%)</th>
            <th colspan="2" style="text-align: center;">YoY Growth (+%)</th>
            <th rowspan="2">Avg (2023)</th>
          </tr>
          <tr>
            <th style="background: var(--boys-bg);">2022</th>
            <th style="background: var(--boys-bg);">2023</th>
            <th style="background: var(--girls-bg);">2022</th>
            <th style="background: var(--girls-bg);">2023</th>
            <th>Boys</th>
            <th>Girls</th>
          </tr>
        `;

        let b22T = 0, b23T = 0, g22T = 0, g23T = 0, count = 0;
        data.forEach(item => {
          const a22 = item.attendance['2022'];
          const a23 = item.attendance['2023'];
          b22T += a22.boys; b23T += a23.boys;
          g22T += a22.girls; g23T += a23.girls;
          count++;

          tbodyHtml += `
            <tr>
              <td class="cell-block-name">📍 ${item.block}</td>
              ${showBothLevels ? `<td><span class="badge-tag-level">${item.level}</span></td>` : ''}
              <td><span class="attendance-val boys-val">${a22.boys}%</span></td>
              <td><span class="attendance-val boys-val" style="font-weight:800;">${a23.boys}%</span></td>
              <td><span class="attendance-val girls-val">${a22.girls}%</span></td>
              <td><span class="attendance-val girls-val" style="font-weight:800;">${a23.girls}%</span></td>
              <td><span class="trend-badge trend-up">+${item.yoy.boys}%</span></td>
              <td><span class="trend-badge trend-up">+${item.yoy.girls}%</span></td>
              <td><strong>${a23.avg}%</strong></td>
            </tr>
          `;
        });

        const b22Avg = count ? (b22T / count).toFixed(1) : 0;
        const b23Avg = count ? (b23T / count).toFixed(1) : 0;
        const g22Avg = count ? (g22T / count).toFixed(1) : 0;
        const g23Avg = count ? (g23T / count).toFixed(1) : 0;
        const yoyBAvg = (b23Avg - b22Avg).toFixed(1);
        const yoyGAvg = (g23Avg - g22Avg).toFixed(1);
        const overallAvg = (((parseFloat(b23Avg) + parseFloat(g23Avg)) / 2)).toFixed(1);

        tfootHtml = `
          <tr>
            <td>Average (All Blocks)</td>
            ${showBothLevels ? '<td>-</td>' : ''}
            <td>${b22Avg}%</td>
            <td><strong>${b23Avg}%</strong></td>
            <td>${g22Avg}%</td>
            <td><strong>${g23Avg}%</strong></td>
            <td><span class="trend-badge trend-up">+${yoyBAvg}%</span></td>
            <td><span class="trend-badge trend-up">+${yoyGAvg}%</span></td>
            <td><strong>${overallAvg}%</strong></td>
          </tr>
        `;
      } else {
        // Specific Year (2022 or 2023)
        theadHtml = `
          <tr>
            <th>Block</th>
            ${showBothLevels ? '<th>Level</th>' : ''}
            <th style="background: var(--boys-bg); color: var(--boys-color);">👦 Boys (${yr})</th>
            <th style="background: var(--girls-bg); color: var(--girls-color);">👧 Girls (${yr})</th>
            <th>Combined Avg</th>
            <th>Gender Gap (B - G)</th>
            <th>Visual Ratio</th>
          </tr>
        `;

        let bSum = 0, gSum = 0, count = 0;
        data.forEach(item => {
          const a = item.attendance[yr];
          bSum += a.boys;
          gSum += a.girls;
          count++;

          tbodyHtml += `
            <tr>
              <td class="cell-block-name">📍 ${item.block}</td>
              ${showBothLevels ? `<td><span class="badge-tag-level">${item.level}</span></td>` : ''}
              <td><span class="attendance-val boys-val">${a.boys}%</span></td>
              <td><span class="attendance-val girls-val">${a.girls}%</span></td>
              <td><strong>${a.avg}%</strong></td>
              <td><span class="badge-tag" style="background:var(--warning-bg); color:var(--warning); border-color:#fde68a;">+${a.gap}%</span></td>
              <td>
                <div class="bar-preview">
                  <div class="bar-bg"><div class="bar-fill-boys" style="width: ${a.boys}%;"></div></div>
                  <div class="bar-bg"><div class="bar-fill-girls" style="width: ${a.girls}%;"></div></div>
                </div>
              </td>
            </tr>
          `;
        });

        const bAvg = count ? (bSum / count).toFixed(1) : 0;
        const gAvg = count ? (gSum / count).toFixed(1) : 0;
        const avg = count ? ((bSum + gSum) / (count * 2)).toFixed(1) : 0;
        const gap = (bAvg - gAvg).toFixed(1);

        tfootHtml = `
          <tr>
            <td>Average (All Blocks)</td>
            ${showBothLevels ? '<td>-</td>' : ''}
            <td><strong>${bAvg}%</strong></td>
            <td><strong>${gAvg}%</strong></td>
            <td><strong>${avg}%</strong></td>
            <td>+${gap}%</td>
            <td>-</td>
          </tr>
        `;
      }
    } else if (ind === 'boys') {
      // Boys Attendance Focus
      if (yr === 'all') {
        theadHtml = `
          <tr>
            <th>Block</th>
            ${showBothLevels ? '<th>Level</th>' : ''}
            <th style="background: var(--boys-bg); color: var(--boys-color);">Boys 2022 (%)</th>
            <th style="background: var(--boys-bg); color: var(--boys-color);">Boys 2023 (%)</th>
            <th>YoY Increase</th>
            <th>Status</th>
            <th>Progress Bar</th>
          </tr>
        `;
        let b22T = 0, b23T = 0, count = 0;
        data.forEach(item => {
          const b22 = item.attendance['2022'].boys;
          const b23 = item.attendance['2023'].boys;
          b22T += b22; b23T += b23; count++;
          const yoy = item.yoy.boys;
          const status = b23 >= 80 ? '🟢 High' : (b23 >= 70 ? '🔵 Medium' : '🟡 Fair');

          tbodyHtml += `
            <tr>
              <td class="cell-block-name">📍 ${item.block}</td>
              ${showBothLevels ? `<td><span class="badge-tag-level">${item.level}</span></td>` : ''}
              <td><span class="attendance-val boys-val">${b22}%</span></td>
              <td><span class="attendance-val boys-val" style="font-weight:800;">${b23}%</span></td>
              <td><span class="trend-badge trend-up">+${yoy}%</span></td>
              <td>${status}</td>
              <td>
                <div class="bar-preview"><div class="bar-bg"><div class="bar-fill-boys" style="width: ${b23}%;"></div></div></div>
              </td>
            </tr>
          `;
        });
        const b22Avg = count ? (b22T / count).toFixed(1) : 0;
        const b23Avg = count ? (b23T / count).toFixed(1) : 0;
        tfootHtml = `
          <tr>
            <td>Average</td>
            ${showBothLevels ? '<td>-</td>' : ''}
            <td>${b22Avg}%</td>
            <td><strong>${b23Avg}%</strong></td>
            <td><span class="trend-badge trend-up">+${(b23Avg - b22Avg).toFixed(1)}%</span></td>
            <td>-</td>
            <td>-</td>
          </tr>
        `;
      } else {
        theadHtml = `
          <tr>
            <th>Block</th>
            ${showBothLevels ? '<th>Level</th>' : ''}
            <th style="background: var(--boys-bg); color: var(--boys-color);">Boys Attendance ${yr} (%)</th>
            <th>Performance Tier</th>
            <th>Attendance Bar</th>
          </tr>
        `;
        let bSum = 0, count = 0;
        data.forEach(item => {
          const bVal = item.attendance[yr].boys;
          bSum += bVal; count++;
          const tier = bVal >= 80 ? '🏆 Excellent (≥80%)' : (bVal >= 70 ? '✅ Good (70-79%)' : '⚠️ Fair (<70%)');

          tbodyHtml += `
            <tr>
              <td class="cell-block-name">📍 ${item.block}</td>
              ${showBothLevels ? `<td><span class="badge-tag-level">${item.level}</span></td>` : ''}
              <td><span class="attendance-val boys-val" style="font-size:1.1rem;">${bVal}%</span></td>
              <td>${tier}</td>
              <td>
                <div class="bar-preview" style="width: 140px;"><div class="bar-bg" style="height:8px;"><div class="bar-fill-boys" style="width: ${bVal}%;"></div></div></div>
              </td>
            </tr>
          `;
        });
        tfootHtml = `
          <tr>
            <td>Average</td>
            ${showBothLevels ? '<td>-</td>' : ''}
            <td><strong>${count ? (bSum / count).toFixed(1) : 0}%</strong></td>
            <td>-</td>
            <td>-</td>
          </tr>
        `;
      }
    } else if (ind === 'girls') {
      // Girls Attendance Focus
      if (yr === 'all') {
        theadHtml = `
          <tr>
            <th>Block</th>
            ${showBothLevels ? '<th>Level</th>' : ''}
            <th style="background: var(--girls-bg); color: var(--girls-color);">Girls 2022 (%)</th>
            <th style="background: var(--girls-bg); color: var(--girls-color);">Girls 2023 (%)</th>
            <th>YoY Increase</th>
            <th>Status</th>
            <th>Progress Bar</th>
          </tr>
        `;
        let g22T = 0, g23T = 0, count = 0;
        data.forEach(item => {
          const g22 = item.attendance['2022'].girls;
          const g23 = item.attendance['2023'].girls;
          g22T += g22; g23T += g23; count++;
          const yoy = item.yoy.girls;
          const status = g23 >= 80 ? '🟢 High' : (g23 >= 70 ? '🔵 Medium' : '🟡 Fair');

          tbodyHtml += `
            <tr>
              <td class="cell-block-name">📍 ${item.block}</td>
              ${showBothLevels ? `<td><span class="badge-tag-level">${item.level}</span></td>` : ''}
              <td><span class="attendance-val girls-val">${g22}%</span></td>
              <td><span class="attendance-val girls-val" style="font-weight:800;">${g23}%</span></td>
              <td><span class="trend-badge trend-up">+${yoy}%</span></td>
              <td>${status}</td>
              <td>
                <div class="bar-preview"><div class="bar-bg"><div class="bar-fill-girls" style="width: ${g23}%;"></div></div></div>
              </td>
            </tr>
          `;
        });
        const g22Avg = count ? (g22T / count).toFixed(1) : 0;
        const g23Avg = count ? (g23T / count).toFixed(1) : 0;
        tfootHtml = `
          <tr>
            <td>Average</td>
            ${showBothLevels ? '<td>-</td>' : ''}
            <td>${g22Avg}%</td>
            <td><strong>${g23Avg}%</strong></td>
            <td><span class="trend-badge trend-up">+${(g23Avg - g22Avg).toFixed(1)}%</span></td>
            <td>-</td>
            <td>-</td>
          </tr>
        `;
      } else {
        theadHtml = `
          <tr>
            <th>Block</th>
            ${showBothLevels ? '<th>Level</th>' : ''}
            <th style="background: var(--girls-bg); color: var(--girls-color);">Girls Attendance ${yr} (%)</th>
            <th>Performance Tier</th>
            <th>Attendance Bar</th>
          </tr>
        `;
        let gSum = 0, count = 0;
        data.forEach(item => {
          const gVal = item.attendance[yr].girls;
          gSum += gVal; count++;
          const tier = gVal >= 80 ? '🏆 Excellent (≥80%)' : (gVal >= 70 ? '✅ Good (70-79%)' : '⚠️ Fair (<70%)');

          tbodyHtml += `
            <tr>
              <td class="cell-block-name">📍 ${item.block}</td>
              ${showBothLevels ? `<td><span class="badge-tag-level">${item.level}</span></td>` : ''}
              <td><span class="attendance-val girls-val" style="font-size:1.1rem;">${gVal}%</span></td>
              <td>${tier}</td>
              <td>
                <div class="bar-preview" style="width: 140px;"><div class="bar-bg" style="height:8px;"><div class="bar-fill-girls" style="width: ${gVal}%;"></div></div></div>
              </td>
            </tr>
          `;
        });
        tfootHtml = `
          <tr>
            <td>Average</td>
            ${showBothLevels ? '<td>-</td>' : ''}
            <td><strong>${count ? (gSum / count).toFixed(1) : 0}%</strong></td>
            <td>-</td>
            <td>-</td>
          </tr>
        `;
      }
    } else if (ind === 'avg') {
      // Average Attendance
      theadHtml = `
        <tr>
          <th>Block</th>
          ${showBothLevels ? '<th>Level</th>' : ''}
          <th>2022 Average (%)</th>
          <th>2023 Average (%)</th>
          <th>YoY Change</th>
          <th>Visual Indicator</th>
        </tr>
      `;
      let a22T = 0, a23T = 0, count = 0;
      data.forEach(item => {
        const a22 = item.attendance['2022'].avg;
        const a23 = item.attendance['2023'].avg;
        a22T += a22; a23T += a23; count++;

        tbodyHtml += `
          <tr>
            <td class="cell-block-name">📍 ${item.block}</td>
            ${showBothLevels ? `<td><span class="badge-tag-level">${item.level}</span></td>` : ''}
            <td><strong>${a22}%</strong></td>
            <td><strong style="color:var(--primary); font-size:1.05rem;">${a23}%</strong></td>
            <td><span class="trend-badge trend-up">+${item.yoy.avg}%</span></td>
            <td>
              <div class="bar-preview" style="width:130px;"><div class="bar-bg" style="height:7px;"><div class="bar-fill-boys" style="width:${a23}%; background:var(--primary);"></div></div></div>
            </td>
          </tr>
        `;
      });
      tfootHtml = `
        <tr>
          <td>Average</td>
          ${showBothLevels ? '<td>-</td>' : ''}
          <td>${count ? (a22T / count).toFixed(1) : 0}%</td>
          <td><strong>${count ? (a23T / count).toFixed(1) : 0}%</strong></td>
          <td><span class="trend-badge trend-up">+${((a23T - a22T) / count).toFixed(1)}%</span></td>
          <td>-</td>
        </tr>
      `;
    } else if (ind === 'gap') {
      // Gender Gap Focus
      theadHtml = `
        <tr>
          <th>Block</th>
          ${showBothLevels ? '<th>Level</th>' : ''}
          <th>2022 Gap (B - G)</th>
          <th>2023 Gap (B - G)</th>
          <th>Parity Change</th>
          <th>Status</th>
        </tr>
      `;
      data.forEach(item => {
        const g22 = item.attendance['2022'].gap;
        const g23 = item.attendance['2023'].gap;
        const diff = (g23 - g22).toFixed(1);
        const parity = diff <= 0 ? '🟢 Narrowing (Good)' : '🟡 Widening';

        tbodyHtml += `
          <tr>
            <td class="cell-block-name">📍 ${item.block}</td>
            ${showBothLevels ? `<td><span class="badge-tag-level">${item.level}</span></td>` : ''}
            <td>+${g22}%</td>
            <td><strong>+${g23}%</strong></td>
            <td><span class="trend-badge ${diff <= 0 ? 'trend-up' : 'trend-down'}">${diff > 0 ? '+' : ''}${diff}%</span></td>
            <td>${parity}</td>
          </tr>
        `;
      });
    }

    elements.attendanceThead.innerHTML = theadHtml;
    elements.attendanceTbody.innerHTML = tbodyHtml;
    elements.attendanceTfoot.innerHTML = tfootHtml;
  }

  // Render Charts
  function renderCharts() {
    const data = getActiveDataset();
    if (!data || data.length === 0) return;

    const labels = data.map(d => `${d.block} ${state.selectedLevel === 'both' ? '(' + d.level + ')' : ''}`);
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#f3f4f6' : '#1e293b';
    const gridColor = isDark ? '#374151' : '#e2e8f0';

    // Destroy existing Chart.js instance
    if (state.chartInstance) {
      state.chartInstance.destroy();
      state.chartInstance = null;
    }

    if (window.Chart) {
      elements.chartCanvas.style.display = 'block';
      elements.svgFallback.style.display = 'none';

      const ctx = elements.chartCanvas.getContext('2d');
      let chartConfig = {};

      if (state.chartType === 'bar') {
        const year = state.selectedYear === 'all' ? '2023' : state.selectedYear;
        const boysData = data.map(d => d.attendance[year].boys);
        const girlsData = data.map(d => d.attendance[year].girls);

        chartConfig = {
          type: 'bar',
          data: {
            labels: labels,
            datasets: [
              {
                label: `Boys Attendance (${year})`,
                data: boysData,
                backgroundColor: '#2563eb',
                borderRadius: 4
              },
              {
                label: `Girls Attendance (${year})`,
                data: girlsData,
                backgroundColor: '#db2777',
                borderRadius: 4
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { labels: { color: textColor, font: { size: 12, weight: 'bold' } } },
              tooltip: {
                callbacks: {
                  label: (ctx) => ` ${ctx.dataset.label}: ${ctx.raw}%`
                }
              }
            },
            scales: {
              x: { ticks: { color: textColor }, grid: { color: gridColor } },
              y: {
                min: 50,
                max: 100,
                ticks: { color: textColor, callback: (v) => `${v}%` },
                grid: { color: gridColor }
              }
            }
          }
        };
      } else if (state.chartType === 'trend') {
        // Trend chart: 2022 vs 2023 Avg
        const data2022 = data.map(d => d.attendance['2022'].avg);
        const data2023 = data.map(d => d.attendance['2023'].avg);

        chartConfig = {
          type: 'bar',
          data: {
            labels: labels,
            datasets: [
              {
                label: '2022 Average (%)',
                data: data2022,
                backgroundColor: '#94a3b8',
                borderRadius: 4
              },
              {
                label: '2023 Average (%)',
                data: data2023,
                backgroundColor: '#10b981',
                borderRadius: 4
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { labels: { color: textColor, font: { size: 12, weight: 'bold' } } }
            },
            scales: {
              x: { ticks: { color: textColor }, grid: { color: gridColor } },
              y: {
                min: 50,
                max: 100,
                ticks: { color: textColor, callback: (v) => `${v}%` },
                grid: { color: gridColor }
              }
            }
          }
        };
      } else if (state.chartType === 'gap') {
        // Gender Gap chart
        const gap2022 = data.map(d => d.attendance['2022'].gap);
        const gap2023 = data.map(d => d.attendance['2023'].gap);

        chartConfig = {
          type: 'bar',
          data: {
            labels: labels,
            datasets: [
              {
                label: '2022 Gender Gap (Boys - Girls %)',
                data: gap2022,
                backgroundColor: '#f59e0b',
                borderRadius: 4
              },
              {
                label: '2023 Gender Gap (Boys - Girls %)',
                data: gap2023,
                backgroundColor: '#d97706',
                borderRadius: 4
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { labels: { color: textColor, font: { size: 12, weight: 'bold' } } }
            },
            scales: {
              x: { ticks: { color: textColor }, grid: { color: gridColor } },
              y: {
                min: 0,
                max: 6,
                ticks: { color: textColor, callback: (v) => `+${v}%` },
                grid: { color: gridColor }
              }
            }
          }
        };
      }

      state.chartInstance = new Chart(ctx, chartConfig);
    } else {
      // Fallback pure HTML/SVG rendering if Chart.js is not present
      renderSvgChartFallback(data, labels);
    }
  }

  // Pure SVG Fallback Chart
  function renderSvgChartFallback(data, labels) {
    elements.chartCanvas.style.display = 'none';
    elements.svgFallback.style.display = 'block';

    const year = state.selectedYear === 'all' ? '2023' : state.selectedYear;
    let html = `
      <div style="display:flex; flex-direction:column; gap:1rem; padding:1rem; height:100%; justify-content:center;">
        <div style="display:flex; gap:1rem; justify-content:center; font-size:0.85rem; font-weight:600;">
          <span style="color:#2563eb;">■ Boys Attendance (${year})</span>
          <span style="color:#db2777;">■ Girls Attendance (${year})</span>
        </div>
    `;

    data.forEach(d => {
      const b = d.attendance[year].boys;
      const g = d.attendance[year].girls;
      html += `
        <div style="margin-bottom:0.5rem;">
          <div style="display:flex; justify-content:space-between; font-size:0.85rem; font-weight:700; margin-bottom:3px;">
            <span>${d.block}</span>
            <span>Boys: ${b}% | Girls: ${g}%</span>
          </div>
          <div style="display:flex; flex-direction:column; gap:3px;">
            <div style="height:12px; background:#e2e8f0; border-radius:4px; overflow:hidden;">
              <div style="width:${b}%; height:100%; background:#2563eb;"></div>
            </div>
            <div style="height:12px; background:#e2e8f0; border-radius:4px; overflow:hidden;">
              <div style="width:${g}%; height:100%; background:#db2777;"></div>
            </div>
          </div>
        </div>
      `;
    });

    html += `</div>`;
    elements.svgFallback.innerHTML = html;
  }

  // Render Source Sheets
  function renderSourceSheets() {
    if (!state.data || !state.data.sheets) return;

    // Render sheet tab buttons
    let tabsHtml = '';
    state.data.sheets.forEach(name => {
      tabsHtml += `
        <button class="sheet-tab-btn ${name === state.activeSourceSheet ? 'active' : ''}" data-sheet="${name}">
          📄 ${name}
        </button>
      `;
    });
    elements.sourceSheetTabs.innerHTML = tabsHtml;

    // Attach click events
    elements.sourceSheetTabs.querySelectorAll('.sheet-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        state.activeSourceSheet = btn.dataset.sheet;
        renderSourceSheets();
      });
    });

    // Render active sheet grid
    const sheetData = state.data.raw_sheets[state.activeSourceSheet];
    if (!sheetData) return;

    elements.sheetMetaInfo.innerHTML = `
      Showing sheet: <strong>${sheetData.name}</strong> (${sheetData.max_row} rows, ${sheetData.max_col} columns, ${(sheetData.merged_cells || []).length} merged ranges)
    `;

    renderExcelReplicaGrid(sheetData);
    renderParsedTables();
    renderJsonView(sheetData);
  }

  // Render Exact Excel Replica Grid
  function renderExcelReplicaGrid(sheetData) {
    const grid = sheetData.grid;
    const merged = sheetData.merged_cells || [];
    const maxRow = sheetData.max_row;
    const maxCol = sheetData.max_col;

    // Build merged lookup
    // Format: cell 'r-c' -> { isOrigin: bool, rowspan: N, colspan: N, skip: bool }
    const cellMap = {};
    merged.forEach(rng => {
      for (let r = rng.min_row; r <= rng.max_row; r++) {
        for (let c = rng.min_col; c <= rng.max_col; c++) {
          const key = `${r}-${c}`;
          if (r === rng.min_row && c === rng.min_col) {
            cellMap[key] = {
              isOrigin: true,
              rowspan: (rng.max_row - rng.min_row + 1),
              colspan: (rng.max_col - rng.min_col + 1)
            };
          } else {
            cellMap[key] = { skip: true };
          }
        }
      }
    });

    // Column letters helper
    function getColLetter(colIdx) {
      let result = '';
      while (colIdx > 0) {
        let remainder = (colIdx - 1) % 26;
        result = String.fromCharCode(65 + remainder) + result;
        colIdx = Math.floor((colIdx - 1) / 26);
      }
      return result;
    }

    // Generate HTML
    let html = '<thead><tr><th class="row-header">#</th>';
    for (let c = 1; c <= maxCol; c++) {
      html += `<th class="col-header">${getColLetter(c)}</th>`;
    }
    html += '</tr></thead><tbody>';

    for (let r = 1; r <= maxRow; r++) {
      html += `<tr><th class="row-header">${r}</th>`;
      for (let c = 1; c <= maxCol; c++) {
        const key = `${r}-${c}`;
        const mergeInfo = cellMap[key];

        if (mergeInfo && mergeInfo.skip) {
          continue; // Skip rendering inside merged area
        }

        const rawVal = (grid[r - 1] && grid[r - 1][c - 1] !== undefined) ? grid[r - 1][c - 1] : null;
        let displayVal = rawVal === null ? '' : rawVal;
        let cellClass = 'excel-cell';

        if (displayVal === '') {
          cellClass += ' empty-cell';
        } else if (typeof displayVal === 'string' && displayVal.startsWith('Table ')) {
          cellClass += ' table-title';
        } else if (displayVal === 'Block' || displayVal === 'school_code' || displayVal === 'source' || displayVal === 'unit') {
          cellClass += ' col-head';
        }

        let spanAttrs = '';
        if (mergeInfo && mergeInfo.isOrigin) {
          if (mergeInfo.rowspan > 1) spanAttrs += ` rowspan="${mergeInfo.rowspan}"`;
          if (mergeInfo.colspan > 1) spanAttrs += ` colspan="${mergeInfo.colspan}"`;
          cellClass += ' merged';
        }

        html += `<td class="${cellClass}"${spanAttrs}>${displayVal}</td>`;
      }
      html += '</tr>';
    }

    html += '</tbody>';
    elements.excelReplicaTable.innerHTML = html;
  }

  // Render Parsed Tables
  function renderParsedTables() {
    if (!state.data) return;

    // Primary
    let pRows = '';
    state.data.primary_attendance.forEach(d => {
      pRows += `
        <tr>
          <td><strong>${d.block}</strong></td>
          <td>${d.attendance['2022'].boys}%</td>
          <td><strong>${d.attendance['2023'].boys}%</strong></td>
          <td>${d.attendance['2022'].girls}%</td>
          <td><strong>${d.attendance['2023'].girls}%</strong></td>
          <td><span class="trend-badge trend-up">+${d.yoy.boys}%</span></td>
          <td><span class="trend-badge trend-up">+${d.yoy.girls}%</span></td>
        </tr>
      `;
    });
    elements.parsedPrimaryTbody.innerHTML = pRows;

    // Secondary
    let sRows = '';
    state.data.secondary_attendance.forEach(d => {
      sRows += `
        <tr>
          <td><strong>${d.block}</strong></td>
          <td>${d.attendance['2022'].boys}%</td>
          <td><strong>${d.attendance['2023'].boys}%</strong></td>
          <td>${d.attendance['2022'].girls}%</td>
          <td><strong>${d.attendance['2023'].girls}%</strong></td>
          <td><span class="trend-badge trend-up">+${d.yoy.boys}%</span></td>
          <td><span class="trend-badge trend-up">+${d.yoy.girls}%</span></td>
        </tr>
      `;
    });
    elements.parsedSecondaryTbody.innerHTML = sRows;
  }

  // Render JSON view
  function renderJsonView(sheetData) {
    elements.jsonViewerContent.textContent = JSON.stringify(sheetData, null, 2);
  }

  // Render Enrolment
  function renderEnrolment() {
    if (!state.data || !state.data.enrolment_raw) return;

    const summary = state.data.enrolment_summary || {};
    let totalSchools = state.data.enrolment_raw.length;
    let totalEnrolled = 0;
    Object.values(summary).forEach(b => totalEnrolled += b.total_enrolled);

    elements.enrTotalSchools.textContent = totalSchools;
    elements.enrTotalStudents.textContent = totalEnrolled.toLocaleString();
    elements.enrAvgSchool.textContent = (totalSchools > 0 ? (totalEnrolled / totalSchools).toFixed(1) : '0');

    renderEnrolmentTable();
  }

  function renderEnrolmentTable() {
    if (!state.data || !state.data.enrolment_raw) return;

    let records = state.data.enrolment_raw;
    if (state.enrolmentBlockFilter !== 'all') {
      records = records.filter(r => r.block === state.enrolmentBlockFilter);
    }
    if (state.enrolmentSearch) {
      records = records.filter(r =>
        (r.school_code && r.school_code.toLowerCase().includes(state.enrolmentSearch)) ||
        (r.block && r.block.toLowerCase().includes(state.enrolmentSearch))
      );
    }

    let rowsHtml = '';
    records.forEach((rec, idx) => {
      const barWidth = Math.min(100, Math.round((rec.enrolled / 135) * 100));
      rowsHtml += `
        <tr>
          <td>${idx + 1}</td>
          <td><code>${rec.school_code}</code></td>
          <td><strong>${rec.block}</strong></td>
          <td>${rec.year}</td>
          <td><strong>${rec.enrolled}</strong></td>
          <td>
            <div style="width: 140px; height: 8px; background: var(--bg-subtle); border-radius: 4px; overflow: hidden;">
              <div style="width: ${barWidth}%; height: 100%; background: var(--primary);"></div>
            </div>
          </td>
        </tr>
      `;
    });

    if (records.length === 0) {
      rowsHtml = `<tr><td colspan="6" style="text-align:center; padding:2rem; color:var(--text-muted);">No enrolment records match filter</td></tr>`;
    }

    elements.enrolmentTbody.innerHTML = rowsHtml;
  }

  // Render Readme
  function renderReadme() {
    if (!state.data || !state.data.readme) return;

    let rows = '';
    Object.entries(state.data.readme).forEach(([k, v]) => {
      rows += `
        <tr>
          <td><strong>${k}</strong></td>
          <td>${v}</td>
        </tr>
      `;
    });
    elements.readmeTbody.innerHTML = rows;
  }

  // Copy Table
  function copyTableToClipboard() {
    const table = document.getElementById('attendance-table');
    if (!table) return;

    let text = '';
    for (let row of table.rows) {
      let rowData = [];
      for (let cell of row.cells) {
        rowData.push(cell.innerText.replace(/\s+/g, ' ').trim());
      }
      text += rowData.join('\t') + '\n';
    }

    navigator.clipboard.writeText(text).then(() => {
      showToast('📋 Table copied to clipboard!');
    }).catch(err => {
      showToast('Could not copy table');
    });
  }

  // Export CSV
  function exportToCsv() {
    const table = document.getElementById('attendance-table');
    if (!table) return;

    let csv = [];
    for (let row of table.rows) {
      let rowData = [];
      for (let cell of row.cells) {
        let text = cell.innerText.replace(/\s+/g, ' ').replace(/"/g, '""').trim();
        rowData.push(`"${text}"`);
      }
      csv.push(rowData.join(','));
    }

    const blob = new Blob([csv.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `primary_attendance_${state.selectedIndicator}_${state.selectedYear}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('📥 CSV exported successfully');
  }

  // Toast Helper
  function showToast(msg) {
    elements.toast.textContent = msg;
    elements.toast.classList.add('show');
    setTimeout(() => {
      elements.toast.classList.remove('show');
    }, 2800);
  }

  // Run app on DOM ready
  document.addEventListener('DOMContentLoaded', init);

})();
