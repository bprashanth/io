// Separate V1 launcher. Cloudflare login is isolated from the terminal renderer.
const {app, BrowserWindow, ipcMain, dialog, shell, session} = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');
const https = require('https');
const remote = require('../remote/client');
const os = require('os');
const {spawn} = require('child_process');
let diagnosticPromise;
let diagnosticReport = {status:'INCONCLUSIVE', executionMode:'remote', rationale:['Diagnostic has not completed.']};
function runDiagnostic(runtime) {
  if (diagnosticPromise) return diagnosticPromise;
  const out=path.join(app.getPath('userData'),'local-diagnostic',String(Date.now()));
  diagnosticPromise=new Promise(resolve=>{
    const child=spawn(process.execPath,[path.join(__dirname,'../diagnostic/diagnose.js'),'--runtime',runtime,'--out',out],{env:{...process.env,ELECTRON_RUN_AS_NODE:'1'},stdio:'ignore'});
    const finish=()=>{try {diagnosticReport=JSON.parse(fs.readFileSync(path.join(out,'capability.json'),'utf8'));} catch {diagnosticReport={status:'INCONCLUSIVE',executionMode:'remote',rationale:['Diagnostic could not produce a report.']};} resolve(diagnosticReport);};
    child.once('error',finish); child.once('close',finish);
  }).finally(()=>{diagnosticPromise=null;});
  return diagnosticPromise;
}

let booting = true;

function endpoint(value) {
  const url = new URL(value);
  if (url.username || url.password || url.search || url.hash || url.pathname !== '/' ||
      (url.protocol !== 'https:' && !(url.protocol === 'http:' && url.hostname === '127.0.0.1')))
    throw Error('Gateway must be an HTTPS origin (or literal loopback for tests).');
  return url;
}

function request(base, token, method, route) {
  return new Promise((resolve, reject) => {
    const url = new URL(route, base);
    const req = (url.protocol === 'https:' ? https : http).request(url, {
      method, headers: {Cookie: 'CF_Authorization=' + token, 'Cf-Access-Jwt-Assertion': token,
        'Content-Length': '0'},
    }, res => {
      let data = '';
      res.on('data', chunk => {data += chunk; if (data.length > 65536) req.destroy(Error('Gateway response too large'));});
      res.on('end', () => {
        if (res.statusCode !== 200) return reject(Error(`Gateway HTTP ${res.statusCode}. Sign in to Cloudflare Access again or check gateway configuration.`));
        try {resolve(JSON.parse(data));} catch {reject(Error('Gateway returned an invalid response'));}
      });
    });
    req.setTimeout(90000, () => req.destroy(Error('Gateway timed out')));
    req.on('error', reject); req.end();
  });
}

async function accessLogin(base) {
  // Test identities must be signed and are accepted only against a literal local origin.
  if (process.env.IO_GATEWAY_TEST_TOKEN_FILE) {
    if (base.protocol !== 'http:' || base.hostname !== '127.0.0.1') throw Error('Test identity is local-only');
    return fs.readFileSync(process.env.IO_GATEWAY_TEST_TOKEN_FILE, 'utf8').trim();
  }
  if (base.protocol !== 'https:') throw Error('Cloudflare login requires HTTPS');
  const partition = session.fromPartition('persist:io-cloudflare-access');
  partition.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  return new Promise((resolve, reject) => {
    const login = new BrowserWindow({width:900, height:760, title:'Sign in to IO',
      webPreferences:{partition:'persist:io-cloudflare-access', sandbox:true, nodeIntegration:false, contextIsolation:true}});
    let completed = false, checking = false;
    login.setMenuBarVisibility(false);
    login.webContents.setWindowOpenHandler(() => ({action:'deny'}));
    login.webContents.on('will-navigate', (event, target) => {
      try {if (new URL(target).protocol !== 'https:') event.preventDefault();} catch {event.preventDefault();}
    });
    login.webContents.on('did-finish-load', async () => {
      const loaded = new URL(login.webContents.getURL());
      if (loaded.origin !== base.origin || loaded.pathname !== '/desktop-ready' || checking) return;
      checking = true;
      try {
        const cookies = await partition.cookies.get({url:base.href, name:'CF_Authorization'});
        const token = cookies[0]?.value;
        if (!token) return;
        await request(base, token, 'GET', '/identity');
        completed = true; resolve(token); login.close();
      } catch {
        dialog.showErrorBox('IO Access', 'Cloudflare sign-in reached IO, but the gateway rejected the identity. Check the gateway issuer and application audience.');
      } finally {checking = false;}
    });
    login.on('closed', () => {if (!completed) reject(Error('IO sign-in was closed'));});
    login.loadURL(new URL('/desktop-ready', base).href).catch(() => {reject(Error('Could not open IO sign-in')); login.close();});
  });
}

async function main() {
  ipcMain.handle('v1-access-logout', async () => {
    await session.fromPartition('persist:io-cloudflare-access').clearStorageData();
    app.quit();
    return {ok:true};
  });
  ipcMain.handle('v1-diagnostic',async (_event, run)=>{
    if (run) {
      const selected=await dialog.showOpenDialog({title:'Select prepared standalone Python runtime',properties:['openDirectory']});
      if(!selected.canceled) return runDiagnostic(selected.filePaths[0]);
    }
    return diagnosticPromise || diagnosticReport;
  });
  runDiagnostic(process.env.IO_DIAGNOSTIC_RUNTIME || path.join(os.homedir(),'.io-conformance-runtime',process.platform+'-'+process.arch,'runtime'));
  const base = endpoint(process.env.IO_GATEWAY_URL || 'https://io.idli.cc');
  const token = await accessLogin(base);
  await request(base, token, 'GET', '/identity');
  const result = await request(base, token, 'POST', '/workspace');
  if (!/^workspace_[a-f0-9]{32}$/.test(result.workspaceId)) throw Error('Invalid workspace handle');
  await remote.install({app, BrowserWindow, ipcMain, dialog, shell}, {
    url:new URL('/workspaces/' + result.workspaceId, base).href, token, auth:'cloudflare',
  });
  booting=false;
}
app.whenReady().then(main).catch(error => {if(error.message !== 'IO sign-in was closed') dialog.showErrorBox('IO V1 experiment', error.message); app.quit();});
app.on('window-all-closed', () => {if (!booting) app.quit();});
