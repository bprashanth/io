const {test} = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const net = require('node:net');
const {createBrowserLogin, validateAuthUrl} = require('../../remote/browser-login');

const AUTH_REDIRECT = 'http://localhost:1455/auth/callback';
const SUCCESS_TEXT = 'Signed in to io. You can close this tab and return to io.';
const VALID_STATE = 'state-1234567890abcdef';
const VALID_CHALLENGE = 'challenge-1234567890abcdef';

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function waitFor(fn, timeoutMs = 1500, intervalMs = 20) {
  const deadline = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < deadline) {
    try {
      if (await fn()) return;
    } catch (error) {
      lastError = error;
    }
    await delay(intervalMs);
  }
  throw lastError || new Error('condition timed out');
}

function hostHeader(hostname, port) {
  return hostname.includes(':') ? `[${hostname}]:${port}` : `${hostname}:${port}`;
}

async function freePort() {
  const server = net.createServer();
  try {
    const port = await new Promise((resolve, reject) => {
      server.once('error', reject);
      server.listen({host: '127.0.0.1', port: 0}, () => {
        resolve(server.address().port);
      });
    });
    return port;
  } finally {
    await new Promise(resolve => server.close(resolve));
  }
}

function buildAuthUrl({
  state = VALID_STATE,
  redirectUri = AUTH_REDIRECT,
  challenge = VALID_CHALLENGE,
  extra = [],
} = {}) {
  const url = new URL('https://auth.openai.com/oauth/authorize');
  url.searchParams.set('redirect_uri', redirectUri);
  url.searchParams.set('response_type', 'code');
  url.searchParams.set('code_challenge_method', 'S256');
  url.searchParams.set('code_challenge', challenge);
  url.searchParams.set('state', state);
  for (const [key, value] of extra) {
    url.searchParams.append(key, value);
  }
  return url.href;
}

function buildCallbackPath({
  code = 'code +/=%',
  state = VALID_STATE,
  extra = [],
} = {}) {
  const params = new URLSearchParams();
  params.set('code', code);
  params.set('state', state);
  for (const [key, value] of extra) {
    params.append(key, value);
  }
  return `/auth/callback?${params.toString()}`;
}

function requestOutcome({
  hostname = '127.0.0.1',
  port,
  path,
  method = 'GET',
  headers = {},
} = {}) {
  return new Promise(resolve => {
    const req = http.request({
      hostname,
      port,
      path,
      method,
      agent: false,
      headers: {
        ...headers,
        Host: headers.Host || hostHeader(hostname, port),
      },
    }, res => {
      const chunks = [];
      res.on('data', chunk => chunks.push(chunk));
      res.on('end', () => {
        resolve({
          kind: 'response',
          status: res.statusCode,
          headers: res.headers,
          body: Buffer.concat(chunks).toString('utf8'),
        });
      });
    });
    req.setTimeout(1000, () => req.destroy(new Error('request timeout')));
    req.on('error', error => resolve({kind: 'error', error}));
    req.end();
  });
}

function isLoopbackCloseError(error) {
  return error && ['ECONNREFUSED', 'ECONNRESET', 'EPIPE', 'ENETUNREACH', 'EADDRNOTAVAIL', 'EHOSTUNREACH'].includes(error.code);
}

async function startLogin(options = {}) {
  const forwardCalls = [];
  const timeoutCalls = [];
  const completeCalls = [];
  const login = await createBrowserLogin({
    ...options,
    forward: async callback => {
      forwardCalls.push(callback);
    },
    onTimeout: () => {
      timeoutCalls.push(true);
      if (typeof options.onTimeout === 'function') options.onTimeout();
    },
    onComplete: error => {
      completeCalls.push(error);
      if (typeof options.onComplete === 'function') options.onComplete(error);
    },
  });
  return {login, forwardCalls, timeoutCalls, completeCalls};
}

test('validateAuthUrl accepts the expected OAuth shape and rejects tampering', {concurrency: false}, () => {
  const valid = buildAuthUrl();
  assert.equal(validateAuthUrl(valid).href, valid);

  for (const bad of [
    'https://auth.openai.com.evil.test/oauth/authorize?redirect_uri=http://localhost:1455/auth/callback&response_type=code&code_challenge_method=S256&code_challenge=abc&state=abcdefghijklmnop',
    'https://user:pass@auth.openai.com/oauth/authorize?redirect_uri=http://localhost:1455/auth/callback&response_type=code&code_challenge_method=S256&code_challenge=abc&state=abcdefghijklmnop',
    'https://auth.openai.com/oauth/authorize/evil?redirect_uri=http://localhost:1455/auth/callback&response_type=code&code_challenge_method=S256&code_challenge=abc&state=abcdefghijklmnop',
    'https://auth.openai.com/oauth/authorize?redirect_uri=http://localhost:1456/auth/callback&response_type=code&code_challenge_method=S256&code_challenge=abc&state=abcdefghijklmnop',
    'https://auth.openai.com/oauth/authorize?redirect_uri=http://localhost:1455/auth/callback&response_type=token&code_challenge_method=S256&code_challenge=abc&state=abcdefghijklmnop',
    'https://auth.openai.com/oauth/authorize?redirect_uri=http://localhost:1455/auth/callback&response_type=code&code_challenge_method=plain&code_challenge=abc&state=abcdefghijklmnop',
    'https://auth.openai.com/oauth/authorize?redirect_uri=http://localhost:1455/auth/callback&response_type=code&code_challenge_method=S256&state=abcdefghijklmnop',
    'https://auth.openai.com/oauth/authorize?redirect_uri=http://localhost:1455/auth/callback&response_type=code&code_challenge_method=S256&code_challenge=abc&state=short',
    'https://auth.openai.com/oauth/authorize?redirect_uri=http://localhost:1455/auth/callback&response_type=code&code_challenge_method=S256&code_challenge=abc&state=abcdefghijklmnop#fragment',
  ]) {
    assert.throws(() => validateAuthUrl(bad), /unsupported browser sign-in URL/);
  }
});

test('browser login forwards the exact callback once and closes after success', {concurrency: false}, async () => {
  const port = await freePort();
  const code = 'code +/=%';
  const callbackPath = buildCallbackPath({code});
  const authUrl = buildAuthUrl();
  const {login, forwardCalls, completeCalls} = await startLogin({port});
  try {
    assert.equal(login.activate(authUrl), authUrl);
    assert.equal(login.permits(authUrl), true);

    const outcome = await requestOutcome({
      hostname: '127.0.0.1',
      port,
      path: callbackPath,
    });
    if (outcome.kind === 'error') throw outcome.error;
    assert.equal(outcome.status, 200);
    assert.equal(outcome.body, SUCCESS_TEXT);
    assert.equal(forwardCalls.length, 1);
    assert.equal(forwardCalls[0], callbackPath);
    assert.equal(completeCalls.length, 1);
    assert.equal(completeCalls[0], undefined);
    assert.ok(!outcome.body.includes(code));

    assert.throws(() => login.activate(authUrl), /Sign-in has expired/);
    assert.equal(login.permits(authUrl), false);

    const second = await requestOutcome({
      hostname: '127.0.0.1',
      port,
      path: callbackPath,
    });
    if (second.kind === 'response') {
      assert.notEqual(second.status, 200);
    } else {
      assert.ok(isLoopbackCloseError(second.error));
    }
    assert.equal(forwardCalls.length, 1);
  } finally {
    login.close();
  }
});

test('browser login accepts localhost callbacks over IPv4 and IPv6 where available', {concurrency: false}, async () => {
  for (const hostname of ['127.0.0.1', '::1']) {
    const port = await freePort();
    const code = `loopback-${hostname.replace(/[^a-z0-9]/gi, '')}-code`;
    const callbackPath = buildCallbackPath({code});
    const authUrl = buildAuthUrl();
    const {login, forwardCalls} = await startLogin({port});
    try {
      login.activate(authUrl);
      const outcome = await requestOutcome({
        hostname,
        port,
        path: callbackPath,
      });
      if (hostname === '::1' && outcome.kind === 'error' && isLoopbackCloseError(outcome.error)) {
        continue;
      }
      if (outcome.kind === 'error') throw outcome.error;
      assert.equal(outcome.status, 200);
      assert.equal(outcome.body, SUCCESS_TEXT);
      assert.equal(forwardCalls.length, 1);
      assert.equal(forwardCalls[0], callbackPath);
    } finally {
      login.close();
    }
  }
});

test('browser login rejects bad callback requests without forwarding', {concurrency: false}, async () => {
  const port = await freePort();
  const {login, forwardCalls} = await startLogin({port});
  const authUrl = buildAuthUrl();
  try {
    login.activate(authUrl);

    const cases = [
      {
        name: 'wrong state',
        request: {
          hostname: '127.0.0.1',
          port,
          path: buildCallbackPath({state: 'wrong-state'}),
        },
        status: 403,
      },
      {
        name: 'wrong method',
        request: {
          hostname: '127.0.0.1',
          port,
          path: buildCallbackPath(),
          method: 'POST',
        },
        status: 400,
      },
      {
        name: 'wrong host',
        request: {
          hostname: '127.0.0.1',
          port,
          path: buildCallbackPath(),
          headers: {Host: `example.test:${port}`},
        },
        status: 400,
      },
      {
        name: 'wrong origin',
        request: {
          hostname: '127.0.0.1',
          port,
          path: buildCallbackPath(),
          headers: {Origin: 'https://example.test'},
        },
        status: 400,
      },
      {
        name: 'wrong path',
        request: {
          hostname: '127.0.0.1',
          port,
          path: `/auth/other?code=ok&state=${encodeURIComponent(VALID_STATE)}`,
        },
        status: 404,
      },
      {
        name: 'duplicate query',
        request: {
          hostname: '127.0.0.1',
          port,
          path: `/auth/callback?code=one&code=two&state=${encodeURIComponent(VALID_STATE)}`,
        },
        status: 400,
      },
      {
        name: 'mismatched issuer',
        request: {
          hostname: '127.0.0.1',
          port,
          path: buildCallbackPath({
            extra: [['iss', 'https://evil.example']],
          }),
        },
        status: 400,
      },
    ];

    for (const testCase of cases) {
      const outcome = await requestOutcome(testCase.request);
      assert.equal(outcome.kind, 'response', testCase.name);
      assert.equal(outcome.status, testCase.status, testCase.name);
    }
    assert.equal(forwardCalls.length, 0);
  } finally {
    login.close();
  }
});

test('browser login manual close and TTL expiry stop the listener', {concurrency: false}, async () => {
  const manualPort = await freePort();
  const manual = await startLogin({port: manualPort});
  const authUrl = buildAuthUrl();
  try {
    manual.login.activate(authUrl);
    manual.login.close();
    assert.throws(() => manual.login.activate(authUrl), /Sign-in has expired/);

    const manualOutcome = await requestOutcome({
      hostname: '127.0.0.1',
      port: manualPort,
      path: buildCallbackPath(),
    });
    if (manualOutcome.kind === 'response') {
      assert.equal(manualOutcome.status, 403);
    } else {
      assert.ok(isLoopbackCloseError(manualOutcome.error));
    }
    assert.equal(manual.forwardCalls.length, 0);
  } finally {
    manual.login.close();
  }

  const ttlPort = await freePort();
  let timedOut = 0;
  const ttl = await startLogin({
    port: ttlPort,
    ttl: 30,
    onTimeout: () => {
      timedOut += 1;
    },
  });
  try {
    ttl.login.activate(authUrl);
    await waitFor(() => timedOut === 1);
    assert.equal(ttl.timeoutCalls.length, 1);
    assert.throws(() => ttl.login.activate(authUrl), /Sign-in has expired/);

    const ttlOutcome = await requestOutcome({
      hostname: '127.0.0.1',
      port: ttlPort,
      path: buildCallbackPath(),
    });
    if (ttlOutcome.kind === 'response') {
      assert.equal(ttlOutcome.status, 403);
    } else {
      assert.ok(isLoopbackCloseError(ttlOutcome.error));
    }
    assert.equal(ttl.forwardCalls.length, 0);
  } finally {
    ttl.login.close();
  }
});

test('browser login reports a clear error when the port is busy', {concurrency: false}, async () => {
  const busyServer = net.createServer();
  const port = await new Promise((resolve, reject) => {
    busyServer.once('error', reject);
    busyServer.listen({host: '127.0.0.1', port: 0}, () => {
      resolve(busyServer.address().port);
    });
  });
  try {
    await assert.rejects(
      () => createBrowserLogin({port}),
      /Browser sign-in needs local port 1455/,
    );
  } finally {
    await new Promise(resolve => busyServer.close(resolve));
  }
});
