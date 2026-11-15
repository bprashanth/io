#!/usr/bin/env python3
"""Small stdio MCP for the person's masked Claude. Never log tool arguments or URLs."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.parse

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from lib import home  # noqa: E402


def data_dir():
    return Path(os.environ.get('IDLI_DATA', '~/idli-insights/cowork-real')).expanduser().resolve()


def page_url(page, ident):
    from lib import formserver
    port, token = formserver.ensure(str(data_dir()))
    return f'http://dashboard.localhost:{port}/{page}?' + urllib.parse.urlencode({'id': ident, 't': token})


def idli_show(title, vega_lite, data_csv, sources=None, script=None):
    import csv
    path = home.allowed_path(data_dir(), data_csv)
    if path.suffix.lower() != '.csv' or not isinstance(vega_lite, dict):
        raise ValueError('Supply a CSV and a Vega-Lite object')
    with path.open(newline='') as f:
        rows = list(csv.DictReader(f))
    # Claude's CSV and spec hold codes (its scripts run on masked copies); the person sees real values.
    title, vega_lite, rows = home.rehydrate(data_dir(), [title, vega_lite, rows])
    from lib import maps
    vega_lite = maps.prepare(vega_lite, rows)
    state = Path(data_dir()) / '.idli/home.json'
    st = home.read(state) if state.exists() else {}
    agent = os.environ.get('PASEO_AGENT_ID') or st.get('terminal')
    workspace = os.environ.get('IDLI_WORKSPACE')
    if workspace:
        try:  # only for "Copy to Claude"; a chart must still open without Paseo's command line
            terminal = home._claude_terminal(data_dir(), workspace)
        except (OSError, ValueError):
            terminal = None
        if terminal:
            home._remember(data_dir(), workspace, terminal)
            agent = terminal
    markdown = home.chart_markdown(data_dir(), title, {'vega_lite': vega_lite, 'data': rows}, agent,
                                   sources, script, workspace)
    url = re.search(r'\n\[Open interactive\]\(([^)]+)\)', markdown)[1]
    # The chart goes into the Drivey chat on the left, the person's running binder of what goes into a Mini.
    if workspace:
        try:
            home.post_to_left(workspace, 'Chart', title)
            return {'shown': True, 'message': 'The chart is in the Drivey chat on the left, where the person can pin '
                                              'it for a Mini. Say so in one short line.'}
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    from lib import uiswitch
    opened = uiswitch.open_url(workspace, url, side='right', focus=True)
    return {'shown': bool(opened.get('ok')), 'url': url,
            'message': 'Chart opened on the right.' if opened.get('ok') else 'Open the chart with this link.'}


def unmask(code, reason, whole_column=False):
    from lib import reveals
    result = reveals.ask(data_dir(), code, reason, os.environ.get('IDLI_WORKSPACE'), whole_column=bool(whole_column))
    if 'refused' in result:
        return result
    # The masked copies in Claude's folder now show the values too, so its commands keep matching the data.
    from lib import maskcopy
    maskcopy.build(data_dir(), home.work_dir())
    if result.get('values'):
        return {'column': result['column'], 'values': {v['code']: v['value'] for v in result['values']},
                'note': 'Your copies in drive/ now show these values instead of the codes.'}
    return {'code': code, 'value': result['value'],
            'note': 'Your copies in drive/ now show this value instead of the code.'}


def lookup(code, query, reason):
    from lib import reveals
    result = reveals.ask(data_dir(), code, reason, os.environ.get('IDLI_WORKSPACE'), 'lookup', query)
    if 'refused' in result:
        return result
    try:
        return reveals.lookup_results(data_dir(), code, result['query'], result['value'])
    except (OSError, ValueError):
        return {'refused': 'The search could not finish. The value stays hidden from Claude.'}


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
    """Older callers also get the editable draft; only the person can publish it."""
    return idli_draft_mini(name, goal, questions, str(home.work_dir()))


def idli_draft_mini(title, story, questions, code=''):
    from lib import journey, uiswitch
    workspace = os.environ.get('IDLI_WORKSPACE')
    ident = journey.draft_mini(data_dir(), title, story, questions, code, workspace, mini_author())
    try:  # the draft shows in the Drivey chat, under the charts it collected
        home.post_to_left(workspace, 'Mini draft', journey.draft_data(data_dir(), ident)['name'])
        return {'draft': ident, 'shown': True, 'message': 'The draft is in the Drivey chat on the left. The person '
                'can change the words there and save. Say so in one short line.'}
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    url = journey.page_url(data_dir(), 'mini-editor', id=ident, ws=workspace or '')
    opened = uiswitch.open_url(workspace, url, side='right', focus=True)
    return {'draft': ident, 'url': url, 'opened': bool(opened.get('ok')),
            'message': 'Check the title, story and questions, then choose Save.'}


TOOLS = {
    'idli_show': (idli_show, 'After the person agrees to see a chart, show your computed CSV in Idli.', {
        'title': {'type': 'string'}, 'vega_lite': {'type': 'object'}, 'data_csv': {'type': 'string'},
        'sources': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Source files under drive/'},
        'script': {'type': 'string', 'description': 'Script that wrote the CSV'}},
        ['title', 'vega_lite', 'data_csv']),
    'idli_save_mini': (idli_save_mini, 'Save questions after brainstorming and checking every script result with the person.', {
        'name': {'type': 'string'}, 'goal': {'type': 'string'}, 'questions': {'type': 'array', 'items': {
            'type': 'object', 'properties': {'id': {'type': 'string'}, 'question': {'type': 'string'},
                'script': {'type': 'string'}, 'params': {'type': 'object', 'additionalProperties': {
                    'type': 'object', 'properties': {'type': {'enum': ['choice', 'number']},
                        'choices': {'type': 'array'}, 'default': {}}, 'required': ['type', 'default']}},
                'chart': {}, 'asks': {'type': 'array', 'items': {'type': 'string'}, 'description':
                    '3 to 5 ways a colleague might ask this in their own words, e.g. "who is most stretched in <a ward>"'}},
                'required': ['id', 'question', 'script', 'params']}}}, ['name', 'goal', 'questions'])}


TOOLS['idli_draft_mini'] = (idli_draft_mini, 'After checking every script, open an editable Mini draft with this workspace\'s pinned charts.',
    {'title': {'type': 'string'}, 'story': {'type': 'string'}, 'questions': TOOLS.pop('idli_save_mini')[2]['questions'],
     'code': {'type': 'string', 'description': 'Where the checked scripts live.'}}, ['title', 'story', 'questions', 'code'])


# lookup (a search from this computer with masked results) is withheld from Claude: pages about a value bring in
# names and facts Idli doesn't know, so the results can't be masked reliably, and they are thinner than WebSearch after
# a reveal. The code stays for the local 9B, which sees real values anyway (owner decision 2026-11-15).
for name, fn, description in [
        ('unmask', unmask, 'Ask the person to reveal one contextual code, or with whole_column every code in its column '
                           '(for short category or species codes). Personal data is never revealed.')]:
    props = {'code': {'type': 'string'}, 'reason': {'type': 'string'}}
    if name == 'lookup':
        props['query'] = {'type': 'string', 'description': 'Search text containing {value}.'}
    required = list(props)
    if name == 'unmask':
        props['whole_column'] = {'type': 'boolean', 'description': 'Reveal every value in this code\'s column (one reveal).'}
    TOOLS[name] = (fn, description, props, required)


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
                except ValueError as exc:
                    from lib.maps import MapError
                    # Idli's own messages are written for people; strip any path or page token before Claude sees it.
                    detail = re.sub(r'(?:[A-Za-z]:)?/[^\s,;)]+|[?&]t=[\w-]+', '<path>', str(exc)).strip()[:300]
                    detail = detail if isinstance(exc, MapError) or detail else 'Check the file paths and inputs, then retry.'
                    result = {'isError': True, 'content': [{'type': 'text', 'text': detail}]}
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
