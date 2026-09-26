#!/usr/bin/env node

const assert = require('assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { EventEmitter } = require('events');
const https = require('https');
const { KeyStore } = require('../openrouter');

const tests = [];

function test(name, fn) {
  tests.push([name, fn]);
}

function tempDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'io-openrouter-'));
}

function installHttpsGet({ statusCode = 200, body = '', requestError = null }) {
  const original = https.get;
  https.get = (...args) => {
    const cb = args.find(arg => typeof arg === 'function');
    const req = new EventEmitter();
    req.destroy = () => req.emit('close');
    req.setTimeout = () => req;
    process.nextTick(() => {
      if (requestError) {
        req.emit('error', requestError instanceof Error ? requestError : new Error(String(requestError)));
        return;
      }
      const res = new EventEmitter();
      res.statusCode = statusCode;
      cb(res);
      if (body !== null && body !== undefined && body !== '') {
        res.emit('data', Buffer.from(String(body)));
      }
      res.emit('end');
    });
    return req;
  };
  return () => {
    https.get = original;
  };
}

async function withHttpsGet(mock, fn) {
  const restore = installHttpsGet(mock);
  try {
    return await fn();
  } finally {
    restore();
  }
}

test('valid key persists with mode 0600 and reloads', async () => {
  const dir = tempDir();
  const file = path.join(dir, 'openrouter-key.json');
  try {
    await withHttpsGet({
      statusCode: 200,
      body: JSON.stringify({ data: { limit_remaining: 17 } }),
    }, async () => {
      const store = new KeyStore(dir);
      const result = await store.replace('  sk-valid-1234  ');
      assert.deepStrictEqual(result, { ok: true, configured: true, suffix: '1234', remaining: 17, persistent: true });
      assert.equal(fs.existsSync(file), true);
      if (process.platform !== 'win32') {
        assert.equal(fs.statSync(file).mode & 0o777, 0o600);
      }
      assert.deepStrictEqual(JSON.parse(fs.readFileSync(file, 'utf8')), { api_key: 'sk-valid-1234' });
      const reloaded = new KeyStore(dir);
      assert.deepStrictEqual(reloaded.status(), { configured: true, suffix: '1234', remaining: null, persistent: true });
    });
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('portable mode keeps the key only in memory and never writes a file', async () => {
  const dir = tempDir();
  const file = path.join(dir, 'openrouter-key.json');
  try {
    await withHttpsGet({
      statusCode: 200,
      body: JSON.stringify({ data: { limit_remaining: 3 } }),
    }, async () => {
      const store = new KeyStore(dir, true);
      const result = await store.replace('sk-portable-7777');
      assert.deepStrictEqual(result, { ok: true, configured: true, suffix: '7777', remaining: 3, persistent: false });
      assert.equal(fs.existsSync(file), false);
      assert.deepStrictEqual(store.status(), { configured: true, suffix: '7777', remaining: 3, persistent: false });
      const reloaded = new KeyStore(dir, true);
      assert.deepStrictEqual(reloaded.status(), { configured: false, suffix: '', remaining: null, persistent: false });
    });
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('bad key leaves the prior key unchanged', async () => {
  const dir = tempDir();
  const file = path.join(dir, 'openrouter-key.json');
  try {
    await withHttpsGet({
      statusCode: 200,
      body: JSON.stringify({ data: { limit_remaining: 11 } }),
    }, async () => {
      const store = new KeyStore(dir);
      const first = await store.replace('sk-good-1111');
      assert.equal(first.ok, true);
      const beforeStatus = store.status();
      const beforeFile = fs.readFileSync(file, 'utf8');
      await withHttpsGet({
        statusCode: 401,
        body: JSON.stringify({ error: `bad key ${'sk-bad-2222'}` }),
      }, async () => {
        const result = await store.replace('sk-bad-2222');
        assert.equal(result.error, 'This key was not accepted. Check it and try again.');
        assert.deepStrictEqual(store.status(), beforeStatus);
        assert.equal(fs.readFileSync(file, 'utf8'), beforeFile);
      });
    });
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('remove deletes the persisted key and clears status', async () => {
  const dir = tempDir();
  const file = path.join(dir, 'openrouter-key.json');
  try {
    await withHttpsGet({
      statusCode: 200,
      body: JSON.stringify({ data: { limit_remaining: 6 } }),
    }, async () => {
      const store = new KeyStore(dir);
      await store.replace('sk-remove-3333');
      assert.equal(fs.existsSync(file), true);
      const result = store.remove();
      assert.deepStrictEqual(result, { ok: true, configured: false, suffix: '', remaining: null, persistent: true });
      assert.equal(fs.existsSync(file), false);
      assert.deepStrictEqual(store.status(), { configured: false, suffix: '', remaining: null, persistent: true });
    });
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('status only exposes the suffix, not the raw key', async () => {
  const dir = tempDir();
  try {
    await withHttpsGet({
      statusCode: 200,
      body: JSON.stringify({ data: { limit_remaining: 9 } }),
    }, async () => {
      const secret = 'sk-secret-9876';
      const store = new KeyStore(dir);
      await store.replace(secret);
      const status = store.status();
      assert.deepStrictEqual(status, { configured: true, suffix: '9876', remaining: 9, persistent: true });
      assert.equal(JSON.stringify(status).includes(secret), false);
      assert.deepStrictEqual(Object.keys(status).sort(), ['configured', 'persistent', 'remaining', 'suffix']);
    });
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('upstream errors never echo the raw key', async () => {
  const dir = tempDir();
  try {
    await withHttpsGet({
      statusCode: 500,
      body: JSON.stringify({ error: 'upstream failure for sk-leak-4444' }),
    }, async () => {
      const store = new KeyStore(dir);
      const result = await store.replace('sk-leak-4444');
      assert.equal(result.error, 'OpenRouter could not check the key just now. Please try again.');
      assert.equal(result.error.includes('sk-leak-4444'), false);
      assert.equal(fs.existsSync(path.join(dir, 'openrouter-key.json')), false);
    });
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

(async () => {
  for (const [name, fn] of tests) {
    await fn();
    console.log('ok -', name);
  }
  console.log(`\n${tests.length} openrouter tests passed`);
})().catch(err => {
  console.error(err);
  process.exitCode = 1;
});
