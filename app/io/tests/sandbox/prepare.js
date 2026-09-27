// Only io's pinned standalone Python; no Electron, pip packages, scanner or model.
const fs = require('fs');
const path = require('path');
const os = require('os');
const {execFileSync} = require('child_process');
const {download, pythonIn, PINS} = require('../../bootstrap');

(async () => {
  const target = `${process.platform}-${process.arch}`;
  const asset = PINS.python.targets[target];
  if (!asset) throw Error(`No Python pin for ${target}`);
  const root = path.resolve(process.argv[2] || path.join(os.homedir(), '.io-conformance-runtime', target));
  const runtime = path.join(root, 'runtime');
  fs.mkdirSync(runtime, {recursive: true});
  // Fetch afresh: do not mistake a leftover partial extraction for a ready runtime.
  await download(`${PINS.python.base}/${PINS.python.release}/${asset}`, path.join(root, asset));
  const tar = process.platform === 'win32' ? path.join(process.env.SystemRoot, 'System32', 'tar.exe') : 'tar';
  execFileSync(tar, ['-xzf', asset, '--strip-components=1', '-C', 'runtime'], {cwd: root, stdio: 'inherit'});
  const python = pythonIn(runtime);
  if (!python) throw Error('Pinned Python did not unpack');
  const version = execFileSync(python, ['--version'], {encoding: 'utf8'}).trim();
  if (version !== `Python ${PINS.python.version}`) throw Error(`Wrong Python: ${version}`);
  console.log(JSON.stringify({target, python, runtime, version}));
  if (process.env.GITHUB_ENV) fs.appendFileSync(process.env.GITHUB_ENV,
    `IO_PROBE_PYTHON=${python}\nIO_PROBE_RUNTIME=${runtime}\n`);
})().catch(e => { console.error(e.message); process.exitCode = 1; });
