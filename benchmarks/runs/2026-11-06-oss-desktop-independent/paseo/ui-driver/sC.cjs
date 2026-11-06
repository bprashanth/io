module.exports = async (page) => {
  await page.waitForTimeout(7000);
  console.log('URL', page.url());
  await page.getByLabel(/Select agent mode/).click(); await page.waitForTimeout(1200);
  console.log('MODES', (await page.innerText('body')).slice(-200).replace(/\n/g, ' | '));
  await page.getByText('Always ask', { exact: true }).last().click(); await page.waitForTimeout(1000);
  await page.getByLabel('Message agent...').fill('Now run compute_visits.py with python3 and show its output.');
  await page.keyboard.press('Enter');
  for (let i = 0; i < 60; i++) {
    await page.waitForTimeout(2000);
    const txt = await page.innerText('body');
    const btns = await page.locator('button, [role=button]').evaluateAll(els => els.map(e => (e.innerText || e.getAttribute('aria-label') || '').trim()).filter(Boolean));
    const allow = btns.filter(b => /^(allow|approve|accept|yes|run)/i.test(b));
    if (allow.length) {
      console.log('PROMPT buttons', btns.filter(b => /allow|approve|deny|reject|accept|always|yes|no/i.test(b)).join(' ; '));
      await page.screenshot({ path: __dirname + '/shots/b-11-permission.png' });
      await page.getByRole('button', { name: new RegExp('^' + allow[0].split('\n')[0]) }).first().click();
      console.log('CLICKED', allow[0]);
      await page.waitForTimeout(2000);
    }
    const labels = await page.locator('[aria-label]').evaluateAll(els => els.map(e => e.getAttribute('aria-label')));
    if (i > 4 && !labels.some(l => /stop agent/i.test(l))) break;
  }
};
