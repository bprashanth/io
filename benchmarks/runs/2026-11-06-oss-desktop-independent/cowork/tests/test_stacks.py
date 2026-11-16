"""Team stacks (narrative/TEAM_STACKS.md): the stack files, consent, the egress proxy, the model door, and the wall.

Fast by default. IDLI_STACK_SLOW=1 also installs a small stack from the internet and runs it in the wall."""
import http.server
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import stackwall, teamcaps  # noqa: E402

TOML = """[workspace]
name = "t"
channels = ["conda-forge"]
platforms = ["linux-64", "linux-aarch64"]

[dependencies]
python = "3.11.*"
"""


def team(stack=None, toml=TOML):
    d = Path(tempfile.mkdtemp(prefix='idli-stack-test-'))
    s = d / 'extensions' / 'stack'
    s.mkdir(parents=True)
    (s / 'pixi.toml').write_text(toml)
    (s / 'stack.json').write_text(json.dumps(stack or {}))
    return d


def connect(sock_path, line):
    c = socket.socket(socket.AF_UNIX)
    c.settimeout(40)
    c.connect(str(sock_path))
    c.sendall(line.encode() + b'\r\n\r\n')
    got = c.recv(200).decode('latin-1')
    c.close()
    return got


class Spec(unittest.TestCase):
    def test_repos_must_be_github_and_pinned(self):
        d = team({'repos': [{'url': 'https://gitlab.com/a/b', 'ref': 'v1'},
                            {'url': 'https://github.com/a/b'},
                            {'url': 'https://github.com/snakers4/silero-vad', 'ref': 'v5.1.2'}]})
        s, problems = stackwall.spec(d)
        self.assertEqual([r['name'] for r in s['repos']], ['silero-vad'])
        self.assertEqual(len(problems), 2)

    def test_downloads_stay_inside(self):
        d = team({'downloads': [{'url': 'https://x.org/a', 'to': '../../a'}, {'url': 'http://x.org/a', 'to': 'm/a'},
                                {'url': 'https://x.org/a', 'to': 'models/a'}]})
        s, problems = stackwall.spec(d)
        self.assertEqual([f['to'] for f in s['downloads']], ['models/a'])
        self.assertEqual(len(problems), 2)

    def test_hosts_match_whole_labels(self):
        self.assertTrue(stackwall._allowed('codeload.github.com', stackwall.INSTALL_HOSTS))
        self.assertTrue(stackwall._allowed('objects.githubusercontent.com', stackwall.INSTALL_HOSTS))
        self.assertFalse(stackwall._allowed('evilgithub.com', stackwall.INSTALL_HOSTS))
        self.assertFalse(stackwall._allowed('github.com.evil.org', stackwall.INSTALL_HOSTS))
        self.assertFalse(stackwall._allowed('example.com', stackwall.INSTALL_HOSTS))

    def test_summary_is_plain_and_names_extra_hosts(self):
        d = team({'why': 'Cut videos', 'hosts': ['storage.googleapis.com'], 'model': True,
                  'repos': [{'url': 'https://github.com/a/b', 'ref': 'v1', 'license': 'MIT'}]},
                 TOML + '\n[pypi-dependencies]\nsilero-vad = "==5.1.2"\n')
        text = stackwall.summary(d)
        for want in ('For: Cut videos', 'silero-vad', 'From GitHub: a/b at v1 (MIT)',
                     'Also allowed while installing: storage.googleapis.com', 'private model'):
            self.assertIn(want, text)
        self.assertNotIn('python', text.split('Packages:')[1].split('\n')[0])


class Consent(unittest.TestCase):
    def test_asks_again_only_for_something_new(self):
        d = team({'downloads': [{'url': 'https://huggingface.co/a/b.onnx', 'to': 'models/b.onnx'}]},
                 TOML + 'numpy = "*"\n')
        self.assertFalse(stackwall.agreed(d))
        stackwall._note_consent(d)  # what install() does once the person said yes
        self.assertTrue(stackwall.agreed(d))
        (d / 'extensions/stack/pixi.toml').write_text(TOML + 'numpy = "<2"\n')  # another version: no new question
        self.assertTrue(stackwall.agreed(d))
        (d / 'extensions/stack/pixi.toml').write_text(TOML + 'numpy = "<2"\nopencv = "*"\n')  # a new package: ask
        self.assertFalse(stackwall.agreed(d))

    def test_consent_lives_outside_extensions(self):
        d = team()
        stackwall._note_consent(d)
        self.assertFalse(stackwall._consent_file(d).is_relative_to(d / 'extensions'))

    def test_hook_asks_with_idlis_words(self):
        import subprocess
        d = team({'why': 'Read voice notes'})
        out = subprocess.run([sys.executable, '-I', str(ROOT / 'desktop/idli-stack-consent.py'), str(d)],
                             input='{}', capture_output=True, text=True, check=True)
        h = json.loads(out.stdout)['hookSpecificOutput']
        self.assertEqual(h['permissionDecision'], 'ask')
        self.assertIn('Read voice notes', h['permissionDecisionReason'])
        stackwall._note_consent(d)
        out = subprocess.run([sys.executable, '-I', str(ROOT / 'desktop/idli-stack-consent.py'), str(d)],
                             input='{}', capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(out.stdout)['hookSpecificOutput']['permissionDecision'], 'allow')


class Doors(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='idli-door-test-', dir='/tmp'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_proxy_refuses_other_hosts_and_plain_http(self):
        log = []
        p = stackwall.EgressProxy(self.tmp / 'e.sock', stackwall.INSTALL_HOSTS, log).start()
        try:
            self.assertIn('403', connect(self.tmp / 'e.sock', 'CONNECT example.com:443 HTTP/1.1'))
            self.assertIn('403', connect(self.tmp / 'e.sock', 'CONNECT github.com:22 HTTP/1.1'))
            self.assertIn('403', connect(self.tmp / 'e.sock', 'GET http://github.com/ HTTP/1.1'))
        finally:
            p.stop()
        self.assertEqual([(e['host'], e['allowed']) for e in log][:2], [('example.com', False), ('github.com', False)])

    @unittest.skipUnless(os.environ.get('IDLI_STACK_SLOW'), 'needs the internet')
    def test_proxy_lets_allowed_hosts_through(self):
        p = stackwall.EgressProxy(self.tmp / 'e.sock', stackwall.INSTALL_HOSTS, []).start()
        try:
            self.assertIn('200', connect(self.tmp / 'e.sock', 'CONNECT github.com:443 HTTP/1.1'))
        finally:
            p.stop()

    def test_model_door_passes_chat_only(self):
        hits = []

        class Fake(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                hits.append(self.path)
                body = b'{"ok": true}'
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            do_GET = do_POST

            def log_message(self, *a):
                pass
        srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Fake)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        door = stackwall.ModelDoor(self.tmp / 'm.sock', f'http://127.0.0.1:{srv.server_address[1]}').start()
        try:
            ok = connect(self.tmp / 'm.sock', 'POST /v1/chat/completions HTTP/1.1\r\nContent-Length: 0')
            self.assertIn('200', ok)
            self.assertIn('403', connect(self.tmp / 'm.sock', 'GET /slots HTTP/1.1'))
            self.assertIn('403', connect(self.tmp / 'm.sock', 'POST /v1/completions/../../props HTTP/1.1'))
        finally:
            door.stop()
            srv.shutdown()
        self.assertEqual(hits, ['/v1/chat/completions'])


class Manifest(unittest.TestCase):
    def test_tool_and_app_need_their_fields(self):
        d = team()
        ext = d / 'extensions'
        teamcaps.ensure(d)
        (ext / 'cut.py').write_text('def run(inputs, args, out):\n    return {}\n')
        (ext / 'tests/test_cut.py').write_text('pass\n')
        (ext / 'manifest.json').write_text(json.dumps({'capabilities': [
            {'id': 'cut', 'title': 'Cut', 'kind': 'tool', 'takes': ['video'], 'entry': 'cut.py',
             'test': 'tests/test_cut.py'},
            {'id': 'bad-tool', 'title': 'Bad', 'kind': 'tool', 'entry': 'cut.py', 'test': 'tests/test_cut.py'},
            {'id': 'page', 'title': 'Page', 'kind': 'app', 'serve': 'serve', 'test': 'tests/test_cut.py'},
            {'id': 'bad-page', 'title': 'Bad page', 'kind': 'app', 'serve': 'rm -rf /', 'test': 'tests/test_cut.py'},
        ]}))
        good, problems = teamcaps.manifest(d)
        self.assertEqual([c['id'] for c in good], ['cut', 'page'])
        self.assertTrue(good[1]['stack'])
        self.assertEqual(len(problems), 2)

    def test_tools_run_in_the_wall_on_originals(self):
        d = team()
        ext = d / 'extensions'
        teamcaps.ensure(d)
        (ext / 'count.py').write_text(
            'import os, socket\n'
            'def run(inputs, args, out):\n'
            '    open(os.path.join(out, "n.txt"), "w").write(str(args["n"]))\n'
            '    try:\n'
            '        socket.create_connection(("1.1.1.1", 443), 3); net = "open"\n'
            '    except OSError:\n'
            '        net = "blocked"\n'
            '    return {"size": os.path.getsize(inputs[0]), "net": net}\n')
        src = d / 'drive' / 'a.mp4'
        src.parent.mkdir()
        src.write_bytes(b'x' * 10)
        cap = {'id': 'count', 'title': 'Count', 'kind': 'tool', 'takes': ['video'], 'entry': 'count.py'}
        res = teamcaps.run_tool(d, cap, [src], {'n': 3})
        self.assertEqual(res['files'], ['n.txt'])
        self.assertEqual(res['result']['size'], 10)
        if shutil.which('bwrap'):
            self.assertEqual(res['result']['net'], 'blocked')
        with self.assertRaises(ValueError):
            teamcaps.run_tool(d, cap, [d / 'team.json'], {})


@unittest.skipUnless(os.environ.get('IDLI_STACK_SLOW') and shutil.which('bwrap'), 'installs from the internet')
class Wall(unittest.TestCase):
    def test_install_pins_and_runs_without_network(self):
        d = team({'why': 'test', 'repos': [{'url': 'https://github.com/snakers4/silero-vad', 'ref': 'v5.1.2'}],
                  'model': False}, TOML + 'numpy = "*"\n\n[tasks]\nprobe = "python tools/probe.py"\n')
        tools = d / 'extensions/stack/tools'
        tools.mkdir()
        (tools / 'probe.py').write_text(
            'import json, os, socket\nr = {}\n'
            'try:\n    socket.create_connection(("1.1.1.1", 443), 3); r["net"] = "open"\n'
            'except OSError:\n    r["net"] = "blocked"\n'
            'r["home"] = sorted(os.listdir(os.path.expanduser("~")))\n'
            'r["keys"] = sorted(k for k in os.environ if "KEY" in k or "TOKEN" in k)\n'
            'import numpy; r["numpy"] = numpy.__version__\n'
            'r["repo"] = os.path.isdir(os.environ["IDLI_STACK"] + "/repos/silero-vad/src")\n'
            'print(json.dumps(r))\n')
        res = stackwall.install(d)
        self.assertTrue(res['ok'], res)
        self.assertTrue(all(h['allowed'] for h in res['hosts']))
        lock = json.loads((d / 'extensions/stack/stack-lock.json').read_text())
        self.assertRegex(lock['repos']['silero-vad']['commit'], r'^[0-9a-f]{40}$')
        self.assertTrue((d / 'extensions/stack/pixi.lock').exists())
        os.environ['FAKE_API_KEY'] = 'x'
        run = stackwall.run(d, ['probe'])
        self.assertTrue(run['ok'], run['output'])
        probe = json.loads([ln for ln in run['output'].splitlines() if ln.startswith('{')][-1])
        self.assertEqual(probe['net'], 'blocked')
        self.assertEqual(probe['keys'], [])
        self.assertTrue(probe['repo'])


if __name__ == '__main__':
    unittest.main()
