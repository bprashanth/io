const $ = s => document.querySelector(s);
function paint(s) {
  $('#status').textContent = s.configured ? `Saved key ending in ${s.suffix}.${s.remaining === null ? ' OpenRouter did not report a remaining credit limit.' : ` Remaining key allowance: $${s.remaining.toFixed(2)}.`}` : 'No OpenRouter key is saved.';
  $('#storage').textContent = s.persistent ? 'Saved on this computer for your next visit. It is never given to the assistant.' : 'Portable mode: kept only until io closes, so the key does not travel on the USB stick.';
  $('#remove').disabled = !s.configured;
}
$('#save').onclick = async () => {
  const value = $('#key').value; $('#key').value = ''; $('#save').disabled = true;
  $('#status').textContent = 'Checking with OpenRouter…';
  try { const r = await window.keySettings.save(value); if (r.error) $('#status').textContent = r.error; else paint(r); }
  finally { $('#save').disabled = false; }
};
$('#remove').onclick = async () => paint(await window.keySettings.remove());
window.keySettings.status().then(paint);
