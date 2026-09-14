// The bundled Codex: where its binary is, where its state lives, how it is launched.
//
// Every Codex process io starts - login, status, the interactive session - gets the same
// three things: the binary io ships (never a system `codex`), an io-owned CODEX_HOME (never
// ~/.codex), and a config.toml that io rewrites on every launch so the model traffic can only
// go to io's privacy proxy. That is the whole isolation story, and it is deliberately
// boring: no fork of Codex, no patched binary, just paths and a config file.
//
// Nothing in here reads auth.json. Login state comes from `codex login status`, which is
// Codex's own supported answer and never prints a token.

const { spawn, spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

let pty = null;
try { pty = require('node-pty'); } catch (e) { pty = null; }

const PINS = JSON.parse(fs.readFileSync(path.join(__dirname, 'codex-pins.json'), 'utf8'));

// One place decides which binary runs. Dev checkout: codex-bin/<plat>-<arch>/codex, put
// there by `node fetch-codex.js`. Packaged: resources/codex/<plat>-<arch>/codex.
function bundledCodexPath(opts = {}) {
  const key = `${process.platform}-${process.arch}`;
  const exe = process.platform === 'win32' ? 'codex.exe' : 'codex';
  const dir = opts.packaged
    ? path.join(opts.resourcesPath || process.resourcesPath, 'codex', key)
    : path.join(__dirname, 'codex-bin', key);
  return { key, path: path.join(dir, exe), pinned: PINS.targets[key] || null, version: PINS.version };
}

function codexHome(dataDir) {
  return path.join(dataDir, 'codex', 'home');
}

// The config Codex reads. Rewritten every launch: a stale port from a previous run would
// send Codex to a socket nobody is listening on (which fails closed, but confusingly).
//
//   openai_base_url   the built-in openai provider's base URL. This is the supported knob;
//                     a [model_providers.openai] table is ignored by Codex 0.154
//                     (merge_configured_model_providers keeps the built-in).
//   chatgpt_base_url  rate limits, account checks, plugins. No workspace content, but
//                     routed through the proxy too so one log shows everything.
//   enable_request_compression = false   Codex would otherwise zstd the body, which the
//                     proxy cannot read and therefore refuses.
//   check_for_update_on_startup = false  io pins its own Codex.
function writeConfig(home, proxyPort, extra = {}) {
  fs.mkdirSync(home, { recursive: true });
  // TOML: every top-level key must come before the first table header, or it silently
  // becomes a key of that table.
  const top = [
    '# Written by io on every launch. Edits here do not survive; io owns this file.',
    `openai_base_url = "http://127.0.0.1:${proxyPort}/backend-api/codex"`,
    `chatgpt_base_url = "http://127.0.0.1:${proxyPort}/backend-api/"`,
    'check_for_update_on_startup = false',
    'model_reasoning_effort = "medium"',
  ];
  const tables = [];
  if (extra.model) top.push(`model = "${extra.model}"`);
  if (extra.noSandbox) {
    // Development machines whose kernel refuses bwrap (the DGX). Never set for a user.
    top.push('sandbox_mode = "danger-full-access"');
  }
  if (extra.devProvider) {
    // Development only: a Responses-API server behind the proxy's /dev/v1 prefix, with an
    // API key in IO_DEV_KEY, so the interactive session can be tested without a ChatGPT
    // login. Same proxy, same transforms, different upstream. Never set for a user.
    top.push('model_provider = "io-dev"');
    tables.push('[model_providers.io-dev]', 'name = "io-dev"',
      `base_url = "http://127.0.0.1:${proxyPort}/dev/v1"`, 'wire_api = "responses"', 'env_key = "IO_DEV_KEY"',
      'supports_websockets = false', '');
  }
  if (extra.trust) {
    // The sheltered folder was chosen and its policy approved in io; Codex's own "do you
    // trust this folder" question would be the same question asked twice.
    tables.push(`[projects."${String(extra.trust).replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"]`, 'trust_level = "trusted"', '');
  }
  // Traffic that is not the model: switched off, and refused by the proxy anyway.
  //   apps / plugins   OpenAI-hosted MCP and plugin catalogues (POST backend-api/ps/mcp,
  //                    GET backend-api/ps/plugins/...) - tool arguments could flow there.
  //   analytics        POST backend-api/codex/analytics-events/events.
  //   update check     GitHub/npm.
  tables.push('[analytics]', 'enabled = false', '',
    '[features]', 'enable_request_compression = false', 'apps = false', 'plugins = false',
    'remote_plugin = false', 'plugin_sharing = false', 'recommended_plugins = false', 'image_generation = false', '');
  fs.writeFileSync(path.join(home, 'config.toml'), top.concat(['']).concat(tables).join('\n'));
}

function baseEnv(home) {
  const env = { ...process.env, CODEX_HOME: home };
  // Codex would treat an OPENAI_API_KEY in the environment as a login. io's Codex logs
  // in with ChatGPT, or not at all.
  for (const k of Object.keys(env)) {
    if (k.startsWith('OPENAI_') || k === 'CODEX_API_KEY') delete env[k];
  }
  env.NO_COLOR = env.NO_COLOR || '';
  return env;
}

function loginStatus(bin, home) {
  // Codex refuses to run when CODEX_HOME does not exist; an empty home is the honest
  // "not logged in", so create it rather than report a configuration error.
  fs.mkdirSync(home, { recursive: true });
  const r = spawnSync(bin, ['login', 'status'], { env: baseEnv(home), encoding: 'utf8', timeout: 20000 });
  const text = `${r.stdout || ''}\n${r.stderr || ''}`;
  const line = (text.split('\n').map(s => s.trim()).find(s => /^(Logged in|Not logged in|Error)/.test(s)) || '').slice(0, 120);
  return { loggedIn: r.status === 0, line, method: /ChatGPT/.test(line) ? 'chatgpt' : (r.status === 0 ? 'other' : null) };
}

// `codex login` opens the browser itself and prints the URL on stderr in case it could not.
// `codex login --device-auth` prints a URL and a one-time code. Both write the tokens into
// this CODEX_HOME and nowhere else. The caller gets the lines as they arrive so the UI can
// show the link or the code; the credential never passes through here.
function startLogin(bin, home, mode, onLine, onExit) {
  const args = ['login'].concat(mode === 'device' ? ['--device-auth'] : []);
  const child = spawn(bin, args, { env: baseEnv(home), stdio: ['ignore', 'pipe', 'pipe'] });
  let buf = '';
  const feed = chunk => {
    buf += chunk.toString();
    let i;
    while ((i = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, i).replace(/\x1b\[[0-9;]*m/g, '').trim();
      buf = buf.slice(i + 1);
      if (line) onLine(line);
    }
  };
  child.stdout.on('data', feed);
  child.stderr.on('data', feed);
  child.on('exit', (code, sig) => { if (buf.trim()) onLine(buf.trim()); onExit(code, sig); });
  return child;
}

function logout(bin, home) {
  const r = spawnSync(bin, ['logout'], { env: baseEnv(home), encoding: 'utf8', timeout: 20000 });
  return { ok: r.status === 0, line: ((r.stderr || r.stdout || '').trim().split('\n')[0] || '').slice(0, 120) };
}

// The interactive session. A real PTY: Codex's TUI needs cursor movement, resize and
// raw keys, none of which survive a pipe.
function spawnSession({ bin, home, cwd, cols, rows, noAltScreen }) {
  if (!pty) throw new Error('node-pty is not available in this build');
  const args = [];
  if (noAltScreen) args.push('--no-alt-screen');
  return pty.spawn(bin, args, {
    name: 'xterm-256color',
    cols: cols || 100,
    rows: rows || 30,
    cwd,
    env: { ...baseEnv(home), TERM: 'xterm-256color', COLORTERM: 'truecolor', LANG: process.env.LANG || 'C.UTF-8' },
  });
}

function binaryInfo(bin) {
  try {
    const st = fs.statSync(bin);
    return { exists: true, size: st.size, executable: !!(st.mode & 0o111) };
  } catch { return { exists: false }; }
}

module.exports = { bundledCodexPath, codexHome, writeConfig, baseEnv, loginStatus, startLogin, logout, spawnSession, binaryInfo, hasPty: () => !!pty, PINS };
