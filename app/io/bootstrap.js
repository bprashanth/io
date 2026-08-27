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
function download(url, dest, onProgress = noop, tries = 4) {
  // Every socket here gets a deadline. A stalled TLS connection that never errors and
  // never delivers a byte is not a hypothetical: it is what wedged the Windows runner for
  // the full 40 minute budget on an 11 MB file, and it is the same shape as the HF hub
  // hang that service.py already carries a comment about. No timeout means no failure,
  // no retry, and a splash that sits on "downloading" forever.
  const CONNECT_MS = 30_000;   // to first response
  const IDLE_MS = 60_000;      // between chunks once the body is flowing
  return new Promise((resolve, reject) => {
    const attempt = left => {
      const tmp = `${dest}.part`;
      let settled = false;
      const fail = err => {
        if (settled) return;
        settled = true;
        fs.rmSync(tmp, { force: true });
        if (left > 1) {
          const wait = (tries - left + 1) * 3000;   // back off a little each time
          onProgress(null, `${err.message}; retrying in ${wait / 1000}s`);
          return setTimeout(() => attempt(left - 1), wait);
        }
        reject(new Error(`${err.message} (after ${tries} attempts) while fetching ${url}`));
      };
      const done = v => { if (!settled) { settled = true; resolve(v); } };

      const get = (u, hops = 0) => {
        if (hops > 5) return fail(new Error('too many redirects'));
        const req = https.get(u, { headers: { 'User-Agent': 'io-installer' }, timeout: CONNECT_MS }, res => {
          if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
            res.resume();
            req.setTimeout(0);
            return get(new URL(res.headers.location, u).toString(), hops + 1);
          }
          if (res.statusCode !== 200) {
            res.resume();
            return fail(new Error(`HTTP ${res.statusCode}`));
          }
          const total = Number(res.headers['content-length'] || 0);
          let seen = 0;
          let idle = setTimeout(() => req.destroy(new Error('connection stalled')), IDLE_MS);
          const out = fs.createWriteStream(tmp);
          res.on('data', c => {
            clearTimeout(idle);
            idle = setTimeout(() => req.destroy(new Error('connection stalled')), IDLE_MS);
            seen += c.length;
            if (total) onProgress(seen / total, null, total);
          });
          res.pipe(out);
          out.on('finish', () => out.close(() => {
            clearTimeout(idle);
            if (total && seen !== total) return fail(new Error(`truncated: got ${seen} of ${total} bytes`));
            fs.renameSync(tmp, dest);
            done(dest);
          }));
          out.on('error', e => { clearTimeout(idle); fail(e); });
          res.on('error', e => { clearTimeout(idle); fail(e); });
        });
        req.on('timeout', () => req.destroy(new Error(`no response in ${CONNECT_MS / 1000}s`)));
        req.on('error', fail);
      };
      get(url);
    };
    attempt(tries);
  });
}

// Which tar we get matters. Windows has had bsdtar in System32 since Windows 10 1803, but
// a machine with Git for Windows installed puts GNU tar ahead of it on PATH - and GNU tar
// reads an argument containing a colon as host:path, so a perfectly ordinary destination
// like C:\Users\me\AppData\Local\io becomes an attempt to reach a host called "C":
//
//     tar (child): Cannot connect to C: resolve failed
//
// That is what killed the first two Windows CI runs. Ask for System32's bsdtar by name
// where it exists, and pass only relative paths either way (see the extract below), so it
// works whichever tar answers.
function tarExe() {
  if (WIN) {
    const sys = path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'tar.exe');
    if (fs.existsSync(sys)) return sys;
  }
  return 'tar';
}

// Checked up front so the failure is a sentence, not a stack trace four minutes in.
function haveTar() {
  return new Promise(resolve => {
    const p = spawn(tarExe(), ['--version'], { stdio: 'ignore' });
    p.on('error', () => resolve(false));
    p.on('exit', code => resolve(code === 0));
  });
}

// Same lesson as download(): a child that stops talking must eventually be declared dead.
// pip and the model warm-up both print steadily, so silence for this long means wedged -
// a stalled index connection, a dead mirror - and waiting forever just moves the failure
// to someone's laptop at the event, where there is no log to read.
const QUIET_MS = 8 * 60_000;

function run(cmd, args, opts = {}, onLine = noop) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { ...opts, stdio: ['ignore', 'pipe', 'pipe'] });
    let tail = '';
    let done = false;
    let quiet = null;
    const finish = fn => (...a) => { if (done) return; done = true; clearTimeout(quiet); fn(...a); };
    const settleOk = finish(resolve);
    const settleErr = finish(reject);
    const arm = () => {
      clearTimeout(quiet);
      quiet = setTimeout(() => {
        p.kill('SIGKILL');
        settleErr(new Error(`${cmd} produced no output for ${QUIET_MS / 60000} minutes and was stopped\n${tail}`));
      }, QUIET_MS);
    };
    const feed = buf => {
      arm();
      tail = (tail + buf.toString()).slice(-4000);
      buf.toString().split(/\r?\n/).filter(Boolean).forEach(onLine);
    };
    arm();
    p.stdout.on('data', feed);
    p.stderr.on('data', feed);
    p.on('error', settleErr);
    p.on('exit', code => code === 0 ? settleOk() : settleErr(new Error(`${cmd} exited ${code}\n${tail}`)));
  });
}

function pythonIn(dir) {
  const tries = WIN
    ? [path.join(dir, 'python.exe'), path.join(dir, 'Scripts', 'python.exe')]
    : [path.join(dir, 'bin', 'python3'), path.join(dir, 'bin', 'python')];
  return tries.find(p => fs.existsSync(p)) || null;
}

// The HuggingFace cache stores snapshots/<rev>/<file> as a symlink into blobs/<sha>. That
// is fine on the machine that created it, and fatal when the tree gets archived: 7-Zip on
// Windows refuses every one of them ("The directory name is invalid" x120) and the fat zip
// build fails outright. Hard links carry the same bytes at the same cost, but they are
// ordinary directory entries that any archiver reads without following anything.
function desymlink(dir, onNote = noop) {
  let swapped = 0, copied = 0;
  const walk = d => {
    let entries;
    try { entries = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      const full = path.join(d, e.name);
      if (e.isSymbolicLink()) {
        let target;
        try { target = path.resolve(d, fs.readlinkSync(full)); } catch { continue; }
        if (!fs.existsSync(target)) continue;          // dangling: leave it alone
        try {
          fs.unlinkSync(full);
          try { fs.linkSync(target, full); swapped++; }
          catch { fs.copyFileSync(target, full); copied++; }   // e.g. across devices
        } catch { /* nothing sensible to do per-file */ }
      } else if (e.isDirectory()) {
        walk(full);
      }
    }
  };
  walk(dir);
  if (swapped || copied) onNote(`flattened ${swapped + copied} symlinks in the model cache`);
  return { swapped, copied };
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
    // The tarball is 25 MB on macOS and 109 MB on linux-x64, so quote the real
    // content-length rather than a number baked in from one platform.
    const label = mb => `downloading python ${PINS.python.version}${mb ? ` (${mb} MB)` : ''}`;
    say('python', label(), 0);
    await download(url, tgz, (f, note, total) =>
      say('python', note || label(total ? Math.round(total / 1e6) : 0), f));
    say('python', 'unpacking python');
    fs.rmSync(runtimeDir, { recursive: true, force: true });
    fs.mkdirSync(runtimeDir, { recursive: true });
    // Every path here is relative to dest, deliberately: an absolute Windows path carries
    // a drive-letter colon, and GNU tar treats that as a remote host. Both the archive and
    // the destination live directly under dest, so basenames are enough.
    // The tarball's single top-level dir is "python/"; strip it so runtime/ is the root.
    await run(tarExe(), ['-xzf', path.basename(tgz), '--strip-components=1', '-C', path.basename(runtimeDir)],
      { cwd: dest });
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

  // Do this every time, not just when baking a payload: one code path is easier to trust
  // than "only on Windows, only for the fat build", and hard links cost nothing.
  desymlink(hfCache, note => say('model', note));

  say('done', 'ready');
  return { runtimeDir, hfCache, python: py };
}

module.exports = { install, download, desymlink, pythonIn, PINS };

if (require.main === module) {
  const i = process.argv.indexOf('--dest');
  const dest = i > -1 ? path.resolve(process.argv[i + 1]) : path.join(os.tmpdir(), 'io-payload');
  install({ dest, onProgress: p => console.log(`[${p.phase}] ${p.detail}${p.frac != null ? ` ${Math.round(p.frac * 100)}%` : ''}`) })
    .then(r => { console.log('payload ready:', r.runtimeDir, r.hfCache); })
    .catch(e => { console.error(String(e.message || e)); process.exit(1); });
}
