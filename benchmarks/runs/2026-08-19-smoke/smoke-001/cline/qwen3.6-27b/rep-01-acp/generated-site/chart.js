<script>
function drawChart(rows) {
  var dpr = window.devicePixelRatio || 1;
  var rect = canvas.parentElement.getBoundingClientRect();
  canvas.width  = rect.width * dpr;
  canvas.height = 380 * dpr;
  ctx.scale(dpr, dpr);
  var W = rect.width, H = 380;
  ctx.clearRect(0, 0, W, H);

  var pad = { top: 20, right: 30, bottom: 60, left: 60 };
  var cW = W - pad.left - pad.right;
  var cH = H - pad.top - pad.bottom;

  var maxVal = Math.max.apply(null, rows.map(function(r){ return +r.children_due; }));
  var n = rows.length;
  var groupW = cW / n;
  var barW   = groupW * 0.3;
  var gap    = 4;

  // Y-axis gridlines and labels
  ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 1;
  ctx.fillStyle   = '#64748b'; ctx.font = '12px system-ui'; ctx.textAlign = 'right';
  for (var i = 0; i <= 5; i++) {
    var val = (maxVal / 5) * i;
    var y   = pad.top + cH - (val / maxVal) * cH;
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();
    ctx.fillText(Math.round(val).toLocaleString(), pad.left - 8, y + 4);
  }

  // Bars
  rows.forEach(function(r, idx) {
    var gx = pad.left + idx * groupW;
    var h1 = (+r.children_due / maxVal) * cH;
    roundRect(ctx, gx + (groupW - barW * 2 - gap) / 2, pad.top + cH - h1, barW, h1, '#3b82f6', 4);
    var h2 = (+r.children_fully_immunised / maxVal) * cH;
    roundRect(ctx, gx + (groupW - barW * 2 - gap) / 2 + barW + gap, pad.top + cH - h2, barW, h2, '#16a34a', 4);

    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 13px system-ui'; ctx.textAlign = 'center';
    ctx.fillText(r.district, gx + groupW / 2, H - pad.bottom + 20);

    ctx.font = '11px system-ui'; ctx.fillStyle = '#334155';
    ctx.fillText(r.children_due, gx + (groupW - barW * 2 - gap) / 2 + barW / 2, pad.top + cH - h1 - 6);
    ctx.fillText(r.children_fully_immunised, gx + (groupW - barW * 2 - gap) / 2 + barW + gap + barW / 2, pad.top + cH - h2 - 6);
  });
}

function roundRect(ctx, x, y, w, h, color, r) {
  if (h <= 0) return;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h);
  ctx.lineTo(x, y + h);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
  ctx.fill();
}

yearSelect.addEventListener('change', function(){ render(); });
window.addEventListener('resize', function(){ render(); });

// Download CSV button
document.getElementById('downloadBtn').addEventListener('click', function() {
  var header = 'district,children_due,children_fully_immunised,coverage_pct\n';
  var rows = DATA.map(function(d) {
    var pct = (+d.children_fully_immunised / +d.children_due * 100).toFixed(1);
    return d.district + ',' + d.children_due + ',' + d.children_fully_immunised + ',' + pct;
  }).join('\n');
  var blob = new Blob([header + rows], { type: 'text/csv' });
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url;
  a.download = 'immunisation_2023.csv';
  a.click();
  URL.revokeObjectURL(url);
});

render();
</script>
