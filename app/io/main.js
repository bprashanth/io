// io — minimal desktop shell.
const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');
const net = require('net');

const HERE = __dirname;
let proc = null;

function pythonExe() {
  // own env first (created by install.sh); else the installed privacy-shield extension's venv
  const own = path.join(HERE, '.venv', process.platform === 'win32' ? 'Scripts\\python.exe' : 'bin/python');
  if (fs.existsSync(own)) return own;
  const shield = path.join(process.env.HOME || '', '.antigravity', 'extensions');
  if (fs.existsSync(shield)) {
    for (const d of fs.readdirSync(shield)) {
      if (d.startsWith('insight-out.privacy-shield')) {
        const p = path.join(shield, d, 'server', '.venv', 'bin', 'python');
        if (fs.existsSync(p)) return p;
      }
    }
  }
  return process.platform === 'win32' ? 'python' : 'python3';
}

const freePort = s => new Promise(res => { const srv = net.createServer(); srv.once('error', () => res(freePort(s + 1))); srv.listen(s, '127.0.0.1', () => srv.close(() => res(s))); });
const waitFor = (url, n = 240) => new Promise((res, rej) => { const t = k => http.get(url, r => { r.resume(); res(); }).on('error', () => k ? setTimeout(() => t(k - 1), 250) : rej(new Error('service did not start'))); t(n); });

function firstRunSetup() {
  const own = path.join(HERE, '.venv', process.platform === 'win32' ? 'Scripts\\python.exe' : 'bin/python');
  if (fs.existsSync(own)) return null;
  const shield = path.join(process.env.HOME || '', '.antigravity', 'extensions');
  if (fs.existsSync(shield) && fs.readdirSync(shield).some(d => d.startsWith('insight-out.privacy-shield'))) return null;
  // first run: build the environment with a small splash
  const splash = new BrowserWindow({ width: 420, height: 180, frame: false, backgroundColor: '#1a1d21' });
  splash.loadURL('data:text/html,' + encodeURIComponent('<body style="background:#1a1d21;color:#8b9096;font:15px system-ui;display:flex;align-items:center;justify-content:center;height:100%"><div style="text-align:center"><div style="color:#e8e6e1;font-size:22px;margin-bottom:8px">io</div>setting up — first time only<br>(a few minutes)</div></body>'));
  return new Promise(res => {
    const cmd = process.platform === 'win32'
      ? spawn('powershell', ['-ExecutionPolicy', 'Bypass', '-File', path.join(HERE, 'install.ps1')], { cwd: HERE })
      : spawn('bash', [path.join(HERE, 'install.sh')], { cwd: HERE });
    const log = fs.createWriteStream(path.join(HERE, 'install.log'), { flags: 'a' });
    cmd.stdout.pipe(log); cmd.stderr.pipe(log);
    cmd.on('exit', () => { splash.close(); res(null); });
  });
}

async function start() {
  const setup = firstRunSetup();
  if (setup) await setup;
  const port = await freePort(8801);
  proc = spawn(pythonExe(), [path.join(HERE, 'service.py'), String(port)], { stdio: ['ignore', 'pipe', 'pipe'] });
  const log = fs.createWriteStream(path.join(app.getPath('userData'), 'io.log'), { flags: 'a' });
  proc.stdout.pipe(log); proc.stderr.pipe(log);
  const win = new BrowserWindow({ width: 1200, height: 820, title: 'io', backgroundColor: '#1a1d21',
    webPreferences: { preload: path.join(HERE, 'preload.js'), contextIsolation: true } });
  win.setMenuBarVisibility(false);
  try { await waitFor(`http://127.0.0.1:${port}/api/state`); await win.loadURL(`http://127.0.0.1:${port}/`); }
  catch (e) { dialog.showErrorBox('io', e.message); app.quit(); }
}

ipcMain.handle('pick-folder', async () => { const r = await dialog.showOpenDialog({ properties: ['openDirectory'] }); return r.canceled ? null : r.filePaths[0]; });
app.whenReady().then(start);
app.on('window-all-closed', () => { if (proc) proc.kill(); app.quit(); });
