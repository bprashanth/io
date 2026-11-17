"""The catalog of vetted tools (lib/catalog.py) and the tools home (lib/toolhome.py), against a fixture catalog
served on 127.0.0.1. IDLI_STACK_SLOW=1 also installs a small real catalog tool when the real catalog answers."""
import hashlib
import http.server
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import catalog, toolhome  # noqa: E402

GB = 1024 ** 3
MODEL = b'tiny model weights\n' * 10
ZIPPED = io.BytesIO()
with zipfile.ZipFile(ZIPPED, 'w') as z:
    z.writestr('voice/model.onnx', b'onnx bytes')
ZIPPED = ZIPPED.getvalue()
ALL = ['linux-64', 'linux-aarch64', 'osx-arm64', 'win-64']


def sha(b):
    return hashlib.sha256(b).hexdigest()


def tool(tid, **kw):
    t = {'id': tid, 'name': tid.replace('-', ' ').title(), 'for': f'Testing {tid}', 'licence': 'MIT',
         'vetted': '2026-11-17', 'cautions': [], 'pixi': {'dependencies': {'python': '3.11.*'}},
         'platforms': ALL, 'models': [], 'needs': {'disk_gb': 0.1, 'ram_gb': 1, 'cores': 1, 'gpu': False},
         'example': None, 'tags': []}
    t.update(kw)
    return t


CATALOG = {'version': 1, 'updated': '2026-11-17T00:00:00Z', 'tools': [
    tool('office-files', pixi={'dependencies': {'python': '3.11.*'}, 'pypi-dependencies': {'python-docx': '==1.1.2'}},
         example='examples/office.py', models=[{'name': 'tiny.bin', 'file': 'models/tiny.bin', 'source':
                                                 'https://example.org/tiny.bin', 'sha256': sha(MODEL),
                                                 'bytes': len(MODEL), 'unpack': 'none'}]),
    tool('voice', cautions=['non-commercial licence'], licence='CC-BY-NC-4.0',
         pixi={'dependencies': {'python': '3.11.*', 'numpy': '>=1.26'}},
         models=[{'name': 'voice', 'file': 'models/voice.zip', 'source': 'https://example.org/voice.zip',
                  'sha256': sha(ZIPPED), 'bytes': len(ZIPPED), 'unpack': 'zip'},
                 {'name': 'tiny.bin', 'file': 'models/tiny.bin', 'source': 'https://example.org/tiny.bin',
                  'sha256': sha(MODEL), 'bytes': len(MODEL), 'unpack': 'none'}]),
    tool('numpy-old', pixi={'dependencies': {'numpy': '<1.20'}}),
    tool('huge-ram', needs={'disk_gb': 1, 'ram_gb': 100000, 'cores': 1, 'gpu': False}),
    tool('cuda-only', needs={'disk_gb': 1, 'ram_gb': 1, 'cores': 1, 'gpu': 'cuda'}),
    tool('windows-only', platforms=['win-64']),
    tool('huge-disk', needs={'disk_gb': 10 ** 6, 'ram_gb': 1, 'cores': 1, 'gpu': False}),
]}
FILES = {'models/tiny.bin': MODEL, 'models/voice.zip': ZIPPED, 'examples/office.py': b'import docx\nprint("hi")\n'}


class Server(http.server.BaseHTTPRequestHandler):
    requests = []

    def do_GET(self):
        p = self.path.split('?')[0]
        if p == '/idli/catalog/catalog.json':
            return self._send(200, json.dumps(CATALOG).encode())
        if p.startswith('/idli/catalog/files/') and p[20:] in FILES:
            return self._send(200, FILES[p[20:]])
        return self._send(404, b'{}')

    def do_POST(self):
        if self.path == '/idli/catalog/requests':
            Server.requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            return self._send(200, b'{"id": "r1"}')
        return self._send(404, b'{}')

    def _send(self, code, body):
        self.send_response(code)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Server)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='idli-catalog-test-'))
        self.env = patch.dict(os.environ, {'IDLI_TOOLS_HOME': str(self.tmp / 'tools'), 'IDLI_HOME': str(self.tmp),
                                           'IDLI_CATALOG_URL': f'http://127.0.0.1:{self.srv.server_address[1]}'})
        self.env.start()
        Server.requests = []

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def res(self, **kw):
        r = {'platform': 'linux-64', 'home': str(self.tmp), 'disk_free': 100 * GB, 'ram': 16 * GB, 'cores': 8,
             'gpu': None}
        r.update(kw)
        return r

    def team(self, name='field-notes'):
        d = self.tmp / 'teams' / name
        (d / 'extensions').mkdir(parents=True)
        (d / 'team.json').write_text(json.dumps({'name': name.replace('-', ' ').title()}))
        return d


class Computer(Base):
    def test_platform_names(self):
        self.assertEqual(catalog.platform('linux', 'x86_64'), 'linux-64')
        self.assertEqual(catalog.platform('linux', 'aarch64'), 'linux-aarch64')
        self.assertEqual(catalog.platform('darwin', 'arm64'), 'osx-arm64')
        self.assertEqual(catalog.platform('darwin', 'x86_64'), 'osx-64')
        self.assertEqual(catalog.platform('win32', 'AMD64'), 'win-64')
        self.assertIn(catalog.platform(), catalog.PLATFORM_WORDS)

    def test_resources_are_real_numbers(self):
        r = catalog.resources()
        self.assertGreater(r['disk_free'], 0)
        self.assertGreater(r['ram'], 0)
        self.assertGreaterEqual(r['cores'], 1)
        self.assertIn(r['gpu'], (None, 'nvidia', 'apple'))
        self.assertTrue(r['home'].startswith(str(self.tmp)))
        self.assertIn('Free disk where tools go', catalog.describe_computer(r))

    def test_tools_home_from_config(self):
        with patch.dict(os.environ, {'IDLI_TOOLS_HOME': ''}):
            self.assertEqual(catalog.tools_home(), self.tmp / 'tools')
            (self.tmp / 'config').mkdir()
            (self.tmp / 'config/tools.json').write_text(json.dumps({'home': str(self.tmp / 'big-disk')}))
            self.assertEqual(catalog.tools_home(), self.tmp / 'big-disk')


    def test_environments_avoid_disks_without_symlinks(self):
        self.assertEqual(catalog.envs_home(), self.tmp / 'tools/envs')
        with patch.object(catalog, '_links_ok', return_value=False):  # the DGX's exFAT disk
            self.assertEqual(catalog.envs_home(), self.tmp / 'tools/envs')  # IDLI_HOME/tools is the fallback
            with patch.dict(os.environ, {'IDLI_TOOLS_HOME': str(self.tmp / 'exfat')}):
                self.assertEqual(catalog.envs_home(), self.tmp / 'tools/envs')
        with patch.dict(os.environ, {'IDLI_TOOLS_HOME': ''}):
            (self.tmp / 'config').mkdir()
            (self.tmp / 'config/tools.json').write_text(json.dumps({'home': '/big', 'envs': str(self.tmp / 'e')}))
            self.assertEqual(catalog.envs_home(), self.tmp / 'e')


class Check(Base):
    def test_load_and_cache(self):
        cat = catalog.load()
        self.assertEqual(len(cat['tools']), len(CATALOG['tools']))
        self.assertTrue((self.tmp / 'tools/catalog-cache.json').exists())
        with patch.dict(os.environ, {'IDLI_CATALOG_URL': 'http://127.0.0.1:9'}):  # server gone: the last copy
            self.assertTrue(catalog.load(refresh=True)['stale'])

    def test_verdicts_in_plain_words(self):
        v = catalog.check(['office-files', 'voice'], res=self.res(), registry=[])
        self.assertTrue(v['ok'], v)
        v = catalog.check(['huge-ram', 'cuda-only', 'windows-only', 'nope'], res=self.res(), registry=[])
        self.assertFalse(v['ok'])
        t = v['tools']
        self.assertIn('needs 100000 GB of memory', t['huge-ram']['reasons'][0])
        self.assertIn('NVIDIA', t['cuda-only']['reasons'][0])
        self.assertIn("doesn't run on this computer (Linux)", t['windows-only']['reasons'][0])
        self.assertIn('runs on Windows', t['windows-only']['reasons'][0])
        self.assertIn('not on Idli', t['nope']['reasons'][0])
        self.assertTrue(catalog.check(['cuda-only'], res=self.res(gpu='nvidia'), registry=[])['ok'])

    def test_disk_counts_what_is_already_installed(self):
        v = catalog.check(['huge-disk'], res=self.res(), registry=[])
        self.assertFalse(v['ok'])
        self.assertIn('Not enough free disk', v['reasons'][0])
        tiny = catalog.check(['office-files'], res=self.res(disk_free=int(2.05 * GB)), registry=[])
        self.assertFalse(tiny['ok'])  # 0.1 GB on top of the 2 GB Idli keeps spare
        # the same team has it already: no new disk
        have = [{'team': 't', 'tool': 'office-files', 'models': [sha(MODEL)]}]
        self.assertTrue(catalog.check(['office-files'], team='t', res=self.res(disk_free=int(2.05 * GB)),
                                      registry=have)['ok'])
        # a model another team installed is shared, so it doesn't count again
        t = next(x for x in CATALOG['tools'] if x['id'] == 'voice')
        self.assertLess(catalog.tool_bytes(t, [sha(MODEL)]), catalog.tool_bytes(t))

    def test_fitting_lists_this_system_only(self):
        rows, other = catalog.fitting(res=self.res(), registry=[])
        ids = {r['id'] for r in rows}
        self.assertNotIn('windows-only', ids)
        self.assertEqual(other, 1)
        self.assertFalse(next(r for r in rows if r['id'] == 'huge-ram')['fits'])

    def test_request_posts_general_words(self):
        out = catalog.request('speech to text for Marathi', 'voice notes into a table', ['voice'], 'field-notes')
        self.assertEqual(out, {'sent': True, 'id': 'r1'})
        got = Server.requests[0]
        self.assertEqual((got['need'], got['team'], got['tools_considered']),
                         ('speech to text for Marathi', 'field-notes', ['voice']))
        self.assertIn(got['platform'], catalog.PLATFORM_WORDS)
        # silo answers 400 to any other field (trusted-catalog W4 on the DGX, 2026-11-17: 'at' and 'version')
        self.assertLessEqual(set(got), {'need', 'why', 'platform', 'team', 'tools_considered'})
        with self.assertRaises(ValueError):
            catalog.request('', 'x')

    def test_example_text(self):
        self.assertIn('import docx', catalog.example('office-files'))

    def test_no_route_says_so(self):
        with patch.dict(os.environ, {'IDLI_CATALOG_URL': ''}), patch.object(catalog, '_local_router',
                                                                            return_value=False), \
                patch('lib.muse.access', return_value=None):
            with self.assertRaisesRegex(ValueError, "can't reach its catalog"):
                catalog.source()


class Manifest(Base):
    def test_union_and_conflicts(self):
        by = catalog.tools_by_id(CATALOG)
        deps, pypi, plats, conflicts = toolhome.union([by['office-files'], by['voice']])
        self.assertEqual(deps, {'python': '3.11.*', 'numpy': '>=1.26'})
        self.assertEqual(pypi, {'python-docx': '==1.1.2'})
        self.assertEqual(plats, sorted(ALL))
        self.assertEqual(conflicts, [])
        _, _, plats, conflicts = toolhome.union([by['voice'], by['numpy-old'], by['windows-only']])
        self.assertEqual(plats, ['win-64'])
        self.assertIn('Voice needs numpy >=1.26, but Numpy Old needs numpy <1.20.', conflicts)
        text = toolhome.manifest_text('field-notes', [by['office-files'], by['voice']])
        import tomllib
        t = tomllib.loads(text)
        self.assertEqual(t['workspace']['name'], 'idli-field-notes')
        self.assertEqual(t['pypi-dependencies']['python-docx'], '==1.1.2')
        with self.assertRaisesRegex(ValueError, 'different versions'):
            toolhome.manifest_text('x', [by['voice'], by['numpy-old']])
        self.assertNotIn('system-requirements', text)

    def test_system_requirements_pass_through(self):
        """faster-whisper's av has Apple Silicon wheels for macOS 14 only (CI 2026-11-17): the catalog says so."""
        import tomllib
        whisper = tool('whisper', pixi={'dependencies': {'python': '3.11.*'}, 'pypi-dependencies': {'av': '*'},
                                        'system-requirements': {'macos': '14.0'}})
        newer = tool('newer', pixi={'dependencies': {}, 'system-requirements': {'macos': '15.1', 'bad key': '1'}})
        t = tomllib.loads(toolhome.manifest_text('field-notes', [whisper]))
        self.assertEqual(t['system-requirements'], {'macos': '14.0'})
        t = tomllib.loads(toolhome.manifest_text('field-notes', [whisper, newer]))
        self.assertEqual(t['system-requirements'], {'macos': '15.1'})

    def test_page_tasks_run_from_the_stack_folder(self):
        """pixi runs a task from its manifest's folder (the tools home), so a page task names the team's stack
        folder; else `python tools/page.py` isn't found (trusted-catalog W2 on the DGX, 2026-11-17)."""
        import tomllib
        d = self.team()
        (d / 'extensions' / 'stack').mkdir()
        (d / 'extensions' / 'stack' / 'stack.json').write_text(json.dumps(
            {'tasks': {'serve': 'python tools/page.py', 'bad key': 'x', 'multi': 'a\nb'}}))
        tasks = toolhome.team_tasks(d)
        stack = str((d / 'extensions' / 'stack').resolve())
        self.assertEqual(tasks, {'serve': {'cmd': 'python tools/page.py', 'cwd': stack}})
        t = tomllib.loads(toolhome.manifest_text('field-notes', [tool('office-files')], tasks))
        self.assertEqual(t['tasks']['serve'], {'cmd': 'python tools/page.py', 'cwd': stack})

    def test_plain_env_is_utf8(self):
        """On Windows a tool printing Hindi to a pipe crashed in cp1252 (CI 2026-11-17)."""
        with patch.dict(os.environ, {'SECRET_TOKEN': 'x'}):
            env = toolhome._plain_env({'A': '1'})
        self.assertEqual((env['PYTHONUTF8'], env['A']), ('1', '1'))
        self.assertNotIn('SECRET_TOKEN', env)
        out = subprocess.run([sys.executable, '-c', 'print("\\u0928\\u092e\\u0938\\u094d\\u0924\\u0947")'],
                             capture_output=True, env={**env, 'PYTHONIOENCODING': ''}, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.decode('utf-8').strip(), '\u0928\u092e\u0938\u094d\u0924\u0947')


class Registry(Base):
    def fake_pixi(self, team, timeout=3600):
        d = toolhome.env_dir(team)
        (d / '.pixi/envs/default').mkdir(parents=True, exist_ok=True)
        (d / '.pixi/envs/default/blob').write_bytes(b'x' * 1000)
        (d / 'pixi.lock').write_text('version: 6\n')
        return True, '', []

    def install(self, team_dir, tools):
        with patch.object(toolhome, 'pixi_install', self.fake_pixi), \
                patch.object(catalog, 'resources', return_value=self.res()):
            return toolhome.install(team_dir, tools)

    def test_install_shares_models_and_remove_is_refcounted(self):
        a, b = self.team('field-notes'), self.team('comms')
        out = self.install(a, ['office-files'])
        self.assertTrue(out['ok'], out)
        tiny = toolhome.model_path(CATALOG['tools'][0]['models'][0])
        self.assertEqual(tiny.read_bytes(), MODEL)
        self.assertEqual(out['models'], [{'model': 'tiny.bin', 'from': 'catalog'}])
        self.assertEqual(json.loads((a / 'extensions/stack/catalog.json').read_text()), {'tools': ['office-files']})
        self.assertTrue((a / 'extensions/stack/pixi.toml').read_text().startswith(toolhome.MADE_BY))
        self.install(b, ['voice'])
        voice = toolhome.model_path(CATALOG['tools'][1]['models'][0])
        self.assertEqual((voice / 'voice/model.onnx').read_bytes(), b'onnx bytes')
        rows = toolhome.installs()
        self.assertEqual(sorted((r['team'], r['tool']) for r in rows), [('comms', 'voice'),
                                                                        ('field-notes', 'office-files')])
        r = rows[0]
        self.assertEqual(set(r), {'team', 'team_name', 'tool', 'bytes', 'models', 'platform', 'installed_at'})
        # the second team adds office-files too: the model is shared
        self.install(b, ['office-files'])
        self.assertEqual(json.loads((b / 'extensions/stack/catalog.json').read_text())['tools'],
                         ['voice', 'office-files'])
        toolhome.remove('field-notes', 'office-files', a)
        self.assertTrue(tiny.exists())  # comms still uses it
        self.assertFalse(toolhome.env_dir('field-notes').exists())
        self.assertFalse((a / 'extensions/stack/catalog.json').exists())
        self.assertFalse((a / 'extensions/stack/pixi.toml').exists())
        toolhome.remove('comms', 'voice', b)
        self.assertTrue(tiny.exists())  # office-files of comms uses tiny.bin
        self.assertFalse(voice.exists())
        self.assertTrue(toolhome.env_dir('comms').exists())
        out = toolhome.purge_team('comms', b)
        self.assertEqual(out['removed'], ['office-files'])
        self.assertFalse(tiny.exists())
        self.assertEqual(toolhome.installs(), [])
        self.assertEqual(list((self.tmp / 'tools/models').iterdir()), [])

    def test_refuses_with_reasons(self):
        a = self.team()
        with self.assertRaisesRegex(ValueError, 'needs 100000 GB of memory'):
            self.install(a, ['huge-ram'])
        with self.assertRaisesRegex(ValueError, 'numpy'):
            self.install(a, ['voice', 'numpy-old'])
        self.assertEqual(toolhome.installs(), [])

    def test_bad_sha_is_thrown_away_and_source_is_the_fallback(self):
        m = {'name': 'm.bin', 'file': 'models/missing.bin', 'source': 'https://example.org/m.bin',
             'sha256': sha(b'right'), 'bytes': 5, 'unpack': 'none'}
        calls = []

        def fake(url, headers, dest, digest, timeout=120):
            calls.append(url)
            if 'missing' in url:
                return False
            dest.write_bytes(b'right')
            return True
        with patch.object(toolhome, '_download', fake):
            p = toolhome.fetch_model(m)
        self.assertEqual(p.read_bytes(), b'right')
        self.assertEqual(calls[1], 'https://example.org/m.bin')
        bad = {**m, 'file': 'models/tiny.bin', 'sha256': sha(b'other'), 'name': 'n.bin'}
        with self.assertRaisesRegex(ValueError, "did not match"):
            toolhome.fetch_model(bad)
        self.assertFalse(toolhome.model_path(bad).exists())

    def test_model_env_points_at_models(self):
        env = toolhome.model_env(['voice'], CATALOG)
        self.assertTrue(env['IDLI_MODEL_TINY_BIN'].endswith('tiny.bin'))
        self.assertIn('voice', json.loads(env['IDLI_MODEL_PATHS']))

    def test_consent_hook_uses_catalog_words(self):
        a = self.team()
        hook = ROOT / 'desktop/idli-stack-consent.py'

        def ask(tools):
            env = {**os.environ}
            out = subprocess.run([sys.executable, '-I', str(hook), str(a)], env=env, capture_output=True, text=True,
                                 input=json.dumps({'tool_input': {'tools': tools}}), check=True)
            return json.loads(out.stdout)['hookSpecificOutput']
        h = ask(['voice'])
        self.assertEqual(h['permissionDecision'], 'ask')
        for want in ("vetted list", 'Adds: Voice', 'non-commercial licence', 'CC-BY-NC-4.0'):
            self.assertIn(want, h['permissionDecisionReason'])
        self.assertEqual(ask(['huge-ram'])['permissionDecision'], 'deny')
        toolhome.note_consent(a, ['voice'])
        self.assertEqual(ask(['voice'])['permissionDecision'], 'allow')

    def test_overview_groups_by_tool_and_team(self):
        a, b = self.team('field-notes'), self.team('comms')
        self.install(a, ['office-files'])
        self.install(b, ['office-files'])
        o = toolhome.overview()
        self.assertEqual([t['tool'] for t in o['by_tool']], ['office-files'])
        self.assertEqual(len(o['by_tool'][0]['installs']), 2)
        self.assertEqual([t['team_name'] for t in o['by_team']], ['Comms', 'Field Notes'])
        self.assertGreater(o['used'], 0)


class Api(Base):
    """POST /api/tools/* and GET /api/tools on the page server."""

    def setUp(self):
        super().setUp()
        from lib import formserver
        self.data = self.tmp / 'cowork-real'
        self.data.mkdir()
        self.token = 'test-token-0123456789abc'
        self.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), formserver.make_handler(
            formserver.Files(str(self.data)), self.token))
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.base = f'http://127.0.0.1:{self.httpd.server_address[1]}'
        self.teams = {'teams': [{'id': 'field-notes', 'name': 'Field Notes'}]}
        self.folder = self.team('field-notes')

    def tearDown(self):
        self.httpd.shutdown()
        super().tearDown()

    def call(self, path, body=None):
        req = urllib.request.Request(f'{self.base}{path}?t={self.token}', method='POST' if body is not None else 'GET',
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    def test_tools_page_api(self):
        from lib import teams
        fake = Registry.fake_pixi
        with patch.object(teams, 'list_teams', return_value=self.teams), \
                patch.object(teams, '_team_folder', return_value=str(self.folder)), \
                patch.object(toolhome, 'pixi_install', lambda team, timeout=3600: fake(self, team)), \
                patch.object(catalog, 'resources', return_value=self.res()):
            code, out = self.call('/api/tools')
            self.assertEqual(code, 200)
            self.assertEqual(out['by_tool'], [])
            self.assertEqual(out['teams'], [{'id': 'field-notes', 'name': 'Field Notes'}])
            self.assertIn('office-files', [t['id'] for t in out['catalog']])
            code, out = self.call('/api/tools/add', {'team': 'field-notes', 'tool': 'huge-ram', 'check_only': True})
            self.assertFalse(out['ok'])
            self.assertIn('memory', out['reasons'][0])
            code, out = self.call('/api/tools/add', {'team': 'field-notes', 'tool': 'office-files', 'check_only': True})
            self.assertTrue(out['ok'])
            self.assertIn('Adds: Office Files', out['summary'])
            code, out = self.call('/api/tools/add', {'team': 'field-notes', 'tool': 'office-files', 'wait': True})
            self.assertTrue(out['ok'], out)
            code, out = self.call('/api/tools')
            self.assertEqual(out['by_team'][0]['installs'][0]['tool'], 'office-files')
            code, out = self.call('/api/tools/remove', {'team': 'field-notes', 'tool': 'office-files'})
            self.assertEqual(out['removed'], ['office-files'])
            self.assertTrue(self.call('/api/tools/add', {'team': 'field-notes', 'tool': 'office-files',
                                                         'wait': True})[1]['ok'])
            code, out = self.call('/api/tools/remove', {'team': 'field-notes'})
            self.assertEqual(out['removed'], ['office-files'])
            code, out = self.call('/api/tools/remove', {'team': '../etc'})
            self.assertEqual(code, 400)
        with self.assertRaises(urllib.error.HTTPError):  # the page's token is needed
            urllib.request.urlopen(f'{self.base}/api/tools?t=wrong', timeout=10)


@unittest.skipUnless(os.environ.get('IDLI_STACK_SLOW'), 'installs from the internet')
class RealCatalog(unittest.TestCase):
    def test_install_a_tiny_real_tool(self):
        try:
            with patch.dict(os.environ, {'IDLI_TOOLS_HOME': tempfile.mkdtemp(prefix='idli-real-tools-',
                                                                               dir=_big_tmp()),
                                         'IDLI_TOOLS_ENVS': tempfile.mkdtemp(prefix='idli-real-envs-')}):
                cat = catalog.load(refresh=True)
                ids = [t['id'] for t in cat['tools']]
        except ValueError:
            self.skipTest('the real catalog does not answer')
        tid = 'office-files' if 'office-files' in ids else None
        if not tid:
            self.skipTest('no small tool in the real catalog')
        home = tempfile.mkdtemp(prefix='idli-real-tools-', dir=_big_tmp())
        d = Path(tempfile.mkdtemp(prefix='idli-real-team-')) / 'real-test'
        (d / 'extensions/stack').mkdir(parents=True)
        (d / 'team.json').write_text('{"name": "Real test"}')
        envs = tempfile.mkdtemp(prefix='idli-real-envs-')  # symlinks: never on an exFAT disk
        with patch.dict(os.environ, {'IDLI_TOOLS_HOME': home, 'IDLI_TOOLS_ENVS': envs + '/envs'}):
            try:
                out = toolhome.install(d, [tid])
                self.assertTrue(out['ok'], out)
                self.assertTrue(toolhome.installed(d))
                from lib import stackwall
                r = stackwall.run(d, ['python', '-c', 'import sys; print(sys.version)'])
                self.assertTrue(r['ok'], r['output'])
            finally:
                toolhome.purge_team('real-test', d)
                for p in (home, envs, d.parent):
                    shutil.rmtree(p, ignore_errors=True)


def _big_tmp():
    return '/mnt/seagate/tmp' if os.path.isdir('/mnt/seagate/tmp') else None


if __name__ == '__main__':
    unittest.main()
