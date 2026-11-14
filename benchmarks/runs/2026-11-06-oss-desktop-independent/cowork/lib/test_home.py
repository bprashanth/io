"""Home/Mini proof of concept: synthetic fixtures, fake Drive, Paseo and model router.

Run: .venv/bin/python -m pytest lib/test_home.py -q
Browser and screenshots: HOME_BROWSER=1 .venv/bin/python -m pytest lib/test_home.py -q
"""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from lib import ccproxy, driveindex, formserver, home, idli_mcp, privacy, muse, uiswitch

HERE = Path(__file__).resolve().parent.parent
FIXTURES = HERE.parent.parent / '2026-11-13-grounded-9b/fixtures/drive'
AGENT = 'abcdef12-1234-1234-1234-abcdef123456'
TOKEN = 'home-test-placeholder'


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path / 'data'
    (root / 'drive').mkdir(parents=True)
    for path in FIXTURES.glob('*.xlsx'):
        shutil.copyfile(path, root / 'drive' / path.name)
    work = tmp_path / 'claude'
    work.mkdir()
    monkeypatch.setenv('IDLI_DATA', str(root))
    monkeypatch.setenv('IDLI_CLAUDE_WORK', str(work))
    monkeypatch.setenv('IDLI_SCANNER', 'http://127.0.0.1:1/scan')
    monkeypatch.setenv('MUSE_URL', 'http://127.0.0.1:1')
    monkeypatch.setenv('IDLI_CDP_PORT', '1')
    monkeypatch.setenv('COWORK_LOG', '')
    monkeypatch.setattr(driveindex, 'DB', str(tmp_path / 'no-index.duckdb'))
    monkeypatch.setattr(uiswitch, 'APP', None)
    return root, work


def files():
    return [{'title': p.stem, 'local': 'drive/' + p.name} for p in sorted(FIXTURES.glob('*.xlsx'))]


@contextmanager
def running(handler):
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def api(server, path, body=None, token=TOKEN):
    url = f'http://127.0.0.1:{server.server_port}' + path + ('&' if '?' in path else '?') + 't=' + token
    req = Request(url, None if body is None else json.dumps(body).encode(), {'Content-Type': 'application/json'})
    with urlopen(req, timeout=30) as response:
        return json.load(response)


@pytest.fixture
def paseo(workspace, tmp_path, monkeypatch):
    root, _ = workspace
    exe = tmp_path / 'bin/paseo'
    exe.parent.mkdir()
    record = tmp_path / 'paseo.jsonl'
    agents = tmp_path / 'agents.json'
    agents.write_text('[]')
    exe.write_text('#!' + sys.executable + '\n' + '''import json, os, sys
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['FAKE_RECORD'],'a') as f:
    f.write(json.dumps({'args':args,'paseo_env':[k for k in os.environ if k.startswith('PASEO_')]})+'\\n')
if args[:2]==['workspace','ls']:
    print(json.dumps([{'workspaceId':'other','name':'Other','cwd':os.environ['IDLI_DATA']},
                      {'workspaceId':'drivey','name':'Drivey','cwd':os.environ['IDLI_DATA']}]))
elif args[:2]==['terminal','ls']:
    t=Path(os.environ['FAKE_AGENTS']).with_name('terms.json')
    print(t.read_text() if t.exists() else '[]')
elif args[:2]==['terminal','create']:
    t=Path(os.environ['FAKE_AGENTS']).with_name('terms.json')
    t.write_text(json.dumps([{'id':'term-1','workspaceId':'drivey'}])); print(json.dumps({'id':'term-1'}))
elif args[0]=='ls': print(Path(os.environ['FAKE_AGENTS']).read_text())
elif args[0]=='run':
    agent={'id':'abcdef12-1234-1234-1234-abcdef123456','provider':'idli-claude','workspaceId':'drivey',
           'status':'idle','labels':{'idli.home':'1'}}
    Path(os.environ['FAKE_AGENTS']).write_text(json.dumps([agent]))
    print(json.dumps({'agentId':agent['id']}))
else: print('{}')
''')
    exe.chmod(0o755)
    monkeypatch.setenv('PATH', str(exe.parent) + os.pathsep + os.environ['PATH'])
    monkeypatch.setenv('FAKE_RECORD', str(record))
    monkeypatch.setenv('FAKE_AGENTS', str(agents))
    monkeypatch.setenv('PASEO_AGENT_ID', AGENT)
    monkeypatch.setenv('PASEO_HOME', '/unused-test-path')
    return record, agents


def test_prepare_and_toggle(workspace):
    root, _ = workspace
    question = 'Compare Yerawada Ward with Village A'
    got = home.prepare(root, files(), question)
    assert len(got['files']) == 2
    assert 'Yerawada' not in got['masked_question'] and 'Village A' not in got['masked_question']
    tracker = got['reviews'][0]
    assert len(tracker['tabs']) == 3
    for f in files():
        setting = privacy.get(root, f['local'])
        assert setting['mode'] == 'mask' and setting['review'] == 'ask'
    rows = [r for tab in tracker['tabs'] for r in tab['suggestions']]
    assert all(r['samples'] and r['as_sent'] and r['reason'] for r in rows)
    assert next(r for r in rows if r['column'] == 'Name')['mask']
    rel = 'drive/households.xlsx'
    before = privacy.get(root, rel)
    privacy.set(root, rel, columns={**before['columns'], 'ward': False})
    after = home.prepare(root, files(), question)
    assert 'Yerawada Ward' in after['masked_question'] and 'Village A' not in after['masked_question']
    transform = ccproxy.Transformer(root)
    outgoing, _ = transform.outbound({'messages': [{'role': 'user', 'content': question}]})
    assert 'Yerawada Ward' in outgoing['messages'][0]['content']
    privacy.set(root, rel, columns={**before['columns'], 'ward': True})
    assert 'Yerawada' not in home.prepare(root, files(), question)['masked_question']
    assert privacy.get(root, rel)['review'] == 'ask'


def test_search_and_download(workspace, monkeypatch, tmp_path):
    root, _ = workspace
    monkeypatch.setattr(driveindex, 'search', lambda q, limit: {'results': [
        {'id': 'fake-drive-id', 'name': 'Programme', 'kind': 'Google Sheets', 'folder': 'NGO/Field'}]})
    hits = home.search(root, 'house')['results']
    assert hits[0]['folder'] == 'on this computer' and hits[-1]['folder'] == 'NGO/Field'
    fake = tmp_path / 'fake-drive'
    fake.mkdir()
    shutil.copyfile(FIXTURES / 'households.xlsx', fake / 'fake-drive-id.xlsx')
    monkeypatch.setenv('IDLI_DRIVE_FAKE', str(fake))
    got = home.prepare(root, [{'id': 'fake-drive-id', 'title': 'Programme'}], 'Yerawada Ward')
    local = root / got['files'][0]['local']
    assert local.is_file() and home.read(str(local) + '.source.json')['id'] == 'fake-drive-id'
    home.prepare(root, [{'id': 'fake-drive-id', 'title': 'households'}], 'test')
    assert home.read(str(root / 'drive/households-fake-drive-i.xlsx') + '.source.json')['id'] == 'fake-drive-id'
    with pytest.raises(ValueError):
        home.prepare(root, [{'local': '../outside.xlsx', 'title': 'bad'}], '')


def test_send_terminal_first_then_typed(workspace, paseo, monkeypatch):
    """Send starts the person's Claude CLI in a Drivey terminal (masked launcher) the first time, then types into it."""
    root, _ = workspace
    record, agents = paseo
    shown = []
    monkeypatch.setattr(uiswitch, 'show_terminal', lambda w, t, side: shown.append((w, t, side)) or {'ok': True})
    chosen = home.prepare(root, files(), 'Yerawada Ward')['files']
    assert home.send(root, chosen, 'Yerawada Ward')['terminal'] == 'term-1'
    home.send(root, chosen, 'Compare Village A')
    calls = [json.loads(line)['args'] for line in record.read_text().splitlines()]
    creates = [c for c in calls if c[:2] == ['terminal', 'create']]
    keys = [c[-1] for c in calls if c[:2] == ['terminal', 'send-keys']]
    assert len(creates) == 1 and creates[0][creates[0].index('--workspace') + 1] == 'drivey'
    assert keys[0].startswith('exec ') and 'claude-masked.sh' in keys[0] and 'Yerawada Ward' in keys[0]
    assert keys[1] == '\r' and 'Compare Village A' in keys[2] and keys[3] == '\r'
    assert not any(json.loads(line)['paseo_env'] for line in record.read_text().splitlines())
    assert shown == [('drivey', 'term-1', 'right')] * 2
    assert home.read(root / '.idli/home.json')['terminal'] == 'term-1'


def script(work):
    path = work / 'answer.py'
    path.write_text('''import argparse, json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=2);a=p.parse_args()
assert Path('drive/households.xlsx').is_file()
print('| Group | Count |\\n|---|---|\\n| A | '+str(a.n)+' |')
print(json.dumps({'vega_lite':{'mark':'bar','encoding':{'x':{'field':'Group','type':'nominal'},'y':{'field':'Count','type':'quantitative'}}},'data':[{'Group':'A','Count':a.n},{'Group':'B','Count':a.n+1}]}))
''')
    return path


def questions(work):
    return [{'id': 'count', 'question': 'Count households', 'script': str(script(work)),
             'params': {'n': {'type': 'number', 'default': 2}}}]


def test_mcp_stdio_and_mini(workspace, monkeypatch):
    root, work = workspace
    q = questions(work)
    home.write(root / 'drive/households.xlsx.source.json', {'id': 'drive-households', 'url': 'https://example.invalid/sheet'})
    home.write(root / '.idli/home.json', {'agent': AGENT, 'files': [{'title': 'Households', 'local': 'drive/households.xlsx'}]})
    csv = work / 'chart.csv'
    csv.write_text('Group,Count\nA,2\nB,3\n')
    browser_calls = []
    class Browser(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            browser_calls.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            data = json.dumps({'result': {'content': [{'type': 'text', 'text': 'opened'}]}}).encode()
            self.send_response(200); self.end_headers(); self.wfile.write(data)
    with running(formserver.make_handler(formserver.Files(root), TOKEN)) as server, running(Browser) as browser:
        home.write(root / '.idli/form-server.json', {'port': server.server_port, 'token': TOKEN})
        env = {**os.environ, 'PASEO_MCP_URL': f'http://127.0.0.1:{browser.server_port}/mcp', 'PASEO_AGENT_ID': AGENT}
        requests = [
            {'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18'}},
            {'id': 2, 'method': 'tools/list'},
            {'id': 3, 'method': 'tools/call', 'params': {'name': 'idli_show', 'arguments': {
                'title': 'Counts', 'vega_lite': {'mark': 'bar'}, 'data_csv': str(csv)}}},
            {'id': 4, 'method': 'tools/call', 'params': {'name': 'idli_save_mini', 'arguments': {
                'name': 'Households', 'goal': 'Count checked households', 'questions': q}}},
            {'id': 5, 'method': 'tools/call', 'params': {'name': 'idli_show', 'arguments': {
                'title': 'bad', 'vega_lite': {}, 'data_csv': '/etc/passwd'}}}]
        r = subprocess.run([sys.executable, '-I', str(HERE / 'lib/idli_mcp.py')],
                           input='\n'.join(json.dumps({'jsonrpc': '2.0', **x}) for x in requests) + '\n',
                           capture_output=True, text=True, env=env, timeout=30)
        assert r.returncode == 0 and not r.stderr
        replies = [json.loads(line) for line in r.stdout.splitlines()]
        assert replies[2]['result']['content'][0]['text'] == 'shown in Idli'
        assert not replies[3]['result'].get('isError') and replies[4]['result']['isError']
        assert len(browser_calls) == 1
        views = list((root / 'views').glob('*.json'))
        assert len(views) == 1
        view = home.read(views[0])
        assert view['data_csv'] == str(csv) and view['agent'] == AGENT
        assert len(api(server, '/api/view?id=' + views[0].stem)['data']) == 2
        mini = home.read(root / 'minis/households/mini.json')
        assert mini['files'][0]['id'] == 'drive-households'
        assert (root / 'minis/households/question_1.py').is_file()
        result = api(server, '/api/mini/run', {'id': 'households', 'qid': 'count', 'params': {'n': 7}})
        assert '| A | 7 |' in result['text'] and result['chart']['data'][0]['Count'] == 7
        assert result['agent'] == AGENT
        mapped = api(server, '/api/mini/map', {'id': 'households', 'question': 'count households'})
        assert mapped == {'qid': 'count', 'params': {'n': 2}, 'method': 'word match'}
        with pytest.raises(HTTPError) as err:
            api(server, '/api/mini?id=households', token='wrong')
        assert err.value.code == 403
        with pytest.raises(ValueError): home.view(root, '../escape')
        with pytest.raises(ValueError): home.run_mini(root, 'households', 'count', {'bad': 1})


def test_router_schema_and_validation(workspace, monkeypatch):
    root, work = workspace
    q = questions(work)
    q.append({**q[0], 'id': 'income', 'question': 'Average income'})
    home.write(root / 'minis/test/mini.json', {'name': 'Test', 'goal': '', 'questions': q})
    seen = []
    class Router(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            seen.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            value = {'qid': 'income', 'params': {'n': 4}}
            data = json.dumps({'choices': [{'message': {'content': json.dumps(value)}}]}).encode()
            self.send_response(200); self.end_headers(); self.wfile.write(data)
    with running(Router) as router:
        monkeypatch.setenv('MUSE_URL', f'http://127.0.0.1:{router.server_port}')
        got = home.map_question(root, 'test', 'mean earnings')
    assert got == {'qid': 'income', 'params': {'n': 4}, 'method': 'idli-9b'}
    assert seen[0]['model'] == 'idli-9b'
    assert seen[0]['response_format']['json_schema']['schema']['properties']['qid']['enum'] == ['count', 'income']
    monkeypatch.setenv('MUSE_URL', 'http://127.0.0.1:1')
    assert home.map_question(root, 'test', 'average income')['qid'] == 'income'


@pytest.mark.skipif(os.environ.get('HOME_BROWSER') != '1', reason='Set HOME_BROWSER=1 to run Chromium and save screenshots')
def test_browser(workspace, paseo, monkeypatch):
    from playwright.sync_api import sync_playwright
    root, work = workspace
    monkeypatch.setattr(idli_mcp, 'page_url', lambda page, ident: '/' + page + '?id=' + ident)
    q = questions(work)
    idli_mcp.idli_save_mini('Households', 'Count households on this computer', q)
    saved_mini = root / 'minis/households/mini.json'
    home.write(saved_mini, {**home.read(saved_mini), 'agent': None})
    home.write(root / 'views/counts.json', {'title': 'Household counts', 'agent': AGENT,
        'data_csv': str(work / 'chart.csv'), 'spec': {'mark': 'bar', 'encoding': {
            'x': {'field': 'Group', 'type': 'nominal'}, 'y': {'field': 'Count', 'type': 'quantitative'}}}})
    (work / 'chart.csv').write_text('Group,Count\nA,2\nB,3\n')
    shots = HERE / 'HOME_SHOTS'
    shots.mkdir(exist_ok=True)
    with running(formserver.make_handler(formserver.Files(root), TOKEN)) as server, sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 480, 'height': 900})
        errors = []
        page.on('pageerror', lambda err: errors.append(str(err)))
        def go(path):
            page.goto(f'http://127.0.0.1:{server.server_port}' + path + ('&' if '?' in path else '?') + 't=' + TOKEN)
        go('/home')
        assert page.evaluate("getComputedStyle(document.body).backgroundColor") == 'rgb(246, 245, 242)'
        page.locator('#search').fill('house')
        page.locator('#hits button').first.wait_for()
        page.locator('#search').press('Enter')
        page.locator('#question').fill('Compare Yerawada Ward with @field')
        page.locator('#mentions button').first.wait_for()
        page.locator('#question').press('Tab')
        assert page.locator('#chips .chip').count() == 2
        page.locator('#question').fill('Compare Yerawada Ward with Village A')
        page.locator('#next').click()
        page.locator('#review').wait_for(state='visible')
        assert page.locator('#reviews article').count() == 2
        assert 'Yerawada' not in page.locator('#masked').inner_text()
        page.screenshot(path=str(shots / 'home-review.png'), full_page=True)
        page.locator('input[data-col="ward"]').uncheck()
        page.wait_for_function("() => document.querySelector('#masked').textContent.includes('Yerawada Ward')")
        page.locator('#send').click()
        page.wait_for_function("() => document.querySelector('#status').textContent.includes('Claude has it')")
        assert not page.locator('#chips .chip').count() and not page.locator('#question').input_value()
        assert any(json.loads(line)['args'][:2] == ['terminal', 'create'] for line in paseo[0].read_text().splitlines())
        page.screenshot(path=str(shots / 'home-sent.png'), full_page=True)
        go('/view?id=counts')
        page.locator('#viz .mark-rect path').first.wait_for()
        page.locator('#viz .mark-rect path').first.click()
        page.locator('#pop').wait_for(state='visible')
        assert page.get_by_text('Show the rows behind it', exact=True).is_visible()
        page.screenshot(path=str(shots / 'view-popover.png'), full_page=True)
        page.get_by_text('Show the rows behind it', exact=True).click()
        page.wait_for_function("() => document.querySelector('#pop').textContent.includes('Sent to Claude')")
        page.emulate_media(color_scheme='dark')
        page.set_viewport_size({'width': 360, 'height': 800})
        go('/mini?id=households')
        page.locator('.run').wait_for()
        page.locator('[data-param="n"]').fill('7')
        page.locator('.run').click()
        page.locator('#answer table').wait_for()
        assert '7' in page.locator('#answer').inner_text()
        page.locator('#viz .mark-rect path').first.wait_for()
        page.locator('#viz .mark-rect path').first.click()
        assert page.locator('#pop').is_hidden()  # no Claude agent on this Mini
        page.locator('#ask').fill('count households')
        page.locator('#match').click()
        page.wait_for_function("() => document.querySelector('#mapping').textContent.includes('word match')")
        assert 'Check the inputs' in page.locator('#mapping').inner_text()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(shots / 'mini-dark.png'), full_page=True)
        assert not errors
        browser.close()


def test_launcher_config_and_proxy(tmp_path):
    """Exercise the real shell wrapper with a fake proxy and Claude, without any user configuration."""
    clone = tmp_path / 'cowork'
    (clone / 'desktop').mkdir(parents=True)
    (clone / 'idli').mkdir()
    (clone / '.venv/bin').mkdir(parents=True)
    shutil.copyfile(HERE / 'desktop/claude-masked.sh', clone / 'desktop/claude-masked.sh')
    shutil.copyfile(HERE / 'idli/CLAUDE-masked.md', clone / 'idli/CLAUDE-masked.md')
    py = clone / '.venv/bin/python'
    py.write_text('#!' + sys.executable + '\n' + '''import subprocess, sys
if 'ensure' in sys.argv: print('18870')
else: sys.exit(subprocess.run([sys.executable,*sys.argv[1:]]).returncode)
''')
    py.chmod(0o755)
    fake = tmp_path / 'claude'
    fake.write_text('#!' + sys.executable + '\n' + '''import json, os, sys
from pathlib import Path
Path(os.environ['LAUNCH_RECORD']).write_text(json.dumps({'args':sys.argv[1:],'cwd':os.getcwd(),
    'base_url':os.environ.get('ANTHROPIC_BASE_URL'),'data':os.environ.get('IDLI_DATA')}))
''')
    fake.chmod(0o755)
    data, work = tmp_path / 'data', tmp_path / 'work'
    (data / 'drive').mkdir(parents=True)
    record = tmp_path / 'launch.json'
    env = {'HOME': str(tmp_path), 'PATH': '/usr/bin:/bin', 'IDLI_DATA': str(data),
           'IDLI_CLAUDE_WORK': str(work), 'CLAUDE_BIN': str(fake), 'LAUNCH_RECORD': str(record)}
    r = subprocess.run(['/bin/sh', str(clone / 'desktop/claude-masked.sh'), '--print', 'test'],
                       capture_output=True, text=True, env=env, timeout=10)
    assert r.returncode == 0 and not r.stdout and not r.stderr
    launch = home.read(record)
    assert launch['base_url'] == 'http://127.0.0.1:18870' and launch['cwd'] == str(work)
    assert launch['args'] == ['--mcp-config=' + str(work / '.idli-mcp.json'), '--print', 'test']
    config = home.read(work / '.idli-mcp.json')['mcpServers']['idli']
    assert config['args'] == ['-I', str(clone / 'lib/idli_mcp.py')]
    assert (work / '.idli-mcp.json').stat().st_mode & 0o777 == 0o600
    assert (work / 'drive').resolve() == data / 'drive'


def test_mcp_path_confinement(workspace, tmp_path, monkeypatch):
    root, work = workspace
    outside = tmp_path / 'outside.csv'
    outside.write_text('a,b\n1,2\n')
    (work / 'escape.csv').symlink_to(outside)
    with pytest.raises(ValueError): home.allowed_path(root, str(work / 'escape.csv'))
    (root / 'views').symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError): idli_mcp.idli_show('bad', {}, str(work / 'escape.csv'))
    (work / 'valid.csv').write_text('a,b\n1,2\n')
    with pytest.raises(ValueError): idli_mcp.idli_show('bad destination', {}, str(work / 'valid.csv'))
    with pytest.raises(ValueError): idli_mcp.idli_save_mini('bad', '', [{
        'id': 'bad', 'question': 'Bad', 'script': str(outside), 'params': {}}])
