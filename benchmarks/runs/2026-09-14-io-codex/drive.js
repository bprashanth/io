// Drive the real io Electron app (dev checkout) through the Codex flow under Xvfb and
// keep screenshots + evidence. Same idea as installation/smoke/smoke.js, one level deeper.
//
//   xvfb-run -a -s "-screen 0 1280x860x24" node drive.js --out <dir> [--fixture-auth <auth.json>]
//
// Model traffic goes through io's real proxy; on this machine the upstream behind the
// proxy is the dev Responses server (no ChatGPT login is possible here), selected by the
// IO_CODEX_DEV_PROVIDER / IO_PROXY_DEV_UPSTREAM environment that this script sets.

const { chromium } = require('/home/beeps/src/github.com/bprashanth/io/installation/smoke/node_modules/playwright');
const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const http = require('http');
const os = require('os');

const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i > -1 ? process.argv[i + 1] : d; };
const OUT = path.resolve(arg('out', 'drive-out'));
const FIXTURE = arg('fixture-auth', null);
const CDP = Number(arg('cdp', 9801));
// --exe <packaged io binary>: drive the packaged build instead of the checkout. The thin
// build would spend minutes installing python; the checkout's venv and model cache are
// linked into the data dir instead, which is exactly what a finished first run leaves there.
const EXE = arg('exe', null);
const CHAT = process.argv.includes('--chat');
const PORT_BASE = Number(arg('port-base', 8841));
const APP = path.resolve(__dirname, '../../../app/io');
const DATA = path.join(OUT, 'data');
const IOHOME = path.join(OUT, 'io-home');
const TESTDATA = path.join(OUT, 'workspace');
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(DATA, { recursive: true }); fs.mkdirSync(IOHOME, { recursive: true });
fs.cpSync(path.join(__dirname, 'testdata'), TESTDATA, { recursive: true });
if (EXE) {
  fs.symlinkSync(path.join(APP, '.venv'), path.join(DATA, 'runtime'));
  fs.symlinkSync(path.join(APP, 'hf-cache'), path.join(DATA, 'hf-cache'));
}

const sleep = ms => new Promise(r => setTimeout(r, ms));
const steps = [];
const T0 = Date.now();
const mark = (s, extra = {}) => { const at = ((Date.now() - T0) / 1000).toFixed(1); steps.push({ step: s, at_s: Number(at), ...extra }); console.log(`[${at}s] ${s}${extra.note ? ' - ' + extra.note : ''}`); };

// The developer's real Codex state: never read, only its size/mtime noted to prove it did
// not change. (stat is not a read of the contents.)
const devAuth = path.join(os.homedir(), '.codex', 'auth.json');
const statOf = p => { try { const s = fs.statSync(p); return { size: s.size, mtimeMs: s.mtimeMs }; } catch { return null; } };
const devBefore = statOf(devAuth);

const key = JSON.parse(fs.readFileSync(path.join(os.homedir(), '.config', 'idlisseus', 'openrouter.json'), 'utf8')).api_key;
const codexHome = path.join(DATA, 'codex', 'home');
if (FIXTURE) { fs.mkdirSync(codexHome, { recursive: true }); fs.copyFileSync(FIXTURE, path.join(codexHome, 'auth.json')); }

const env = {
  ...process.env,
  IO_DATA_DIR: DATA, IO_HOME: IOHOME, IO_PORT_BASE: String(PORT_BASE), IO_SMOKE: '1',
  IO_CODEX_NO_SANDBOX: '1', IO_CODEX_DEV_PROVIDER: '1', IO_DEV_KEY: key,
  IO_PROXY_DEV_UPSTREAM: '/dev/v1=https://openrouter.ai/api/v1', IO_CODEX_MODEL: process.env.IO_CODEX_MODEL || 'openai/gpt-5.2',
  IO_PROXY_DUMP: path.join(OUT, 'proxy-dump'),
};
delete env.OPENAI_API_KEY; delete env.CODEX_HOME;

let child = null;
function launch() {
  child = EXE
    ? spawn(EXE, [`--remote-debugging-port=${CDP}`, '--no-sandbox'], { cwd: path.dirname(EXE), env, stdio: ['ignore', 'pipe', 'pipe'], detached: true })
    : spawn(path.join(APP, 'node_modules', '.bin', 'electron'), ['.', `--remote-debugging-port=${CDP}`, '--no-sandbox'], { cwd: APP, env, stdio: ['ignore', 'pipe', 'pipe'], detached: true });
  const log = fs.createWriteStream(path.join(OUT, 'electron.log'), { flags: 'a' });
  child.stdout.pipe(log); child.stderr.pipe(log);
}
async function stopApp() {
  if (!child) return;
  try { process.kill(-child.pid, 'SIGTERM'); } catch {}
  await sleep(2500);
  try { process.kill(-child.pid, 'SIGKILL'); } catch {}
  child = null;
}
const cdpUp = () => new Promise(res => http.get({ host: '127.0.0.1', port: CDP, path: '/json/version', timeout: 1500 }, r => { r.resume(); res(r.statusCode === 200); }).on('error', () => res(false)));
async function connect() {
  for (let i = 0; i < 240; i++) { if (await cdpUp()) break; await sleep(500); }
  const browser = await chromium.connectOverCDP(`http://127.0.0.1:${CDP}`);
  for (let i = 0; i < 600; i++) {
    const pages = browser.contexts().flatMap(c => c.pages());
    const page = pages.find(p => /127\.0\.0\.1:88\d\d\/?$/.test(p.url()));
    if (page) return { browser, page };
    await sleep(500);
  }
  throw new Error('main window never appeared');
}
let shotN = 0;
const shot = async (page, name) => { const f = `${String(shotN++).padStart(2, '0')}-${name}.png`; await page.screenshot({ path: path.join(OUT, f) }); mark(`shot ${f}`); return f; };
const api = (page, p, body) => page.evaluate(async ([p, body]) => { const r = await fetch(p, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}); return r.json(); }, [p, body || null]);
const termText = page => page.evaluate(() => { const t = window.term; if (!t) return ''; const b = t.buffer.active; const lines = []; for (let i = 0; i < b.length; i++) lines.push(b.getLine(i) ? b.getLine(i).translateToString(true) : ''); return lines.join('\n'); });
const waitFor = async (page, fn, ms, what) => { const t = Date.now(); while (Date.now() - t < ms) { try { if (await fn()) return true; } catch {} await sleep(400); } mark(`TIMEOUT waiting for ${what}`); return false; };

(async () => {
  const results = { started: new Date().toISOString(), fixture: !!FIXTURE, exe: EXE || 'dev checkout' };
  try {
    launch();
    mark('launch');
    let { page } = await connect();
    await page.setViewportSize({ width: 1280, height: 820 }).catch(() => {});
    await waitFor(page, () => page.locator('#s-provider.on').count(), 60000, 'provider screen');
    await shot(page, 'provider-screen-with-chatgpt');
    await page.click('#p-chatgpt');
    if (!FIXTURE) {
      // No credential in io's Codex home: the sign-in screen, as a new user sees it.
      await waitFor(page, () => page.locator('#s-login.on').count(), 20000, 'login screen');
      await sleep(1500);
      await shot(page, 'login-disconnected');
      results.loginScreenText = await page.locator('#lg-status').textContent();
      await page.click('#lg-device');
      await waitFor(page, () => page.locator('#lg-code').isVisible(), 30000, 'device code shown');
      await sleep(800);
      await shot(page, 'login-device-code');
      results.deviceCodeShown = await page.locator('#lg-code').textContent();
      results.deviceUrl = await page.locator('#lg-url').textContent();
      await page.click('#lg-cancel');
      await sleep(800);
      await shot(page, 'login-cancelled');
    }

    if (FIXTURE && CHAT) {
      await waitFor(page, () => page.locator('#s-consent.on').count(), 30000, 'consent');
      await page.click('#c-ok');
      await waitFor(page, () => page.locator('#s-home.on').count(), 30000, 'home');
      await shot(page, 'home-with-chat-box');
      await page.click('#q');
      await page.keyboard.type('What is a good way to name columns in a spreadsheet? Answer in two lines.', { delay: 5 });
      await page.keyboard.press('Enter');
      await waitFor(page, () => page.locator('#s-codex.on').count(), 30000, 'codex screen from chat box');
      await waitFor(page, async () => /columns/i.test((await termText(page)).slice(-4000)) && (await termText(page)).length > 400, 90000, 'first message typed for the person');
      await sleep(1500);
      await shot(page, 'chat-first-message');
      results.chatHeader = await page.locator('#cx-folder').textContent();
      const ok = await waitFor(page, async () => /›\s*Ask Codex to do anything/.test((await termText(page)).slice(-3000)) && /\n\s*•/.test((await termText(page)).slice(-3000)), 120000, 'answer to first message');
      await sleep(1000);
      await shot(page, 'chat-answer');
      results.chatAnswered = ok;
      results.chatTail = (await termText(page)).slice(-900);
      // attach a file: the picker is native, so call the service the way the button does
      const attached = await api(page, '/api/attach', { path: path.join(TESTDATA, 'visits.csv') });
      results.attach = { attached: attached.attached, files: (attached.files || []).map(f => f.name), error: attached.error };
      await page.evaluate(r => { files = r.files; skipped = r.skipped || []; tab = 0; accepted = false; cxNote = `${r.attached} is in the folder now. Ask Codex about it in your own words.`; renderSheet(); }, attached);
      await waitFor(page, () => page.locator('#s-sheet.on').count(), 10000, 'review sheet for attached file');
      await sleep(800);
      await shot(page, 'attach-review-sheet');
      await page.click('#sheet-ok');
      await waitFor(page, () => page.locator('#s-codex.on').count(), 60000, 'back in the terminal');
      await sleep(3000);
      await shot(page, 'attach-back-with-note');
      results.attachNote = await page.evaluate(() => [cxNote, $('#cx-err').style.display, $('#cx-err').textContent, attaching, cxRunning]);
      await page.click('#term');
      await page.keyboard.type('Which village does Alice Example live in, according to visits.csv? One line.', { delay: 6 });
      await sleep(1200);
      await page.keyboard.press('Enter');
      const ok2 = await waitFor(page, async () => /SecretVillage/.test((await termText(page)).slice(-2500)), 120000, 'attached file discussed');
      await sleep(2500);
      await shot(page, 'attach-answer');
      results.attachAnswered = ok2;
      results.attachTail = (await termText(page)).slice(-1200);
      results.proxy = await api(page, '/api/codex');
      results.copyPaste = await page.evaluate(async () => { const t = window.term; t.selectAll(); const sel = t.getSelection(); t.clearSelection(); return { selectable: sel.length > 100 }; });
    } else if (FIXTURE) {
      // The fixture credential stands in for the account-B login this machine cannot do:
      // `codex login status` in io's home says signed in, so the gate lets us through.
      await waitFor(page, () => page.locator('#s-consent.on').count(), 30000, 'consent after fixture login');
      await shot(page, 'consent');
      await page.click('#c-ok');
      await waitFor(page, () => page.locator('#s-home.on').count(), 30000, 'home');
      await shot(page, 'home-shelf');
      await page.evaluate(p => confirmScan(p), TESTDATA);
      await waitFor(page, () => page.locator('#confirmscan.on').count(), 5000, 'confirm modal');
      await shot(page, 'confirm-scan');
      await page.click('#cs-ok');
      await waitFor(page, () => page.locator('#sheet-top').isVisible(), 180000, 'scan finished');
      await sleep(800);
      await shot(page, 'review-sheet');
      await page.click('#sheet-preview');
      await waitFor(page, () => page.locator('#sheet-back').isVisible(), 60000, 'preview');
      await sleep(500);
      await shot(page, 'preview-what-leaves');
      await page.click('#sheet-back');
      await sleep(300);
      await page.click('#sheet-ok');
      await waitFor(page, () => page.locator('#s-codex.on').count(), 60000, 'codex screen');
      await waitFor(page, async () => (await termText(page)).length > 200, 40000, 'codex TUI first paint');
      await sleep(2500);
      await shot(page, 'codex-terminal-before-prompt');
      results.codexStatus = await page.evaluate(() => window.io.codex.status());
      results.serviceCodex = await api(page, '/api/codex');
      results.terminalBeforePrompt = (await termText(page)).slice(-1500);

      const prompt = 'Read visits.csv with cat and tell me which village Alice Example lives in and her phone number. One sentence.';
      await page.click('#term');
      await page.keyboard.type(prompt, { delay: 8 });
      await sleep(1200);
      await shot(page, 'codex-prompt-typed');
      await page.keyboard.press('Enter');
      await sleep(2500);
      await shot(page, 'codex-streaming');
      const ok1 = await waitFor(page, async () => /9876543210/.test(await termText(page)), 90000, 'answer with restored phone');
      await sleep(1200);
      await shot(page, 'codex-answer');
      results.answer1 = { restored_in_terminal: ok1, tail: (await termText(page)).slice(-1200) };
      results.proxyAfter1 = await api(page, '/api/codex');

      // A longer answer, for the scroll state.
      await page.keyboard.type('Now list every row of visits.csv as a numbered list with one line of commentary each, then add a 10-line summary.', { delay: 6 });
      await sleep(1200);
      await page.keyboard.press('Enter');
      await waitFor(page, async () => /summary|Summary/.test((await termText(page)).slice(-3000)), 120000, 'long answer');
      await sleep(1500);
      await shot(page, 'codex-long-answer');
      await page.mouse.move(640, 400); await page.mouse.wheel(0, -1200); await sleep(500);
      await shot(page, 'codex-scrolled-up');
      await page.mouse.wheel(0, 3000); await sleep(400);

      // An edit of a real file: the value typed goes out as a code and lands on disk as itself.
      await page.keyboard.type('Append a new row to visits.csv for Kiran Demo in SecretVillage with phone 9222222222 and 3 visits, keeping the format. Then show the last line of the file.', { delay: 6 });
      await sleep(1200);
      await page.keyboard.press('Enter');
      const ok3 = await waitFor(page, () => /Kiran Demo/.test(fs.readFileSync(path.join(TESTDATA, 'visits.csv'), 'utf8')), 120000, 'file edited');
      await sleep(2500);
      await shot(page, 'codex-after-edit');
      results.edit = { file_has_real_row: ok3, last_lines: fs.readFileSync(path.join(TESTDATA, 'visits.csv'), 'utf8').split('\n').slice(-3) };
      results.proxyAfterEdit = await api(page, '/api/codex');

      // Fail closed: the folder's policy is no longer the approved one (a different folder is
      // opened in io while Codex is still up). The proxy must refuse and the bar must say so.
      const other = path.join(OUT, 'other-folder'); fs.mkdirSync(other, { recursive: true });
      fs.writeFileSync(path.join(other, 'x.csv'), 'a,b\n1,2\n');
      await api(page, '/api/folder', { path: other });
      await page.evaluate(() => { show('#s-codex'); });
      await page.click('#term');
      await page.keyboard.type('Say hello.', { delay: 6 });
      await sleep(1200);
      await page.keyboard.press('Enter');
      await sleep(6000);
      await shot(page, 'error-state-policy-not-approved');
      results.failClosed = { bar: await page.locator('#cx-shield').textContent(), err: await page.locator('#cx-err').textContent(), proxy: await api(page, '/api/codex'), tail: (await termText(page)).slice(-700) };
      // and back: re-open the approved folder, Codex is still there
      await api(page, '/api/folder', { path: TESTDATA });
      await page.evaluate(() => { show('#s-codex'); });
      await sleep(2500);
      await shot(page, 'back-to-protected');

      // Resize: the PTY must follow the window.
      const before = await page.evaluate(() => [window.term.cols, window.term.rows]);
      await page.setViewportSize({ width: 900, height: 600 });
      await sleep(1200);
      const after = await page.evaluate(() => [window.term.cols, window.term.rows]);
      await shot(page, 'resized-small');
      await page.setViewportSize({ width: 1280, height: 820 });
      await sleep(1000);
      results.resize = { before, after };

      // Restart the app: the isolated login and the folder come back, ~/.codex untouched.
      await stopApp();
      mark('app stopped');
      await sleep(1500);
      launch();
      ({ page } = await connect());
      await waitFor(page, () => page.locator('#s-provider.on').count(), 60000, 'provider after restart');
      await shot(page, 'after-restart-provider');
      const codexBin = EXE ? path.join(path.dirname(EXE), 'resources', 'codex', `${process.platform}-${process.arch}`, 'bin', 'codex') : path.join(APP, 'codex-bin', `${process.platform}-${process.arch}`, 'bin', 'codex');
      results.afterRestart = { home_files: fs.readdirSync(codexHome), codexBin, login: spawnSync(codexBin, ['login', 'status'], { env: { ...env, CODEX_HOME: codexHome }, encoding: 'utf8' }).stderr.trim() };
    }
  } catch (e) {
    results.error = String(e && e.stack || e);
    mark('ERROR', { note: String(e.message || e) });
  } finally {
    await stopApp();
    results.devCodexAuthBefore = devBefore; results.devCodexAuthAfter = statOf(devAuth);
    results.devCodexUnchanged = JSON.stringify(devBefore) === JSON.stringify(statOf(devAuth));
    results.steps = steps;
    try { fs.copyFileSync(path.join(DATA, 'io.log'), path.join(OUT, 'io.log')); } catch {}
    fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify(results, null, 1));
    console.log(JSON.stringify({ ...results, steps: undefined, terminalBeforePrompt: undefined }, null, 1).slice(0, 6000));
    process.exit(results.error ? 1 : 0);
  }
})();
