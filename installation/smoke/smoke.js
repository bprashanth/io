// Cold-start smoke for a packaged io build. Same script on all three platforms.
//
//   node smoke.js --exe <path to the io binary> --out <dir> [--cdp 9800] [--port-base 8811]
//
// It drives the real artifact the way a person would: launch it with an empty data dir,
// wait out the first-run install, land on the provider screen, set a provider, add a
// folder, see the shelf. Screenshots and a results.json come out in --out.
//
// Scope is startup only. No API key, no model request: the provider is pointed at a dead
// local address that is never called, because nothing in this path asks a question.
//
// On this repo's Linux box the primary agent owns ports 8801/8802/8890 and its own CDP
// ports, so the defaults here are deliberately 8811 and 9800.

const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');

const arg = (name, dflt) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : dflt;
};

const EXE = arg('exe');
const OUT = path.resolve(arg('out', 'smoke-out'));
const CDP = Number(arg('cdp', 9800));
const PORT_BASE = Number(arg('port-base', 8811));
const LABEL = arg('label', `${process.platform}-${process.arch}`);
const BUDGET_MIN = Number(arg('budget-min', 25));   // thin cold start downloads ~1.9 GB

if (!EXE) { console.error('need --exe'); process.exit(2); }

const sleep = ms => new Promise(r => setTimeout(r, ms));
const steps = [];
const T0 = Date.now();
const mark = (name, extra = {}) => {
  const at = (Date.now() - T0) / 1000;
  steps.push({ step: name, at_s: Number(at.toFixed(1)), ...extra });
  console.log(`[${at.toFixed(1)}s] ${name}${extra.note ? ' - ' + extra.note : ''}`);
};

function fixture(dir) {
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'beneficiaries.csv'),
    'name,village,phone,amount\n' +
    'Ramesh Kumar,Sitapur,9876543210,1200\n' +
    'Anita Devi,Sitapur,9876500011,900\n' +
    'Suresh Patel,Barabanki,9812345678,1500\n');
  fs.writeFileSync(path.join(dir, 'notes.txt'),
    'Spoke to Ramesh Kumar on 9876543210 about the October payment.\n');
  return dir;
}

const cdpUp = () => new Promise(res => {
  http.get({ host: '127.0.0.1', port: CDP, path: '/json/version', timeout: 2000 }, r => {
    r.resume(); res(r.statusCode === 200);
  }).on('error', () => res(false)).on('timeout', function () { this.destroy(); res(false); });
});

async function appPage(browser) {
  // the splash is a file:// page; the app itself is served over http from the local service
  for (const ctx of browser.contexts()) {
    for (const p of ctx.pages()) {
      if (/^http:\/\/127\.0\.0\.1:\d+\//.test(p.url())) return p;
    }
  }
  return null;
}

async function splashPage(browser) {
  for (const ctx of browser.contexts()) {
    for (const p of ctx.pages()) if (/splash\.html$/.test(p.url())) return p;
  }
  return null;
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'io-smoke-'));
  // A fresh data dir forces a genuine first run. --data points at an already-populated one,
  // which is the same code path a fat build takes: everything present, nothing to install.
  const dataDir = arg('data') ? path.resolve(arg('data')) : path.join(tmp, 'data');
  const confDir = path.join(tmp, 'conf');       // keeps ~/.config/io untouched
  const folder = fixture(path.join(tmp, 'sample'));
  const shot = n => path.join(OUT, `${n}.png`);

  // Snapshot before launch so "did this run install anything" is a before/after fact,
  // not a guess from which windows happened to be open when we looked.
  const runtimeBefore = fs.existsSync(path.join(dataDir, 'runtime'));

  mark('launch', { note: `${path.basename(EXE)} cdp=${CDP} data=${dataDir}` });
  const child = spawn(EXE, [`--remote-debugging-port=${CDP}`, '--no-sandbox'], {
    env: { ...process.env, IO_PORT_BASE: String(PORT_BASE), IO_DATA_DIR: dataDir, IO_HOME: confDir },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const appLog = fs.createWriteStream(path.join(OUT, 'app.log'), { flags: 'a' });
  child.stdout.pipe(appLog); child.stderr.pipe(appLog);
  let exited = null;
  child.on('exit', c => { exited = c; });

  const deadline = Date.now() + BUDGET_MIN * 60_000;
  while (!(await cdpUp())) {
    if (exited !== null) throw new Error(`io exited with code ${exited} before opening (see app.log)`);
    if (Date.now() > deadline) throw new Error(`no CDP on ${CDP} after ${BUDGET_MIN} min`);
    await sleep(1000);
  }
  mark('window_open');

  const browser = await chromium.connectOverCDP(`http://127.0.0.1:${CDP}`);

  // If this is a thin cold start the splash is up and the install is running. Catch it,
  // because "the splash stays honest about progress" is a thing we claim. The splash also
  // covers service startup, so seeing one proves nothing about whether an install ran -
  // that question is answered from the filesystem further down.
  const sp = await splashPage(browser);
  if (sp) {
    try { await sp.screenshot({ path: shot('01-splash') }); mark('splash_seen'); } catch {}
  }

  let page = null;
  while (!page) {
    if (Date.now() > deadline) throw new Error('the app window never loaded the service');
    page = await appPage(browser);
    if (!page) await sleep(1000);
  }
  await page.waitForSelector('#s-provider.on', { timeout: 120_000 });
  await page.waitForSelector('#p-key', { state: 'visible' });
  const servicePort = Number(page.url().match(/:(\d+)\//)[1]);
  mark('provider_screen', { note: `service on ${servicePort}` });
  await page.screenshot({ path: shot('02-provider') });

  // the key form accepts input
  await page.fill('#p-key', 'not-a-real-key');
  if ((await page.inputValue('#p-key')) !== 'not-a-real-key') throw new Error('key field did not accept input');
  await page.fill('#p-key', '');

  // a dead address, never contacted: this smoke asks nothing
  await page.fill('#p-server', 'http://127.0.0.1:9/v1');
  await page.click('#p-go');
  await page.waitForSelector('#s-home.on', { timeout: 60_000 });
  mark('home_screen');
  await page.screenshot({ path: shot('03-home') });

  // The "+ Add Sheltered Dir" button opens a native OS dialog, which CDP cannot drive.
  // Post the folder through the same endpoint the dialog feeds, then let the UI redraw.
  const added = await page.evaluate(async p => {
    const r = await fetch('/api/folder', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: p }),
    });
    return r.status;
  }, folder);
  if (added !== 200) throw new Error(`/api/folder returned ${added}`);
  await page.reload();
  await page.waitForSelector('#s-home.on', { timeout: 60_000 });
  await page.waitForSelector('#shelf .fol[data-p]', { timeout: 60_000 });
  const shelf = await page.$$eval('#shelf .fol[data-p]', els => els.map(e => e.textContent.trim()));
  mark('shelf_rendered', { note: shelf.join(' | ') });
  await page.screenshot({ path: shot('04-shelf') });

  // Only a thin build writes a runtime into the data dir; a fat build reads its own from
  // inside the bundle and leaves the data dir alone. An install happened this run if the
  // runtime was not there before and is there now.
  const installed = !runtimeBefore && fs.existsSync(path.join(dataDir, 'runtime'));

  const result = {
    label: LABEL,
    platform: `${process.platform}-${process.arch}`,
    exe: EXE,
    cold_start_s: steps.find(s => s.step === 'provider_screen').at_s,
    total_s: Number(((Date.now() - T0) / 1000).toFixed(1)),
    first_run_install: installed,
    splash_seen: !!sp,
    data_dir: dataDir,
    service_port: servicePort,
    shelf,
    steps,
    ok: true,
  };
  fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify(result, null, 2));
  console.log('\nPASS  cold start to provider screen: ' + result.cold_start_s + 's');

  await browser.close();
  child.kill();
  await sleep(500);
  try { process.kill(child.pid, 'SIGKILL'); } catch {}
}

main().catch(async e => {
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, 'results.json'),
    JSON.stringify({ label: LABEL, ok: false, error: String(e.message || e), steps }, null, 2));
  console.error('\nFAIL  ' + (e.message || e));
  process.exit(1);
});
