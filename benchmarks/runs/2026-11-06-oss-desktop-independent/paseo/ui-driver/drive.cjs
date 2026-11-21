// node drive.cjs <profile> <url> <steps.cjs> [shotName]
const { chromium } = require('playwright');
const [,, profile, url, steps, shot] = process.argv;
(async () => {
  const ctx = await chromium.launchPersistentContext(__dirname + '/profiles/' + profile,
    { headless: true, viewport: { width: 1400, height: 900 }, acceptDownloads: true });
  const page = ctx.pages()[0] || await ctx.newPage();
  const ext = new Map(); ctx.on('request', r => { try { const h = new URL(r.url()).host; if (!/^172\.|^localhost|^127\./.test(h) && !r.url().startsWith('data:') && !r.url().startsWith('blob:')) ext.set(h, (ext.get(h) || 0) + 1); } catch {} });
  page.on('console', m => { if (m.type() === 'error') console.log('[console]', m.text().slice(0, 200)); });
  if (page.url() !== url) await page.goto(url, { waitUntil: 'domcontentloaded' });
  try { await require(require('path').resolve(steps))(page, ctx); }
  catch (e) { console.log('STEP ERROR', e.message.split('\n')[0]); }
  await page.screenshot({ path: __dirname + '/shots/' + (shot || 'last') + '.png' });
  console.log('--- visible text ---\n' + (await page.innerText('body')).slice(0, 2500));
  console.log('EXTERNAL_REQUESTS', JSON.stringify(Object.fromEntries(ext)));
  await ctx.close();
})();
