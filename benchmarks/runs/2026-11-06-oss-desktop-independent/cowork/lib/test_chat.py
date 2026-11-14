"""Drivey chat contract: synthetic files only, with local HTTP/Paseo doubles."""
import importlib
import copy
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
import json
import shutil
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from lib import drivefetch, driveindex, drivestubs, formserver, home, idli_mcp, modes, privacy
from sites.files import tools as ft

FIXTURE = Path(__file__).with_name('chat_fixtures')
DRIVE = Path(__file__).resolve().parents[3] / '2026-11-13-grounded-9b/fixtures/drive'


@pytest.fixture
def data(tmp_path, monkeypatch):
    root = tmp_path / 'data'
    shutil.copytree(DRIVE, root / 'drive')
    shutil.copytree(FIXTURE, root / 'minis/synthetic')
    (root / 'minis/synthetic/drive').symlink_to(root / 'drive', target_is_directory=True)
    monkeypatch.setenv('IDLI_DATA', str(root))
    monkeypatch.setenv('IDLI_9B_URL', 'http://127.0.0.1:1')
    monkeypatch.setenv('IDLI_SCANNER', 'http://127.0.0.1:1')
    monkeypatch.delenv('PASEO_AGENT_ID', raising=False)
    monkeypatch.delenv('IDLI_WORKSPACE', raising=False)
    monkeypatch.setattr(formserver, 'ensure', lambda *a: (8797, 'test-token'))
    monkeypatch.setattr(ft, 'files', lambda: formserver.Files(root))
    return root


def test_stubs_refresh_and_folder_fetch(data, monkeypatch):
    monkeypatch.setattr(driveindex, 'DB', str(data / 'index.duckdb'))
    con = driveindex.connect()
    rows = [('a', 'households', 'Google Sheets', 'My Drive / Survey'),
            ('b', 'visits.xlsx', 'Microsoft Excel', 'My Drive / Survey / Visits'),
            ('c', 'other.csv', 'CSV', 'My Drive / Survey2'),
            ('folder', 'Survey', 'Folder', 'My Drive')]
    con.executemany('INSERT INTO files (id,name,kind,path) VALUES (?,?,?,?)', rows)
    con.close()
    entries = drivestubs.refresh(data)
    assert len(entries) == 3
    stub = home.read(data / 'Drive/My Drive/Survey/households')
    assert stub == {'id':'a','kind':'Google Sheets','title':'households', 'url':'https://drive.google.com/file/d/a/view'}
    assert (data / 'Drive/My Drive/Survey/Visits').is_dir()
    calls = []
    def fetch(fid, sheet=True):
        calls.append((fid,sheet))
        return (DRIVE / ('households.xlsx' if fid == 'a' else 'field_programme_tracker.xlsx')).read_bytes()
    monkeypatch.setattr(drivefetch, 'fetch', fetch)
    got = ft.t_drive_fetch(['Drive/My Drive/Survey/', 'Drive/My Drive/Survey/households'])
    assert calls == [('a',True),('b',False)]
    assert len(got['files']) == 2
    assert (data / 'drive/My Drive/Survey/households.xlsx').read_bytes() == (DRIVE/'households.xlsx').read_bytes()
    assert len(home.read(data/'.idli/home.json')['files']) == 2
    con = driveindex.connect()
    con.execute("DELETE FROM files WHERE id='a'")
    con.close()
    drivestubs.refresh(data)
    assert not (data / 'Drive/My Drive/Survey/households').exists()
    with pytest.raises(ValueError): drivestubs.fetch(data, ['Drive/../escape'])
    with pytest.raises(ValueError): drivestubs.fetch(data, ['Drive/missing/'])


def test_stub_cannot_escape(data, monkeypatch, tmp_path):
    monkeypatch.setattr(driveindex, '_read', lambda *a: [('id', '../../escape', 'CSV', 'My Drive')])
    with pytest.raises(ValueError): drivestubs.refresh(data)
    monkeypatch.setattr(driveindex, '_read', lambda *a: [('id', 'file', 'CSV', 'x')])
    (data / 'Drive').symlink_to(tmp_path / 'elsewhere')
    with pytest.raises(ValueError): drivestubs.refresh(data)


@pytest.mark.parametrize('text,expected', [
    ('use @Drive/Survey/ and @Drive/test.xlsx', ['Drive/Survey/', 'Drive/test.xlsx']),
    ('use @"Drive/My Drive/test file.xlsx"', ['Drive/My Drive/test file.xlsx']),
    ('use @Drive/My\\ Drive/test\\ file.xlsx', ['Drive/My Drive/test file.xlsx']),
    ('use @Drive/My Drive/test file.xlsx and compare it', ['Drive/My Drive/test file.xlsx']),
    ('use @Drive/My Drive/Survey/ for this', ['Drive/My Drive/Survey/'])])
def test_mentions(text, expected):
    assert drivestubs.mentions(text) == expected


def req(text, model):
    return {'model':model, 'messages':[{'role':'user','content':text}], 'tools':[
        {'name':'mcp__cowork__'+t} for t in ('mini_open','mini_ask','drive_fetch')]}


def result(j, name, args, value):
    j = copy.deepcopy(j)
    j['messages'].extend([
        {'role':'assistant','content':[{'type':'tool_use','id':'call-'+str(len(j['messages'])),
                                       'name':'mcp__cowork__'+name,'input':args}]},
        {'role':'user','content':[{'type':'tool_result','tool_use_id':'call-'+str(len(j['messages'])),
                                  'content':json.dumps(value)}]}])
    return j


@pytest.mark.parametrize('model', list(modes.MODES) + ['future-model'])
def test_routing_four_message_kinds_and_mini_state(data, monkeypatch, model):
    assert modes.privacy_route(req('Start Drivey',model))['content'][0]['text'] == modes.DRIVEY_OPENING
    chart = 'Chart from Claude: Debt\n![Debt](/tmp/debt.svg)\nOpen interactive: http://test/view'
    assert modes.privacy_route(req(chart,model))['content'][0]['text'] == chart
    opened = req('Open Mini: Synthetic NGO Mini [synthetic]',model)
    assert modes.privacy_route(opened)['content'][0]['input'] == {'id':'synthetic'}
    fetched = modes.privacy_route(req('Use @Drive/Survey/ for this question', model))
    assert fetched['content'][0]['input'] == {'paths':['Drive/Survey/']}
    active = result(opened,'mini_open',{'id':'synthetic'},home.read(FIXTURE/'mini.json'))
    # Code returns tool replies verbatim; neither chat model nor mapper rewrites script output.
    answer = result(opened,'mini_ask',{}, {'reply':'Using: Test: ward = Kasewadi, months = 6\nNo households.'})
    assert 'No households.' in modes.privacy_route(answer)['content'][0]['text']
    active['messages'].append({'role':'user','content':'the question'})
    monkeypatch.setattr(importlib.import_module('lib.minimap'), 'map_questions', lambda *a: {'qid':'threshold','params':{'ward':'Kasewadi','months':6}})
    routed = modes.privacy_route(active)['content'][0]
    assert routed['input'] == {'id':'synthetic','qid':'threshold','params':{'ward':'Kasewadi','months':6}}
    monkeypatch.setattr(importlib.import_module('lib.minimap'), 'map_questions', lambda *a: {'qid':None,'params':{}})
    assert modes.privacy_route(active)['content'][0]['text'].startswith("I don't know. This Mini can answer:")
    assert modes.privacy_route(req('hello',model)) is None
    # Drive fetching must return to the ordinary model path, rather than repeatedly downloading.
    continuation = result(req('Use @Drive/test.xlsx',model),'drive_fetch',{}, {'files':[{'file':'drive/test.xlsx'}]})
    assert modes.privacy_route(continuation) is None


def test_open_and_run_examples(data):
    got = ft.t_mini_open('synthetic')
    assert len(got['questions']) == 5
    assert 'Goal:' in got['reply'] and 'Source files: households.xlsx, field_programme_tracker.xlsx' in got['reply']
    assert got['reply'].count('[Open interactive](') == 5
    assert got['reply'].count('![') == 5
    assert len(list((data/'views').glob('*.svg'))) == 5
    for path in (data/'views').glob('*.json'):
        view = home.read(path)
        assert view['sources'] == ['drive/households.xlsx', 'drive/field_programme_tracker.xlsx']
        assert Path(view['script']).parent == data/'minis/synthetic'
        assert Path(view['script']).is_file()
    answer = ft.t_mini_ask('synthetic','threshold', {'ward':'Kasewadi','months':6})
    assert answer['reply'].startswith('Using: Which households')
    assert 'ward = Kasewadi, months = 6' in answer['reply']
    latest = max((data/'views').glob('*.json'), key=lambda p: p.stat().st_mtime_ns)
    assert home.read(latest)['script'] == str(data/'minis/synthetic/threshold.py')
    assert '<svg' in next((data/'views').glob('*.svg')).read_text()
    with pytest.raises(ValueError): ft.t_mini_ask('synthetic','threshold',{'ward':'Unknown'})


def test_warning_in_card_and_review(data):
    for i in range(10):
        privacy.set(data, f'drive/{i}.xlsx', mode='mask', review='ask', columns={})
    assert not privacy.review_warning(data)
    privacy.set(data, 'drive/10.xlsx', mode='mask', review='ask')
    assert '11 files' in privacy.review_warning(data) and 'Auto' in privacy.review_warning(data)
    assert not privacy.review_warning(data, ['drive/0.xlsx'])
    review = privacy.review(data,'drive/households.xlsx',data/'drive/households.xlsx')
    assert '11 files' in review['warning']
    card = ft._masked_ask('drive/households.xlsx','hello',None,None)['card']
    assert '11 files' in card['questions'][0]['question']
    assert 'id="warning"' in Path(privacy.__file__).with_name('privacy.html').read_text()
    for i in range(11): privacy.set(data, f'drive/{i}.xlsx',review='auto')
    assert not privacy.review_warning(data)


@contextmanager
def server(data):
    s = ThreadingHTTPServer(('127.0.0.1',0), formserver.make_handler(formserver.Files(data),'secret'))
    t = threading.Thread(target=s.serve_forever,daemon=True)
    t.start()
    try: yield f'http://127.0.0.1:{s.server_port}'
    finally:
        s.shutdown(); s.server_close(); t.join()


@pytest.mark.parametrize('origin', ['paseo://app','null','https://untrusted.example'])
def test_public_list_only_and_cors(data, origin):
    with server(data) as url:
        with urlopen(Request(url+'/api/minis-public', headers={'Origin':origin})) as r:
            rows = json.load(r)
            assert r.headers.get('Access-Control-Allow-Origin') == (origin if origin != 'https://untrusted.example' else None)
        assert set(rows[0]) == {'id','name','heading','date','author'}
        assert rows[0]['date'] == '2026-11-14'
        with urlopen(Request(url+'/api/minis-public',method='OPTIONS',headers={'Origin':origin})) as r:
            assert r.status == 204
        with pytest.raises(HTTPError): urlopen(url+'/api/mini?id=synthetic')
        with pytest.raises(HTTPError): urlopen(Request(url+'/api/minis-public',data=b'{}'))


def test_claude_posts_to_matching_left_chat(data, monkeypatch):
    csv = data/'chart.csv'
    csv.write_text('ward,debt\nKasewadi,12\nRamtekdi,20\n')
    monkeypatch.setenv('IDLI_WORKSPACE','workspace-2')
    calls = []
    def cli(*args):
        calls.append(args)
        if args[0] == 'terminal':
            return json.dumps([{'id':'claude-terminal','name':'Claude','workspaceId':'workspace-2'}])
        return json.dumps([{'id':'right','labels':{}}, {'id':'left','labels':{'idli.left':'1'}}]) if args[0]=='ls' else ''
    monkeypatch.setattr(home,'cli',cli)
    assert idli_mcp.idli_show('Debt',{'mark':'bar','encoding':{'x':{'field':'ward','type':'nominal'},'y':{'field':'debt','type':'quantitative'}}},str(csv)) == 'shown in Idli'
    assert calls[1] == ('ls','--json','--label','idli.ws=workspace-2')
    assert calls[2][:3] == ('send','--no-wait','left')
    assert calls[2][3].startswith('Chart from Claude: Debt\n![Debt](')
    assert '\n[Open interactive](' in calls[2][3]
    assert next(home.read(p)['agent'] for p in (data/'views').glob('*.json')) == 'claude-terminal'
    assert next(home.read(p)['workspace'] for p in (data/'views').glob('*.json')) == 'workspace-2'


def test_save_limits_and_author(data, monkeypatch):
    monkeypatch.setenv('IDLI_AUTHOR','Asha')
    monkeypatch.setenv('IDLI_CLAUDE_WORK',str(FIXTURE))
    manifest = home.read(FIXTURE/'mini.json')
    idli_mcp.idli_save_mini('Saved','Goal',manifest['questions'])
    saved = home.read(data/'minis/saved/mini.json')
    assert saved['author'] == 'Asha' and saved['date']
    with pytest.raises(ValueError): idli_mcp.idli_save_mini('Too many','',manifest['questions']*2)
    q = copy.deepcopy(manifest['questions'][0]); q['params']['extra']={'type':'text','default':'a'}
    with pytest.raises(ValueError): idli_mcp.idli_save_mini('Text','',[q])
    monkeypatch.delenv('IDLI_AUTHOR')
    monkeypatch.setenv('IDLI_HOME',str(data/'config-home'))
    home.write(data/'config-home/config/accounts.json',{'name':'Test name','secret':'never returned'})
    assert idli_mcp.mini_author() == 'Test name'


def test_mapper_unavailable_does_not_guess(data):
    assert home.map_question(data,'synthetic','rank wards')['qid'] is None


def test_launcher_passes_workspace_to_mcp(data):
    import os
    import subprocess
    import sys
    launcher = Path(__file__).resolve().parents[1]/'desktop/claude-masked.sh'
    config_code = launcher.read_text().split("<<'PYCONFIG'\n",1)[1].split('\nPYCONFIG',1)[0]
    target = data/'mcp.json'
    subprocess.run([sys.executable,'-c',config_code,'/installed/cowork',str(target)], check=True,
                   env={**os.environ,'IDLI_WORKSPACE':'workspace-test','IDLI_AUTHOR':'Test author'})
    config = home.read(target)['mcpServers']['idli']
    assert config['env']['IDLI_WORKSPACE'] == 'workspace-test'
    assert config['env']['IDLI_AUTHOR'] == 'Test author'
    assert target.stat().st_mode & 0o777 == 0o600


def test_native_document_exports(monkeypatch):
    urls = []
    monkeypatch.delenv('IDLI_DRIVE_FAKE', raising=False)
    monkeypatch.setattr(drivefetch,'session_fetch', lambda url: urls.append(url) or b'export')
    assert drivefetch.fetch('fake-doc',sheet=False,kind='Google Docs') == b'export'
    assert urls == ['https://docs.google.com/document/d/fake-doc/export?format=docx']


def test_folder_attempts_every_file_and_keeps_successes(data, monkeypatch):
    monkeypatch.setattr(driveindex, '_read', lambda *a: [
        ('bad','unavailable.xlsx','Microsoft Excel','Folder'),
        ('good','available.xlsx','Microsoft Excel','Folder')])
    calls = []
    def fetch(fid, sheet=True):
        calls.append(fid)
        if fid == 'bad': raise drivefetch.NoAccess('not available')
        return b'workbook'
    monkeypatch.setattr(drivefetch, 'fetch',fetch)
    got = drivestubs.fetch(data,['Drive/Folder/'],workspace='chosen-workspace')
    assert calls == ['bad','good']
    assert got['files'][0]['local'] == 'drive/Folder/available.xlsx'
    assert got['errors'][0]['path'] == 'Drive/Folder/unavailable.xlsx'
    assert home.read(data/'.idli/home.json')['workspace_files']['chosen-workspace'] == got['files']


def test_duplicate_names_and_extensionless_mentions(data, monkeypatch):
    monkeypatch.setattr(driveindex, '_read', lambda *a: [
        ('a','Households','Google Sheets','My Drive'),('b','Households','Google Sheets','My Drive')])
    stubs = drivestubs.refresh(data)
    assert set(stubs) == {'My Drive/Households','My Drive/Households__b'}
    monkeypatch.setattr(drivefetch,'fetch',lambda *a,**k: b'workbook')
    mention = drivestubs.mentions('Use @Drive/My Drive/Households to compare debts')
    got = drivestubs.fetch(data, mention)
    assert [f['id'] for f in got['files']] == ['a']


def test_chat_workspace_from_left_label(data, monkeypatch):
    monkeypatch.setenv('PASEO_AGENT_ID','left-chat')
    monkeypatch.setattr(home,'cli',lambda *a: json.dumps([
        {'id':'left-chat','labels':{'idli.ws':'workspace-a','idli.left':'1'}}]))
    assert home.chat_workspace() == 'workspace-a'


def test_visible_chart_text_is_plain(data):
    markdown = home.chart_markdown(data, 'Debt · trend', {'vega_lite':{'mark':'bar','encoding':{
        'x':{'field':'ward','type':'nominal'},'y':{'field':'debt','type':'quantitative'}}},
        'data':[{'ward':'Ward → A','debt':4}]})
    assert '·' not in markdown and '→' not in markdown
    svg = next((data/'views').glob('*.svg')).read_text()
    assert '·' not in svg and '→' not in svg


def test_chart_provenance_paths(data, monkeypatch, tmp_path):
    monkeypatch.setenv('IDLI_CLAUDE_WORK', str(data))
    csv = data/'counts.csv'
    csv.write_text('ward,count\nA,2\n')
    script = data/'counts.py'
    script.write_text('# Synthetic CSV writer\n')
    idli_mcp.idli_show('Counts', {'mark': 'bar'}, str(csv), ['drive/households.xlsx'], str(script))
    view = home.read(next((data/'views').glob('*.json')))
    assert view['sources'] == ['drive/households.xlsx'] and view['script'] == str(script)
    assert home.view(data, next((data/'views').glob('*.json')).stem)['data'] == [{'ward':'A','count':'2'}]
    outside = tmp_path/'outside.xlsx'
    outside.write_text('outside')
    (data/'drive/escape.xlsx').symlink_to(outside)
    for sources in (['counts.csv'], [str(outside)], ['drive/escape.xlsx'], 'drive/households.xlsx'):
        with pytest.raises(ValueError):
            idli_mcp.idli_show('Bad source', {'mark':'bar'}, str(csv), sources, str(script))
    with pytest.raises(ValueError):
        idli_mcp.idli_show('Bad script', {'mark':'bar'}, str(csv), [], str(outside))
    assert len(list((data/'views').glob('*.json'))) == 1
