#!/usr/bin/env python3
"""Small stdio MCP for the person's masked Claude. Never log tool arguments or URLs."""
import json
import os
from pathlib import Path
import re
import shutil
import sys
import urllib.parse
import uuid

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from lib import home  # noqa: E402


def data_dir():
    return Path(os.environ.get('IDLI_DATA', '~/idli-insights/cowork-real')).expanduser().resolve()


def page_url(page, ident):
    from lib import formserver
    port, token = formserver.ensure(str(data_dir()))
    return f'http://dashboard.localhost:{port}/{page}?' + urllib.parse.urlencode({'id': ident, 't': token})


def idli_show(title, vega_lite, data_csv):
    from lib import browser, uiswitch
    path = home.allowed_path(data_dir(), data_csv)
    if path.suffix.lower() != '.csv' or not isinstance(vega_lite, dict):
        raise ValueError('Supply a CSV and a Vega-Lite object')
    ident = uuid.uuid4().hex
    st = home.read(Path(data_dir()) / '.idli/home.json') if (Path(data_dir()) / '.idli/home.json').exists() else {}
    # the person's Claude is a terminal (no chat id): clicks on the chart are typed into it; Paseo's browser tools
    # act for a chat, so the tab is opened on behalf of one in the same workspace
    home.write(home.inside(data_dir(), 'views/' + ident + '.json', exists=False),
               {'title': str(title), 'spec': vega_lite, 'data_csv': str(path),
                'agent': os.environ.get('PASEO_AGENT_ID') or st.get('terminal')})
    # Idli's home page (Drivey's left pane) watches for new views and opens this one itself; a chat-side Claude can
    # also open it as a tab
    if os.environ.get('PASEO_AGENT_ID'):
        try:
            browser.paseo('browser_new_tab', url=page_url('view', ident))
        except Exception:  # noqa: BLE001
            pass
    return 'shown in Idli'


def idli_save_mini(name, goal, questions):
    if not isinstance(questions, list) or not questions:
        raise ValueError('Give the Mini at least one checked question')
    scripts, checked, ids = [], [], set()
    for i, question in enumerate(questions):
        q = dict(question)
        if not re.fullmatch(r'[\w-]{1,80}', str(q.get('id', ''))) or q['id'] in ids:
            raise ValueError('Give every question a unique id')
        ids.add(q['id'])
        path = home.inside(home.work_dir(), q['script'])
        if path.suffix != '.py' or not str(q.get('question') or '').strip():
            raise ValueError('Give every question a Python script and question text')
        params = q.get('params', {})
        if not isinstance(params, dict) or any(not isinstance(d, dict) or d.get('type') not in
                                              ('choice', 'number', 'text') for d in params.values()):
            raise ValueError('Invalid parameters')
        q['params'] = params
        home.params_for(q, {})
        q['script'] = f'question_{i + 1}.py'
        scripts.append(path)
        checked.append(q)
    root = data_dir()
    state = home.inside(root, '.idli/home.json', exists=False)
    selected = home.read(state).get('files', []) if state.exists() else []
    sources = []
    for item in selected:
        path = home.inside(root, item['local'])
        sidecar = home.inside(root, str(path) + '.source.json', exists=False)
        sources.append({**item, **(home.read(sidecar) if sidecar.exists() else {})})
    ident = (re.sub(r'[^a-z0-9]+', '-', str(name).lower()).strip('-') or 'mini')[:60]
    folder = root / 'minis' / ident
    if folder.exists():
        ident += '-' + uuid.uuid4().hex[:8]
        folder = root / 'minis' / ident
    # Resolve before creating: reject a redirected minis directory.
    home.inside(root, folder / 'mini.json', exists=False)
    folder.mkdir(parents=True)
    try:
        for path, q in zip(scripts, checked):
            shutil.copyfile(path, folder / q['script'])
        drive = root / 'drive'
        drive.mkdir(exist_ok=True)
        (folder / 'drive').symlink_to(drive, target_is_directory=True)
        home.write(folder / 'mini.json', {'id': ident, 'name': str(name), 'goal': str(goal), 'questions': checked,
                                        'files': sources, 'agent': os.environ.get('PASEO_AGENT_ID')})
    except Exception:
        shutil.rmtree(folder)
        raise
    return page_url('mini', ident)


TOOLS = {
    'idli_show': (idli_show, 'After the person agrees to see a chart, show your computed CSV in Idli.', {
        'title': {'type': 'string'}, 'vega_lite': {'type': 'object'}, 'data_csv': {'type': 'string'}},
        ['title', 'vega_lite', 'data_csv']),
    'idli_save_mini': (idli_save_mini, 'Save questions after brainstorming and checking every script result with the person.', {
        'name': {'type': 'string'}, 'goal': {'type': 'string'}, 'questions': {'type': 'array', 'items': {
            'type': 'object', 'properties': {'id': {'type': 'string'}, 'question': {'type': 'string'},
                'script': {'type': 'string'}, 'params': {'type': 'object', 'additionalProperties': {
                    'type': 'object', 'properties': {'type': {'enum': ['choice', 'number', 'text']},
                        'choices': {'type': 'array'}, 'default': {}}, 'required': ['type', 'default']}},
                'chart': {}}, 'required': ['id', 'question', 'script', 'params']}}}, ['name', 'goal', 'questions'])}


def main():
    for line in sys.stdin:
        try:
            message = json.loads(line)
            mid, method = message.get('id'), message.get('method')
            if mid is None:
                continue
            if method == 'initialize':
                result = {'protocolVersion': message.get('params', {}).get('protocolVersion', '2025-06-18'),
                          'capabilities': {'tools': {}}, 'serverInfo': {'name': 'idli', 'version': '0.1'}}
            elif method == 'tools/list':
                result = {'tools': [{'name': name, 'description': desc, 'inputSchema': {
                    'type': 'object', 'properties': props, 'required': required}}
                    for name, (_, desc, props, required) in TOOLS.items()]}
            elif method == 'tools/call':
                try:
                    args = message['params']
                    out = TOOLS[args['name']][0](**args.get('arguments', {}))
                    result = {'content': [{'type': 'text', 'text': out if isinstance(out, str) else json.dumps(out)}]}
                except Exception:
                    # Keep paths, tool contents and browser URLs (which contain tokens) out of errors.
                    result = {'isError': True, 'content': [{'type': 'text', 'text':
                              'Idli could not complete this tool. Check the file paths and inputs, then retry.'}]}
            else:
                print(json.dumps({'jsonrpc': '2.0', 'id': mid, 'error': {'code': -32601, 'message': 'Unknown method'}}), flush=True)
                continue
            print(json.dumps({'jsonrpc': '2.0', 'id': mid, 'result': result}), flush=True)
        except (ValueError, TypeError, AttributeError):
            print(json.dumps({'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'Invalid JSON-RPC'}}), flush=True)


if __name__ == '__main__':
    main()
