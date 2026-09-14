// Fetch the pinned Codex binary for this machine (or a named target) into codex-bin/.
//
//     node fetch-codex.js                 this platform and architecture
//     node fetch-codex.js linux-x64       a specific target (for cross-packaging)
//
// The release tarball is checked against the sha256 in codex-pins.json before it is
// unpacked. A target with a null hash (never fetched before) gets its hash recorded on
// first fetch, printed so it can be pasted into the pins file; a later mismatch fails.
// Build-time only: the app never downloads Codex at runtime.

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const https = require('https');
const zlib = require('zlib');
const { execFileSync } = require('child_process');

const PINS = JSON.parse(fs.readFileSync(path.join(__dirname, 'codex-pins.json'), 'utf8'));
const target = process.argv[2] || `${process.platform}-${process.arch}`;
const pin = PINS.targets[target];
if (!pin) { console.error(`no pinned Codex for ${target}`); process.exit(2); }

const url = `${PINS.base}/${PINS.tag}/${pin.asset}`;
const outDir = path.join(__dirname, 'codex-bin', target);
const dl = path.join(__dirname, 'codex-bin', 'downloads');
fs.mkdirSync(outDir, { recursive: true });
fs.mkdirSync(dl, { recursive: true });
const tgz = path.join(dl, pin.asset);

function download(u, dest) {
  return new Promise((resolve, reject) => {
    const go = (link, hops) => https.get(link, res => {
      if ([301, 302, 303, 307, 308].includes(res.statusCode) && res.headers.location && hops < 8) { res.resume(); return go(res.headers.location, hops + 1); }
      if (res.statusCode !== 200) { res.resume(); return reject(new Error(`HTTP ${res.statusCode} for ${link}`)); }
      const f = fs.createWriteStream(dest);
      res.pipe(f);
      f.on('finish', () => f.close(resolve));
      f.on('error', reject);
    }).on('error', reject);
    go(u, 0);
  });
}

const sha = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');

(async () => {
  if (!fs.existsSync(tgz) || (pin.sha256 && sha(tgz) !== pin.sha256)) {
    console.log(`fetching ${url}`);
    await download(url, tgz);
  }
  const got = sha(tgz);
  if (pin.sha256 && got !== pin.sha256) { console.error(`sha256 mismatch for ${pin.asset}: ${got}`); process.exit(1); }
  if (!pin.sha256) console.log(`first fetch of ${target}: sha256 ${got} - record it in codex-pins.json`);
  // one file inside the tarball
  const exe = process.platform === 'win32' && target.startsWith('win32') ? 'codex.exe' : 'codex';
  const out = path.join(outDir, exe);
  execFileSync('tar', ['xzf', tgz, '-O'], { stdio: ['ignore', fs.openSync(out, 'w'), 'inherit'], maxBuffer: 1 << 30 });
  fs.chmodSync(out, 0o755);
  const bsha = sha(out);
  if (pin.binary_sha256 && bsha !== pin.binary_sha256) { console.error(`binary sha256 mismatch: ${bsha}`); process.exit(1); }
  fs.writeFileSync(path.join(outDir, 'VERSION.json'), JSON.stringify({ version: PINS.version, tag: PINS.tag, asset: pin.asset, sha256: got, binary_sha256: bsha, fetched: new Date().toISOString() }, null, 1));
  console.log(`${out}  codex ${PINS.version}  sha256 ${bsha}`);
})().catch(e => { console.error(e.message || e); process.exit(1); });
