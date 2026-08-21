
"use strict";

// ---- Raw data, exactly as it appears in anc4_coverage.csv ----
const CSV = `district,year,pregnancies_registered,anc4_completed,source
Gaya,2020,1200,744,synthetic Bihar ANC fixture
Gaya,2021,1250,825,synthetic Bihar ANC fixture
Gaya,2022,1300,897,synthetic Bihar ANC fixture
Gaya,2023,1350,999,synthetic Bihar ANC fixture
Nalanda,2020,1000,700,synthetic Bihar ANC fixture
Nalanda,2021,1100,803,synthetic Bihar ANC fixture
Nalanda,2022,1200,924,synthetic Bihar ANC fixture
Nalanda,2023,1250,1000,synthetic Bihar ANC fixture
Purnia,2020,1400,770,synthetic Bihar ANC fixture
Purnia,2021,1500,870,synthetic Bihar ANC fixture
Purnia,2022,1550,992,synthetic Bihar ANC fixture
Purnia,2023,1600,1072,synthetic Bihar ANC fixture
Kishanganj,2020,800,400,synthetic Bihar ANC fixture
Kishanganj,2021,900,486,synthetic Bihar ANC fixture
Kishanganj,2022,1000,570,synthetic Bihar ANC fixture
Kishanganj,2023,1100,671,synthetic Bihar ANC fixture
Patna,2020,1500,1170,synthetic Bihar ANC fixture
Patna,2021,1600,1280,synthetic Bihar ANC fixture
Patna,2022,1700,1411,synthetic Bihar ANC fixture
Patna,2023,1800,1548,synthetic Bihar ANC fixture`;

// ---- Parse CSV ----
function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  const header = lines[0].split(",").map(h => h.trim());
  const idx = {
    district: header.indexOf("district"),
    year: header.indexOf("year"),
    reg: header.indexOf("pregnancies_registered"),
    anc4: header.indexOf("anc4_completed"),
    source: header.indexOf("source")
  };
  return lines.slice(1).filter(l => l.trim()).map(line => {
    const c = line.split(",");
    return {
      district: c[idx.district].trim(),
      year: parseInt(c[idx.year], 10),
      reg: parseInt(c[idx.reg], 10),
      anc4: parseInt(c[idx.anc4], 10),
      source: c[idx.source].trim()
    };
  });
}

const ALL_ROWS = parseCSV(CSV);

// ---- Show only 2021–2023 (2020 rows are loaded but hidden from all views) ----
const MIN_YEAR = 2021, MAX_YEAR = 2023;
const rows = ALL_ROWS.filter(r => r.year >= MIN_YEAR && r.year <= MAX_YEAR);
const districts = [...new Set(rows.map(r => r.district))].sort((a, b) => a.localeCompare(b));
const years = [...new Set(rows.map(r => r.year))].sort((a, b) => a - b);
const sources = [...new Set(rows.map(r => r.source))];

let selectedYear = years[years.length - 1]; // default to latest year

const fmt = n => n.toLocaleString("en-US");
const rate = r => r.anc4 / r.reg * 100;
const pct = r => r.toFixed(1) + "%";
const rowFor = (d, y) => rows.find(r => r.district === d && r.year === y);

function aggregate(y) {
  const set = rows.filter(r => r.year === y);
  return {
    reg: set.reduce((s, r) => s + r.reg, 0),
    anc4: set.reduce((s, r) => s + r.anc4, 0)
  };
}

// ---- Render ----
function render() {
  const sel = document.getElementById("yearSelector");
  sel.innerHTML = "";
  years.forEach(y => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = y;
    b.className = y === selectedYear ? "active" : "";
    b.setAttribute("aria-pressed", String(y === selectedYear));
    b.addEventListener("click", () => { selectedYear = y; render(); });
    sel.appendChild(b);
  });

  const data = districts
    .map(d => ({ d, r: rowFor(d, selectedYear) }))
    .filter(x => x.r)
    .sort((a, b) => rate(b.r) - rate(a.r));

  const topRate = rate(data[0].r);
  const agg = aggregate(selectedYear);
  const aggRate = agg.anc4 / agg.reg * 100;

  // Summary strip
  document.getElementById("summary").innerHTML = `
    <div class="stat">
      <div class="label">All-district total, ${selectedYear}</div>
      <div class="value">${aggRate.toFixed(1)}%</div>
      <div class="hint">${fmt(agg.anc4)} of ${fmt(agg.reg)} pregnancies</div>
    </div>
    <div class="stat">
      <div class="label">Best district</div>
      <div class="value">${data[0].d}</div>
      <div class="hint">${pct(data[0].r)} ANC4 coverage</div>
    </div>
    <div class="stat">
      <div class="label">Lowest district</div>
      <div class="value">${data[data.length - 1].d}</div>
      <div class="hint">${pct(data[data.length - 1].r)} ANC4 coverage</div>
    </div>`;

  // Chart
  document.getElementById("chartTitle").textContent = `ANC4 coverage by district — ${selectedYear}`;
  const chart = document.getElementById("chart");
  chart.innerHTML = "";
  data.forEach(({ d, r }) => {
    const isBest = rate(r) === topRate;
    const rowEl = document.createElement("div");
    rowEl.className = "bar-row";
    rowEl.innerHTML = `
      <div class="name">${d}${isBest ? '<span class="best-tag">BEST</span>' : ""}</div>
      <div class="track" role="img" aria-label="${d}: ${pct(rate(r))} ANC4 coverage">
        <div class="fill" style="width:${rate(r).toFixed(2)}%"></div>
      </div>
      <div class="pct">${pct(rate(r))}</div>`;
    chart.appendChild(rowEl);
  });

  // Table
  const tbody = document.querySelector("#dataTable tbody");
  tbody.innerHTML = "";
  data.forEach(({ d, r }) => {
    const isBest = rate(r) === topRate;
    const trend = years.map(y => {
      const rr = rowFor(d, y);
      return `<span class="cell${y === selectedYear ? " sel" : ""}" title="${d} ${y}">${rr ? rate(rr).toFixed(0) : "–"}</span>`;
    }).join("");
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${d}${isBest ? " <b style='color:var(--best)'>★</b>" : ""}</td>
      <td>${fmt(r.reg)}</td>
      <td>${fmt(r.anc4)}</td>
      <td class="${isBest ? "best-td" : ""}">${pct(rate(r))}</td>
      <td><div class="trend">${trend}</div></td>`;
    tbody.appendChild(tr);
  });
  const total = document.createElement("tr");
  total.className = "total-row";
  total.innerHTML = `
    <td>All districts</td>
    <td>${fmt(agg.reg)}</td>
    <td>${fmt(agg.anc4)}</td>
    <td>${aggRate.toFixed(1)}%</td>
    <td></td>`;
  tbody.appendChild(total);

  // Live worked example
  const ex = data[0];
  document.getElementById("calcExample").innerHTML =
    `<b>Worked example (${ex.d}, ${selectedYear}):</b> ${fmt(ex.r.anc4)} pregnancies completed ANC4 out of ` +
    `${fmt(ex.r.reg)} registered → ${ex.r.anc4} &divide; ${ex.r.reg} &times; 100 = <b>${rate(ex.r).toFixed(1)}%</b>`;
}

// ---- Source card ----
function renderSource() {
  const ul = document.getElementById("sourceList");
  ul.innerHTML = sources
    .map(s => `<li><b>Source:</b> <code>${s}</code></li>`)
    .join("");
  const note = document.getElementById("syntheticNote");
  const isSynthetic = sources.some(s => /synthetic|fixture|demo|sample/i.test(s));
  if (isSynthetic) {
    note.hidden = false;
    note.textContent = "Note: the source is marked as a synthetic (generated) dataset — " +
      "these figures are a fixture for demonstration, not an official health survey.";
  }
  document.getElementById("trendTh").textContent = `Trend (${years[0]}→${years[years.length - 1]})`;
  document.getElementById("footerNote").textContent =
    `Data: ${sources.join(", ")} · ${districts.length} districts · years ${years[0]}–${years[years.length - 1]} · File: anc4_coverage.csv`;
}

renderSource();
render();
