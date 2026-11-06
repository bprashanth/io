module.exports = async (page) => {
  await page.waitForTimeout(5000);
  console.log('URL', page.url(), 'LOGIN_PAGE', await page.locator('input[type=password]').count());
  await page.getByText('Created', { exact: false }).first().click(); await page.waitForTimeout(4000);
  const ta = page.locator('textarea').first(); await ta.fill('Without running any command, tell me the name of the CSV file you wrote earlier in this chat and its three totals.'); await ta.press('Enter');
  let last = '';
  for (let i = 0; i < 60; i++) { await page.waitForTimeout(3000); const t = (await page.innerText('body')).slice(-700);
    if (i > 3 && !/Processing|Thinking/.test(t) && t === last) break; last = t; }
  console.log('TAIL', (await page.innerText('body')).slice(-500));
};
