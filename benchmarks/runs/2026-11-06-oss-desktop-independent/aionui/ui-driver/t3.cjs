const path = require('path');
module.exports = async (page) => {
  await page.waitForTimeout(5000);
  if (process.env.NEWCHAT) { await page.getByText('New Chat', { exact: true }).click(); await page.waitForTimeout(2000); }
  await page.getByText(process.env.AGENT, { exact: true }).first().click(); await page.waitForTimeout(1500);
  const ta = page.locator('textarea').first();
  await ta.fill(process.env.PROMPT);
  if (process.env.CSV) {
    const [fc] = await Promise.all([page.waitForEvent('filechooser', { timeout: 8000 }).catch(() => null), page.locator('button').filter({ has: page.locator('svg') }).first().click().catch(() => null)]);
    console.log('filechooser', !!fc);
  }
  await page.waitForTimeout(500);
  await ta.press('Enter');
  const t0 = Date.now();
  for (let i = 0; i < Number(process.env.POLLS || 40); i++) { await page.waitForTimeout(3000);
    if (i % 5 === 0) console.log('t', 3 * i, (await page.innerText('body')).slice(-160).replace(/\n/g, ' | ')); }
  console.log('ELAPSED_MS', Date.now() - t0);
};
