// The launcher seam: which binary, which home, which config, which environment.
// Run: node tests/test_codex_launcher.js   (no Electron needed)

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execSync } = require('child_process');
const codex = require('../codex');

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'io-codex-launcher-'));
let passed = 0;
const test = (name, fn) => { fn(); passed++; console.log('ok -', name); };

test('bundled path is inside the app, never a system codex', () => {
  const b = codex.bundledCodexPath();
  assert.ok(b.path.startsWith(path.join(__dirname, '..', 'codex-bin')), b.path);
  let system = null;
  try { system = execSync('command -v codex', { encoding: 'utf8' }).trim(); } catch {}
  if (system) assert.notStrictEqual(fs.realpathSync.native(system), b.path);
  assert.strictEqual(b.version, codex.PINS.version);
});

test('packaged path resolves under resources/codex/<target>', () => {
  const b = codex.bundledCodexPath({ packaged: true, resourcesPath: '/opt/io/resources' });
  assert.strictEqual(b.path, path.join('/opt/io/resources/codex', `${process.platform}-${process.arch}`, 'bin', process.platform === 'win32' ? 'codex.exe' : 'codex'));
});

test('codex home is io-owned and distinct from ~/.codex', () => {
  const home = codex.codexHome('/data/io');
  assert.strictEqual(home, path.join('/data/io', 'codex', 'home'));
  assert.notStrictEqual(path.resolve(home), path.join(os.homedir(), '.codex'));
});

test('config points both base urls at the loopback proxy and keeps the codex suffix', () => {
  const home = path.join(tmp, 'home');
  codex.writeConfig(home, 43210, { trust: '/some/folder', codexDir: '/opt/io/codex-bin/linux-x64' });
  const toml = fs.readFileSync(path.join(home, 'io.config.toml'), 'utf8');
  assert.ok(toml.includes('"/opt/io/codex-bin/linux-x64" = "read"'), 'the Codex package dir must be readable inside the wall');
  assert.ok(toml.includes('"/tmp" = "write"'));
  assert.ok(toml.includes('openai_base_url = "http://127.0.0.1:43210/backend-api/codex"'));
  assert.ok(toml.includes('chatgpt_base_url = "http://127.0.0.1:43210/backend-api/"'));
  assert.ok(toml.includes('enable_request_compression = false'));
  assert.ok(toml.includes('[projects."/some/folder"]\ntrust_level = "trusted"'));
  assert.ok(!toml.includes('model_provider ='), 'production config uses the built-in openai provider');
  assert.ok(!/api_key|OPENAI_API_KEY/i.test(toml));
  // no top-level key after the first table header
  const firstTable = toml.indexOf('\n[');
  assert.ok(!/\n(openai_base_url|chatgpt_base_url|model|sandbox_mode|default_permissions) = /.test(toml.slice(firstTable)));
  assert.ok(toml.includes('[permissions.io.network]\nenabled = false'), 'a sheltered folder has no network for commands');
});

test('config is rewritten with a new port, not appended', () => {
  const home = path.join(tmp, 'home2');
  codex.writeConfig(home, 1111);
  codex.writeConfig(home, 2222);
  const toml = fs.readFileSync(path.join(home, 'io.config.toml'), 'utf8');
  assert.ok(toml.includes(':2222/'));
  assert.ok(!toml.includes(':1111/'));
});

test('environment carries CODEX_HOME and strips any OpenAI key', () => {
  process.env.OPENAI_API_KEY = 'sk-should-not-leak';
  process.env.OPENAI_BASE_URL = 'https://example.invalid';
  const env = codex.baseEnv('/data/io/codex/home');
  assert.strictEqual(env.CODEX_HOME, '/data/io/codex/home');
  assert.strictEqual(env.OPENAI_API_KEY, undefined);
  assert.strictEqual(env.OPENAI_BASE_URL, undefined);
  delete process.env.OPENAI_API_KEY; delete process.env.OPENAI_BASE_URL;
});

test('login status on an empty home is "not logged in" and never reads ~/.codex', () => {
  const b = codex.bundledCodexPath();
  if (!fs.existsSync(b.path)) { console.log('   (skipped: bundled binary not fetched)'); return; }
  const home = path.join(tmp, 'empty-home');
  assert.ok(codex.binaryInfo(b.path).host, 'codex-code-mode-host must ship beside codex');
  const st = codex.loginStatus(b.path, home);
  assert.strictEqual(st.loggedIn, false);
  assert.ok(/Not logged in/.test(st.line), st.line);
  assert.ok(!fs.existsSync(path.join(home, 'auth.json')));
});

test('AGENTS.md for the audience is written beside the profile, chat variant differs', () => {
  const home = path.join(tmp, 'home4');
  codex.writeConfig(home, 7, {});
  const a = fs.readFileSync(path.join(home, 'AGENTS.md'), 'utf8');
  assert.ok(/not programmers/.test(a) && /NAME_001/.test(a) && !/attach a file/.test(a));
  codex.writeConfig(home, 7, { chat: true });
  const b = fs.readFileSync(path.join(home, 'AGENTS.md'), 'utf8');
  assert.ok(/attach a file/.test(b));
  const t = fs.readFileSync(path.join(home, 'io.config.toml'), 'utf8'); assert.ok(t.includes('default_permissions = "io"') && t.includes('[permissions.io.network]\nenabled = true') && t.includes('":minimal" = "read"'));
});

test('dev provider block only appears when asked for', () => {
  const home = path.join(tmp, 'home3');
  codex.writeConfig(home, 5, { devProvider: true });
  const toml = fs.readFileSync(path.join(home, 'io.config.toml'), 'utf8');
  assert.ok(toml.includes('model_provider = "io-dev"') && toml.includes('/dev/v1"'));
  assert.ok(toml.indexOf('model_provider = "io-dev"') < toml.indexOf('\n['), 'top-level key before any table');
});

test('the three walls differ only in network, and never in the folder boundary', () => {
  const read = (name, extra) => {
    const home = path.join(tmp, 'wall-' + name);
    codex.writeConfig(home, 9, Object.assign({ wall: name }, extra || {}));
    return fs.readFileSync(path.join(home, 'io.config.toml'), 'utf8');
  };
  const offline = read('offline'), tools = read('tools'), open_ = read('open');
  assert.ok(offline.includes('[permissions.io.network]\nenabled = false'), 'offline has no network');
  assert.ok(tools.includes('[permissions.io.network]\nenabled = false'), 'io-tools gives commands no network');
  assert.ok(open_.includes('[permissions.io.network]\nenabled = true'), 'open has network');
  // the folder boundary is the same in all three
  for (const t of [offline, tools, open_]) {
    assert.ok(t.includes('default_permissions = "io"'), 'the wall is always on');
    assert.ok(t.includes('[permissions.io.filesystem.":workspace_roots"]\n"." = "write"'));
    assert.ok(t.includes('":minimal" = "read"'));
    assert.ok(!t.includes('[sandbox_workspace_write]'), 'never the unwalled fallback');
  }
  // Escalation: Codex's default policy lets the model ask the person to run a command
  // outside the sandbox, which would hand it the whole machine and the whole network
  // whatever setting they chose. No setting may ask: the flag on every command line and
  // the policy in every profile. Tools reach Codex another way (below).
  for (const t of [offline, tools, open_]) assert.ok(t.includes('\napproval_policy = "never"\n'), 'no profile may escalate');
  for (const w of ['offline', 'tools', 'open', 'nonsense']) assert.deepStrictEqual(codex.sessionArgs({ wall: w }).slice(-2), ['-a', 'never']);
  assert.strictEqual(codex.wallOf('offline').tools, false, 'offline has no toolbox');
  assert.strictEqual(codex.wallOf('tools').tools, true);
  assert.strictEqual(codex.wallOf('open').tools, true);
  assert.strictEqual(codex.wallOf('nonsense').tools, codex.wallOf(codex.DEFAULT_WALL).tools);
  // an unknown or missing name falls back to the suggested one, never to the open one
  const fallback = read('nonsense-value');
  assert.strictEqual(codex.DEFAULT_WALL, 'tools');
  assert.ok(fallback.includes('[permissions.io.network]\nenabled = false'), 'unknown wall must not grant network');
  assert.ok(read(undefined).includes('[permissions.io.network]\nenabled = false'), 'missing wall must not grant network');
  // a conversation with no folder keeps its network whatever the wall says
  assert.ok(read('offline', { chat: true }).includes('[permissions.io.network]\nenabled = true'));
});

test('io ships the analysis packages into the wall, and only io-owned paths', () => {
  const home = path.join(tmp, 'libs');
  codex.writeConfig(home, 9, { wall: 'tools', libsDir: '/opt/io/runtime' });
  const toml = fs.readFileSync(path.join(home, 'io.config.toml'), 'utf8');
  assert.ok(toml.includes('"/opt/io/runtime" = "read"'), 'io runtime is readable');
  codex.writeConfig(home, 9, { wall: 'tools' });
  assert.ok(!fs.readFileSync(path.join(home, 'io.config.toml'), 'utf8').includes('runtime'), 'nothing granted when io has no runtime to grant');
});

test('the sandbox check answers with a verdict, and with the admin fix when it fails', () => {
  const r = codex.sandboxCheck(codex.bundledCodexPath().dir);
  assert.strictEqual(typeof r.ok, 'boolean');
  if (process.platform === 'linux') {
    assert.strictEqual(r.checked, true);
    if (!r.ok) { assert.ok(r.why); if (r.fix) { assert.ok(/userns/.test(r.fix.profile)); assert.ok(/apparmor_parser/.test(r.fix.install)); } }
  } else {
    assert.strictEqual(r.checked, false);
  }
  console.log(`   (this machine: ${r.ok ? 'wall can run' : 'wall cannot run - ' + r.why})`);
});

fs.rmSync(tmp, { recursive: true, force: true });

test('the toolbox is registered as an approve-mode server where the setting has tools, and never Offline', () => {
  const tb = { command: '/opt/io/io', args: ['/opt/io/tools/mcp.js'], env: { ELECTRON_RUN_AS_NODE: '1', IO_TOOLS_PORT: '8123', IO_TOOLS_TOKEN: 'abc' } };
  const read = (wall, extra) => {
    const home = path.join(tmp, 'tb-' + wall + (extra ? '-x' : ''));
    codex.writeConfig(home, 9, Object.assign({ wall, toolbox: tb }, extra || {}));
    return fs.readFileSync(path.join(home, 'io.config.toml'), 'utf8');
  };
  for (const w of ['tools', 'open']) {
    const t = read(w);
    assert.ok(t.includes('[mcp_servers.io]\ncommand = "/opt/io/io"\nargs = ["/opt/io/tools/mcp.js"]\ndefault_tools_approval_mode = "approve"'), w + ' registers the toolbox');
    assert.ok(t.includes('[mcp_servers.io.env]\nELECTRON_RUN_AS_NODE = "1"\nIO_TOOLS_PORT = "8123"\nIO_TOOLS_TOKEN = "abc"'));
    assert.ok(t.includes('direct_only_tool_namespaces = ["mcp__io", "io"]'), 'the tool is in the list, not behind tool_search');
  }
  // the provider's hosted web search is off unless the setting is Open
  assert.ok(read('offline').includes('\nweb_search = "disabled"\n'));
  assert.ok(read('tools').includes('\nweb_search = "disabled"\n'));
  assert.ok(!read('open').includes('web_search = "disabled"'));
  assert.ok(!read('offline').includes('mcp_servers'), 'Offline has no toolbox');
  assert.ok(!read('tools', { toolbox: null }).includes('mcp_servers'), 'no server without a running toolbox');
  // and the assistant is told about the renderer only where it exists
  assert.ok(/render_page/.test(codex.agentsMd({ wall: 'tools', toolbox: tb })));
  assert.ok(!/render_page/.test(codex.agentsMd({ wall: 'offline', toolbox: tb })));
  assert.ok(codex.TOOLBOX.some(t => t.id === 'render_page' && /nothing/.test(t.reaches)));
});

test('a switch resumes the thread under the profile, and Offline still cannot escalate', () => {
  const fresh = codex.sessionArgs({ wall: 'tools' });
  assert.deepStrictEqual(fresh, ['-p', 'io', '-a', 'never']);
  const sw = codex.sessionArgs({ wall: 'open', resume: '--last' });
  assert.deepStrictEqual(sw, ['resume', '--last', '-p', 'io', '-a', 'never']);
  const off = codex.sessionArgs({ wall: 'offline', resume: '--last' });
  assert.deepStrictEqual(off, ['resume', '--last', '-p', 'io', '-a', 'never']);
});

test('the toolbox server speaks MCP over stdio and returns a picture, not the page', () => {
  const { spawnSync } = require('child_process');
  const lines = [
    { jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 't', version: '0' } } },
    { jsonrpc: '2.0', method: 'notifications/initialized' },
    { jsonrpc: '2.0', id: 2, method: 'tools/list' },
    { jsonrpc: '2.0', id: 3, method: 'tools/call', params: { name: 'render_page', arguments: { file: 'people.html' } } },
    { jsonrpc: '2.0', id: 4, method: 'tools/call', params: { name: 'delete_everything', arguments: {} } },
  ].map(m => JSON.stringify(m)).join('\n') + '\n';
  const r = spawnSync(process.execPath, [path.join(__dirname, '..', 'tools', 'mcp.js')], { input: lines, encoding: 'utf8', env: { ...process.env, IO_TOOLS_FAKE: '1' }, timeout: 10000 });
  const replies = r.stdout.trim().split('\n').map(l => JSON.parse(l));
  assert.strictEqual(replies.length, 4, r.stderr);
  assert.strictEqual(replies[0].result.serverInfo.name, 'io');
  assert.deepStrictEqual(replies[1].result.tools.map(t => t.name), ['render_page']);
  assert.strictEqual(replies[1].result.tools[0].annotations.openWorldHint, false);
  const c = replies[2].result.content;
  assert.strictEqual(c[1].type, 'image'); assert.strictEqual(c[1].mimeType, 'image/png'); assert.ok(c[1].data.length > 20);
  assert.ok(/codes/.test(c[0].text));
  assert.strictEqual(replies[3].result.isError, true);
});

console.log(`\n${passed} launcher tests passed`);
