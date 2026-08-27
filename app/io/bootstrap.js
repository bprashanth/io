// First run: put a python runtime and the scanner model on disk. No shell scripts, no
// PowerShell execution policy, no bash on Windows, no admin anywhere.
//
// The old install.ps1 assumed Python and Node were already on PATH, which is why it never
// worked for a real participant. This does the whole thing itself: fetch a
// python-build-standalone tarball (a plain extract - no registry, no PATH, no installer),
// pip the pinned packages into it, then warm the model into the cache.
//
// It is also the build-time tool for the fat artifacts:
//     node bootstrap.js --dest out/payload
// produces out/payload/{runtime,hf-cache}, which the packer drops into resources/.
// Thin and fat therefore install the exact same bytes; fat just does it before shipping.

const fs = require('fs');
const path = require('path');
const os = require('os');
const https = require('https');
const { spawn } = require('child_process');

const PINS = JSON.parse(fs.readFileSync(path.join(__dirname, 'pins.json'), 'utf8'));
const WIN = process.platform === 'win32';
const MAC = process.platform === 'darwin';

const noop = () => {};

function pythonTarball() {
  const key = `${process.platform}-${process.arch}`;
  const name = PINS.python.targets[key];
  if (!name) throw new Error(`no pinned python build for ${key}`);
  return { name, url: `${PINS.python.base}/${PINS.python.release}/${name}` };
}

// GitHub release assets redirect to a CDN, so follow redirects. Retry, because an event
// venue's wifi drops connections and a half-written tarball is worse than a clear failure.
function download(url, dest, onProgress = noop, tries = 3) {
  return new Promise((resolve, reject) => {
    const attempt = left => {
      const tmp = `${dest}.part`;
      const fail = err => {
        fs.rmSync(tmp, { force: true });
        if (left > 1) return setTimeout(() => attempt(left - 1), 2000);
        reject(err);
      };
      const get = (u, hops = 0) => {
        if (hops > 5) return fail(new Error('too many redirects'));
        https.get(u, { headers: { 'User-Agent': 'io-installer' } }, res => {
          if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
            res.resume();
            return get(new URL(res.headers.location, u).toString(), hops + 1);
          }
          if (res.statusCode !== 200) {
            res.resume();
            return fail(new Error(`HTTP ${res.statusCode} for ${u}`));
          }
          const total = Number(res.headers['content-length'] || 0);
          let seen = 0;
          const out = fs.createWriteStream(tmp);
          res.on('data', c => {
            seen += c.length;
            if (total) onProgress(seen / total);
          });
          res.pipe(out);
          out.on('finish', () => out.close(() => {
            fs.renameSync(tmp, dest);
            resolve(dest);
          }));
          out.on('error', fail);
        }).on('error', fail);
      };
      get(url);
    };
    attempt(tries);
  });
}

// Every platform we ship to has tar: bsdtar in System32 since Windows 10 1803, and the
// real thing on macOS and Linux. Checked up front so the failure is a sentence, not a
// stack trace four minutes in.
function haveTar() {
  return new Promise(resolve => {
    const p = spawn('tar', ['--version'], { stdio: 'ignore' });
    p.on('error', () => resolve(false));
    p.on('exit', code => resolve(code === 0));
  });
}

function run(cmd, args, opts = {}, onLine = noop) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { ...opts, stdio: ['ignore', 'pipe', 'pipe'] });
    let tail = '';
    const feed = buf => {
      tail = (tail + buf.toString()).slice(-4000);
      buf.toString().split(/\r?\n/).filter(Boolean).forEach(onLine);
    };
    p.stdout.on('data', feed);
    p.stderr.on('data', feed);
    p.on('error', reject);
    p.on('exit', code => code === 0 ? resolve() : reject(new Error(`${cmd} exited ${code}\n${tail}`)));
  });
}

function pythonIn(dir) {
  const tries = WIN
    ? [path.join(dir, 'python.exe'), path.join(dir, 'Scripts', 'python.exe')]
    : [path.join(dir, 'bin', 'python3'), path.join(dir, 'bin', 'python')];
  return tries.find(p => fs.existsSync(p)) || null;
}

/**
 * @param dest      directory that will hold runtime/ and hf-cache/
 * @param onProgress ({phase, detail, frac}) - frac is 0..1 within the phase, or null
 */
async function install({ dest, onProgress = noop }) {
  const say = (phase, detail, frac = null) => onProgress({ phase, detail, frac });
  const runtimeDir = path.join(dest, 'runtime');
  const hfCache = path.join(dest, 'hf-cache');
  fs.mkdirSync(dest, { recursive: true });

  if (!await haveTar()) {
    throw new Error('tar was not found. On Windows 10 or 11 it lives in C:\\Windows\\System32; on macOS and Linux it is standard.');
  }

  // 1. python runtime
  if (!pythonIn(runtimeDir)) {
    const { name, url } = pythonTarball();
    const tgz = path.join(dest, name);
    say('python', `downloading python ${PINS.python.version}`, 0);
    await download(url, tgz, f => say('python', `downloading python ${PINS.python.version}`, f));
    say('python', 'unpacking python');
    fs.rmSync(runtimeDir, { recursive: true, force: true });
    fs.mkdirSync(runtimeDir, { recursive: true });
    // the tarball's single top-level dir is "python/"; strip it so runtime/ is the root
    await run('tar', ['-xzf', tgz, '--strip-components=1', '-C', runtimeDir]);
    fs.rmSync(tgz, { force: true });
    if (!pythonIn(runtimeDir)) throw new Error('python did not unpack as expected');
  }
  const py = pythonIn(runtimeDir);

  // 2. packages. torch comes from the CPU-only index on Windows and Linux so we do not
  //    drag in a couple of GB of CUDA. macOS wheels on PyPI are already CPU/MPS.
  const pip = (args, label) => run(py, ['-m', 'pip', 'install', '--no-input', '--disable-pip-version-check', ...args],
    { env: { ...process.env, PIP_DISABLE_PIP_VERSION_CHECK: '1' } },
    line => { if (/^(Collecting|Downloading|Installing|Successfully)/.test(line)) say('packages', label + ' - ' + line.slice(0, 70)); });

  const torch = PINS.packages.find(p => p.startsWith('torch=='));
  const rest = PINS.packages.filter(p => p !== torch);

  say('packages', 'preparing pip');
  await pip(['--upgrade', 'pip'], 'pip');
  say('packages', 'installing torch (CPU only, this is the big one)');
  await pip(MAC ? [torch] : ['--index-url', PINS.torchIndex, torch], 'torch');
  say('packages', 'installing the rest');
  await pip(rest, 'packages');

  // 3. the scanner. Warmed through the same code path the app uses, into the same cache,
  //    so a fat build's cache is byte-identical to what a thin first run would produce.
  //
  //    The os._exit is not a shortcut. huggingface_hub's hf_xet transfer layer leaves a
  //    Rust tokio runtime running - a dozen non-daemon hf-xet threads plus a tracing
  //    appender - and those block interpreter shutdown after the download is finished.
  //    Seen live: "scanner cached" printed, then the process sat at 9% CPU for minutes
  //    with 62 threads and 11 open sockets. To a participant that is a splash that never
  //    goes away. The cache is fully written by the time from_pretrained returns, so
  //    leaving without finalising the interpreter costs nothing.
  say('model', 'downloading the on-device scanner (about 500 MB)');
  fs.mkdirSync(hfCache, { recursive: true });
  await run(py, ['-c', [
    'import os, sys',
    'from gliner import GLiNER',
    `GLiNER.from_pretrained(${JSON.stringify(PINS.model)}, map_location="cpu")`,
    'print("scanner cached")',
    'sys.stdout.flush(); sys.stderr.flush()',
    'os._exit(0)',
  ].join('\n')], { env: { ...process.env, HF_HOME: hfCache } },
    line => say('model', line.slice(0, 70)));

  say('done', 'ready');
  return { runtimeDir, hfCache, python: py };
}

module.exports = { install, pythonIn, PINS };

if (require.main === module) {
  const i = process.argv.indexOf('--dest');
  const dest = i > -1 ? path.resolve(process.argv[i + 1]) : path.join(os.tmpdir(), 'io-payload');
  install({ dest, onProgress: p => console.log(`[${p.phase}] ${p.detail}${p.frac != null ? ` ${Math.round(p.frac * 100)}%` : ''}`) })
    .then(r => { console.log('payload ready:', r.runtimeDir, r.hfCache); })
    .catch(e => { console.error(String(e.message || e)); process.exit(1); });
}
