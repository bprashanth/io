// Short-lived, loopback-only OAuth callback relay. Never logs codes or returns tokens.
const http = require('node:http');
const {timingSafeEqual} = require('node:crypto');

function validateAuthUrl(value) {
  const url = new URL(value);
  if ([...url.searchParams.keys()].some(k => url.searchParams.getAll(k).length !== 1)) throw new Error('Duplicate sign-in URL parameters.');
  if (url.origin !== 'https://auth.openai.com' || url.pathname !== '/oauth/authorize' ||
      url.username || url.password || url.hash ||
      url.searchParams.get('redirect_uri') !== 'http://localhost:1455/auth/callback' ||
      url.searchParams.get('response_type') !== 'code' ||
      url.searchParams.get('code_challenge_method') !== 'S256' ||
      !url.searchParams.get('code_challenge') || (url.searchParams.get('state') || '').length < 16) {
    throw new Error('The remote worker returned an unsupported browser sign-in URL.');
  }
  return url;
}

async function createBrowserLogin({forward, onComplete = () => {}, onTimeout = () => {}, port = 1455, ttl = 600000}) {
  let authUrl = null, consumed = false, closed = false, timer;
  const servers = [];
  function close() {
    closed = true; clearTimeout(timer); authUrl = null;
    for (const server of servers) server.close();
  }
  function reply(res, code, message) {
    res.writeHead(code, {'Content-Type':'text/plain; charset=utf-8', 'Cache-Control':'no-store',
      'Referrer-Policy':'no-referrer', 'Content-Security-Policy':"default-src 'none'; frame-ancestors 'none'", 'Connection':'close'});
    res.end(message);
  }
  async function handle(req, res) {
    if (req.method !== 'GET' || ![`localhost:${port}`, `127.0.0.1:${port}`, `[::1]:${port}`].includes(req.headers.host) || req.headers.origin) {
      return reply(res, 400, 'Invalid sign-in callback.');
    }
    let url;
    try { url = new URL(req.url, 'http://localhost'); } catch { return reply(res, 400, 'Invalid callback.'); }
    if (url.pathname !== '/auth/callback' || req.url.length > 16384) return reply(res, 404, 'Not found.');
    const state = url.searchParams.get('state') || '', expected = authUrl?.searchParams.get('state') || '';
    if (closed || consumed || !expected || url.searchParams.getAll('state').length !== 1 ||
        Buffer.byteLength(state) !== Buffer.byteLength(expected) || !timingSafeEqual(Buffer.from(state), Buffer.from(expected))) {
      return reply(res, 403, 'This sign-in request is no longer active or belongs to another session.');
    }
    const keys = [...url.searchParams.keys()];
    if (keys.some(k => !['code','state','error','error_description','scope','session_state','iss'].includes(k)) ||
        new Set(keys).size !== keys.length ||
        (url.searchParams.has('iss') && url.searchParams.get('iss') !== 'https://auth.openai.com') ||
        (url.searchParams.has('code') && url.searchParams.has('error')) || (!url.searchParams.get('code') && !url.searchParams.get('error'))) {
      return reply(res, 400, 'Invalid callback parameters.');
    }
    consumed = true;
    try {
      await forward(url.pathname + url.search);
      reply(res, 200, 'Signed in to io. You can close this tab and return to io.');
      onComplete();
    } catch {
      reply(res, 400, 'Sign-in did not complete. Return to io and try Sign in again.');
      onComplete(new Error('Browser sign-in did not complete. Please try again.'));
    } finally { close(); }
  }
  try {
    for (const host of ['127.0.0.1', '::1']) {
      const server = http.createServer((req,res) => {handle(req,res).catch(() => reply(res,500,'Sign-in failed.'));});
      server.requestTimeout = 10000; server.headersTimeout = 10000;
      servers.push(server);
      try {
        await new Promise((resolve,reject) => {server.once('error',reject);server.listen({port,host,ipv6Only:true},resolve);});
      } catch (error) {
        if (host === '::1' && ['EAFNOSUPPORT','EADDRNOTAVAIL'].includes(error.code)) continue;
        throw error;
      }
    }
  } catch (error) {
    close();
    if (error.code === 'EADDRINUSE') throw new Error('Browser sign-in needs local port 1455. Close another Codex sign-in window or use device code sign-in.');
    throw error;
  }
  timer = setTimeout(() => {close();onTimeout();},ttl); timer.unref();
  return {close, activate(value) {if(closed) throw new Error('Sign-in has expired.');authUrl = validateAuthUrl(value);return authUrl.href;},
    permits(value) {return !closed && authUrl?.href === value;}};
}
module.exports = {createBrowserLogin, validateAuthUrl};
