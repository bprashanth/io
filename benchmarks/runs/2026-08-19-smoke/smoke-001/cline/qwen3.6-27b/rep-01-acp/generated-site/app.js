<script>
const RAW_CSV = 'district,year,children_due,children_fully_immunised,source\nGaya,2023,1100,935,synthetic smoke fixture\nNalanda,2023,850,765,synthetic smoke fixture\nPurnia,2023,1000,760,synthetic smoke fixture';

function parseCSV(text) {
  var lines = text.trim().split('\n');
  var headers = lines[0].split(',');
  return lines.slice(1).map(function(l) {
    var vals = l.split(',');
    var obj = {};
    headers.forEach(function(h, i) { obj[h.trim()] = vals[i].trim(); });
    return obj;
  });
}

var DATA      = parseCSV(RAW_CSV);
var SOURCES   = Array.from(new Set(DATA.map(function(d){return d.source;})));

var yearSelect = document.getElementById('yearSelect');
var tableBody  = document.getElementById('tableBody');
var sourceLine = document.getElementById('sourceLine');
var canvas     = document.getElementById('barChart');
var ctx        = canvas.getContext('2d');

function render() {
  var filtered = DATA;
  tableBody.innerHTML = '';
  filtered.forEach(function(d) {
    var pct = ((+d.children_fully_immunised / +d.children_due) * 100).toFixed(1);
    var cls = +pct >= 80 ? 'pct-good' : 'pct-bad';
    var rowClass = d.district === 'Purnia' ? 'style="background:#fef2f2;font-weight:bold"' : '';
    tableBody.innerHTML += '<tr ' + rowClass + '><td>' + d.district + (d.district === 'Purnia' ? ' <span style="color:#dc2626;font-size:.8rem">(lowest)</span>' : '') + '</td><td>' + Number(d.children_due).toLocaleString() + '</td><td>' + Number(d.children_fully_immunised).toLocaleString() + '</td><td class="' + cls + '">' + pct + '%</td></tr>';
  });
  sourceLine.textContent = 'Source: ' + SOURCES.join('; ');
  drawChart(filtered);
}

</script>
