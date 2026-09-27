// Headless conformance: call bundled Codex directly, never io's sandboxCheck/start gate.
const fs = require('fs');
const path = require('path');
const os = require('os');
const net = require('net');
const dns = require('dns').promises;
const crypto = require('crypto');
const {spawn, spawnSync} = require('child_process');
const codex = require('../../codex');
const {pythonIn} = require('../../bootstrap');

const NAMES = {
  workspace_read: 'Workspace read', workspace_write: 'Workspace write',
  outside_read: 'Outside read blocked', outside_write: 'Outside write blocked',
  link_read: 'Symlink/junction read blocked', link_write: 'Symlink/junction write blocked',
  child_execution: 'Child interpreter works',
};
const within = (root, file) => { const rel = path.relative(root, file); return rel === '' || (!rel.startsWith('..' + path.sep) && rel !== '..' && !path.isAbsolute(rel)); };
const hash = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const cleanEnv = env => Object.fromEntries(Object.entries(env).filter(([k]) =>
  !/^(IO_CODEX_|IO_SANDBOX_|IO_DEV_KEY$|IO_SHELL_TOKEN$|CODEX_|OPENAI_|OPENROUTER_|GH_|CURSOR_|ANTHROPIC_|CLAUDE_)/i.test(k) &&
  !/TOKEN|SECRET|PASSWORD|API_KEY/i.test(k)));
const parseProbe = stdout => {
  const rows = stdout.split(/\r?\n/).filter(s => s.startsWith('IO_SANDBOX_PROBE='));
  if (rows.length !== 1) return null;
  try { return JSON.parse(rows[0].slice('IO_SANDBOX_PROBE='.length)); } catch { return null; }
};
function execute(file, args, env, cwd, timeout = 90000) {
  return new Promise(resolve => {
    const p = spawn(file, args, {env, cwd, windowsHide: true});
    let stdout = '', stderr = '', error = null, timedOut = false;
    const timer = setTimeout(() => { timedOut = true; p.kill('SIGKILL'); }, timeout);
    p.stdout.on('data', d => { stdout += d; }); p.stderr.on('data', d => { stderr += d; });
    p.on('error', e => { error = e.message; });
    p.on('close', (status, signal) => {
      clearTimeout(timer);
      resolve({status, signal, error, timedOut, stdout, stderr, probe: parseProbe(stdout)});
    });
  });
}
function valid(run) { return !!run && run.status === 0 && !run.error && !run.timedOut && !!run.probe?.checks; }
function evaluate(runs, endpoints) {
  const keys = ['workspace_read', 'workspace_write', 'outside_read', 'outside_write', 'link_read', 'link_write', 'child_execution',
    'child:outside_read', 'child:outside_write', 'child:link_read', 'child:link_write'];
  for (const e of endpoints) keys.push(`tcp:${e.name}`, `child:tcp:${e.name}`);
  return keys.map(id => {
    const name = NAMES[id] || (id.startsWith('child:') ? 'Child ' + (NAMES[id.slice(6)] || id.slice(6) + ' blocked') : id + ' blocked');
    const allowed = id.startsWith('workspace_') || id === 'child_execution';
    const network = id.includes('tcp:');
    let status = 'PASS', reason = 'Controls succeeded; restricted behavior matches contract';
    // A witnessed forbidden operation is a violation, even if a different control fails.
    if (!allowed && runs.offline?.probe?.checks[id]?.outcome === 'allowed') {
      status = 'VIOLATION'; reason = 'Offline sandbox allowed a forbidden operation';
    } else if (!allowed && !network && runs.open?.probe?.checks[id]?.outcome === 'allowed') {
      status = 'VIOLATION'; reason = 'Open sandbox allowed access outside the filesystem grants';
    } else if (['host_before', 'host_after'].some(k => !valid(runs[k]) || runs[k].probe.checks[id]?.outcome !== 'allowed')) {
      status = 'CONTROL ERROR'; reason = 'Unconfined before/after control did not demonstrate this operation';
    } else if (['offline', 'open'].some(k => !valid(runs[k]) || !runs[k].probe.checks[id] || runs[k].probe.checks[id].outcome === 'error')) {
      status = 'EXECUTION ERROR'; reason = 'Codex/interpreter did not produce a valid observation for this operation';
    } else if (runs.offline.probe.checks[id].outcome !== (allowed ? 'allowed' : 'denied')) {
      status = 'EXECUTION ERROR'; reason = 'An allowed operation failed in Offline';
    } else if (runs.open.probe.checks[id].outcome !== (allowed || network ? 'allowed' : 'denied')) {
      status = 'CONTROL ERROR'; reason = 'Open profile did not demonstrate its intended allowed operation';
    }
    // Independent host observation catches a false denial emitted by the probe itself.
    const base = id.replace(/^child:/, '');
    if (['outside_write', 'link_write'].includes(base)) {
      for (const k of ['offline', 'open']) if (runs[k]?.mutations?.[base]?.[id.startsWith('child:') ? 'child' : 'parent']) {
        status = 'VIOLATION'; reason = `${k} changed the outside sentinel (host observation)`;
      }
    }
    if (network) {
      const endpoint = id.split(':').at(-1), role = id.startsWith('child:') ? 'child' : 'parent';
      if (runs.offline?.received?.some(e => e.endpoint === endpoint && e.role === role)) {
        status = 'VIOLATION'; reason = 'Offline connection reached the local receiver';
      }
      if (endpoints.find(e => e.name === endpoint)?.ack && status === 'PASS') {
        if (['host_before', 'host_after', 'open'].some(k =>
          !runs[k].received?.some(e => e.endpoint === endpoint && e.role === role) || !runs[k].probe.checks[id].ack)) {
          status = 'CONTROL ERROR'; reason = 'Reachable control lacks matching listener acknowledgment';
        }
      }
    }
    return {id, name, status, reason};
  });
}
function markdown(report) {
  return `# Codex sandbox conformance: ${report.target}\n\nOverall: **${report.overall}**\n\n` +
    (report.error ? `Setup error: ${report.error}\n\n` : '') +
    '| Property | Result | Reason |\n|---|---|---|\n' +
    (report.properties || []).map(p => `| ${p.name} | ${p.status} | ${p.reason} |`).join('\n') + '\n';
}
async function main() {
  const arg = name => { const i = process.argv.indexOf(name); return i >= 0 ? process.argv[i + 1] : undefined; };
  const out = path.resolve(arg('--out') || 'sandbox-results'); fs.mkdirSync(out, {recursive: true});
  const target = `${process.platform}-${process.arch}`;
  const report = {schema: 1, target, overall: 'FAIL', metadata: {
    timestamp: new Date().toISOString(), commit: process.env.GITHUB_SHA || spawnSync('git', ['rev-parse', 'HEAD'], {encoding: 'utf8'}).stdout?.trim(),
    os: os.type(), release: os.release(), version: os.version(), arch: process.arch, node: process.version,
    runnerImage: process.env.ImageOS || null, runnerImageVersion: process.env.ImageVersion || null,
    username: os.userInfo().username, uid: process.getuid?.() ?? null,
    provisioning: process.env.IO_CONFORMANCE_SETUP || 'none',
    sourceHashes: {runner: hash(__filename), probe: hash(path.join(__dirname, 'probe.py')), profileGenerator: hash(path.join(__dirname, '../../codex.js'))},
  }, properties: [], runs: {}};
  let base, alias, server;
  try {
    if (process.getuid?.() === 0) throw Error('Run Unix conformance as an ordinary user, not root');
    // Product generator consults process.env for a dev bypass; remove it before generation.
    for (const k of Object.keys(process.env)) if (/^IO_(CODEX_|SANDBOX_)/.test(k)) delete process.env[k];
    const bin = codex.bundledCodexPath();
    if (!bin.pinned?.sha256 || !/^[0-9a-f]{64}$/.test(bin.pinned.sha256)) throw Error('Missing pinned package hash');
    const stamp = JSON.parse(fs.readFileSync(path.join(bin.dir, 'VERSION.json'), 'utf8'));
    if (stamp.version !== codex.PINS.version || stamp.sha256 !== bin.pinned.sha256 || stamp.binary_sha256 !== hash(bin.path)) throw Error('Bundled package/binary does not match pin metadata');
    if (!codex.binaryInfo(bin.path).host) throw Error('Missing bundled command host');
    const archive = path.join(__dirname, '../../codex-bin/downloads', bin.pinned.asset);
    if (!fs.existsSync(archive) || hash(archive) !== bin.pinned.sha256) throw Error('Pinned package archive unavailable or hash differs; run fetch-codex.js');
    report.metadata.codexPackage = stamp;
    const version = spawnSync(bin.path, ['--version'], {encoding: 'utf8', env: cleanEnv(process.env), timeout: 15000});
    if (version.status !== 0 || version.stdout.trim() !== `codex-cli ${codex.PINS.version}`) throw Error(`Wrong Codex version/status: ${version.stdout} ${version.stderr}`);
    report.metadata.codexVersion = version.stdout.trim();
    const runtime = fs.realpathSync(arg('--runtime') || process.env.IO_PROBE_RUNTIME || path.join(__dirname, '../../.venv'));
    const python = path.resolve(arg('--python') || process.env.IO_PROBE_PYTHON || pythonIn(runtime) || 'missing-python');
    const py = spawnSync(python, ['-c', 'import sys,json; print(json.dumps({"version":sys.version,"executable":sys.executable}))'], {encoding: 'utf8', timeout: 10000});
    if (py.status !== 0) throw Error(`Python control cannot start: ${py.stderr || py.error}`);
    report.metadata.python = JSON.parse(py.stdout);
    if (process.platform === 'win32') {
      const who = spawnSync('whoami.exe', ['/groups'], {encoding: 'utf8'});
      report.metadata.accountGroups = who.stdout; // SIDs/group attributes; no credentials.
    }
    base = fs.mkdtempSync(path.join(os.homedir(), '.io-sandbox-conformance-'));
    const ws = path.join(base, 'allowed workspace'), outside = path.join(base, 'outside');
    fs.mkdirSync(ws); fs.mkdirSync(outside);
    const roots = [runtime, bin.dir, os.tmpdir(), '/tmp', ws].filter(p => fs.existsSync(p)).map(p => fs.realpathSync(p));
    if (roots.some(r => within(r, fs.realpathSync(outside)))) throw Error('Outside sentinel lies within a granted root');
    if (!within(runtime, fs.realpathSync(python))) throw Error('Interpreter is outside its granted runtime (use standalone Python)');
    const link = path.join(ws, 'outside link');
    fs.symlinkSync(outside, link, process.platform === 'win32' ? 'junction' : 'dir');
    const token = crypto.randomBytes(16).toString('hex');
    const events = [];
    server = net.createServer(socket => {
      socket.setTimeout(5000, () => socket.destroy());
      let input = '';
      socket.on('error', () => {});
      socket.on('data', d => {
        input += d; if (input.length > 8192) { socket.destroy(); return; }
        if (!input.includes('\n')) return;
        try { const e = JSON.parse(input.split('\n')[0]); if (e.token === token) { events.push(e); socket.end('io-ack\n'); } else socket.destroy(); } catch { socket.destroy(); }
      });
    });
    await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '0.0.0.0', resolve); });
    const lan = Object.values(os.networkInterfaces()).flat().find(a => a && a.family === 'IPv4' && !a.internal && !a.address.startsWith('169.254.'));
    if (!lan) throw Error('No non-loopback IPv4 address for controlled receiver');
    const externalHost = arg('--external-host') || 'example.com';
    const external = await dns.lookup(externalHost, {family: 4});
    const endpoints = [
      {name: 'loopback', host: '127.0.0.1', port: server.address().port, ack: true},
      {name: 'nonloopback', host: lan.address, port: server.address().port, ack: true},
      {name: 'internet', host: external.address, port: 443, ack: false},
    ];
    report.metadata.endpoints = endpoints; report.metadata.externalHostname = externalHost;
    report.metadata.fixtureRoot = base; report.metadata.explicitGrantedRoots = roots;
    const manifest = {token, workspace_read: path.join(ws, 'read.txt'), workspace_write: path.join(ws, 'written.txt'),
      outside_read: path.join(outside, 'read.txt'), outside_write: path.join(outside, 'write.txt'),
      link_read: path.join(link, 'read.txt'), link_write: path.join(link, 'link-write.txt'), endpoints};
    const manifestFile = path.join(ws, 'manifest.json'), script = path.join(ws, 'probe.py');
    fs.writeFileSync(manifestFile, JSON.stringify(manifest)); fs.copyFileSync(path.join(__dirname, 'probe.py'), script);
    const env = cleanEnv(process.env);
    if (process.platform === 'linux') {
      alias = fs.mkdtempSync(path.join(os.tmpdir(), 'io-conformance-arg0-'));
      fs.symlinkSync(bin.path, path.join(alias, 'codex-linux-sandbox'));
      env.PATH = alias + path.delimiter + (env.PATH || '');
    }
    const reset = () => { for (const f of [manifest.workspace_read, manifest.outside_read, manifest.outside_write, path.join(outside, 'link-write.txt')]) fs.writeFileSync(f, token); };
    for (const label of ['host_before', 'offline', 'open', 'host_after']) {
      reset(); let result;
      const home = path.join(base, `codex-${label}`);
      const childEnv = {...env, ...cleanEnv(codex.baseEnv(home, runtime)), CODEX_HOME: home};
      if (alias) childEnv.PATH = alias + path.delimiter + childEnv.PATH;
      if (label.startsWith('host_')) result = await execute(python, [script, manifestFile, label], childEnv, ws);
      else {
        codex.writeConfig(home, 1, {wall: label, trust: ws, codexDir: bin.dir, libsDir: runtime});
        const profile = fs.readFileSync(path.join(home, 'io.config.toml'), 'utf8');
        if (!profile.includes('default_permissions = "io"') || profile.includes('danger-full-access')) throw Error('Wall missing from generated profile');
        fs.writeFileSync(path.join(out, `${label}.config.toml`), profile);
        result = await execute(bin.path, ['sandbox', '-p', 'io', '-P', 'io', '-C', ws, '--', python, script, manifestFile, label], childEnv, ws);
      }
      result.mutations = {};
      for (const [id, file] of [['outside_write', manifest.outside_write], ['link_write', path.join(outside, 'link-write.txt')]]) {
        const content = fs.readFileSync(file, 'utf8');
        result.mutations[id] = Object.fromEntries(['parent', 'child'].map(role => [role, content.includes(`${token}:${label}:${role}`)]));
        if (content !== token && !result.mutations[id].parent && !result.mutations[id].child) throw Error(`Unattributed sentinel mutation: ${id}`);
      }
      result.received = events.filter(e => e.label === label);
      fs.writeFileSync(path.join(out, `${label}.stdout.txt`), result.stdout);
      fs.writeFileSync(path.join(out, `${label}.stderr.txt`), result.stderr);
      report.runs[label] = result;
      console.log(`${label}: exit=${result.status}, probe=${!!result.probe}, received=${result.received.length}`);
    }
    report.properties = evaluate(report.runs, endpoints);
    report.overall = report.properties.every(p => p.status === 'PASS') ? 'PASS' : 'FAIL';
  } catch (e) { report.error = e.stack || e.message; }
  finally {
    if (server) await new Promise(resolve => server.close(resolve));
    if (base) { try { fs.rmSync(base, {recursive: true, force: true}); } catch (e) { report.cleanupError = e.message; report.overall = 'FAIL'; } }
    if (alias) fs.rmSync(alias, {recursive: true, force: true});
    fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify(report, null, 2));
    fs.writeFileSync(path.join(out, 'summary.md'), markdown(report));
    console.log(markdown(report)); process.exitCode = report.overall === 'PASS' ? 0 : 1;
  }
}
if (require.main === module) main().catch(e => { console.error(e); process.exitCode = 1; });
module.exports = {evaluate, parseProbe, within, markdown};
