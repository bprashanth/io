module.exports = async (page) => {
  await page.waitForTimeout(4000);
  await page.getByText('New Chat', { exact: true }).click(); await page.waitForTimeout(1500);
  await page.getByText('Codex CLI', { exact: true }).first().click(); await page.waitForTimeout(1000);
  await page.locator('span,div,button').filter({ hasText: /^(Read Only|Auto|Full Access)$/ }).last().click(); await page.waitForTimeout(800);
  await page.getByText('Full Access', { exact: true }).last().click(); await page.waitForTimeout(800);
  const ta = page.locator('textarea').first(); await ta.fill(process.env.PROMPT); await ta.press('Enter');
  for (let i = 0; i < 30; i++) { await page.waitForTimeout(2000); if (/slow\.py/.test((await page.innerText('body')).slice(-1500)) && i > 8) break; }
  await page.screenshot({ path: __dirname + '/shots/aion-a-30-running.png' });
  const labels = await page.locator('[aria-label],[title]').evaluateAll(els => els.map(e => e.getAttribute('aria-label') || e.getAttribute('title')));
  console.log('LABELS', labels.filter(l => /stop|cancel|interrupt/i.test(l || '')).join(';'));
  const t0 = Date.now();
  const stop = page.locator('[aria-label*="top"],[title*="top"]').first();
  if (await stop.count()) await stop.click(); else await page.mouse.click(1043, 851);
  await page.waitForTimeout(4000);
  console.log('AFTER_STOP_MS', Date.now() - t0, (await page.innerText('body')).slice(-300).replace(/\n/g, ' | '));
};
