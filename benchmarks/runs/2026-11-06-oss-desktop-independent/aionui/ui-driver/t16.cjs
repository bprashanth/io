module.exports = async (page) => {
  await page.waitForTimeout(4000);
  await page.getByText('New Chat', { exact: true }).click(); await page.waitForTimeout(1500);
  await page.getByText(process.env.AGENT, { exact: true }).first().click(); await page.waitForTimeout(1000);
  const ta = page.locator('textarea').first(); await ta.fill('Reply with the single word PONG.'); await ta.press('Enter');
  const t0 = Date.now(); let last = '';
  for (let i = 0; i < 80; i++) { await page.waitForTimeout(3000); const t = (await page.innerText('body')).slice(-500);
    if (i % 10 === 0) console.log('t', 3 * i, t.slice(-200).replace(/\n/g, ' | '));
    if (i > 5 && !/Processing|Thinking/.test(t) && t === last) { console.log('SETTLED_S', 3 * i); break; } last = t; }
  console.log('ELAPSED_MS', Date.now() - t0); console.log('TAIL', (await page.innerText('body')).slice(-500));
};
