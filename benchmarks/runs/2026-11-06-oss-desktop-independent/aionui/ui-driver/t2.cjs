const fs = require('fs');
module.exports = async (page) => {
  await page.waitForTimeout(5000);
  for (let k = 0; k < 6; k++) { const skip = page.getByText('Skip', { exact: true }); if (await skip.count()) { await skip.first().click(); await page.waitForTimeout(1500); } else break; }
  if (await page.locator('input[type=password]').count()) {
    await page.locator('input[placeholder="Enter your username"]').fill('admin');
    await page.locator('input[type=password]').fill(fs.readFileSync(process.env.PWFILE, 'utf8').trim());
    await page.getByText('Sign In', { exact: true }).click();
    await page.waitForTimeout(8000);
  }
  for (let k = 0; k < 6; k++) { const skip = page.getByText('Skip', { exact: true }); if (await skip.count()) { await skip.first().click(); await page.waitForTimeout(1500); } else break; }
};
