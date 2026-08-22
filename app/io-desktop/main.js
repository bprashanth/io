// io desktop shim: spawn the local Python service, open a window on it.
const { app, BrowserWindow, dialog, ipcMain, shell } = require('electron');
const { spawn, spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');
const net = require('net');

const HERE = __dirname;
const SERVER = path.join(HERE, 'server', 'io_service.py');
let proc = null;
let port = 8791;

function pythonExe() {
  const venv = process.platform === 'win32' ? path.join(HERE, '.venv', 'Scripts', 'python.exe') : path.join(HERE, '.venv', 'bin', 'python');
  if (fs.existsSync(venv)) return venv;
  for (const cand of process.platform === 'win32' ? ['python', 'py'] : ['python3', 'python']) {
    const r = spawnSync(cand, ['-c', 'import duckdb, pandas, sqlglot'], { stdio: 'ignore' });
    if (r.status === 0) return cand;
  }
  return null;
}

function freePort(start) {
  return new Promise(resolve => {
    const s = net.createServer();
    s.once('error', () => resolve(freePort(start + 1)));
    s.listen(start, '127.0.0.1', () => s.close(() => resolve(start)));
  });
}

function waitFor(url, tries = 60) {
  return new Promise((resolve, reject) => {
    const tick = n => http.get(url, res => { res.resume(); resolve(); }).on('error', () => n ? setTimeout(() => tick(n - 1), 250) : reject(new Error('service did not start')));
    tick(tries);
  });
}

async function createWindow() {
  const py = pythonExe();
  if (!py) {
    dialog.showErrorBox('io needs Python', 'Run install.sh (or install.ps1) once in the app folder to create the Python environment.');
    app.quit();
    return;
  }
  port = await freePort(8791);
  proc = spawn(py, [SERVER, String(port)], { cwd: HERE, stdio: ['ignore', 'pipe', 'pipe'] });
  const logFile = fs.createWriteStream(path.join(app.getPath('userData'), 'service.log'), { flags: 'a' });
  proc.stdout.pipe(logFile); proc.stderr.pipe(logFile);
  const win = new BrowserWindow({
    width: 1380, height: 900, title: 'io',
    webPreferences: { preload: path.join(HERE, 'preload.js'), contextIsolation: true, nodeIntegration: false },
  });
  win.webContents.setWindowOpenHandler(({ url }) => { if (url.startsWith(`http://127.0.0.1:${port}/`)) return { action: 'allow' }; shell.openExternal(url); return { action: 'deny' }; });
  try {
    await waitFor(`http://127.0.0.1:${port}/api/state`);
    await win.loadURL(`http://127.0.0.1:${port}/`);
  } catch (e) {
    dialog.showErrorBox('io service failed to start', `${e.message}\nSee ${path.join(app.getPath('userData'), 'service.log')}`);
    app.quit();
  }
}

ipcMain.handle('pick-folder', async () => {
  const r = await dialog.showOpenDialog({ properties: ['openDirectory'] });
  return r.canceled ? null : r.filePaths[0];
});

app.whenReady().then(createWindow);
app.on('window-all-closed', () => { if (proc) proc.kill(); app.quit(); });
app.on('before-quit', () => { if (proc) proc.kill(); });
