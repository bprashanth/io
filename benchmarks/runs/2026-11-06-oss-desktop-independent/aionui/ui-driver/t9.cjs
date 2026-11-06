const path = require('path');
module.exports = async (page) => {
  await page.waitForTimeout(4000);
  await page.getByText('New Chat', { exact: true }).click(); await page.waitForTimeout(1500);
  await page.getByText(process.env.AGENT, { exact: true }).first().click(); await page.waitForTimeout(1000);
  if (process.env.PERM) {
    await page.locator('span,div,button').filter({ hasText: /^(Read Only|Default|Auto|Full Access|Plan|Accept Edits|Bypass.*)$/ }).last().click(); await page.waitForTimeout(1000);
    await page.getByText(process.env.PERM, { exact: true }).last().click(); await page.waitForTimeout(800);
  }
  const ta = page.locator('textarea').first(); await ta.fill(process.env.PROMPT);
  await page.mouse.click(476, 441); await page.waitForTimeout(800);
  const [fc] = await Promise.all([page.waitForEvent('filechooser', { timeout: 8000 }), page.getByText('Upload from device', { exact: true }).click()]);
  await fc.setFiles(path.resolve(process.env.CSV)); await page.waitForTimeout(2500);
  await page.screenshot({ path: __dirname + '/shots/' + process.env.TAG + '-attached.png' });
  await ta.press('Enter'); const t0 = Date.now();
  let last = '';
  for (let i = 0; i < Number(process.env.POLLS || 60); i++) { await page.waitForTimeout(3000);
    const btns = await page.locator('button').evaluateAll(els => els.map(e => (e.innerText || '').trim()).filter(Boolean));
    const allow = btns.find(b => /^(Allow|Allow once|Approve|Yes|Accept)/i.test(b));
    if (allow) { console.log('PERMISSION', btns.filter(b => /allow|deny|reject|approve|always|once|yes|no\b/i.test(b)).join(' ; ')); await page.screenshot({ path: __dirname + '/shots/' + process.env.TAG + '-permission.png' }); await page.getByRole('button', { name: allow }).first().click(); await page.waitForTimeout(1500); }
    const t = await page.innerText('body'); if (i === 4) await page.screenshot({ path: __dirname + '/shots/' + process.env.TAG + '-streaming.png' });
    const busy = /Processing\.\.\.|Thinking|Running/.test(t.slice(-600));
    if (i > 3 && !busy && t === last) { console.log('IDLE_AFTER_S', 3 * i); break; } last = t; }
  console.log('ELAPSED_MS', Date.now() - t0);
  console.log('TAIL', (await page.innerText('body')).slice(-900));
};
