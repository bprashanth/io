// Bootstrap tests: the first-run installer, its privacy-server probe, and the thin/local
// choice. Run: node tests/test_bootstrap.js

const assert = require('assert');
const http = require('http');
const bootstrap = require('../bootstrap');

let passed = 0;
const tests = [];
const test = (name, fn) => tests.push({ name, fn });

function listen(server) {
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => resolve(server.address().port));
  });
}

function close(server) {
  return new Promise(resolve => server.close(resolve));
}

async function serve(handler, fn) {
  const server = http.createServer(handler);
  const port = await listen(server);
  const base = `http://127.0.0.1:${port}`;
  try {
    return await fn(base);
  } finally {
    await close(server);
  }
}

test('probePrivacyServer accepts the actual /health shape', async () => {
  await serve((req, res) => {
    if (req.url === '/health') {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end('<!doctype html><title>io privacy server</title><h1>io privacy server</h1><p>Scanning for laptops that cannot run the model themselves.</p>');
      return;
    }
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('not found');
  }, async base => {
    assert.strictEqual(await bootstrap.probePrivacyServer(base), true);
  });
});

test('probePrivacyServer rejects a 200 page that is not the privacy-server health page', async () => {
  await serve((req, res) => {
    if (req.url === '/health') {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end('<!doctype html><title>something else</title><p>healthy-ish</p>');
      return;
    }
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('not found');
  }, async base => {
    assert.strictEqual(await bootstrap.probePrivacyServer(base), false);
  });
});

test('scannerInstallPlan prefers readers-only when the privacy server answers', async () => {
  const plan = await bootstrap.scannerInstallPlan({
    platformKey: 'linux-x64',
    scanner: 'auto',
    privacyServer: 'https://secret-token@privacy.example.org',
    probe: async () => true,
  });
  assert.strictEqual(plan.mode, 'readers');
  assert.ok(/privacy server/.test(plan.marker), plan.marker);
  assert.ok(!plan.marker.includes('secret-token'), plan.marker);
  assert.ok(plan.marker.includes('privacy.example.org'), plan.marker);
});

test('scannerInstallPlan forces the local scanner only when asked or for fat payloads', async () => {
  let calls = 0;
  const probe = async () => { calls += 1; return false; };
  const local = await bootstrap.scannerInstallPlan({
    platformKey: 'linux-x64',
    scanner: 'local',
    probe,
  });
  assert.strictEqual(local.mode, 'local');
  assert.strictEqual(calls, 0);

  const fat = await bootstrap.scannerInstallPlan({
    platformKey: 'linux-x64',
    fat: true,
    probe,
  });
  assert.strictEqual(fat.mode, 'local');
  assert.strictEqual(calls, 0);
});

test('scannerInstallPlan accepts scanner as the explicit local-install alias', async () => {
  let calls = 0;
  const probe = async () => { calls += 1; return false; };
  const plan = await bootstrap.scannerInstallPlan({
    platformKey: 'linux-x64',
    scanner: 'scanner',
    probe,
  });
  assert.strictEqual(plan.mode, 'local');
  assert.strictEqual(calls, 0);
});

test('installThresholds keeps readers-only lighter and skips model RAM checks', () => {
  const readers = bootstrap.installThresholds({ mode: 'readers' });
  const local = bootstrap.installThresholds({ mode: 'local' });
  assert.strictEqual(readers.ramGb, null);
  assert.ok(readers.roomGb < local.roomGb);
  assert.ok(local.ramGb !== null);
});

test('scannerInstallPlan leaves an honest fallback sentence when the server is down', async () => {
  const plan = await bootstrap.scannerInstallPlan({
    platformKey: 'linux-x64',
    scanner: 'auto',
    privacyServer: 'https://privacy.example.org',
    probe: async () => false,
  });
  assert.strictEqual(plan.mode, 'readers');
  assert.ok(/could not reach the privacy server/.test(plan.marker), plan.marker);
  assert.ok(/pattern matching/.test(plan.marker), plan.marker);
  assert.ok(!/cannot/i.test(plan.marker), plan.marker);
});

test('unsupported platforms keep the readers-only path without saying "cannot"', async () => {
  const platformKey = (bootstrap.PINS.scannerUnsupported || [])[0];
  if (!platformKey) {
    console.log('   (skipped: no unsupported platform listed in pins)');
    return;
  }
  const plan = await bootstrap.scannerInstallPlan({
    platformKey,
    scanner: 'auto',
    probe: async () => true,
  });
  assert.strictEqual(plan.mode, 'readers');
  assert.ok(!/cannot/i.test(plan.marker), plan.marker);
});

(async () => {
  for (const t of tests) {
    await t.fn();
    passed += 1;
    console.log('ok -', t.name);
  }
  console.log(`\n${passed} bootstrap tests passed`);
})().catch(err => {
  console.error(err && err.stack || err);
  process.exit(1);
});
