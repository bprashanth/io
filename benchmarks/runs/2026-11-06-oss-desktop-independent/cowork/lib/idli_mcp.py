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
    import csv
    path = home.allowed_path(data_dir(), data_csv)
    if path.suffix.lower() != '.csv' or not isinstance(vega_lite, dict):
        raise ValueError('Supply a CSV and a Vega-Lite object')
    with path.open(newline='') as f:
        rows = list(csv.DictReader(f))
    state = Path(data_dir()) / '.idli/home.json'
    st = home.read(state) if state.exists() else {}
    agent = os.environ.get('PASEO_AGENT_ID') or st.get('terminal')
    workspace = os.environ.get('IDLI_WORKSPACE')
    if workspace:
        terminal = home._claude_terminal(data_dir(), workspace)
        if terminal:
            home._remember(data_dir(), workspace, terminal)
            agent = terminal
    markdown = home.chart_markdown(data_dir(), title, {'vega_lite': vega_lite, 'data': rows}, agent)
    if workspace:
        chats = json.loads(home.cli('ls', '--json', '--label', 'idli.ws=' + workspace))
        if isinstance(chats, dict):
            chats = chats.get('agents', [])
        left = next((c for c in chats if (c.get('labels') or {}).get('idli.left') == '1'), None)
        if not left:
            raise ValueError('No left chat in this workspace')
        home.cli('send', '--no-wait', left.get('id') or left['agentId'],
                 'Chart from Claude: ' + home.plain(title) + '\n' + markdown)
    return 'shown in Idli'


def mini_author():
    if os.environ.get('IDLI_AUTHOR', '').strip():
        return home.plain(os.environ['IDLI_AUTHOR'].strip())
    # Read only the supported name field, never an account id or token.
    path = Path(os.environ.get('IDLI_HOME', '~/idli-insights')).expanduser() / 'config/accounts.json'
    try:
        accounts = home.read(path)
        names = [accounts.get('name'), (accounts.get('google') or {}).get('name')]
        for name in names:
            if isinstance(name, str) and name.strip():
                return home.plain(name.strip())
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    import getpass
    return getpass.getuser()


def idli_save_mini(name, goal, questions):
    if not isinstance(questions, list) or not 1 <= len(questions) <= 8:
        raise ValueError('Give the Mini between one and eight checked questions')
    import datetime
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
        if not isinstance(params, dict) or len(params) > 3 or any(not isinstance(d, dict) or d.get('type') not in
                                              ('choice', 'number') for d in params.values()):
            raise ValueError('Invalid parameters')
        for desc in params.values():
            if 'default' not in desc or (desc['type'] == 'choice' and
                    (not isinstance(desc.get('choices'), list) or not desc['choices'] or
                     any(not isinstance(c, str) for c in desc['choices']))):
                raise ValueError('List every choice and supply a default for every option')
        q['params'] = params
        home.params_for(q, {})
        q['script'] = f'question_{i + 1}.py'
        scripts.append(path)
        checked.append(q)
    root = data_dir()
    state = home.inside(root, '.idli/home.json', exists=False)
    saved_state = home.read(state) if state.exists() else {}
    selected = saved_state.get('workspace_files', {}).get(os.environ.get('IDLI_WORKSPACE'),
                                                         saved_state.get('files', []))
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
        home.write(folder / 'mini.json', {'id': ident, 'name': home.plain(name), 'goal': home.plain(goal), 'questions': checked,
                                        'files': sources, 'date': datetime.date.today().isoformat(), 'author': mini_author(),
                                        'agent': os.environ.get('PASEO_AGENT_ID')})
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
                    'type': 'object', 'properties': {'type': {'enum': ['choice', 'number']},
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
