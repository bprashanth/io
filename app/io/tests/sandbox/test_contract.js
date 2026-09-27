const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {evaluate, parseProbe, within} = require('./run.js');

const REPORT_SCRIPT = path.join(__dirname, 'report.js');
const REQUIRED_TARGETS = ['linux-x64', 'darwin-x64', 'darwin-arm64', 'win32-x64'];
const PROPERTY_IDS = [
  'workspace_read',
  'workspace_write',
  'outside_read',
  'outside_write',
  'link_read',
  'link_write',
  'child_execution',
  'child:outside_read',
  'child:outside_write',
  'child:link_read',
  'child:link_write',
  'tcp:loopback',
  'child:tcp:loopback',
  'tcp:nonloopback',
  'child:tcp:nonloopback',
  'tcp:internet',
  'child:tcp:internet',
];
const REACHABLE_ENDPOINTS = ['loopback', 'nonloopback'];
const RECEIVED_EVENTS = REACHABLE_ENDPOINTS.flatMap(endpoint => ([
  {endpoint, role: 'parent'},
  {endpoint, role: 'child'},
]));

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

function makeProperty(id, status = 'PASS', extra = {}) {
  return {
    id,
    name: id,
    status,
    reason: status === 'PASS' ? 'ok' : status,
    ...extra,
  };
}

function makeReport(target, options = {}) {
  const properties = options.properties || PROPERTY_IDS.map(id => makeProperty(id, 'PASS'));
  return {
    schema: 1,
    target,
    overall: options.overall || 'PASS',
    metadata: {target},
    properties,
    ...options.extra,
  };
}

function writeReport(root, target, options = {}, subdir = '') {
  const dir = path.join(root, target, subdir);
  fs.mkdirSync(dir, {recursive: true});
  fs.writeFileSync(path.join(dir, 'results.json'), JSON.stringify(makeReport(target, options), null, 2));
  return dir;
}

function runReportCli(root, outDir, extraEnv = {}) {
  return spawnSync(process.execPath, [REPORT_SCRIPT, root, outDir], {
    encoding: 'utf8',
    env: {...process.env, ...extraEnv},
  });
}

function readMatrix(outDir) {
  return JSON.parse(fs.readFileSync(path.join(outDir, 'matrix.json'), 'utf8'));
}

function main() {
  assert.equal(within('/tmp/root', '/tmp/root/file.txt'), true);
  assert.equal(within('/tmp/root', '/tmp/root-sibling/file.txt'), false);

  assert.deepStrictEqual(parseProbe('IO_SANDBOX_PROBE={"checks":{"ok":true}}\n'), {checks: {ok: true}});
  assert.equal(parseProbe('IO_SANDBOX_PROBE=not-json\n'), null);
  assert.equal(parseProbe('IO_SANDBOX_PROBE={"checks":{}}\nIO_SANDBOX_PROBE={"checks":{}}\n'), null);

  const passingRuns = makePassingRuns();
  const passing = evaluate(passingRuns, [
    {name: 'loopback', ack: true},
    {name: 'nonloopback', ack: true},
    {name: 'internet', ack: false},
  ]);
  assert.deepStrictEqual(passing.map(row => row.id), PROPERTY_IDS);
  assert.ok(passing.every(row => row.status === 'PASS'), 'expected all synthetic control rows to PASS');

  const forbiddenAllowed = makePassingRuns();
  forbiddenAllowed.offline.probe.checks.outside_write.outcome = 'allowed';
  assert.equal(
    evaluate(forbiddenAllowed, [
      {name: 'loopback', ack: true},
      {name: 'nonloopback', ack: true},
      {name: 'internet', ack: false},
    ]).find(row => row.id === 'outside_write').status,
    'VIOLATION'
  );

  const missingChild = makePassingRuns();
  delete missingChild.offline.probe.checks['child:outside_read'];
  assert.equal(
    evaluate(missingChild, [
      {name: 'loopback', ack: true},
      {name: 'nonloopback', ack: true},
      {name: 'internet', ack: false},
    ]).find(row => row.id === 'child:outside_read').status,
    'EXECUTION ERROR'
  );

  const crashedInterpreter = makePassingRuns();
  crashedInterpreter.offline.status = 1;
  assert.equal(
    evaluate(crashedInterpreter, [
      {name: 'loopback', ack: true},
      {name: 'nonloopback', ack: true},
      {name: 'internet', ack: false},
    ]).find(row => row.id === 'workspace_read').status,
    'EXECUTION ERROR'
  );

  const failedControl = makePassingRuns();
  failedControl.host_after.status = 1;
  assert.equal(
    evaluate(failedControl, [
      {name: 'loopback', ack: true},
      {name: 'nonloopback', ack: true},
      {name: 'internet', ack: false},
    ]).find(row => row.id === 'workspace_read').status,
    'CONTROL ERROR'
  );

  const receiverArrival = makePassingRuns();
  receiverArrival.offline.received = [{endpoint: 'loopback', role: 'parent'}];
  assert.equal(
    evaluate(receiverArrival, [
      {name: 'loopback', ack: true},
      {name: 'nonloopback', ack: true},
      {name: 'internet', ack: false},
    ]).find(row => row.id === 'tcp:loopback').status,
    'VIOLATION'
  );

  const missingAck = makePassingRuns();
  missingAck.open.received = missingAck.open.received.filter(event => !(event.endpoint === 'loopback' && event.role === 'child'));
  assert.equal(
    evaluate(missingAck, [
      {name: 'loopback', ack: true},
      {name: 'nonloopback', ack: true},
      {name: 'internet', ack: false},
    ]).find(row => row.id === 'child:tcp:loopback').status,
    'CONTROL ERROR'
  );

  const hostMutation = makePassingRuns();
  hostMutation.open.mutations.outside_write.child = true;
  assert.equal(
    evaluate(hostMutation, [
      {name: 'loopback', ack: true},
      {name: 'nonloopback', ack: true},
      {name: 'internet', ack: false},
    ]).find(row => row.id === 'child:outside_write').status,
    'VIOLATION'
  );

  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'sandbox-report-contract-'));
  try {
    const artifactRoot = path.join(tempRoot, 'artifacts');
    const outputDir = path.join(tempRoot, 'matrix-out');
    const summaryFile = path.join(tempRoot, 'summary.md');
    fs.mkdirSync(artifactRoot, {recursive: true});

    for (const target of REQUIRED_TARGETS) {
      writeReport(artifactRoot, target, {}, 'nested/deeper');
    }

    const ok = runReportCli(artifactRoot, outputDir, {GITHUB_STEP_SUMMARY: summaryFile});
    assert.equal(ok.status, 0, ok.stderr);
    assert.ok(fs.existsSync(path.join(outputDir, 'matrix.json')));
    assert.ok(fs.existsSync(path.join(outputDir, 'matrix.md')));
    assert.ok(fs.readFileSync(summaryFile, 'utf8').includes('# Sandbox conformance matrix'));
    const matrix = readMatrix(outputDir);
    assert.equal(matrix.overall, 'PASS');
    assert.deepStrictEqual(matrix.requiredTargets, REQUIRED_TARGETS);
    assert.equal(matrix.rows.length, PROPERTY_IDS.length);
    for (const target of REQUIRED_TARGETS) {
      assert.equal(matrix.targets[target].state, 'PASS');
    }
    for (const row of matrix.rows) {
      for (const target of REQUIRED_TARGETS) {
        assert.equal(row.cells[target], 'PASS');
      }
    }

    const missingRoot = path.join(tempRoot, 'missing-target');
    fs.mkdirSync(missingRoot, {recursive: true});
    for (const target of REQUIRED_TARGETS.slice(0, 3)) {
      writeReport(missingRoot, target, {}, 'deep');
    }
    const missing = runReportCli(missingRoot, path.join(tempRoot, 'missing-out'));
    assert.notEqual(missing.status, 0);
    const missingMatrix = readMatrix(path.join(tempRoot, 'missing-out'));
    assert.equal(missingMatrix.targets['win32-x64'].state, 'MISSING');

    const zeroPropsRoot = path.join(tempRoot, 'zero-properties');
    fs.mkdirSync(zeroPropsRoot, {recursive: true});
    for (const target of REQUIRED_TARGETS) {
      writeReport(zeroPropsRoot, target, target === 'darwin-arm64' ? {properties: [], overall: 'PASS'} : {}, 'deep');
    }
    const zeroProps = runReportCli(zeroPropsRoot, path.join(tempRoot, 'zero-out'));
    assert.notEqual(zeroProps.status, 0);
    const zeroMatrix = readMatrix(path.join(tempRoot, 'zero-out'));
    assert.equal(zeroMatrix.targets['darwin-arm64'].state, 'ERROR');
    assert.ok(zeroMatrix.targets['darwin-arm64'].notes.some(note => note.includes('Missing property')));

    const duplicateRoot = path.join(tempRoot, 'duplicate-target');
    fs.mkdirSync(duplicateRoot, {recursive: true});
    for (const target of REQUIRED_TARGETS) {
      writeReport(duplicateRoot, target, {}, 'deep');
    }
    writeReport(duplicateRoot, 'linux-x64', {}, 'duplicate');
    const duplicate = runReportCli(duplicateRoot, path.join(tempRoot, 'duplicate-out'));
    assert.notEqual(duplicate.status, 0);
    const duplicateMatrix = readMatrix(path.join(tempRoot, 'duplicate-out'));
    assert.equal(duplicateMatrix.targets['linux-x64'].state, 'ERROR');
    assert.ok(duplicateMatrix.targets['linux-x64'].notes.some(note => note.includes('Duplicate target artifact')));
    // A complete-looking report with duplicated rows must not pass aggregation.
    const duplicateProps = PROPERTY_IDS.map(id => makeProperty(id));
    duplicateProps.push(makeProperty('outside_read'));
    writeReport(artifactRoot, 'linux-x64', {properties: duplicateProps}, 'nested/deeper');
    assert.notEqual(runReportCli(artifactRoot, path.join(tempRoot, 'duplicate-props-out')).status, 0);
  } finally {
    fs.rmSync(tempRoot, {recursive: true, force: true});
  }
}

main();
console.log('Sandbox classification and matrix integrity checks passed (synthetic observations only).');
