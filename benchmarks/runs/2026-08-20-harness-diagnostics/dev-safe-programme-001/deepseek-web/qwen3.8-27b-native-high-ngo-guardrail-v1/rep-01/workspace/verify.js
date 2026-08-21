// Validation: cross-check index.html against women_livelihood_outcomes.csv
const fs = require("fs");
const path = require("path");
const dir = __dirname;

// 1. Parse the real CSV
const csv = fs.readFileSync(path.join(dir, "women_livelihood_outcomes.csv"), "utf8").trim().split(/\r?\n/);
const header = csv[0].split(",");
const rows = csv.slice(1).map(l => Object.fromEntries(l.split(",").map((v, i) => [header[i], v])));
const csvData = {};
const csvSource = new Set();
for (const r of rows) {
  (csvData[r.year] ||= {})[r.district] = {
    enrolled: +r.women_enrolled,
    completed: +r.completed_training,
    employed: +r.employed_at_6_months,
  };
  csvSource.add(r.source);
}

// 2. Extract embedded DATA from index.html and check it matches the CSV exactly
const html = fs.readFileSync(path.join(dir, "index.html"), "utf8");
const m = html.match(/const DATA = (\{[\s\S]*?\n\});/);
if (!m) throw new Error("Could not find embedded DATA in index.html");
const pageData = new Function("return (" + m[1] + ");")();

let failures = 0;
const fail = (msg) => { failures++; console.log("FAIL: " + msg); };
const ok = (msg) => console.log("ok: " + msg);

for (const [year, districts] of Object.entries(csvData)) {
  for (const [district, r] of Object.entries(districts)) {
    const p = pageData[year]?.[district];
    if (!p) { fail(`missing ${year}/${district} in page`); continue; }
    for (const k of ["enrolled", "completed", "employed"]) {
      if (p[k] !== r[k]) fail(`${year}/${district}.${k}: page=${p[k]} csv=${r[k]}`);
    }
  }
}
if (JSON.stringify(Object.keys(pageData).sort()) === JSON.stringify(Object.keys(csvData).sort())
  && csvData["2022"] && pageData["2022"]
  && JSON.stringify(Object.keys(pageData["2022"]).sort()) === JSON.stringify(Object.keys(csvData["2022"]).sort())) {
  ok("page DATA covers exactly the CSV districts and years");
} else fail("page DATA does not cover exactly the CSV districts/years");
if (csvSource.size === 1 && html.includes([...csvSource][0])) ok("source string shown on page matches CSV source field");
else fail("source string mismatch");

// 3. Independently recompute all displayed rates (formulas: completed/enrolled, employed/enrolled)
const pct = (n, d) => (n / d) * 100;
const f = (x) => x.toFixed(1);
const districts = Object.keys(csvData["2022"]);
const years = Object.keys(csvData).sort();
const totals = (y) => districts.reduce((t, d) => {
  const r = csvData[y][d];
  return { enrolled: t.enrolled + r.enrolled, completed: t.completed + r.completed, employed: t.employed + r.employed };
}, { enrolled: 0, completed: 0, employed: 0 });

console.log("\n--- Expected results (recomputed from CSV) ---");
for (const y of years) {
  console.log(`\nYear ${y}:`);
  for (const d of districts) {
    const r = csvData[y][d];
    console.log(`${d.padEnd(12)} enrolled=${String(r.enrolled).padStart(4)} completed=${String(r.completed).padStart(4)} completion=${f(pct(r.completed, r.enrolled))}% employed=${String(r.employed).padStart(4)} employment=${f(pct(r.employed, r.enrolled))}%`);
  }
  const t = totals(y);
  console.log(`All districts enrolled=${t.enrolled} completed=${t.completed} completion=${f(pct(t.completed, t.enrolled))}% employed=${t.employed} employment=${f(pct(t.employed, t.enrolled))}%`);
}

console.log("\n--- Expected comparison (2022 vs 2023, points) ---");
for (const d of [...districts, "All"]) {
  const a = d === "All" ? totals("2022") : csvData["2022"][d];
  const b = d === "All" ? totals("2023") : csvData["2023"][d];
  const dc = pct(b.completed, b.enrolled) - pct(a.completed, a.enrolled);
  const de = pct(b.employed, b.enrolled) - pct(a.employed, a.enrolled);
  console.log(`${d.padEnd(12)} completion ${f(pct(a.completed, a.enrolled))} -> ${f(pct(b.completed, b.enrolled))} (${dc >= 0 ? "+" : ""}${f(dc)}) | employment ${f(pct(a.employed, a.enrolled))} -> ${f(pct(b.employed, b.enrolled))} (${de >= 0 ? "+" : ""}${f(de)})`);
}

// 4. Worked example values shown for each year (Gaya)
console.log("\n--- Worked examples shown on page ---");
for (const y of years) {
  const g = csvData[y]["Gaya"];
  console.log(`Gaya ${y}: completion ${g.completed} \u00f7 ${g.enrolled} \u00d7 100 = ${f(pct(g.completed, g.enrolled))}% | employment ${g.employed} \u00f7 ${g.enrolled} \u00d7 100 = ${f(pct(g.employed, g.enrolled))}%`);
}

console.log(failures === 0 ? "\nALL CHECKS PASSED" : `\n${failures} CHECK(S) FAILED`);
process.exit(failures === 0 ? 0 : 1);
