// Where everything lives, for all three platforms and both build flavours.
//
// There is exactly one io binary per platform. "Thin" and "fat" are the same app; the
// only difference is whether the packer put a python runtime and a model cache inside
// resources/. So resolution is always: use what shipped with the app, else use what the
// first run installed under the user's data dir.
//
//   packaged fat    resources/runtime  + resources/hf-cache      (offline, nothing to do)
//   packaged thin   <data>/runtime     + <data>/hf-cache         (bootstrap.js fills these)
//   git checkout    .venv              + hf-cache                (install.sh, unchanged)
//
// <data> is %LOCALAPPDATA%\io, ~/Library/Application Support/io, or ~/.local/share/io.
// Nothing here ever writes inside the app bundle: an AppImage is read-only squashfs and a
// signed .app must not be modified after the fact.

const path = require('path');
const fs = require('fs');
const os = require('os');

const WIN = process.platform === 'win32';
const MAC = process.platform === 'darwin';

function dataDir() {
  if (process.env.IO_DATA_DIR) return path.resolve(process.env.IO_DATA_DIR);
  if (WIN) return path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local'), 'io');
  if (MAC) return path.join(os.homedir(), 'Library', 'Application Support', 'io');
  return path.join(process.env.XDG_DATA_HOME || path.join(os.homedir(), '.local', 'share'), 'io');
}

// A python-build-standalone tree, or the checkout's venv. Both are probed so the dev flow
// keeps working untouched.
function pythonIn(dir) {
  if (!dir) return null;
  const tries = WIN
    ? [path.join(dir, 'python.exe'), path.join(dir, 'Scripts', 'python.exe')]
    : [path.join(dir, 'bin', 'python3'), path.join(dir, 'bin', 'python')];
  return tries.find(p => fs.existsSync(p)) || null;
}

function resolve(opts = {}) {
  const packaged = !!opts.packaged;
  const res = opts.resourcesPath || process.resourcesPath;
  const data = dataDir();

  const appDir = packaged ? path.join(res, 'io') : __dirname;

  // runtime: bundled first, then the checkout venv, then the per-user install target
  const bundledRuntime = packaged ? path.join(res, 'runtime') : null;
  const devRuntime = packaged ? null : path.join(__dirname, '.venv');
  const userRuntime = path.join(data, 'runtime');
  const runtimeDir = [bundledRuntime, devRuntime, userRuntime].find(d => pythonIn(d)) || userRuntime;

  // model cache: same idea. A bundled cache only counts if the scanner is actually in it.
  const bundledCache = packaged ? path.join(res, 'hf-cache') : null;
  const devCache = packaged ? null : path.join(__dirname, 'hf-cache');
  const userCache = path.join(data, 'hf-cache');
  const hfCache = [bundledCache, devCache, userCache].find(hasScanner) || userCache;

  return {
    appDir,
    dataDir: data,
    runtimeDir,
    hfCache,
    python: pythonIn(runtimeDir),
    service: path.join(appDir, 'service.py'),
    bundled: runtimeDir === bundledRuntime,
    ready: !!pythonIn(runtimeDir) && hasScanner(hfCache),
  };
}

// The scanner is cached when its hub folder holds at least one real snapshot. An empty
// models--… shell is what a half-finished download leaves behind, and treating that as
// "ready" is how you get an app that starts and then hangs on first scan.
function hasScanner(cacheDir) {
  if (!cacheDir) return false;
  const hub = path.join(cacheDir, 'hub');
  if (!fs.existsSync(hub)) return false;
  for (const d of fs.readdirSync(hub)) {
    if (!d.startsWith('models--knowledgator--')) continue;
    const snaps = path.join(hub, d, 'snapshots');
    if (!fs.existsSync(snaps)) continue;
    for (const s of fs.readdirSync(snaps)) {
      const files = fs.readdirSync(path.join(snaps, s));
      if (files.some(f => f.endsWith('.safetensors') || f.endsWith('.bin') || f.endsWith('.onnx'))) return true;
    }
  }
  return false;
}

module.exports = { resolve, dataDir, pythonIn, hasScanner };
