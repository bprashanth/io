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

// One place decides which binary runs. Dev checkout: codex-bin/<plat>-<arch>/bin/codex, put
// there by `node fetch-codex.js`. Packaged: resources/codex/<plat>-<arch>/bin/codex. The tree
// around it (bin/codex-code-mode-host, codex-path/rg, codex-resources/) is the release package
// and Codex finds those relative to its own executable, so the tree is copied whole.
function bundledCodexPath(opts = {}) {
  const key = `${process.platform}-${process.arch}`;
  const exe = process.platform === 'win32' ? 'codex.exe' : 'codex';
  const dir = opts.packaged
    ? path.join(opts.resourcesPath || process.resourcesPath, 'codex', key)
    : path.join(__dirname, 'codex-bin', key);
  return { key, dir, path: path.join(dir, 'bin', exe), pinned: PINS.targets[key] || null, version: PINS.version };
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
// io's settings go into a profile, `<home>/io.config.toml`, and every session is launched
// with `-p io`. Codex layers the profile on top of its own config.toml, so what Codex
// writes there itself - the model a person picks with /model - survives the next launch
// instead of being wiped by io. Effort is "low" by default: the audience is on the free
// plan and a chat about a spreadsheet does not need long thinking.
const PROFILE = 'io';

// The three settings a person picks after choosing a folder, before anything is scanned.
// They differ in what the *tools* Codex runs may reach. None of them changes what goes to
// the model: that is replaced with codes by the proxy and sent over TLS in all three.
//
//   offline  commands have no internet, and io will not open a page in the browser either.
//            Nothing this folder's work produces can leave by any route io controls.
//   tools    commands still have no internet; io will open a page it wrote for the person.
//            The name is forward-looking: when io ships tools that need the internet, they
//            run on io's side of the wall and only they go online. Nothing Codex runs does.
//   open     commands get the internet, may install what they judge useful, and a page
//            opens in the person's own browser.
//
// The folder boundary does not move between them. Commands may write the sheltered folder
// and temp, read what the platform needs, and nothing else, in every setting.
//
// Escalation is closed in all three. Codex's default approval policy lets the model ask
// the person to run a command outside the sandbox - the "Environment: local" prompt seen
// on 2026-09-15 when it wanted xdg-open. A person who says yes to that gets a command with
// the whole machine and the whole network, whichever setting they picked, so "Offline"
// would have been a label and not a fact. `-a never` (and `approval_policy = "never"` in
// the profile, so `codex exec` is covered too) returns the failure to the model instead.
//
// `tools` is the third lever: whether io's toolbox is registered. Until 2026-09-15 the
// escalation lock and the tool channel were the same switch (an MCP tool call under
// `-a never` failed with "requires approval, but approval policy is never"), so the middle
// setting had to keep escalation open to have tools at all. Codex 0.154 has a per-server
// `default_tools_approval_mode`; "approve" is checked before the approval policy
// (codex-mcp: mcp_permission_prompt_is_auto_approved), so a server io registers that way
// runs without a prompt while every shell escalation is still refused. Measured on the
// DGX, chronology 2026-09-15T2330-dgx. Offline has no toolbox: nothing io operates on
// its behalf, by construction.
const WALLS = {
  offline: { network: false, openPages: false, tools: false },
  tools:   { network: false, openPages: true,  tools: true  },
  open:    { network: true,  openPages: true,  tools: true  },
};
const DEFAULT_WALL = 'tools';
// What is in the toolbox, in the person's words. Shown on the setting card and in the
// toolbox window; the MCP server in tools/mcp.js is the machine-readable side.
const TOOLBOX = [
  { id: 'render_page', name: 'Renderer',
    does: 'shows the assistant a picture of a page it wrote, so it can check its own work',
    sees: 'a copy of the page with names, places, phone numbers and the like replaced by codes - never the real page, never a chart image',
    reaches: 'nothing' },
];
const wallOf = name => WALLS[name] || WALLS[DEFAULT_WALL];

function writeConfig(home, proxyPort, extra = {}) {
  fs.mkdirSync(home, { recursive: true });
  // TOML: every top-level key must come before the first table header, or it silently
  // becomes a key of that table.
  const top = [
    '# Written by io on every launch. Edits here do not survive; io owns this file.',
    '# Codex keeps its own choices (the /model pick) in config.toml next to this one.',
    `openai_base_url = "http://127.0.0.1:${proxyPort}/backend-api/codex"`,
    `chatgpt_base_url = "http://127.0.0.1:${proxyPort}/backend-api/"`,
    'check_for_update_on_startup = false',
    `model_reasoning_effort = "${extra.effort || 'low'}"`,
    // never ask the person to run something outside the wall (see WALLS)
    'approval_policy = "never"',
  ];
  // The provider's hosted web search is a tool too: the query leaves coded, but it goes
  // to the web from the provider's side, and the middle setting says "does not go to a
  // website by itself". Off unless the setting is Open.
  if (!(extra.chat || wallOf(extra.wall).network)) top.push('web_search = "disabled"');
  const tables = [];
  const esc = p => String(p).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
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
  // Windows: Codex's sandbox is off unless asked for (WindowsSandboxLevel defaults to
  // Disabled; `[windows] sandbox` selects it). "unelevated" is the restricted-token sandbox
  // that needs no administrator; "elevated" is stronger and needs one. Untested by io as of
  // 2026-09-15; written so the first Windows run starts from the right place.
  if (process.platform === 'win32') tables.push('[windows]', 'sandbox = "unelevated"', '');
  // Traffic that is not the model: switched off, and refused by the proxy anyway.
  //   apps / plugins   OpenAI-hosted MCP and plugin catalogues (POST backend-api/ps/mcp,
  //                    GET backend-api/ps/plugins/...) - tool arguments could flow there.
  //   analytics        POST backend-api/codex/analytics-events/events.
  //   update check     GitHub/npm.
  tables.push('[analytics]', 'enabled = false', '',
    '[features]', 'enable_request_compression = false', 'apps = false', 'plugins = false',
    'remote_plugin = false', 'plugin_sharing = false', 'recommended_plugins = false', 'image_generation = false', '');
  // io's toolbox: one local MCP server that io launches and Codex calls. It runs on io's
  // side of the wall (an MCP server is Codex's child, not a sandboxed command), so this is
  // the one channel through which a folder session can ask io for anything. "approve"
  // means Codex never asks the person about a call to it; what a tool may do is decided
  // when T4GC puts it in the box, not per call. Registered only where the setting has
  // tools; Offline gets no server at all.
  if (extra.toolbox && wallOf(extra.wall).tools) {
    const tb = extra.toolbox;
    tables.push('[mcp_servers.io]', `command = "${esc(tb.command)}"`,
      `args = [${(tb.args || []).map(a => `"${esc(a)}"`).join(', ')}]`,
      'default_tools_approval_mode = "approve"', 'startup_timeout_sec = 30', 'tool_timeout_sec = 120', '',
      '[mcp_servers.io.env]', ...Object.entries(tb.env || {}).map(([k, v]) => `${k} = "${esc(v)}"`), '');
    // Codex 0.154 hides MCP tools behind a `tool_search` step ("deferred" exposure) when
    // the model supports it; a low-effort model then answers "that tool is not available"
    // without ever searching (seen on the DGX). This names io's namespace as direct-only,
    // so render_page is in the tool list like exec_command is.
    // (the table is a sub-table of [features]; the namespace is the server name, with
    // Codex's "mcp__" prefix when prefixing is on, so both spellings are listed)
    tables.push('[features.code_mode]', 'direct_only_tool_namespaces = ["mcp__io", "io"]', '');
  }
  // The wall around the folder. A permissions profile: commands may write the working
  // folder, read what the platform needs to run at all (":minimal": system libraries,
  // shells) and nothing else - not the home directory, not other folders. Network is on
  // only in a conversation with no data, so Codex can fetch what it is asked for.
  // Codex 0.154 enforces read denial through bwrap (its Landlock backend cannot, and is
  // deprecated). The DGX cannot run bwrap at all, so the dev bypass skips the profile.
  // Codex reads its own AGENTS.md through the same wall (seen: "failed to load AGENTS.md
  // instructions ... fs sandbox helper"), so that one file is granted; the rest of the
  // home - auth.json above all - stays out of reach of commands. IO_CODEX_NO_WALL=1 is the
  // escape hatch if a platform's sandbox cannot do read denial.
  if (!extra.noSandbox && process.env.IO_CODEX_NO_WALL !== '1') {
    top.push('default_permissions = "io"');
    // Codex's own runner (bin/codex-code-mode-host, codex-resources/bwrap, zsh, codex-path/rg)
    // lives in the package directory, outside ":minimal" and the folder; without it the
    // sandbox cannot start the runner and Codex asks to run outside it ("the sandbox
    // runner itself is missing", laptop 2026-09-15). Temp is writable, as in Codex's own
    // workspace-write profile, or python and friends fail on their scratch files.
    const fsEntries = ['":minimal" = "read"', `"${esc(path.join(home, 'AGENTS.md'))}" = "read"`];
    if (extra.codexDir) fsEntries.push(`"${esc(extra.codexDir)}" = "read"`);
    // io's own python and its packages. ":minimal" is the platform's bare interpreter and
    // stdlib; pandas, numpy and openpyxl are not in it. On the laptop the only copies on
    // the machine were a per-user install under $HOME, which the wall correctly refuses,
    // so `import pandas` failed and Codex fell back to unzipping xlsx files and walking
    // the XML by hand - badly (2026-09-15). io ships a runtime that has them, io owns it,
    // and it holds nobody's data, so every setting may read it.
    if (extra.libsDir) fsEntries.push(`"${esc(extra.libsDir)}" = "read"`);
    for (const t of new Set([os.tmpdir(), '/tmp'].filter(Boolean))) fsEntries.push(`"${esc(t)}" = "write"`);
    const wall = wallOf(extra.wall);
    // "Open" had the network but no name resolution (DGX, 2026-09-15): ":minimal" does not
    // include /run, and on systemd-resolved machines /etc/resolv.conf is a symlink into
    // /run/systemd/resolve, so every curl inside the wall failed with "could not resolve
    // host" while loopback worked. Grant the resolver's directory when commands may go online.
    if ((extra.chat || wall.network) && process.platform === 'linux' && fs.existsSync('/run/systemd/resolve')) {
      fsEntries.push('"/run/systemd/resolve" = "read"');
    }
    tables.push('[permissions.io]', 'description = "io: the sheltered folder and nothing else"', '',
      '[permissions.io.filesystem]', ...fsEntries, '',
      '[permissions.io.filesystem.":workspace_roots"]', '"." = "write"', '',
      '[permissions.io.network]', `enabled = ${extra.chat || wall.network ? 'true' : 'false'}`, '');
  } else if (extra.chat) {
    tables.push('[sandbox_workspace_write]', 'network_access = true', '');
  }
  fs.writeFileSync(path.join(home, `${PROFILE}.config.toml`), top.concat(['']).concat(tables).join('\n'));
  fs.writeFileSync(path.join(home, 'AGENTS.md'), agentsMd(extra));
  // an older io wrote its settings into config.toml itself; take those lines out once
  const cfg = path.join(home, 'config.toml');
  if (fs.existsSync(cfg)) {
    const t = fs.readFileSync(cfg, 'utf8');
    if (t.includes('Written by io on every launch')) fs.writeFileSync(cfg, '');
  }
}

// What Codex is told about who it is talking to. Written to <home>/AGENTS.md, which Codex
// reads as the person's own instructions in every session (a project AGENTS.md in the
// folder is added after it, not instead of it).
function agentsMd(extra = {}) {
  const lines = [
    '# Who you are talking to',
    '',
    'You are running inside io, a small desktop app, for people who work at non-profit',
    'organisations in India. They are not programmers. Most will never have used a terminal.',
    '',
    '## How to talk',
    '',
    '- Plain words. No jargon, no acronyms without saying what they mean, no code unless asked.',
    '- Never ask a technical question back (nothing about paths, formats, encodings, shells,',
    '  branches, permissions). If you need to choose, choose the sensible thing and say what',
    '  you chose in one line.',
    '- Short answers. One idea per sentence. Numbers in a small table when there are several.',
    '- When you have done something, say what changed in their words: "I added a column with',
    '  the total per village", not "I appended a Series".',
    '',
    '## Show, do not describe',
    '',
    '- When asked for a chart, dashboard, report or anything visual, save it as a file in the',
    '  working folder and io shows it to them at once, in its own window. Do not try to open',
    '  it yourself (no xdg-open, no open, no start); just save it and say the file name on',
    '  its own line.',
    '- A chart: draw it with matplotlib (it is installed; use `matplotlib.use("Agg")` and',
    '  `savefig`) as a PNG in the working folder. Pick a clean style, label the axes in plain',
    '  words, put the numbers on the bars when there are few, and keep it readable at a',
    '  glance. No internet is needed or available for this.',
    '- A dashboard or report: one self-contained HTML file (inline CSS and JS, no internet',
    '  needed to view it, no external scripts, fonts, tiles or images).',
    '- `python3` here already has pandas, numpy, openpyxl and matplotlib. Use them; never',
    '  take a spreadsheet apart by unzipping it and reading the XML inside.',
    '- Prefer a page in the browser over long text in this window.',
    ...(extra.toolbox && wallOf(extra.wall).tools ? [
    '- After you save a page, you may call the io tool `render_page` with the file name once',
    '  to see a picture of it and check it looks right. In that picture names and places',
    '  appear as codes; that is expected, do not try to fix it. Charts (PNG) cannot be',
    '  rendered this way; trust matplotlib.'] : []),
    '- When you refer to a file or a web page, give the full path or link on its own line.',
    '',
    '## Their data',
    '',
    '- The files in the working folder are theirs. Answering questions about them - who is',
    '  in a file, which village or phone number a row has, totals, comparisons, reports - is',
    '  the job. Do not refuse on privacy grounds: the person owns this data and io has already',
    '  protected it before you see it.',
    '- Names, phone numbers and places may appear as codes like NAME_001 or PLACE_003. That is',
    '  expected: treat them as ordinary labels, report them as they are, never mention that',
    '  they are codes and never try to work out what they stand for.',
    '- Do not upload their files anywhere, and do not paste their data into web forms or',
    '  search boxes.',
  ];
  if (extra.chat) {
    lines.push(
      '- This conversation has no sheltered folder. Work only inside the current working',
      '  folder. Do not read, list or open files anywhere else on this computer. If they want',
      '  help with their own files, tell them to press "attach a file" in io, which checks the',
      '  file for private details first.',
    );
  } else {
    lines.push(
      '- Work inside the current working folder. It has been checked for private details;',
      '  other folders on this computer have not, so do not read files outside it.',
    );
  }
  lines.push('', '## Be careful with their time and their plan', '',
    '- Keep steps few. Do not run long explorations. Ask nothing you can find out yourself.',
    '');
  return lines.join('\n');
}

function baseEnv(home, libsDir) {
  const env = { ...process.env, CODEX_HOME: home };
  // Granting the wall read access to io's runtime is only half of it: commands still run
  // the platform's own python3, which has no pandas or openpyxl (the only copies on the
  // laptop were a per-user install under $HOME, which the wall rightly refuses). Putting
  // io's runtime first on PATH makes `python3` mean io's python, the one that has them.
  const bin = libsDir && path.join(libsDir, process.platform === 'win32' ? 'Scripts' : 'bin');
  if (bin && fs.existsSync(bin)) env.PATH = bin + path.delimiter + (env.PATH || '');
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
// The command line for a session. A switch of setting is a relaunch with the thread
// resumed (`codex resume --last`), and the profile flag has to be repeated: a resumed
// session takes its wall from the profile file as it is now, not from the session it
// resumes (measured, chronology 2026-09-15T2330-dgx).
function sessionArgs({ resume, noAltScreen } = {}) {
  const args = resume ? ['resume', resume, '-p', PROFILE] : ['-p', PROFILE];
  args.push('-a', 'never');
  if (noAltScreen) args.push('--no-alt-screen');
  return args;
}

function spawnSession({ bin, home, cwd, cols, rows, noAltScreen, libsDir, wall, resume }) {
  if (!pty) throw new Error('node-pty is not available in this build');
  const args = sessionArgs({ resume, noAltScreen });
  return pty.spawn(bin, args, {
    name: 'xterm-256color',
    cols: cols || 100,
    rows: rows || 30,
    cwd,
    env: { ...baseEnv(home, libsDir), TERM: 'xterm-256color', COLORTERM: 'truecolor', LANG: process.env.LANG || 'C.UTF-8' },
  });
}

// Can this machine run the wall at all? On Linux the wall is bubblewrap, and Ubuntu 24.04
// confines any unconfined binary that creates a user namespace into a capability-less
// AppArmor profile, so bwrap dies with "loopback: Failed RTM_NEWADDR" or "setting up uid
// map: Permission denied" (measured on the DGX, chronology 2026-09-15T1856-dgx). Codex
// prefers a system bwrap on PATH and falls back to its bundled one, so the same binary
// Codex would use is the one tried here, with the same three namespaces. There is no
// user-side fix: an administrator has to grant `userns` to that binary once (the profile
// text this returns), or io runs without a wall, which it refuses to do silently.
// macOS uses Seatbelt (built in, no setup); Windows uses Codex's own sandbox: both
// report "not checked here" rather than a guess.
let sandboxCache = null;
function sandboxCheck(codexDir) {
  if (sandboxCache) return sandboxCache;
  if (process.platform !== 'linux') return (sandboxCache = { ok: true, checked: false, why: `${process.platform}: Codex's own sandbox, not checked by io` });
  const bundled = path.join(codexDir || '', 'codex-resources', 'bwrap');
  let system = null;
  try { system = execFileSyncQuiet('sh', ['-c', 'command -v bwrap']).trim() || null; } catch { system = null; }
  const bwrap = system || (fs.existsSync(bundled) ? bundled : null);
  if (!bwrap) return (sandboxCache = { ok: false, checked: true, why: 'no bubblewrap found, neither on PATH nor bundled with Codex', fix: null });
  const r = spawnSync(bwrap, ['--unshare-user', '--unshare-net', '--unshare-pid', '--ro-bind', '/', '/', '/bin/true'], { encoding: 'utf8', timeout: 10000 });
  if (r.status === 0) return (sandboxCache = { ok: true, checked: true, bwrap });
  const err = ((r.stderr || '') + (r.error ? String(r.error.message) : '')).trim().split('\n')[0].slice(0, 200);
  let restricted = false;
  try { restricted = fs.readFileSync('/proc/sys/kernel/apparmor_restrict_unprivileged_userns', 'utf8').trim() === '1'; } catch {}
  const paths = [...new Set([system, fs.existsSync(bundled) ? bundled : null].filter(Boolean))];
  const profile = ['abi <abi/4.0>,', 'include <tunables/global>']
    .concat(paths.map((p, i) => `profile io-bwrap-${i} ${p} flags=(unconfined) {\n  userns,\n}`)).join('\n') + '\n';
  return (sandboxCache = {
    ok: false, checked: true, bwrap, error: err,
    why: restricted
      ? "this computer's settings (Ubuntu's AppArmor rule for user namespaces) do not let the wall start"
      : `the wall could not start: ${err}`,
    fix: restricted ? { profile, install: 'sudo install -m 644 io-bwrap /etc/apparmor.d/io-bwrap && sudo apparmor_parser -r /etc/apparmor.d/io-bwrap' } : null,
  });
}

function execFileSyncQuiet(cmd, args) {
  const r = spawnSync(cmd, args, { encoding: 'utf8', timeout: 5000 });
  return r.status === 0 ? (r.stdout || '') : '';
}

function binaryInfo(bin) {
  try {
    const st = fs.statSync(bin);
    // the command host lives beside codex; without it every shell call fails closed
    const host = path.join(path.dirname(bin), process.platform === 'win32' ? 'codex-code-mode-host.exe' : 'codex-code-mode-host');
    return { exists: true, size: st.size, executable: !!(st.mode & 0o111), host: fs.existsSync(host) };
  } catch { return { exists: false }; }
}

module.exports = {
  WALLS, DEFAULT_WALL, TOOLBOX, wallOf, sandboxCheck, bundledCodexPath, codexHome, writeConfig, agentsMd, baseEnv, loginStatus, startLogin, logout, spawnSession, sessionArgs, binaryInfo, hasPty: () => !!pty, PINS, PROFILE };
