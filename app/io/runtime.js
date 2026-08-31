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

// Portable mode: a folder named io-data sitting next to the app makes io keep everything
// it writes inside that folder - the python env, the model cache, decisions, and the vault.
// That is what turns a USB stick into a self-contained io: plug it into someone's laptop,
// shelter folders that live on their disk, and leave nothing of your own behind when you
// pull the stick out. Create the folder to switch it on; delete it to go back to normal.
//
// "Next to the app" differs per platform: beside io.exe on Windows, beside the AppImage or
// the extracted folder on Linux, and beside io.app on macOS (not buried inside the bundle,
// which is read-only once signed).
function portableDir() {
  if (process.env.IO_PORTABLE) return path.resolve(process.env.IO_PORTABLE);
  const beside = [];
  // APPIMAGE is set by the AppImage runtime and points at the .AppImage file itself;
  // process.execPath would point into the temporary mount, which vanishes on exit.
  if (process.env.APPIMAGE) beside.push(path.dirname(process.env.APPIMAGE));
  const exeDir = path.dirname(process.execPath);
  beside.push(exeDir);
  if (MAC) {
    // io.app/Contents/MacOS/io -> look beside the bundle, where a user would put the folder,
    // and also inside Contents/, which is the only place a dmg can ship it pre-made.
    beside.push(path.resolve(exeDir, '..', '..', '..'));
    beside.push(path.resolve(exeDir, '..'));
  }
  for (const dir of beside) {
    const candidate = path.join(dir, 'io-data');
    try {
      if (!fs.statSync(candidate).isDirectory()) continue;
      // Existing is not enough, it has to be writable. A dmg mounts read-only, and an .app
      // dragged into /Applications is owned by root on a managed Mac - in both cases the
      // folder is right there and every write into it fails. Falling back to the user's
      // profile is far better than starting and then dying on the first log line.
      fs.accessSync(candidate, fs.constants.W_OK);
      return candidate;
    } catch { /* not there, or not ours to write to */ }
  }
  return null;
}

function dataDir() {
  if (process.env.IO_DATA_DIR) return path.resolve(process.env.IO_DATA_DIR);
  const portable = portableDir();
  if (portable) return portable;
  if (WIN) return path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local'), 'io');
  if (MAC) return path.join(os.homedir(), 'Library', 'Application Support', 'io');
  return path.join(process.env.XDG_DATA_HOME || path.join(os.homedir(), '.local', 'share'), 'io');
}

// A python-build-standalone tree, or the checkout's venv. Both are probed so the dev flow
// keeps working untouched.
function pythonIn(dir) {
  if (!dir) return null;
  if (WIN) {
    return [path.join(dir, 'python.exe'), path.join(dir, 'Scripts', 'python.exe')]
      .find(p => fs.existsSync(p)) || null;
  }
  const bin = path.join(dir, 'bin');
  const named = [path.join(bin, 'python3'), path.join(bin, 'python')].find(p => fs.existsSync(p));
  if (named) return named;
  // bin/python3 and bin/python are both symlinks to bin/python3.12, and a filesystem that
  // cannot store symlinks drops them - exFAT, which is what a USB stick shared between
  // Windows, macOS and Linux has to be. The real interpreter is still there under its
  // versioned name, so fall back to it rather than declaring there is no python.
  try {
    const versioned = fs.readdirSync(bin)
      .filter(f => /^python3\.\d+$/.test(f))
      .sort()
      .map(f => path.join(bin, f))
      .find(p => { try { return fs.statSync(p).isFile(); } catch { return false; } });
    if (versioned) return versioned;
  } catch { /* no bin dir at all */ }
  return null;
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
    // Why the scanner is missing, if a previous run already found out it cannot be
    // installed here. Without this the app would retry the whole download every start.
    scannerError: scannerError(data),
    ready: !!pythonIn(runtimeDir) && (hasScanner(hfCache) || !!scannerError(data)),
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

function scannerError(dataDir) {
  try { return fs.readFileSync(path.join(dataDir, 'scanner-unavailable.txt'), 'utf8').trim() || null; }
  catch { return null; }
}

module.exports = { resolve, dataDir, portableDir, pythonIn, hasScanner, scannerError };
