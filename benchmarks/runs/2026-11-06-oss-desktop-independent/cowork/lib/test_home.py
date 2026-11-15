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
    monkeypatch.setenv('IDLI_HOME', str(tmp_path / 'idli-home'))
    monkeypatch.setenv('IDLI_SCANNER', 'http://127.0.0.1:1/scan')
    monkeypatch.setenv('MUSE_URL', 'http://127.0.0.1:1')
    monkeypatch.setenv('IDLI_9B_URL', 'http://127.0.0.1:1')
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
    assert keys[0].startswith('IDLI_WORKSPACE=drivey exec ') and 'claude-masked.sh' in keys[0] and 'Yerawada Ward' in keys[0]
    assert keys[1] == '\r' and 'Compare Village A' in keys[2] and keys[3] == '\r'
    assert not any(set(json.loads(line)['paseo_env']) - {'PASEO_HOME'} for line in record.read_text().splitlines())
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


def test_mcp_stdio_and_mini(workspace, paseo, monkeypatch):
    root, work = workspace
    q = questions(work)
    home.write(root / 'drive/households.xlsx.source.json', {'id': 'drive-households', 'url': 'https://example.invalid/sheet'})
    home.write(root / '.idli/home.json', {'agent': AGENT, 'workspace_files': {'synthetic-home':[{'title':'Households','local':'drive/households.xlsx'}]}, 'files': [{'title': 'Households', 'local': 'drive/households.xlsx'}]})
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
        env = {**os.environ, 'PASEO_MCP_URL': f'http://127.0.0.1:{browser.server_port}/mcp', 'PASEO_AGENT_ID': AGENT, 'IDLI_WORKSPACE':'synthetic-home'}
        requests = [
            {'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18'}},
            {'id': 2, 'method': 'tools/list'},
            {'id': 3, 'method': 'tools/call', 'params': {'name': 'idli_show', 'arguments': {
                'title': 'Counts', 'vega_lite': {'mark': 'bar'}, 'data_csv': str(csv),
                'sources': ['drive/households.xlsx'], 'script': str(work / 'answer.py')}}},
            {'id': 4, 'method': 'tools/call', 'params': {'name': 'idli_draft_mini', 'arguments': {
                'title': 'Households', 'story': 'Count checked households', 'questions': q, 'code': str(work)}}},
            {'id': 5, 'method': 'tools/call', 'params': {'name': 'idli_show', 'arguments': {
                'title': 'bad', 'vega_lite': {}, 'data_csv': '/etc/passwd'}}}]
        r = subprocess.run([sys.executable, '-I', str(HERE / 'lib/idli_mcp.py')],
                           input='\n'.join(json.dumps({'jsonrpc': '2.0', **x}) for x in requests) + '\n',
                           capture_output=True, text=True, env=env, timeout=30)
        assert r.returncode == 0 and not r.stderr
        replies = [json.loads(line) for line in r.stdout.splitlines()]
        assert 'url' in json.loads(replies[2]['result']['content'][0]['text'])
        assert not replies[3]['result'].get('isError') and replies[4]['result']['isError']
        assert len(browser_calls) == 0
        views = list((root / 'views').glob('*.json'))
        assert len(views) == 1
        view = home.read(views[0])
        assert Path(view['data_csv']).read_text() == csv.read_text() and view['agent'] == AGENT
        assert view['sources'] == ['drive/households.xlsx'] and view['script'] == str(work / 'answer.py')
        props = replies[1]['result']['tools'][0]['inputSchema']['properties']
        assert props['sources']['type'] == 'array' and props['script']['type'] == 'string'
        assert len(api(server, '/api/view?id=' + views[0].stem)['data']) == 2
        draft_id = json.loads(replies[3]['result']['content'][0]['text'])['draft']
        assert not list((root / 'minis').glob('*/mini.json'))
        draft = api(server, '/api/mini-draft?id=' + draft_id)
        saved = api(server, '/api/mini-save', {'id': draft_id, 'name': draft['name'], 'goal': draft['goal'],
                                            'questions': draft['questions'], 'charts': []})
        mini_id = saved['id']
        mini = home.read(root / 'minis' / mini_id / 'mini.json')
        assert mini['files'][0]['local'] == 'drive/households.xlsx'
        assert (root / 'minis' / mini_id / mini['questions'][0]['script']).is_file()
        result = api(server, '/api/mini/run', {'id': mini_id, 'qid': 'count', 'params': {'n': 7}})
        assert '| A | 7 |' in result['text'] and result['chart']['data'][0]['Count'] == 7
        assert result['agent'] is None
        mapped = api(server, '/api/mini/map', {'id': mini_id, 'question': 'count households'})
        assert mapped == {'qid': None, 'params': {}, 'method': 'unavailable'}
        with pytest.raises(HTTPError) as err:
            api(server, '/api/mini?id=' + mini_id, token='wrong')
        assert err.value.code == 403
        with pytest.raises(ValueError): home.view(root, '../escape')
        with pytest.raises(ValueError): home.run_mini(root, mini_id, 'count', {'bad': 1})


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
            if seen[-1]['messages'][0]['content'].startswith('Check one saved'):
                value = {'reason':'Same calculation', 'supported':True, 'params':{'n':4}}
            data = json.dumps({'choices': [{'message': {'content': json.dumps(value)}}]}).encode()
            self.send_response(200); self.end_headers(); self.wfile.write(data)
    with running(Router) as router:
        monkeypatch.setenv('IDLI_9B_URL', f'http://127.0.0.1:{router.server_port}')
        got = home.map_question(root, 'test', 'mean earnings')
    assert got == {'qid': 'income', 'params': {'n': 4}, 'method': 'idli-9b'}
    assert seen[0]['model'] == 'qwen3.5-9b'
    assert [b['properties']['qid'] for b in seen[0]['response_format']['json_schema']['schema']['oneOf']] == [
        {'const': 'count'}, {'const': 'income'}, {'type': 'null'}]
    monkeypatch.setenv('MUSE_URL', 'http://127.0.0.1:1')
    monkeypatch.setenv('IDLI_9B_URL', 'http://127.0.0.1:1')
    assert home.map_question(root, 'test', 'average income')['qid'] is None


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
        assert page.locator('#pop').is_visible()  # local provenance works without a Claude agent
        assert page.get_by_text('How is this number worked out?', exact=True).is_disabled()
        page.locator('#ask').fill('count households')
        page.locator('#match').click()
        page.wait_for_function("() => document.querySelector('#mapping').textContent.includes('This Mini can answer:')")
        assert 'Count households' in page.locator('#mapping').inner_text()
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
    shutil.copytree(HERE / 'idli/claude-commands', clone / 'idli/claude-commands')
    shutil.copytree(HERE / 'idli/claude-skills', clone / 'idli/claude-skills')
    shutil.copytree(HERE / 'lib', clone / 'lib', ignore=shutil.ignore_patterns('test_*', '__pycache__'))
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
    assert home.read(work / '.claude/settings.json')['permissions']['ask'] == ['mcp__idli__unmask']
    # drive/ holds masked copies (none yet: nothing reviewed), never a link to the real downloads.
    assert (work / 'drive').is_dir() and not (work / 'drive').is_symlink()
    settings = home.read(work / '.claude/settings.json')
    assert settings['sandbox']['enabled'] and str(data.resolve()) in settings['sandbox']['filesystem']['denyRead']


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


def test_claude_insert_and_left_chat(workspace, paseo, monkeypatch):
    root, _ = workspace
    record, agents = paseo
    agents.write_text(json.dumps([{'id': AGENT, 'labels': {'idli.left': '1'}}]))
    agents.with_name('terms.json').write_text(json.dumps([
        {'id': 'term-other', 'workspaceId': 'other', 'name': 'Claude'},
        {'id': 'term-drivey', 'workspaceId': 'drivey', 'name': 'Claude'}]))
    # A stale recorded terminal from another workspace must never win.
    home.write(root / '.idli/home.json', {'terminals': {'drivey': 'term-other'}})
    shown = []
    monkeypatch.setattr(uiswitch, 'show_terminal', lambda *args: shown.append(args) or {'ok': True})
    context = 'About the chart "Counts" (data: counts.csv; made by: answer.py; from: redacted(drive/households.xlsx)): Group = A '
    with running(formserver.make_handler(formserver.Files(root), TOKEN)) as server:
        assert api(server, '/api/claude-insert', {'ws': 'drivey', 'text': context}) == {
            'inserted': True, 'terminal': 'term-drivey', 'focused': True}
        assert api(server, '/api/say', {'ws': 'drivey', 'agent': 'term-other', 'text': 'Compare A'}) == {'sent': True}
        calls = [json.loads(line)['args'] for line in record.read_text().splitlines()]
        assert ['terminal', 'send-keys', '-l', 'term-drivey', context] in calls
        assert ['ls', '--json', '--label', 'idli.ws=drivey'] in calls
        assert ['send', '--no-wait', AGENT, 'Compare A'] in calls
        assert shown == [('drivey', 'term-drivey', 'right')]
        for body in ({'ws': '', 'text': context}, {'ws': 'missing', 'text': context},
                     {'ws': 'drivey', 'text': 'bad\rinput'}, {'ws': 'drivey', 'text': 'bad\ninput'},
                     {'ws': 'drivey', 'text': '\x1b[20~'}, {'ws': 'drivey', 'text': ''}):
            with pytest.raises(HTTPError) as err:
                api(server, '/api/claude-insert', body)
            assert err.value.code == 400
        with pytest.raises(HTTPError) as err:
            api(server, '/api/claude-insert', {'ws': 'drivey', 'text': context}, token='wrong')
        assert err.value.code == 403
    keys = [json.loads(line)['args'] for line in record.read_text().splitlines()
            if json.loads(line)['args'][:2] == ['terminal', 'send-keys']]
    assert keys == [['terminal', 'send-keys', '-l', 'term-drivey', context]]  # no Enter or startup command


@pytest.mark.skipif(os.environ.get('HOME_BROWSER') != '1', reason='Set HOME_BROWSER=1 for Chromium')
def test_embed_browser(workspace, paseo, monkeypatch, tmp_path):
    from playwright.sync_api import sync_playwright
    root, work = workspace
    record, agents = paseo
    agents.write_text(json.dumps([{'id': AGENT, 'labels': {'idli.left': '1'}}]))
    agents.with_name('terms.json').write_text(json.dumps([
        {'id': 'claude-drivey', 'workspaceId': 'drivey', 'name': 'Claude'}]))
    shown = []
    monkeypatch.setattr(uiswitch, 'show_terminal', lambda *args: shown.append(args) or {'ok': True})
    ident = 'a' * 32
    csv = work / 'counts.csv'
    csv.write_text('Group,Count\nA,2\nB,3\n')
    script = work / 'counts.py'
    script.write_text('# Synthetic CSV writer\n')
    home.write(root / f'views/{ident}.json', {'title': 'Household counts', 'agent': 'claude-drivey',
        'data_csv': str(csv), 'sources': ['drive/households.xlsx'], 'script': str(script),
        'spec': {'mark': 'bar', 'encoding': {'x': {'field': 'Group', 'type': 'nominal'},
                                          'y': {'field': 'Count', 'type': 'quantitative'}}}})
    with running(formserver.make_handler(formserver.Files(root), TOKEN)) as server, sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 480, 'height': 320})
        errors, posts = [], []
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.on('request', lambda req: posts.append((req.url.split('?')[0], req.post_data_json)) if req.method == 'POST' else None)
        page.goto(f'http://127.0.0.1:{server.server_port}/view?id={ident}&t={TOKEN}&embed=1&ws=drivey')
        marks = page.locator('#viz .mark-rect path')
        marks.first.wait_for()
        assert page.locator('#homelink').is_hidden() and page.locator('#title').is_hidden()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth && document.documentElement.scrollHeight <= innerHeight')
        svg = page.locator('#viz svg').bounding_box()
        assert svg['width'] <= 480 and svg['height'] <= 320
        marks.first.click()
        assert page.locator('#pop button').first.inner_text() == 'Where did this come from?'
        page.locator('#pop button').first.click()
        detail = page.locator('#pop').inner_text()
        assert 'drive/households.xlsx' in detail and str(script) in detail and str(csv) in detail
        assert 'Rows behind this element: 1' in detail
        assert page.locator('#pop tbody').inner_text() == 'A\t2'
        assert posts == []  # provenance comes from the saved CSV and metadata, without a model
        page.keyboard.press('Escape')
        marks.first.click()
        page.get_by_text('Show the rows behind it', exact=True).click()
        page.wait_for_function("() => document.querySelector('#pop').textContent.includes('Sent to the left chat.')")
        assert posts[-1][0].endswith('/api/say') and posts[-1][1]['ws'] == 'drivey'
        page.keyboard.press('Escape')
        for whole in (False, True):
            marks.first.click(button='right')
            assert page.locator('#pop').get_attribute('role') == 'menu'
            assert page.locator('#pop button').all_text_contents() == ['Copy to Claude', 'Copy whole chart to Claude']
            page.get_by_text('Copy whole chart to Claude' if whole else 'Copy to Claude', exact=True).click()
            page.locator('#pop').wait_for(state='hidden')
            assert posts[-1][0].endswith('/api/claude-insert')
            body = posts[-1][1]
            base = f'About the chart "Household counts" (data: {csv}; made by: {script}; from: redacted(drive/households.xlsx))'
            assert body == {'ws': 'drivey', 'text': base + (' ' if whole else ': Group = A, Count = 2 ')}
        for scheme in ('dark', 'light'):
            page.emulate_media(color_scheme=scheme)
            page.set_viewport_size({'width': 360 if scheme == 'dark' else 720, 'height': 320})
            page.wait_for_timeout(250)
            marks.first.wait_for()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth && document.documentElement.scrollHeight <= innerHeight')
            assert page.evaluate('getComputedStyle(document.body).backgroundColor') == ('rgb(22, 22, 21)' if scheme == 'dark' else 'rgb(246, 245, 242)')
            assert page.locator('#viz .role-axis-label text').first.get_attribute('fill') == ('rgb(236, 235, 231)' if scheme == 'dark' else 'rgb(29, 29, 27)')
            page.screenshot(path=str(tmp_path / f'embed-{scheme}.png'))
        # Multi-panel charts cannot use fit autosize. Scaling must preserve click targeting and CSV lineage.
        panel = {'mark': 'bar', 'width': 400, 'height': 400, 'encoding': {
            'x': {'field': 'Group', 'type': 'nominal'},
            'y': {'field': 'Count', 'aggregate': 'sum', 'type': 'quantitative'}}}
        view = home.read(root / f'views/{ident}.json')
        view['spec'] = {'hconcat': [panel, panel], 'background': 'white'}
        home.write(root / f'views/{ident}.json', view)
        csv.write_text('Group,Count\nA,2\nA,4\nB,3\n')
        page.reload()
        marks.first.wait_for()
        svg = page.locator('#viz svg').bounding_box()
        assert svg['width'] <= 720 and svg['height'] <= 320
        marks.first.click()
        page.get_by_text('Where did this come from?', exact=True).click()
        assert 'Rows behind this element: 2' in page.locator('#pop').inner_text()
        assert page.locator('#pop tbody tr').count() == 2
        assert not errors
        browser.close()
    calls = [json.loads(line)['args'] for line in record.read_text().splitlines()]
    assert any(c[:3] == ['send', '--no-wait', AGENT] for c in calls)
    keys = [c for c in calls if c[:2] == ['terminal', 'send-keys']]
    assert len(keys) == 2 and all(c[2:4] == ['-l', 'claude-drivey'] and c[-1].endswith(' ') for c in keys)
    assert shown == [('drivey', 'claude-drivey', 'right')] * 2
