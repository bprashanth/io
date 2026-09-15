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

fs.rmSync(tmp, { recursive: true, force: true });
console.log(`\n${passed} launcher tests passed`);
