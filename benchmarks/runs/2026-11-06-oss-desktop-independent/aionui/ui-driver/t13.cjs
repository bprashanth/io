module.exports = async (page) => {
  await page.waitForTimeout(4000);
  await page.getByText('Created', { exact: false }).first().click(); await page.waitForTimeout(3000);
  await page.mouse.dblclick(1253, 166); await page.waitForTimeout(3000);
  await page.screenshot({ path: __dirname + '/shots/aion-a-23-preview.png' });
  const labels = await page.locator('[aria-label],[title]').evaluateAll(els => els.map(e => e.getAttribute('aria-label') || e.getAttribute('title')));
  console.log('LABELS', labels.filter(Boolean).join(' ; '));
  const dl = page.locator('[aria-label*="ownload"],[title*="ownload"]').first();
  if (await dl.count()) { const [d] = await Promise.all([page.waitForEvent('download', { timeout: 15000 }), dl.click()]); const out = __dirname + '/downloads-aion-a/' + d.suggestedFilename(); await d.saveAs(out); console.log('DOWNLOADED', out); }
};
