"""Synthetic privacy regressions; run .venv/bin/python -m pytest lib/test_privacy.py."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import pandas as pd
import pytest
from lib import privacy as p, formserver


@pytest.fixture
def book(tmp_path, monkeypatch):
    monkeypatch.setenv('IDLI_SCANNER', 'http://127.0.0.1:1/scan')
    path = tmp_path/'families.xlsx'
    pd.DataFrame({'Name': ['Asha Patil', 'Ravi Shah', 'Meena Rao'],
                  'Ward': ['Yerawada', 'Aundh', 'Yerawada'],
                  'Income': [12000, 18000, 9000], 'Season': ['winter', 'summer', 'winter']}).to_excel(path, index=False)
    return tmp_path, path.name, path


def choose(book, **columns):
    root, file, _ = book
    p.set(root, file, mode='mask', columns={'Name': True, 'Ward': True, 'Income': False, **columns})


def test_masking(book):
    root, file, path = book
    assert p.get(root, file) == {'mode': None, 'review': 'ask', 'columns': {}}
    rows = {r['column']: r for r in p.suggest(path, None)}
    assert rows['Name']['mask'] and rows['Ward']['mask'] and not rows['Income']['mask']
    assert 'regex only' in rows['Name']['reason']
    choose(book)
    coded = p.masked_frame(root, file, path, None)
    assert coded.Name[0].startswith('NAME_') and coded.Ward[0].startswith('PLACE_')
    assert str(coded.Income[0]) == '12000'
    for ward in ['yerawada', 'yearwada']:
        got = p.mask_text(root, file, path, 'monthly income for '+ward+' in winter')
        assert coded.Ward[0] in got['masked']
        assert 'monthly income' in got['masked'] and 'winter' in got['masked']
        assert got['scanner'] == 'regex only' and not p.leak_check(root, file, got['masked'])
    assert p.leak_check(root, file, 'Left Yerawada here') == ['Yerawada']
    assert p.unmask(root, file, {'filters': {'Ward': [coded.Ward[0]]}}) == {'filters': {'Ward': ['Yerawada']}}
    choose(book, Income=True)
    coded = p.masked_frame(root, file, path, None)
    assert coded.Income[0].startswith('VALUE_') and p.unmask(root, file, coded.Income[0]) == '12000'
    assert p.leak_check(root, file, 'income 12000') == ['12000']
    assert not p.leak_check(root, file, json.dumps(coded.to_dict()))
    assert p.masked_frame(root, file, path, None).equals(coded)
    assert all(v.stat().st_mode & 0o777 == 0o600 for v in (root/'vault').glob('*.json'))
    assert (root/'privacy.json').stat().st_mode & 0o777 == 0o600
    assert p.get(root, './families.xlsx') == p.get(root, file)
    with pytest.raises(ValueError): p.set(root, '../escape.xlsx', mode='mask')
    with pytest.raises(ValueError): p.set(root, file, columns={'Income': 'true'})


def form():
    return {'_measures': {'rows': {'label': 'Number of households', 'sql': 'count(*)'}},
            'group_by': [{'id': 'Ward', 'label': 'Ward'}],
            'filters': [{'column': 'Ward', 'label': 'Ward', 'kind': 'choice', 'values': ['Yerawada', 'Aundh']}],
            'presets': [], 'date_columns': [], '_groups': {'Ward': {'sql': '"Ward"', 'label': 'Ward'}}, '_kinds': {}}


def test_plan(book, monkeypatch):
    root, file, path = book
    choose(book)
    prompts = []
    def claude(prompt):
        prompts.append(prompt)
        assert not p.leak_check(root, file, prompt)
        code = p.mask_text(root, file, path, 'yerawada')['masked']
        return {'spec': {'measures': ['bad' if len(prompts) == 1 else 'rows'], 'filters': {'Ward': [code]}}}
    monkeypatch.setattr(p, '_claude', claude)
    got = p.plan(root, file, path, None, form(), 'monthly income for yearwada in winter',
                 [{'question': 'Asha Patil in Yerawada', 'spec': {}, 'answer': 'DO NOT SEND THIS ANSWER'}])
    assert got['error'] is None, got
    assert got['spec']['filters']['Ward'] == ['Yerawada']
    assert len(prompts) == 2 and got['sent'] == prompts[-1]
    assert 'DO NOT SEND' not in got['sent'] and 'yearwada' not in got['sent']
    assert 'invalid shape' in prompts[-1]
    monkeypatch.setattr(p, 'leak_check', lambda *args: ['leftover'])
    got = p.plan(root, file, path, None, form(), 'a question', [])
    assert got['spec'] is None and got['sent'] == '' and 'Refused' in got['error']
    assert len(prompts) == 2


def test_scanner_remainder_and_threshold(book, monkeypatch):
    root, file, path = book
    choose(book)
    seen = []
    class H(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            text = json.loads(self.rfile.read(int(self.headers['Content-Length'])))['text']
            seen.append(text)
            spans = []
            for word, score in [('winter', .6), ('New Person', .95)]:
                if word in text:
                    a = text.index(word); spans.append([a, a+len(word), 'person_name', score])
            self.send_response(200); self.end_headers(); self.wfile.write(json.dumps({'spans': spans}).encode())
    server = ThreadingHTTPServer(('127.0.0.1', 0), H)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        monkeypatch.setenv('IDLI_SCANNER', f'http://127.0.0.1:{server.server_port}/scan')
        got = p.mask_text(root, file, path, 'yerawada winter New Person contact test@example.org')
        assert got['scanner'] == 'ok' and 'winter' in got['masked'] and 'New Person' not in got['masked']
        assert all('yerawada' not in s and 'test@example.org' not in s and 'PLACE_' not in s for s in seen)
    finally:
        server.shutdown(); server.server_close(); thread.join()


def test_short_values_and_subdirectories(book):
    root, file, path = book
    folder = root/'nested'; folder.mkdir()
    other = folder/file
    pd.DataFrame({'Ward': ['A', '7', 'Yerawada']}).to_excel(other, index=False)
    p.set(root, 'nested/'+file, mode='mask', columns={'Ward': True})
    got = p.mask_text(root, 'nested/'+file, other, 'A and 7 in Yerawada')
    assert not p.leak_check(root, 'nested/'+file, got['masked'])
    assert len(list((root/'vault').glob('*.json'))) == 1 and p.get(root, file)['mode'] is None


def test_http(book):
    root, file, path = book
    token = 'synthetic-test-token-not-a-credential'
    server = ThreadingHTTPServer(('127.0.0.1', 0), formserver.make_handler(formserver.Files(root), token))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    def request(route, body=None):
        req = Request(base+route+('&' if '?' in route else '?')+'t='+token,
                      data=json.dumps(body).encode() if body else None, headers={'Content-Type': 'application/json'})
        with urlopen(req) as response: return response.read()
    try:
        assert b'File privacy' in request('/privacy?file='+file)
        got = json.loads(request('/api/privacy?file='+file))
        assert len(got['suggestions']) == 4 and got['mode'] is None
        got = json.loads(request('/api/privacy', {'file': file, 'action': 'preview', 'columns': {'Income': True}}))
        assert next(r for r in got['suggestions'] if r['column'] == 'Income')['as_sent'][0].startswith('VALUE_')
        assert p.get(root, file)['mode'] is None
        settings = {'file': file, 'mode': 'mask', 'review': 'auto', 'columns': {'Ward': True}}
        assert json.loads(request('/api/privacy', settings))['review'] == 'auto'
        assert json.loads(request('/api/privacy?file='+file))['mode'] == 'mask'
        with pytest.raises(HTTPError) as e: urlopen(base+'/api/privacy?file='+file)
        assert e.value.code == 403
        with pytest.raises(HTTPError) as e: request('/api/privacy?file=../outside.xlsx')
        assert e.value.code == 400
    finally:
        server.shutdown(); server.server_close(); thread.join()


def test_large_measures_and_multitab_preview(book):
    root, file, path = book
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({'Ward': ['Yerawada'], 'Income': [12345678]}).to_excel(writer, sheet_name='First', index=False)
        pd.DataFrame({'Ward': ['Aundh'], 'Income': [98765432]}).to_excel(writer, sheet_name='Second', index=False)
    assert not next(r for r in p.suggest(path, 'First') if r['column'] == 'Income')['mask']
    choices = {'Ward': True, 'Income': True}
    preview = p.review(root, file, path, 'Second', choices)
    p.set(root, file, mode='mask', columns=choices)
    p._seed(root, file, path)
    coded = p.masked_frame(root, file, path, 'Second')
    assert next(r for r in preview['suggestions'] if r['column'] == 'Ward')['as_sent'] == coded.Ward.tolist()
    assert p.mask_text(root, file, path, 'Aundh')['masked'] == coded.Ward[0]


def test_claude_process_isolation(monkeypatch):
    from types import SimpleNamespace
    def run(args, **kwargs):
        assert args[:3] == ['claude', '-p', 'masked prompt']
        assert '--tools=' in args and '--strict-mcp-config' in args
        assert args[args.index('--model')+1] == 'configured-model'
        assert not list(__import__('pathlib').Path(kwargs['cwd']).iterdir())
        return SimpleNamespace(returncode=0, stdout=json.dumps({'result': '{"spec":{"measures":["rows"]}}'}))
    monkeypatch.setenv('IDLI_PLANNER_MODEL', 'configured-model')
    monkeypatch.setattr(p.subprocess, 'run', run)
    assert p._claude('masked prompt') == {'spec': {'measures': ['rows']}}
