#!/usr/bin/env node

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');

const diagnostic = require('../diagnostic/diagnose.js');
const {evaluate} = require('./sandbox/run.js');

const DIAG = path.join(__dirname, '..', 'diagnostic', 'diagnose.js');
const REQUIRED_TARGETS = ['linux-x64', 'darwin-x64', 'darwin-arm64', 'win32-x64'];
const PROPERTY_IDS = diagnostic.REQUIRED_IDS;
const PROPERTY_NAMES = {
  workspace_read: 'Workspace read',
  workspace_write: 'Workspace write',
  outside_read: 'Outside read blocked',
  outside_write: 'Outside write blocked',
  link_read: 'Symlink/junction read blocked',
  link_write: 'Symlink/junction write blocked',
  child_execution: 'Child interpreter works',
};

const ENDPOINTS = [
  {name: 'loopback', ack: true},
  {name: 'nonloopback', ack: true},
  {name: 'internet', ack: false},
];

const RECEIVED_EVENTS = [
  {endpoint: 'loopback', role: 'parent'},
  {endpoint: 'loopback', role: 'child'},
  {endpoint: 'nonloopback', role: 'parent'},
  {endpoint: 'nonloopback', role: 'child'},
];

let passed = 0;
const test = (name, fn) => {
  fn();
  passed += 1;
  console.log('ok -', name);
};

function humanName(id) {
  if (PROPERTY_NAMES[id]) return PROPERTY_NAMES[id];
  if (id.startsWith('child:')) {
    const base = id.slice('child:'.length);
    return `Child ${PROPERTY_NAMES[base] || `${base} blocked`}`;
  }
  if (id.startsWith('tcp:')) return `TCP ${id.slice('tcp:'.length)}`;
  return id;
}

function buildChecks(mode) {
  const checks = {};
  for (const id of PROPERTY_IDS) {
    const allowed = id.startsWith('workspace_') || id === 'child_execution';
    const network = id.includes('tcp:');
    let outcome;
    if (mode === 'host') {
      outcome = 'allowed';
    } else if (mode === 'offline') {
      outcome = allowed ? 'allowed' : 'denied';
    } else if (mode === 'open') {
      outcome = allowed || network ? 'allowed' : 'denied';
    } else {
      throw new Error(`Unknown mode: ${mode}`);
    }
    const check = {outcome};
    if (network) {
      check.ack = id.endsWith('internet') ? false : mode !== 'offline';
    }
    checks[id] = check;
  }
  return checks;
}

function makeRun(mode, received) {
  return {
    status: 0,
    signal: null,
    error: null,
    timedOut: false,
    stdout: '',
    stderr: '',
    probe: {checks: buildChecks(mode)},
    received,
    mutations: {
      outside_write: {parent: false, child: false},
      link_write: {parent: false, child: false},
    },
  };
}

function makePassingRuns() {
  return {
    host_before: makeRun('host', RECEIVED_EVENTS),
    offline: makeRun('offline', []),
    open: makeRun('open', RECEIVED_EVENTS),
    host_after: makeRun('host', RECEIVED_EVENTS),
  };
}

function makeProperties(overrides = {}) {
  return PROPERTY_IDS
    .filter(id => !overrides.omit?.includes(id))
    .map(id => ({
      id,
      name: humanName(id),
      status: overrides.statuses?.[id] || 'PASS',
      reason: overrides.reasons?.[id] || 'ok',
    }));
}

function makeReport(target, overrides = {}) {
  const report = {
    schema: 1,
    target,
    overall: overrides.overall || 'PASS',
    metadata: {
      timestamp: '2026-09-27T00:00:00.000Z',
      commit: 'deadbeefdeadbeefdeadbeefdeadbeefdeadbeef',
      os: os.type(),
      release: os.release(),
      version: os.version(),
      arch: process.arch,
      node: process.version,
      codexVersion: 'codex-cli 0.0.0',
      codexPackage: {version: '0.0.0', sha256: 'f'.repeat(64)},
      endpoints: ENDPOINTS,
    },
    properties: makeProperties(overrides),
    runs: makePassingRuns(),
  };
  if (overrides.mutateRuns) overrides.mutateRuns(report.runs);
  if (overrides.extra) Object.assign(report, overrides.extra);
  return report;
}

function writeResults(root, report, subdir = 'nested/deeper') {
  const dir = path.join(root, subdir);
  fs.mkdirSync(dir, {recursive: true});
  const file = path.join(dir, 'results.json');
  fs.writeFileSync(file, JSON.stringify(report, null, 2));
  return {dir, file};
}

function readCapability(outDir) {
  return JSON.parse(fs.readFileSync(path.join(outDir, 'capability.json'), 'utf8'));
}

test('classifyCapability keeps a complete report as PASS', () => {
  const report = makeReport('linux-x64');
  const capability = diagnostic.classifyCapability(report, {
    runtime: '/tmp/io-probe-runtime/runtime',
    reportSource: '/tmp/io-diagnostic/raw/results.json',
  });

  assert.equal(capability.status, 'PASS');
  assert.equal(capability.executionMode, 'remote');
  assert.equal(capability.routingChanged, false);
  assert.equal(capability.probes.length, PROPERTY_IDS.length);
  assert.equal(capability.probes.find(p => p.id === 'outside_write').observed.offline.outcome, 'denied');
  assert.ok(capability.rationale[0].includes('All required probes passed'));
});

test('missing rows stay INCONCLUSIVE', () => {
  const report = makeReport('linux-x64', {omit: ['child:link_write']});
  const capability = diagnostic.classifyCapability(report, {
    runtime: '/tmp/io-probe-runtime/runtime',
    reportSource: '/tmp/io-diagnostic/raw/results.json',
  });

  assert.equal(capability.status, 'INCONCLUSIVE');
  assert.ok(capability.rationale.some(line => /Missing required property child:link_write/.test(line)));
  assert.equal(capability.probes.find(p => p.id === 'child:link_write').status, 'INCONCLUSIVE');
});

test('violations become FAIL', () => {
  const report = makeReport('linux-x64', {
    mutateRuns(runs) {
      runs.offline.probe.checks.outside_write.outcome = 'allowed';
      runs.open.probe.checks.outside_write.outcome = 'allowed';
    },
    statuses: {outside_write: 'VIOLATION'},
    reasons: {outside_write: 'Offline sandbox allowed a forbidden operation'},
  });
  const capability = diagnostic.classifyCapability(report, {
    runtime: '/tmp/io-probe-runtime/runtime',
    reportSource: '/tmp/io-diagnostic/raw/results.json',
  });

  assert.equal(capability.status, 'FAIL');
  assert.ok(capability.rationale.some(line => /outside write blocked/i.test(line) || /forbidden operation/i.test(line)));
});

test('launcher errors are INCONCLUSIVE', () => {
  const report = makeReport('linux-x64', {extra: {error: 'sandbox launcher failed: ENOENT'}});
  const capability = diagnostic.classifyCapability(report, {
    runtime: '/tmp/io-probe-runtime/runtime',
    reportSource: '/tmp/io-diagnostic/raw/results.json',
  });

  assert.equal(capability.status, 'INCONCLUSIVE');
  assert.ok(capability.rationale.some(line => /Launcher error/.test(line)));
});

test('report-existing mode reads an actual results tree and preserves it', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'io-diagnostic-'));
  const source = path.join(root, 'existing');
  const out = path.join(root, 'out');
  const report = makeReport('linux-x64');
  const {file} = writeResults(source, report);

  const result = spawnSync(process.execPath, [DIAG, '--runtime', '/tmp/io-probe-runtime/runtime', '--out', out, '--report-existing', source], {
    encoding: 'utf8',
  });

  assert.equal(result.status, 0, result.stderr);
  const capability = readCapability(out);
  assert.equal(capability.status, 'PASS');
  assert.equal(capability.executionMode, 'remote');
  assert.equal(capability.routingChanged, false);
  assert.equal(capability.source.mode, 'report-existing');
  assert.ok(capability.probes.some(p => p.id === 'outside_write' && p.observed.offline.outcome === 'denied'));
  assert.equal(fs.readFileSync(file, 'utf8').includes('"schema": 1'), true);

  fs.rmSync(root, {recursive: true, force: true});
});

test('report-existing mode treats incomplete reports as INCONCLUSIVE', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'io-diagnostic-missing-'));
  const source = path.join(root, 'existing');
  const out = path.join(root, 'out');
  const report = makeReport('linux-x64', {omit: ['link_write']});
  writeResults(source, report);

  const result = spawnSync(process.execPath, [DIAG, '--runtime', '/tmp/io-probe-runtime/runtime', '--out', out, '--report-existing', source], {
    encoding: 'utf8',
  });

  assert.notEqual(result.status, 0, result.stderr);
  const capability = readCapability(out);
  assert.equal(capability.status, 'INCONCLUSIVE');
  assert.ok(capability.rationale.some(line => /Missing required property link_write/.test(line)));
  assert.equal(capability.probes.find(p => p.id === 'link_write').status, 'INCONCLUSIVE');

  fs.rmSync(root, {recursive: true, force: true});
});

test('evaluate still agrees with the synthetic pass fixture', () => {
  const report = makeReport('linux-x64');
  const rows = evaluate(report.runs, ENDPOINTS);
  assert.ok(rows.every(row => row.status === 'PASS'));
  assert.equal(rows.length, PROPERTY_IDS.length);
});

console.log(`\n${passed} diagnostic tests passed`);
