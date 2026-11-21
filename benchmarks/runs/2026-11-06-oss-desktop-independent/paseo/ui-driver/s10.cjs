const path = require('path');
module.exports = async (page) => {
  const file = path.resolve(process.env.CSV);
  await page.waitForTimeout(6000);
  if (await page.getByText('New workspace', { exact: true }).count() > 1) { await page.getByText('New workspace', { exact: true }).nth(1).click(); await page.waitForTimeout(3000); }
  await page.getByLabel(/Select model/).or(page.getByText('Select model')).first().click(); await page.waitForTimeout(1500);
  await page.getByText(process.env.PROVIDER_LABEL).click(); await page.waitForTimeout(1500);
  await page.getByText('Muse Glimmer 30B (Idli)').last().click(); await page.waitForTimeout(1500);
  await page.getByLabel(/Select agent mode/).click(); await page.waitForTimeout(1500);
  console.log('MODES', (await page.innerText('body')).slice(-300).replace(/\n/g, ' | '));
  const want = process.env.MODE; if (want) { await page.getByText(want, { exact: true }).last().click(); await page.waitForTimeout(1000); } else await page.keyboard.press('Escape');
  await page.getByLabel('Message agent...').fill(process.env.PROMPT); await page.waitForTimeout(500);
  await page.getByLabel('Add attachment').click(); await page.waitForTimeout(800);
  const [fc] = await Promise.all([page.waitForEvent('filechooser', { timeout: 10000 }), page.getByText('Upload file', { exact: true }).click()]);
  await fc.setFiles(file); await page.waitForTimeout(2000);
  await page.screenshot({ path: __dirname + '/shots/' + process.env.TAG + '-attached.png' });
  const t0 = Date.now();
  await page.getByLabel('Create', { exact: true }).last().click();
  // wait for agent to finish: poll text for result
  for (let i = 0; i < 90; i++) {
    await page.waitForTimeout(2000);
    if (i === 3) await page.screenshot({ path: __dirname + '/shots/' + process.env.TAG + '-streaming.png' });
    const labels = await page.locator('[aria-label]').evaluateAll(els => els.map(e => e.getAttribute('aria-label')));
    const busy = labels.some(l => /stop|interrupt|cancel/i.test(l));
    if (i % 5 === 0) console.log('t', i * 2, busy, labels.filter(l => /stop|interrupt|cancel|running|working/i.test(l)).join(','));
    if (i > 5 && !busy) break;
  }
  console.log('ELAPSED_MS', Date.now() - t0);
};
