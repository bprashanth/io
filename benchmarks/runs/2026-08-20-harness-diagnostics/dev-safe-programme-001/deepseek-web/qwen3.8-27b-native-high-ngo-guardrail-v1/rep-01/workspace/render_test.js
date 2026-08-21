// Run index.html's own inline script against a minimal DOM stub and
// capture the rendered tables for each year selection.
const fs = require("fs");
const html = fs.readFileSync(__dirname + "/index.html", "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

function makeEl(id) {
  return {
    id,
    _innerHTML: "",
    _listeners: {},
    textContent: "",
    value: "",
    set innerHTML(v) { this._innerHTML = v; },
    get innerHTML() { return this._innerHTML; },
    appendChild(child) { (this.children ||= []).push(child); },
    addEventListener(ev, fn) { (this._listeners[ev] ||= []).push(fn); },
    dispatch(ev) { (this._listeners[ev] || []).forEach(fn => fn()); },
  };
}

const ids = ["yearSelect","compareHint","resultsCaption","resultsBody","compareCaption",
  "thCompOld","thCompNew","thEmpOld","thEmpNew","compareBody",
  "exampleCompletion","exampleEmployment"];
const els = Object.fromEntries(ids.map(id => [id, makeEl(id)]));

global.document = {
  getElementById: (id) => { if (!els[id]) throw new Error("unknown element id: " + id); return els[id]; },
  createElement: () => makeEl("option"),
};

eval(script); // defines yearSelect and renders the default (2023)

const strip = (h) => h.replace(/<[^>]+>/g, "|").replace(/\|+/g, " | ").replace(/^ | $/g, "");

let failures = 0;
const expect = (label, haystack, needle) => {
  const found = haystack.includes(needle);
  console.log((found ? "ok  " : "FAIL") + " " + label + (found ? "" : " — missing: " + needle));
  if (!found) failures++;
};

for (const year of ["2022", "2023"]) {
  els.yearSelect.value = year;
  els.yearSelect.dispatch("change");
  const results = els.resultsBody._innerHTML;
  const compare = els.compareBody._innerHTML;
  console.log("\n=== Selected year:", year, "===");
  console.log("hint:", els.compareHint.textContent);
  console.log("results caption:", els.resultsCaption.textContent);
  console.log("compare caption:", els.compareCaption.textContent);
  console.log("results rows:\n" + strip(results));
  console.log("compare rows:\n" + strip(compare));
  console.log("example completion:", els.exampleCompletion.textContent);
  console.log("example employment:", els.exampleEmployment.textContent);
}

// Spot-checks against independently recomputed values (see verify.js output)
els.yearSelect.value = "2023"; els.yearSelect.dispatch("change");
const r23 = strip(els.resultsBody._innerHTML);
expect("2023 Gaya row", r23, "Gaya | 1100 | 902 | 82.0 | 616 | 56.0");
expect("2023 All-districts row", r23, "All districts | 4300 | 3333 | 77.5 | 2206 | 51.3");
expect("2023 compare headers", els.thCompOld.textContent + els.thEmpNew.textContent, "Completion rate 2022 (%)Employment rate 2023 (%)");

els.yearSelect.value = "2022"; els.yearSelect.dispatch("change");
const r22 = strip(els.resultsBody._innerHTML);
const c22 = strip(els.compareBody._innerHTML);
expect("2022 Nalanda row", r22, "Nalanda | 900 | 765 | 85.0 | 540 | 60.0");
expect("2022 Kishanganj row", r22, "Kishanganj | 800 | 520 | 65.0 | 280 | 35.0");
expect("2022 comparison shows 2022 vs 2023", els.compareCaption.textContent, "Compare 2022 with 2023");
expect("2022 comparison Purnia change", c22, "Purnia | 70.0 | 73.0 | +3.0 | 42.0 | 46.0 | +4.0");
expect("2022 comparison Kishanganj change", c22, "Kishanganj | 65.0 | 68.0 | +3.0 | 35.0 | 38.0 | +3.0");

console.log(failures === 0 ? "\nRENDER TESTS PASSED" : `\n${failures} RENDER TEST(S) FAILED`);
process.exit(failures === 0 ? 0 : 1);
