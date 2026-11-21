module.exports = async (page) => {
  await page.waitForTimeout(7000);
  await page.getByLabel('Message agent...').fill(process.env.PROMPT);
  await page.keyboard.press('Enter');
  await page.waitForTimeout(Number(process.env.WAIT || 12000));
  await page.screenshot({ path: __dirname + '/shots/' + process.env.TAG + '-running.png' });
  if (process.env.STOP) {
    const t0 = Date.now();
    await page.getByLabel('Stop agent').first().click();
    for (let i = 0; i < 30; i++) { await page.waitForTimeout(500);
      const labels = await page.locator('[aria-label]').evaluateAll(els => els.map(e => e.getAttribute('aria-label')));
      if (!labels.some(l => /stop agent/i.test(l))) { console.log('STOPPED_AFTER_MS', Date.now() - t0); break; } }
    await page.waitForTimeout(2000);
  } else {
    for (let i = 0; i < Number(process.env.POLLS || 60); i++) { await page.waitForTimeout(2000);
      const labels = await page.locator('[aria-label]').evaluateAll(els => els.map(e => e.getAttribute('aria-label')));
      if (!labels.some(l => /stop agent/i.test(l))) { console.log('IDLE_AFTER_S', 2 * i); break; } }
  }
  console.log('TAIL', (await page.innerText('body')).slice(-700));
};
