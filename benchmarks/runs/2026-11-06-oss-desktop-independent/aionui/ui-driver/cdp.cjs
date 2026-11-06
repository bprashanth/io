// node cdp.cjs <cdpUrl> <steps.cjs> <shot>
const { chromium } = require('playwright');
const [,, url, steps, shot] = process.argv;
(async () => {
  const browser = await chromium.connectOverCDP(url);
  const page = browser.contexts()[0].pages().find(p => p.url().includes('index.html')) || browser.contexts()[0].pages()[0];
  try { await require(require('path').resolve(steps))(page); } catch (e) { console.log('STEP ERROR', e.message.split('\n')[0]); }
  await page.screenshot({ path: __dirname + '/shots/' + shot + '.png' });
  console.log('--- visible text ---\n' + (await page.innerText('body')).slice(0, 2500));
  await browser.close().catch(() => {});
  process.exit(0);
})();
