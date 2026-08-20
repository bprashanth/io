"use strict";

/* ------------------------------------------------------------------ */
/* Embedded fallback: exact copy of anc4_coverage.csv so the site     */
/* still works when opened directly (file://) without a web server.   */
/* When served over HTTP, the live CSV file is fetched and preferred.  */
/* ------------------------------------------------------------------ */
const EMBEDDED_CSV = `district,year,pregnancies_registered,anc4_completed,source
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

/* ------------------------- CSV parsing ---------------------------- */

// Parse a simple CSV (header + rows). Values here contain no quotes,
// so a line split is safe, but we still trim whitespace.
function parseCSV(text) {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0);
  const header = lines[0].split(",").map((h) => h.trim());
  return lines.slice(1).map((line) => {
    const cells = line.split(",").map((c) => c.trim());
    const row = {};
    header.forEach((h, i) => {
      row[h] = cells[i] !== undefined ? cells[i] : "";
    });
    return row;
  });
}

function toInt(v) {
  const n = parseInt(v, 10);
  return Number.isFinite(n) ? n : 0;
}

/* ------------------------- Derived data --------------------------- */

// Coverage rate (%) = anc4_completed / pregnancies_registered * 100
function rate(row) {
  if (!row) return null;
  const den = toInt(row.pregnancies_registered);
  const num = toInt(row.anc4_completed);
  return den > 0 ? (num / den) * 100 : null;
}

function fmtPct(v, digits = 1) {
  return v === null ? "—" : v.toFixed(digits) + "%";
}

function fmtDelta(v) {
  if (v === null || v === undefined) return "—";
  const sign = v > 0 ? "+" : "";
  return sign + v.toFixed(1) + " pp";
}

/* ------------------------- Rendering ------------------------------ */

const yearSelect = document.getElementById("year-select");
const summaryLine = document.getElementById("summary-line");
const chartEl = document.getElementById("chart");
const chartYearEl = document.getElementById("chart-year");
const tableYearEl = document.getElementById("table-year");
const tableBody = document.getElementById("table-body");
const sourceLine = document.getElementById("source-line");
const workedExample = document.getElementById("worked-example");
const loadingNote = document.getElementById("data-loading-note");

let rows = [];
let years = [];
let currentYear = null;

function rowsFor(year) {
  return rows.filter((r) => Number(r.year) === year);
}

function render() {
  const year = currentYear;
  const data = rowsFor(year).map((r) => ({
    ...r,
    rate: rate(r),
    prevRate: rate(rows.find(
      (p) => p.district === r.district && Number(p.year) === year - 1
    )),
  }));

  // Rank by rate, best first
  data.sort((a, b) => (b.rate ?? -1) - (a.rate ?? -1));
  const best = data[0];
  const avg =
    data.reduce((s, d) => s + (d.rate ?? 0), 0) / (data.length || 1);

  chartYearEl.textContent = year;
  tableYearEl.textContent = year;

  if (best) {
    summaryLine.innerHTML =
      `${data.length} districts in ${year}. ` +
      `Highest: <strong>${best.district} (${fmtPct(best.rate)})</strong>, ` +
      `all-district average: <strong>${fmtPct(avg)}</strong>.`;
  } else {
    summaryLine.textContent = `No data for ${year}.`;
  }

  /* --- Bar chart (pure HTML/CSS) --- */
  chartEl.innerHTML = "";
  const maxRate = Math.max(...data.map((d) => d.rate ?? 0), 1);
  data.forEach((d, i) => {
    const barPct = d.rate === null ? 0 : (d.rate / maxRate) * 100;
    const delta =
      d.prevRate === null || d.rate === null
        ? null
        : d.rate - d.prevRate;
    const deltaCls =
      delta === null ? "delta-na" : delta >= 0 ? "delta-up" : "delta-down";
    const deltaTxt =
      delta === null ? "no prev. data" : fmtDelta(delta);

    const rowEl = document.createElement("div");
    rowEl.className = "chart-row";
    rowEl.innerHTML = `
      <div class="chart-label">
        <span class="chart-rank">${i + 1}</span>
        <span class="chart-district">${d.district}</span>
      </div>
      <div class="chart-track">
        <div class="chart-bar ${i === 0 ? "chart-bar-top" : ""}"
             style="width:${barPct.toFixed(2)}%"
             title="${d.district}: ${fmtPct(d.rate)}"></div>
        <span class="chart-value">${fmtPct(d.rate)}</span>
      </div>
      <div class="chart-delta ${deltaCls}">${deltaTxt}</div>`;
    chartEl.appendChild(rowEl);
  });

  /* --- Table --- */
  tableBody.innerHTML = "";
  data.forEach((d, i) => {
    const delta =
      d.prevRate === null || d.rate === null
        ? null
        : d.rate - d.prevRate;
    const deltaCls =
      delta === null ? "delta-na" : delta >= 0 ? "delta-up" : "delta-down";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${i + 1}</td>
      <td class="strong">${d.district}</td>
      <td>${toInt(d.anc4_completed).toLocaleString()}</td>
      <td>${toInt(d.pregnancies_registered).toLocaleString()}</td>
      <td class="strong">${fmtPct(d.rate)}</td>
      <td class="${deltaCls}">${fmtDelta(delta)}</td>`;
    tableBody.appendChild(tr);
  });

  /* --- Worked example for the selected year --- */
  if (best) {
    workedExample.innerHTML =
      `<strong>Example — ${best.district}, ${year}:</strong> ` +
      `${toInt(best.anc4_completed).toLocaleString()} completed 4+ checkups &divide; ` +
      `${toInt(best.pregnancies_registered).toLocaleString()} registered &times; 100 ` +
      `= <strong>${fmtPct(best.rate)}</strong>.`;
  } else {
    workedExample.textContent = "";
  }
}

function populateYearSelect() {
  years = [...new Set(rows.map((r) => Number(r.year)))].sort((a, b) => a - b);
  yearSelect.innerHTML = "";
  years.forEach((y) => {
    const opt = document.createElement("option");
    opt.value = y;
    opt.textContent = y;
    yearSelect.appendChild(opt);
  });
  if (years.length > 0) {
    currentYear = years[years.length - 1]; // most recent year by default
    yearSelect.value = String(currentYear);
  }
}

function populateSource() {
  const sources = [...new Set(rows.map((r) => r.source).filter(Boolean))];
  if (sources.length > 0) {
    sourceLine.innerHTML =
      `The <code>source</code> field in the CSV records this data as: ` +
      `<strong>${sources.join("; ")}</strong>.`;
  } else {
    sourceLine.textContent = "No source field found in the data.";
  }
}

/* ------------------------- Startup -------------------------------- */

async function loadData() {
  let text = EMBEDDED_CSV;
  let usingEmbedded = true;
  try {
    const res = await fetch("anc4_coverage.csv", { cache: "no-store" });
    if (res.ok) {
      text = await res.text();
      usingEmbedded = false;
    }
  } catch (e) {
    /* fetch failed (e.g. file:// protocol) — fall back to embedded copy */
  }
  rows = parseCSV(text);
  if (rows.length === 0) {
    loadingNote.textContent = "No rows could be parsed from the data.";
    return;
  }
  loadingNote.innerHTML = usingEmbedded
    ? `Data loaded from: the embedded copy of <code>anc4_coverage.csv</code> ` +
      `(live file was not reachable — this happens when the page is opened ` +
      `directly instead of via a web server).`
    : `Data loaded from: the live <code>anc4_coverage.csv</code> file in this folder.`;
}

async function main() {
  await loadData();
  populateYearSelect();
  populateSource();
  yearSelect.addEventListener("change", () => {
    currentYear = Number(yearSelect.value);
    render();
  });
  render();
}

main();

