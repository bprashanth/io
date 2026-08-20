// Runs the real <script> from index.html against a minimal DOM stub.
// Usage: node verify_page.js ["?query=string"]
// Prints a JSON report: the resolved state, control values, and the HTML the
// page's own functions produce for a set of indicator/year/district states.
const fs = require('fs');
const vm = require('vm');

const html = fs.readFileSync('index.html', 'utf8');
const code = html.match(/<script>([\s\S]*)<\/script>/)[1];

const els = {};
function el(id) {
  if (!els[id]) els[id] = { innerHTML: '', textContent: '', value: '', style: {}, addEventListener() {}, appendChild() {} };
  return els[id];
}
const created = [];
const sandbox = {
  document: {
    getElementById: el,
    createElement: tag => { const o = { tag, value: '', textContent: '', style: {}, checked: false, addEventListener() {}, appendChild() {} }; created.push(o); return o; },
    createTextNode: t => ({ t }),
    addEventListener() {},
  },
  location: { search: process.argv[2] || '' },
  history: { replaceState() {} },
  URLSearchParams,
  console,
};
vm.createContext(sandbox);
vm.runInContext(code, sandbox);

function fn(expr) { return vm.runInContext(expr, sandbox); }

function combo(ind, year, districts) {
  const s = `{indicator:${JSON.stringify(ind)}, year:${year}, districts:${JSON.stringify(districts)}}`;
  return {
    table: fn(`tableHTML(${s})`),
    summary: fn(`summaryText(${s})`),
    change: fn(`changeHTML(${s})`),
  };
}

const report = {
  search: process.argv[2] || '',
  state: JSON.parse(fn('JSON.stringify(state)')),
  csv: fn('buildCSV(state)'),
  csvName: fn('csvName(state)'),
  controls: {
    indicator: els['indicator'].value,
    year: els['year'].value,
    chips: created.filter(o => o.tag === 'input').map(o => ({ v: o.value, checked: o.checked })),
  },
  defaults: {
    postnatal48_2023_gaya_nalanda: combo('postnatal48', 2023, ['Gaya', 'Nalanda']),
    postnatal48_2022_gaya_nalanda: combo('postnatal48', 2022, ['Gaya', 'Nalanda']),
    institutional_2023_all: combo('institutional', 2023, ['Gaya', 'Nalanda', 'Purnia']),
    postnatal48_2023_none: combo('postnatal48', 2023, []),
  },
  init: {
    notesBody: els['notesBody'].innerHTML,
    rawBody: els['rawBody'].innerHTML,
    caveat: els['caveat'].innerHTML,
    indTitle: els['indTitle'].textContent,
    chgTitle: els['chgTitle'].textContent,
    cmpBody: els['cmpBody'].innerHTML,
    chgBody: els['chgBody'].innerHTML,
    summary: els['summary'].textContent,
  },
};
process.stdout.write(JSON.stringify(report, null, 1));
