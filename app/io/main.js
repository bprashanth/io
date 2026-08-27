// io — minimal desktop shell.
const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');
const net = require('net');

const runtime = require('./runtime');
const bootstrap = require('./bootstrap');

const PORT_BASE = Number(process.env.IO_PORT_BASE || 8801);
let proc = null;
let env = null;
let splash = null;

const freePort = s => new Promise(res => { const srv = net.createServer(); srv.once('error', () => res(freePort(s + 1))); srv.listen(s, '127.0.0.1', () => srv.close(() => res(s))); });
const waitFor = (url, n = 600) => new Promise((res, rej) => { const t = k => http.get(url, r => { r.resume(); res(); }).on('error', () => k ? setTimeout(() => t(k - 1), 250) : rej(new Error('service did not start'))); t(n); });

// The privacy-shield extension carries the same tested venv, so a developer with the
// plugin installed can borrow it instead of building a second copy of torch. A shipped
// build never borrows: it owns its runtime, or it installs one. Half-borrowed is how you
// get an app that starts against an empty model cache and then hangs on the first scan.
function borrowedPython() {
  if (app.isPackaged) return null;
  const dir = path.join(process.env.HOME || '', '.antigravity', 'extensions');
  if (!fs.existsSync(dir)) return null;
  for (const d of fs.readdirSync(dir)) {
    if (!d.startsWith('insight-out.privacy-shield')) continue;
    const p = path.join(dir, d, 'server', '.venv', 'bin', 'python');
    if (fs.existsSync(p)) return p;
  }
  return null;
}

// First run only. A packaged fat build never gets here: its runtime and model cache
// shipped inside resources/, so env.ready is already true.
async function ensureRuntime() {
  if (env.ready) return;
  if (!env.python && borrowedPython()) return;   // dev checkout with the plugin installed

  await openSplash();

  const logPath = path.join(env.dataDir, 'install.log');
  fs.mkdirSync(env.dataDir, { recursive: true });
  const log = fs.createWriteStream(logPath, { flags: 'a' });
  log.write(`\n--- ${new Date().toISOString()} ${process.platform}-${process.arch} ---\n`);

  const NOTE = {
    python: 'a self-contained python, no installer and no admin',
    packages: 'about 1.2 GB on disk. Windows Defender scans every file, so an older laptop can sit here for several minutes.',
    model: 'about 500 MB over the network',
  };

  // A first run on an old laptop is genuinely slow, and a screen that has not changed in
  // four minutes reads as crashed. The clock makes slow look slow instead of frozen.
  const began = Date.now();
  const elapsed = () => {
    const s = Math.round((Date.now() - began) / 1000);
    return s < 90 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`;
  };
  let latest = { phase: 'python', detail: 'starting' };
  const tick = setInterval(() => {
    if (!splash || splash.isDestroyed()) return;
    splash.webContents.executeJavaScript(
      `window.ioProgress(${JSON.stringify({ note: `${NOTE[latest.phase] || ''} - ${elapsed()} so far` })})`
    ).catch(() => {});
  }, 1000);
  // The splash gets every event; the log gets one line per real change. A download fires a
  // progress callback per chunk, and a log with ten thousand identical lines in it is not a
  // log anyone can read when an install goes wrong on someone's laptop.
  let lastLine = '';
  const show = p => {
    const pct = p.frac != null ? ` ${Math.round(p.frac * 20) * 5}%` : '';
    const line = `[${p.phase}] ${p.detail}${pct}`;
    if (line !== lastLine) { lastLine = line; log.write(line + '\n'); }
    latest = p;
    if (!splash || splash.isDestroyed()) return;
    splash.webContents.executeJavaScript(
      `window.ioProgress(${JSON.stringify({ detail: p.detail, frac: p.frac, note: `${NOTE[p.phase] || ''} - ${elapsed()} so far` })})`
    ).catch(() => {});
  };

  try {
    await bootstrap.install({ dest: env.dataDir, onProgress: show });
  } catch (e) {
    log.write(`FAILED: ${e && e.stack || e}\n`);
    clearInterval(tick);
    closeSplash();
    dialog.showErrorBox('io could not finish setting up',
      `${e.message || e}\n\nThe full log is at:\n${logPath}\n\nIf this was a network drop, starting io again picks up where it left off.`);
    app.exit(1);
    return;
  }
  clearInterval(tick);
  log.write(`done in ${elapsed()}\n`);
  env = runtime.resolve({ packaged: app.isPackaged });   // re-resolve: the paths exist now
}

async function openSplash() {
  if (splash && !splash.isDestroyed()) return splash;
  splash = new BrowserWindow({
    width: 440, height: 210, frame: false, resizable: false, show: false,
    backgroundColor: '#1a1d21', webPreferences: { contextIsolation: true },
  });
  await splash.loadFile(path.join(__dirname, 'splash.html'));
  splash.show();
  return splash;
}

const tellSplash = (detail, note) => {
  if (!splash || splash.isDestroyed()) return;
  splash.webContents.executeJavaScript(
    `window.ioProgress(${JSON.stringify({ detail, note: note || '', frac: null })})`
  ).catch(() => {});
};

const closeSplash = () => { if (splash && !splash.isDestroyed()) splash.destroy(); splash = null; };

async function start() {
  env = runtime.resolve({ packaged: app.isPackaged });
  await ensureRuntime();

  const python = env.python || borrowedPython();
  if (!python) {
    dialog.showErrorBox('io', 'No python runtime was found and the setup did not produce one.');
    return app.exit(1);
  }

  // Only point the service at a cache that actually holds the scanner. Handing it an empty
  // one turns the offline fast path off and sends it to the network at startup.
  const senv = { ...process.env };
  if (runtime.hasScanner(env.hfCache)) senv.HF_HOME = env.hfCache;

  const port = await freePort(PORT_BASE);
  proc = spawn(python, [env.service, String(port)], { stdio: ['ignore', 'pipe', 'pipe'], env: senv });
  const log = fs.createWriteStream(path.join(app.getPath('userData'), 'io.log'), { flags: 'a' });
  proc.stdout.pipe(log); proc.stderr.pipe(log);

  // Loading torch and the scanner off a cold disk takes a while the first time - minutes on
  // an older Windows laptop, because Defender reads every file in site-packages as it goes.
  // Keep the splash up and say so, rather than showing an empty window that looks hung.
  await openSplash();
  tellSplash('starting the on-device scanner', 'the first start after setup is the slow one');

  const win = new BrowserWindow({
    width: 1200, height: 820, title: 'io', backgroundColor: '#1a1d21', show: false,
    icon: path.join(__dirname, 'icons', 'icon.png'),
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true },
  });
  win.setMenuBarVisibility(false);
  try {
    await waitFor(`http://127.0.0.1:${port}/api/state`);
    await win.loadURL(`http://127.0.0.1:${port}/`);
    closeSplash();
    win.show();
  } catch (e) {
    closeSplash();
    dialog.showErrorBox('io', `${e.message}\n\nThe service log is at:\n${path.join(app.getPath('userData'), 'io.log')}`);
    app.quit();
  }
}

ipcMain.handle('pick-folder', async () => { const r = await dialog.showOpenDialog({ properties: ['openDirectory'] }); return r.canceled ? null : r.filePaths[0]; });
app.whenReady().then(start);
app.on('window-all-closed', () => { if (proc) proc.kill(); app.quit(); });
