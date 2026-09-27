const path = require('path');
const fs = require('fs');
const http = require('http');
const https = require('https');
const { StringDecoder } = require('string_decoder');
const { URL } = require('url');

const MAX_FILE_BYTES = 10 * 1024 * 1024;
const JSON_BYTES = 1024 * 1024;

let installed = false;
let current = null;

function isLoopbackHttp(url) {
  if (url.protocol !== 'http:') return false;
  const host = String(url.hostname || '').toLowerCase();
  return host === '127.0.0.1' || host === '[::1]';
}

function validateConnection(connection) {
  if (!connection || typeof connection.url !== 'string' || typeof connection.token !== 'string') {
    return { error: 'Remote connection is missing.' };
  }
  let url;
  try {
    url = new URL(connection.url);
  } catch {
    return { error: 'Remote connection URL is invalid.' };
  }
  if (url.username || url.password || url.hash || url.search || connection.token.length < 40 || (url.protocol !== 'https:' && !isLoopbackHttp(url))) {
    return { error: 'Remote connection must use https, except for literal loopback http.' };
  }
  return { url, token: connection.token };
}

function joinUrl(baseUrl, endpoint) {
  const u = new URL(baseUrl.href);
  const raw = String(endpoint || '');
  const q = raw.indexOf('?');
  const clean = (q === -1 ? raw : raw.slice(0, q)).replace(/^\/+/, '');
  const search = q === -1 ? '' : raw.slice(q + 1);
  const basePath = u.pathname.endsWith('/') ? u.pathname : `${u.pathname}/`;
  u.pathname = `${basePath}${clean}`.replace(/\/{2,}/g, '/');
  if (!u.pathname.startsWith('/')) u.pathname = `/${u.pathname}`;
  u.search = search ? `?${search}` : '';
  return u;
}

function parseBodyText(buffer) {
  const text = buffer.toString('utf8').trim();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { error: text };
  }
}

function normalizeBody(body, headers) {
  if (body == null) return null;
  if (Buffer.isBuffer(body)) return body;
  if (body instanceof Uint8Array) return Buffer.from(body);
  if (typeof body === 'string') return Buffer.from(body);
  if (typeof body === 'object') {
    if (!headers['Content-Type'] && !headers['content-type']) {
      headers['Content-Type'] = 'application/json';
    }
    return Buffer.from(JSON.stringify(body));
  }
  throw new Error('Unsupported request body.');
}

function performRequest(method, endpoint, { body, headers = {}, maxBytes = JSON_BYTES, timeoutMs = 30000 } = {}) {
  if (!current || !current.connection) return Promise.reject(new Error('Remote connection is not ready.'));
  const url = joinUrl(current.connection.url, endpoint);
  const payloadHeaders = { Authorization: `Bearer ${current.connection.token}`, ...headers };
  const payload = normalizeBody(body, payloadHeaders);
  if (payload != null && payloadHeaders['Content-Length'] == null && payloadHeaders['content-length'] == null) {
    payloadHeaders['Content-Length'] = Buffer.byteLength(payload);
  }
  const transport = url.protocol === 'https:' ? https : http;
  return new Promise((resolve, reject) => {
    const req = transport.request({
      protocol: url.protocol,
      hostname: url.hostname.replace(/^\[|\]$/g, ''),
      port: url.port || undefined,
      method,
      path: `${url.pathname}${url.search}`,
      headers: payloadHeaders,
    }, res => {
      const statusCode = res.statusCode || 0;
      if (statusCode >= 300 && statusCode < 400) {
        const where = res.headers.location ? ` (${res.headers.location})` : '';
        res.resume();
        reject(new Error(`redirects are not allowed${where}`));
        return;
      }
      const chunks = [];
      let size = 0;
      res.on('data', chunk => {
        size += chunk.length;
        if (size > maxBytes) {
          req.destroy(new Error(`response exceeded ${Math.round(maxBytes / 1024 / 1024)} MiB`));
          return;
        }
        chunks.push(Buffer.from(chunk));
      });
      res.on('end', () => resolve({
        statusCode,
        headers: res.headers,
        buffer: Buffer.concat(chunks),
      }));
      res.on('error', reject);
    });
    req.on('error', reject);
    if (timeoutMs > 0) {
      req.setTimeout(timeoutMs, () => req.destroy(new Error('request timed out')));
    }
    if (payload != null) req.write(payload);
    req.end();
  });
}

async function requestJson(method, endpoint, options = {}) {
  const result = await performRequest(method, endpoint, { ...options, maxBytes: options.maxBytes || JSON_BYTES });
  if (result.statusCode < 200 || result.statusCode >= 300) {
    const parsed = parseBodyText(result.buffer);
    throw new Error(parsed.error || `HTTP ${result.statusCode}`);
  }
  return parseBodyText(result.buffer);
}

async function requestBytes(method, endpoint, options = {}) {
  const result = await performRequest(method, endpoint, { ...options, maxBytes: options.maxBytes || MAX_FILE_BYTES });
  if (result.statusCode < 200 || result.statusCode >= 300) {
    const parsed = parseBodyText(result.buffer);
    throw new Error(parsed.error || `HTTP ${result.statusCode}`);
  }
  return result.buffer;
}

function decorateStatus(status) {
  const connection = {
    live: !!current && !!current.stream && !current.streamClosing && !current.streamReconnecting,
    reconnecting: !!current && (!!current.streamReconnecting || !!current.streamClosing),
    gap: !!current && !!current.gapSeen,
    error: current && current.streamError ? current.streamError : null,
    after: current ? current.lastSeq : 0,
  };
  return { ...status, connection };
}

function send(channel, payload) {
  if (!current || !current.window || current.window.isDestroyed()) return;
  current.window.webContents.send(channel, payload);
}

async function refreshStatus() {
  if (!current) return null;
  try {
    const status = await requestJson('GET', '/status');
    if (current.status?.instance && status.instance && current.status.instance !== status.instance) {
      stopStream(false);
      current.streamClosing = false;
      current.lastSeq = 0;
      current.gapSeen = false;
      send('remote-event', {kind:'reset', data:'The server restarted. Files, conversation and login were erased.'});
      connectEvents().catch(() => {});
    }
    current.status = status;
    send('remote-status', decorateStatus(status));
    return status;
  } catch (error) {
    const payload = { error: error.message || String(error), connection: { live: false, reconnecting: false, gap: !!current.gapSeen, error: error.message || String(error), after: current.lastSeq || 0 } };
    send('remote-status', payload);
    send('remote-error', payload.error);
    return payload;
  }
}

function parseEventBlock(block) {
  const lines = block.split('\n');
  let id = null;
  let event = 'message';
  const data = [];
  for (const line of lines) {
    if (!line || line.startsWith(':')) continue;
    const idx = line.indexOf(':');
    const field = idx === -1 ? line : line.slice(0, idx);
    const value = idx === -1 ? '' : line.slice(idx + 1).replace(/^\s/, '');
    if (field === 'id') id = value;
    else if (field === 'event') event = value;
    else if (field === 'data') data.push(value);
  }
  return { id, event, data: data.join('\n') };
}

async function connectEvents() {
  if (!current || current.quitting || current.stream || current.streamClosing) return;
  const after = Number(current.lastSeq || 0);
  const url = joinUrl(current.connection.url, `/events?after=${encodeURIComponent(after)}`);
  const transport = url.protocol === 'https:' ? https : http;
  current.streamReconnecting = !!current.lastSeq;
  current.streamClosing = false;
  send('remote-status', decorateStatus(current.status || {}));
  const req = transport.request({
    protocol: url.protocol,
    hostname: url.hostname.replace(/^\[|\]$/g, ''),
    port: url.port || undefined,
    method: 'GET',
    path: `${url.pathname}${url.search}`,
    headers: {
      Authorization: `Bearer ${current.connection.token}`,
      Accept: 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    },
  }, res => {
    const statusCode = res.statusCode || 0;
    if (statusCode >= 300 && statusCode < 400) {
      res.resume();
      onStreamFailure(new Error('redirects are not allowed'));
      return;
    }
    if (statusCode !== 200) {
      const chunks = [];
      res.on('data', chunk => {
        if (chunks.reduce((n, b) => n + b.length, 0) + chunk.length > JSON_BYTES) return req.destroy(new Error('Error response exceeds limit'));
        chunks.push(Buffer.from(chunk));
      });
      res.on('end', () => {
        const parsed = parseBodyText(Buffer.concat(chunks));
        onStreamFailure(new Error(parsed.error || `HTTP ${statusCode}`));
      });
      return;
    }
    current.stream = {
      request: req,
      closed: false,
      reconnecting: false,
      error: null,
    };
    current.streamError = null;
    current.streamReconnecting = false;
    send('remote-status', decorateStatus(current.status || {}));
    const decoder = new StringDecoder('utf8');
    let buffer = '';
    let block = [];
    const flushBlock = () => {
      if (!block.length) return;
      const event = parseEventBlock(block.join('\n'));
      block = [];
      if (event.id != null) {
        const seq = Number(event.id);
        if (Number.isFinite(seq)) {
          if (seq <= current.lastSeq) return;
          current.lastSeq = seq;
        }
      }
      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch {
        send('remote-error', 'Received malformed event data from the server.');
        return;
      }
      if (!payload || typeof payload.kind !== 'string') return;
      if (payload.kind === 'gap') {
        current.gapSeen = true;
        send('remote-event', { kind: 'gap', data: payload.data });
        send('remote-status', decorateStatus(current.status || {}));
        return;
      }
      send('remote-event', { ...payload, seq: current.lastSeq });
      if (payload.kind === 'state' || payload.kind === 'login' || payload.kind === 'exit') {
        refreshStatus().catch(() => {});
      }

    };
    res.on('data', chunk => {
      buffer += decoder.write(chunk);
      if (buffer.length + block.join('').length > 262144) return req.destroy(new Error('Event exceeds limit'));
      let index;
      while ((index = buffer.indexOf('\n')) !== -1) {
        let line = buffer.slice(0, index);
        buffer = buffer.slice(index + 1);
        if (line.endsWith('\r')) line = line.slice(0, -1);
        if (line === '') {
          flushBlock();
        } else {
          block.push(line);
        }
      }
    });
    res.on('end', () => {
      buffer += decoder.end();
      if (buffer) {
        const lines = buffer.split('\n');
        for (const line of lines) {
          if (line === '') flushBlock();
          else block.push(line.replace(/\r$/, ''));
        }
      }
      if (block.length) flushBlock();
      onStreamFailure(new Error('event stream ended'));
    });
    res.on('error', onStreamFailure);
  });
  req.on('error', onStreamFailure);
  req.setTimeout(30000, () => req.destroy(new Error('Event stream timed out')));
  req.end();
  current.stream = {
    request: req,
    closed: false,
    reconnecting: false,
    error: null,
  };

  let failed = false;
  function onStreamFailure(error) {
    if (failed || (current?.stream && current.stream.request !== req)) return;
    failed = true;
    if (!current || current.quitting || current.permanentClose) return;
    req.destroy();
    if (current.streamClosing) {
      current.streamClosing = false;
      if (!current.quitting && !current.permanentClose) {
        current.stream = null;
        current.streamReconnecting = true;
        send('remote-status', decorateStatus(current.status || {}));
        scheduleReconnect();
      }
      return;
    }
    current.stream = null;
    current.streamReconnecting = true;
    current.streamError = error.message || String(error);
    send('remote-error', current.streamError);
    send('remote-status', decorateStatus(current.status || {}));
    if (!current.permanentClose) scheduleReconnect();
  }
}

function scheduleReconnect() {
  if (!current || current.quitting || current.permanentClose) return;
  if (current.reconnectTimer) return;
  current.reconnectTimer = setTimeout(() => {
    if (!current || current.quitting || current.permanentClose) return;
    current.reconnectTimer = null;
    connectEvents().catch(error => {
      send('remote-error', error.message || String(error));
      scheduleReconnect();
    });
  }, 1000);
}

function stopStream(permanent = false) {
  if (!current) return;
  if (permanent) current.permanentClose = true;
  if (current.reconnectTimer) {
    clearTimeout(current.reconnectTimer);
    current.reconnectTimer = null;
  }
  current.streamReconnecting = false;
  if (current.stream && current.stream.request) {
    current.streamClosing = true;
    try { current.stream.request.destroy(); } catch {}
  }
  current.stream = null;
  current.streamError = null;
  if (permanent) current.streamClosing = false;
}

async function pickFileForUpload() {
  if (!current || !current.window || current.window.isDestroyed()) return { canceled: true };
  const result = await current.dialog.showOpenDialog(current.window, {
    title: 'Attach a copy',
    properties: ['openFile'],
  });
  if (result.canceled || !result.filePaths || !result.filePaths[0]) return { canceled: true };
  const filePath = result.filePaths[0];
  const stat = await fs.promises.stat(filePath);
  if (!stat.isFile() || stat.size > MAX_FILE_BYTES) {
    return { error: `The file is too large. The limit is ${Math.round(MAX_FILE_BYTES / 1024 / 1024)} MiB.` };
  }
  const bytes = await fs.promises.readFile(filePath);
  if (bytes.length > MAX_FILE_BYTES) return {error:'File grew beyond 10 MiB'};
  const name = path.basename(filePath);
  const reply = await requestJson('POST', `/files?name=${encodeURIComponent(name)}`, {
    body: bytes,
    headers: { 'Content-Type': 'application/octet-stream' },
    maxBytes: JSON_BYTES,
  });
  if (reply && reply.error) return { error: reply.error };
  await refreshStatus().catch(() => {});
  return { ok: true, name, size: stat.size };
}

async function saveRemoteFile(name) {
  if (!current || !current.window || current.window.isDestroyed()) return { canceled: true };
  const cleanName = String(name || '').trim();
  if (!cleanName) return { error: 'No file name was provided.' };
  const result = await current.dialog.showSaveDialog(current.window, {
    title: 'Save result file',
    defaultPath: path.basename(cleanName),
  });
  if (result.canceled || !result.filePath) return { canceled: true };
  const bytes = await requestBytes('GET', `/file?name=${encodeURIComponent(cleanName)}`, { maxBytes: MAX_FILE_BYTES });
  await fs.promises.writeFile(result.filePath, bytes);
  return { ok: true, path: result.filePath, name: cleanName, size: bytes.length };
}

function registerIpc({ app, BrowserWindow, ipcMain, dialog, shell }) {
  if (installed) return;
  installed = true;

  ipcMain.handle('remote-status', async () => {
    if (!current || !current.connection) return { error: 'Remote connection is not ready.' };
    if (!current.status?.ended) await refreshStatus().catch(() => {});
    return current.status ? decorateStatus(current.status) : { error: 'Remote status is unavailable.' };
  });
  ipcMain.handle('remote-login', async () => {
    try {
      const reply = await requestJson('POST', '/login', { maxBytes: JSON_BYTES });
      await refreshStatus().catch(() => {});
      return reply;
    } catch (error) {
      return { error: error.message || String(error) };
    }
  });
  ipcMain.handle('remote-start', async (_event, opts = {}) => {
    const cols = Number(opts.cols || 0);
    const rows = Number(opts.rows || 0);
    try {
      const reply = await requestJson('POST', '/start', {
        body: { cols, rows, resume: !!opts.resume },
        maxBytes: JSON_BYTES,
      });
      await refreshStatus().catch(() => {});
      if (!current.permanentClose) connectEvents().catch(() => {});
      return reply;
    } catch (error) {
      return { error: error.message || String(error) };
    }
  });
  let inputQueue = Promise.resolve();
  ipcMain.on('remote-input', (_event, data) => {
    inputQueue = inputQueue.then(async () => {
    try {
      await requestJson('POST', '/input', {
        body: { data: String(data || '') },
        maxBytes: JSON_BYTES,
      });
    } catch (error) {
      send('remote-error', error.message || String(error));
    }
    });
  });
  ipcMain.on('remote-resize', async (_event, size = {}) => {
    const cols = Number(size.cols || 0);
    const rows = Number(size.rows || 0);
    if (!cols || !rows) return;
    try {
      await requestJson('POST', '/resize', {
        body: { cols, rows },
        maxBytes: JSON_BYTES,
      });
    } catch (error) {
      send('remote-error', error.message || String(error));
    }
  });
  ipcMain.handle('remote-interrupt', async () => {
    try {
      const reply = await requestJson('POST', '/interrupt', { maxBytes: JSON_BYTES });
      await refreshStatus().catch(() => {});
      return reply;
    } catch (error) {
      return { error: error.message || String(error) };
    }
  });
  ipcMain.handle('remote-stop', async () => {
    try {
      const reply = await requestJson('POST', '/stop', { maxBytes: JSON_BYTES });
      await refreshStatus().catch(() => {});
      return reply;
    } catch (error) {
      return { error: error.message || String(error) };
    }
  });
  ipcMain.handle('remote-end', async () => {
    try {
      const reply = await requestJson('POST', '/end', { maxBytes: JSON_BYTES });
      stopStream(true);
      current.status = {...current.status, running:false, loggedIn:false, ended:true};
      send('remote-status', decorateStatus(current.status));
      return reply;
    } catch (error) {
      return { error: error.message || String(error) };
    }
  });
  ipcMain.handle('remote-files', async () => {
    try {
      return await requestJson('GET', '/files', { maxBytes: JSON_BYTES });
    } catch (error) {
      return { error: error.message || String(error) };
    }
  });
  ipcMain.handle('remote-attach', async () => {
    try {
      return await pickFileForUpload();
    } catch (error) {
      return { error: error.message || String(error) };
    }
  });
  ipcMain.handle('remote-download', async (_event, name) => {
    try {
      return await saveRemoteFile(name);
    } catch (error) {
      return { error: error.message || String(error) };
    }
  });
  ipcMain.handle('remote-open-external', async (_event, url) => {
    const target = String(url || '').trim();
    let parsed;
    try {
      parsed = new URL(target);
    } catch {
      return { error: 'Only the device login page may be opened.' };
    }
    const allowed = parsed.protocol === 'https:' &&
      parsed.origin === 'https://auth.openai.com' &&
      /^\/codex\/device(?:[/?#]|$)/.test(parsed.pathname);
    if (!allowed) return { error: 'Only the device login page may be opened.' };
    await shell.openExternal(parsed.toString());
    return { ok: true };
  });
}

async function install({ app, BrowserWindow, ipcMain, dialog, shell }, connection) {
  const validated = validateConnection(connection);
  if (validated.error) {
    if (dialog && dialog.showErrorBox) dialog.showErrorBox('Remote io', validated.error);
    return { error: validated.error };
  }
  current = current || {};
  current.connection = validated;
  current.dialog = dialog;
  current.shell = shell;
  current.app = app;
  current.BrowserWindow = BrowserWindow;
  current.ipcMain = ipcMain;
  current.status = null;
  current.lastSeq = current.lastSeq || 0;
  current.gapSeen = false;
  current.permanentClose = false;
  current.quitting = false;
  current.stream = null;
  current.streamError = null;
  current.streamClosing = false;
  current.streamReconnecting = false;
  current.reconnectTimer = null;
  if (current.window && !current.window.isDestroyed()) {
    current.window.focus();
    await refreshStatus().catch(() => {});
    if (!current.permanentClose && !current.stream && !current.reconnectTimer) {
      connectEvents().catch(error => send('remote-error', error.message || String(error)));
    }
    return current.window;
  }

  registerIpc({ app, BrowserWindow, ipcMain, dialog, shell });

  const win = new BrowserWindow({
    width: 1280,
    height: 900,
    title: 'Remote Linux experiment',
    backgroundColor: '#1a1d21',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  current.window = win;
  win.webContents.on('will-navigate', event => event.preventDefault());
  win.setMenuBarVisibility(false);
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  win.on('closed', () => {
    stopStream(true);
    current.window = null;
  });
  win.on('close', () => {
    // Keep the remote session alive. Only the local SSE bridge is shut down.
    stopStream(true);
  });
  if (!current.beforeQuitHookInstalled) {
    current.beforeQuitHookInstalled = true;
    app.on('before-quit', () => {
      current.quitting = true;
      stopStream(true);
    });
  }
  await win.loadFile(app.isPackaged ? path.join(process.resourcesPath, 'io', 'ui', 'remote.html') : path.join(__dirname, '..', 'ui', 'remote.html'));
  win.show();
  await refreshStatus().catch(() => {});
  if (!current.permanentClose) connectEvents().catch(error => send('remote-error', error.message || String(error)));
  return win;
}

module.exports = { install, validateConnection, parseEventBlock };
