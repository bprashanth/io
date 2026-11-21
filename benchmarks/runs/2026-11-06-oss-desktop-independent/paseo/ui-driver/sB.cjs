const fs = require('fs');
module.exports = async (page) => {
  await page.waitForTimeout(3000);
  await page.getByText('Direct connection').click(); await page.waitForTimeout(1000);
  const inp = page.locator('input');
  await inp.nth(0).fill(process.env.HOSTIP); await inp.nth(2).fill(fs.readFileSync(process.env.PWFILE, 'utf8').trim());
  await page.getByText('Connect', { exact: true }).click(); await page.waitForTimeout(8000);
  const skip = page.getByText('Skip setup', { exact: true }); if (await skip.count()) { await skip.click(); await page.waitForTimeout(1500); }
  await page.getByText('Add project', { exact: true }).first().click(); await page.waitForTimeout(1500);
  await page.getByText('Search for directory', { exact: true }).click(); await page.waitForTimeout(1500);
  await page.locator('input').last().fill('/workspace'); await page.waitForTimeout(2500);
  await page.getByText('Open this path').click(); await page.waitForTimeout(6000);
};
