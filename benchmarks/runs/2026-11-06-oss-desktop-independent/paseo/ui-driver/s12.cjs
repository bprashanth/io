module.exports = async (page) => {
  await page.waitForTimeout(7000);
  if (!(await page.getByText('Not a git repository').count())) { await page.getByLabel('Open Explorer sidebar').click(); await page.waitForTimeout(2500); }
  await page.mouse.click(1118, 18); await page.waitForTimeout(3000);
  await page.screenshot({ path: __dirname + '/shots/a-12-explorer.png' });
  const row = page.getByText('result.csv', { exact: true }).last();
  const box = await row.boundingBox(); console.log('ROWBOX', JSON.stringify(box));
  await row.hover(); await page.waitForTimeout(800);
  await row.click({ button: 'right' }); await page.waitForTimeout(1500);
  console.log('CTX', (await page.innerText('body')).slice(-200).replace(/\n/g, ' | '));
  await page.screenshot({ path: __dirname + '/shots/a-12-context.png' });
  const dl = page.getByText(/^Download/).last();
  if (await dl.count()) {
    const [d] = await Promise.all([page.waitForEvent('download', { timeout: 15000 }), dl.click()]);
    const out = __dirname + '/downloads-a/' + d.suggestedFilename(); await d.saveAs(out); console.log('DOWNLOADED', out);
  }
};
