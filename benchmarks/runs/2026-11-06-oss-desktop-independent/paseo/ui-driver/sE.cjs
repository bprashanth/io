module.exports = async (page) => {
  for (let i = 0; i < 100; i++) { await page.waitForTimeout(3000);
    const labels = await page.locator('[aria-label]').evaluateAll(els => els.map(e => e.getAttribute('aria-label')));
    if (i > 2 && !labels.some(l => /stop agent/i.test(l))) { console.log('IDLE_AFTER_EXTRA_S', 3 * i); break; } }
  console.log('TAIL', (await page.innerText('body')).slice(-600));
};
