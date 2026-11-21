module.exports = async (page) => {
  await page.waitForTimeout(4000);
  await page.getByText('Created', { exact: false }).first().click({ timeout: 10000 }).catch(e => console.log('noclick')); await page.waitForTimeout(4000);
  await page.mouse.click(1383, 166); await page.waitForTimeout(1200);
  console.log('MENU', (await page.innerText('body')).slice(-250).replace(/\n/g, ' | '));
  await page.screenshot({ path: __dirname + '/shots/aion-a-22-filemenu.png' });
  const dl = page.getByText(/^Download/).last();
  if (await dl.count()) { const [d] = await Promise.all([page.waitForEvent('download', { timeout: 15000 }), dl.click()]); const out = __dirname + '/downloads-aion-a/' + d.suggestedFilename(); await d.saveAs(out); console.log('DOWNLOADED', out); }
};
