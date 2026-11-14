"""Local home, chart views and script Minis. No model is used for privacy review."""
import csv
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
import uuid

from lib import privacy, filekit, muse

_SEND_LOCK = threading.Lock()


def inside(root, name, exists=True):
    root = Path(root).resolve()
    path = (root / name).resolve()
    if path == root or not path.is_relative_to(root) or (exists and not path.is_file()):
        raise ValueError('File must be inside its workspace folder')
    return path


def work_dir():
    return Path(os.environ.get('IDLI_CLAUDE_WORK', '~/idli-insights/claude-masked')).expanduser().resolve()


def allowed_path(data_dir, name):
    for root in (work_dir(), Path(data_dir).resolve()):
        try:
            return inside(root, name)
        except ValueError:
            pass
    raise ValueError('File must be inside the Claude work folder or data directory')


def write(path, obj):
    privacy._write(Path(path), obj)


def read(path):
    return json.loads(Path(path).read_text())


def search(data_dir, query):
    from lib import driveindex
    results = []
    drive = Path(data_dir) / 'drive'
    for path in sorted(drive.rglob('*.xlsx')):
        if query.casefold() not in str(path.relative_to(drive)).casefold():
            continue
        try:
            rel = str(inside(data_dir, path).relative_to(Path(data_dir).resolve()))
        except ValueError:
            continue
        results.append({'title': path.stem, 'local': rel, 'folder': 'on this computer'})
    hits = driveindex.search(query, limit=12)
    for hit in hits.get('results', []):
        if hit.get('kind') not in ('sheet', 'spreadsheet', 'xlsx', 'application/vnd.google-apps.spreadsheet',
                                   'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'Google Sheets', 'Microsoft Excel'):
            continue
        results.append({'id': hit['id'], 'title': hit['name'], 'folder': hit.get('folder', ''),
                        'sheet': hit.get('kind') != 'Microsoft Excel'})
    return {'results': results[:24]}


def selected(data_dir, files, fetch=False):
    if not isinstance(files, list) or not files or len(files) > 20:
        raise ValueError('Choose between one and twenty files')
    root = Path(data_dir).resolve()
    out = []
    for item in files:
        if item.get('local'):
            path = inside(root, item['local'])
            if not path.is_relative_to(root / 'drive') or path.suffix.lower() != '.xlsx':
                raise ValueError('Choose an Excel file in drive/')
        elif fetch and item.get('id'):
            from lib import drivefetch
            fid = str(item['id'])
            if not re.fullmatch(r'[\w-]+', fid):
                raise ValueError('Invalid Drive id')
            title = re.sub(r'[^\w .()-]+', '_', str(item.get('title') or fid)).strip(' .')[:80] or fid
            if title.lower().endswith('.xlsx'):
                title = title[:-5]
            path = inside(root, 'drive/' + title + '.xlsx', exists=False)
            if path.exists() and (not Path(str(path) + '.source.json').exists()
                                  or read(str(path) + '.source.json').get('id') != fid):
                path = inside(root, 'drive/' + title + '-' + fid[:12] + '.xlsx', exists=False)
                if path.exists() and (not Path(str(path) + '.source.json').exists()
                                      or read(str(path) + '.source.json').get('id') != fid):
                    raise ValueError('Another file already uses that download name')
            data = drivefetch.fetch(fid, item.get('sheet', True))
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
            try:
                tmp.write_bytes(data)
                os.replace(tmp, path)
            finally:
                tmp.unlink(missing_ok=True)
            write(str(path) + '.source.json', {'id': fid, 'url': ('https://docs.google.com/spreadsheets/d/' if item.get('sheet', True)
                                                       else 'https://drive.google.com/file/d/') + fid,
                                                   'sheet': item.get('sheet', True)})
        else:
            raise ValueError('Prepare these files before sending')
        rel = path.relative_to(root).as_posix()
        if not any(x['local'] == rel for x in out):
            out.append({'title': item.get('title') or path.stem, 'local': rel,
                        **({'id': item['id']} if item.get('id') else {})})
    return out


def prepare(data_dir, files, question):
    chosen = selected(data_dir, files, fetch=True)
    with privacy.session_lock(data_dir):
        for item in chosen:
            rel = item['local']
            if privacy.get(data_dir, rel)['mode'] is None:
                sheets, _ = filekit.raw_sheets(str(Path(data_dir) / rel))
                columns = {}
                for tab in sheets:
                    for row in privacy.suggest(Path(data_dir) / rel, tab):
                        columns[row['column']] = columns.get(row['column'], False) or row['mask']
                privacy.set(data_dir, rel, mode='mask', review='ask', columns=columns)
        # Seed all files before masking: the namespace and the question span every workbook.
        privacy.session_vault(data_dir)
        masked = str(question)
        reviews = []
        for item in chosen:
            rel, path = item['local'], Path(data_dir) / item['local']
            masked = privacy.mask_text(data_dir, rel, path, masked, active=True)['masked']
            sheets, _ = filekit.raw_sheets(str(path))
            reviews.append({**item, 'tabs': [privacy.review(data_dir, rel, path, tab) for tab in sheets]})
        return {'files': chosen, 'reviews': reviews, 'masked_question': masked,
                'warning': privacy.review_warning(data_dir, [x['local'] for x in chosen])}


def cli(*args):
    env = {k: v for k, v in os.environ.items() if not k.startswith('PASEO_')}
    r = subprocess.run([shutil.which('paseo') or 'paseo', *args], env=env, capture_output=True,
                       text=True, timeout=90, stdin=subprocess.DEVNULL)
    if r.returncode:
        raise ValueError('Paseo could not complete the request')
    return r.stdout


def chat_workspace():
    if os.environ.get('IDLI_WORKSPACE'):
        return os.environ['IDLI_WORKSPACE']
    agent = os.environ.get('PASEO_AGENT_ID')
    if agent:
        chats = json.loads(cli('ls', '--json', '--label', 'idli.left=1'))
        if isinstance(chats, dict):
            chats = chats.get('agents', [])
        return next(((c.get('labels') or {}).get('idli.ws') for c in chats
                     if (c.get('id') or c.get('agentId')) == agent), None)
    return None


LAUNCHER = Path(__file__).resolve().parent.parent / 'desktop' / 'claude-masked.sh'


def type_into(terminal, text):
    """Type one line into a terminal and press Enter (the person's Claude CLI)."""
    cli('terminal', 'send-keys', '-l', terminal, ' '.join(str(text).split()))
    cli('terminal', 'send-keys', '-l', terminal, '\r')


def _drivey_workspace(data_dir, workspace=''):
    workspaces = json.loads(cli('workspace', 'ls', '--json'))
    mine = [w for w in workspaces if Path(w.get('cwd') or '.').expanduser().resolve() == Path(data_dir).resolve()]
    if workspace and any(w.get('workspaceId') == workspace for w in mine):
        return workspace
    if not mine:
        raise ValueError('No Drivey workspace found')
    return sorted(mine, key=lambda w: w.get('name') != 'Drivey')[0]['workspaceId']


def _claude_terminal(data_dir, wid):
    """The live Claude terminal recorded for this workspace, or None."""
    state_path = Path(data_dir) / '.idli/home.json'
    state = read(state_path) if state_path.exists() else {}
    tid = (state.get('terminals') or {}).get(wid) or (state.get('terminal') if state.get('workspace') == wid else None)
    terms = json.loads(cli('terminal', 'ls', '--all', '--json') or '[]')
    live = {t.get('id') or t.get('terminalId') for t in terms}
    if tid in live:
        return tid
    # Drivey's "+" (Paseo P18) starts the Claude terminal itself: use that one
    return next((t.get('id') or t.get('terminalId') for t in terms
                 if (t.get('workspaceId') or t.get('workspace')) == wid and t.get('name') == 'Claude'), None)


def _remember(data_dir, wid, tid, **more):
    state_path = Path(data_dir) / '.idli/home.json'
    state = read(state_path) if state_path.exists() else {}
    state.setdefault('terminals', {})[wid] = tid
    state.update(terminal=tid, workspace=wid, **more)
    write(state_path, state)


def _start_claude(wid, prompt=None):
    import shlex
    made = json.loads(cli('terminal', 'create', '--workspace', wid, '--name', 'Claude', '--json'))
    tid = made.get('id') or made.get('terminalId')
    if not tid:
        raise ValueError('Paseo did not create a terminal')
    cmd = 'IDLI_WORKSPACE=' + shlex.quote(wid) + ' exec ' + shlex.quote(str(LAUNCHER)) + (' ' + shlex.quote(prompt) if prompt else '')
    cli('terminal', 'send-keys', '-l', tid, cmd)
    cli('terminal', 'send-keys', '-l', tid, '\r')
    return tid


def ensure_claude(data_dir, workspace=''):
    """Idli home opened in a Drivey workspace: make sure the person's Claude CLI is running on the right (without
    taking focus from Idli home)."""
    from lib import uiswitch
    with _SEND_LOCK:
        wid = _drivey_workspace(data_dir, workspace)
        tid = _claude_terminal(data_dir, wid) or _start_claude(wid)
        _remember(data_dir, wid, tid)
    shown = uiswitch.show_terminal(wid, tid, 'right', focus=False)
    return {'terminal': tid, 'placed': bool(shown.get('ok'))}


def send(data_dir, files, question, workspace=''):
    """Hand the question to the person's Claude Code CLI in this Drivey workspace (desktop/claude-masked.sh, through
    the masking proxy), on the right with focus: typed into it, or started with it if it isn't running."""
    from lib import uiswitch
    chosen = selected(data_dir, files)
    if not str(question).strip():
        raise ValueError('Write a question first')
    if any(privacy.get(data_dir, x['local'])['mode'] != 'mask' for x in chosen):
        raise ValueError('Choose Mask for these files before sending to Claude')
    with _SEND_LOCK:
        wid = _drivey_workspace(data_dir, workspace)
        prompt = ('Files (in drive/): ' + ', '.join(x['local'] for x in chosen) + '. ' + ' '.join(str(question).split()))
        tid = _claude_terminal(data_dir, wid)
        if tid:
            type_into(tid, prompt)
        else:
            tid = _start_claude(wid, prompt)
        _remember(data_dir, wid, tid, files=chosen)
    shown = uiswitch.show_terminal(wid, tid, 'right')
    return {'terminal': tid, 'focused': bool(shown.get('ok')), 'message': 'Claude has it on the right'}


def object_path(data_dir, kind, ident):
    if not re.fullmatch(r'[\w-]{1,100}', str(ident)):
        raise ValueError('Invalid id')
    return inside(data_dir, f'{kind}/{ident}.json' if kind == 'views' else f'minis/{ident}/mini.json')


def minis(data_dir):
    out = []
    for path in sorted((Path(data_dir) / 'minis').glob('*/mini.json')):
        try:
            m = read(object_path(data_dir, 'minis', path.parent.name))
            out.append({'id': path.parent.name, 'name': plain(m['name']), 'goal': plain(m['goal']),
                        'heading': plain(m.get('heading') or m['goal']), 'date': m.get('date', ''),
                        'author': plain(m.get('author', '')), 'questions': len(m['questions'])})
        except (OSError, ValueError, KeyError):
            continue
    return out


def view(data_dir, ident):
    v = read(object_path(data_dir, 'views', ident))
    path = allowed_path(data_dir, v['data_csv'])
    if path.suffix.lower() != '.csv':
        raise ValueError('Charts require a CSV file')
    with path.open(newline='') as f:
        data = list(csv.DictReader(f))
    return {**v, 'data': data}


def params_for(q, values):
    if not isinstance(values, dict) or values.keys() - q.get('params', {}).keys():
        raise ValueError('Unknown parameter')
    out = {}
    for key, desc in q.get('params', {}).items():
        if not isinstance(desc, dict) or desc.get('type') not in ('choice', 'number', 'text'):
            raise ValueError('Invalid parameter type')
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', key):
            raise ValueError('Invalid parameter name')
        value = values.get(key, desc.get('default'))
        if value is None:
            raise ValueError('Enter ' + key)
        if desc['type'] == 'choice' and value not in desc.get('choices', []):
            raise ValueError('Invalid choice for ' + key)
        if desc['type'] == 'number':
            import math
            if isinstance(value, bool) or not math.isfinite(float(value)):
                raise ValueError('Enter a finite number for ' + key)
            value = float(value)
            value = int(value) if value.is_integer() else value
        if not isinstance(value, (str, int, float)) or len(str(value)) > 2000:
            raise ValueError('Invalid parameter value')
        out[key] = value
    return out


def run_mini(data_dir, ident, qid, params):
    manifest = object_path(data_dir, 'minis', ident)
    m = read(manifest)
    q = next((q for q in m['questions'] if q['id'] == qid), None)
    if not q:
        raise ValueError('Unknown Mini question')
    values = params_for(q, params)
    script = inside(manifest.parent, q['script'])
    if script.suffix != '.py':
        raise ValueError('Mini scripts must be Python files')
    args = [sys.executable, '-I', str(script)]
    for key, value in values.items():
        args.extend(['--' + key, str(value)])
    env = {k: v for k, v in os.environ.items() if not k.startswith('PASEO_')}
    try:
        r = subprocess.run(args, cwd=manifest.parent, env=env, capture_output=True, text=True, timeout=60,
                           stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        raise ValueError('This question took longer than 60 seconds') from None
    if r.returncode:
        raise ValueError('The Mini script failed. Ask Claude to check it.')
    lines = r.stdout.rstrip().splitlines()
    chart = None
    if lines:
        try:
            last = json.loads(lines[-1])
            if isinstance(last, dict) and isinstance(last.get('vega_lite'), dict) and isinstance(last.get('data'), list):
                chart = last
                lines.pop()
        except ValueError:
            pass
    return {'text': '\n'.join(lines), 'chart': chart, 'qid': qid, 'params': values, 'agent': m.get('agent')}


def map_questions(questions, text, local_url=None):
    """The local 9B selects a saved question, or explicitly declines. Never guess on failure."""
    if not questions:
        raise ValueError('This Mini has no questions')
    brief = [{k: q.get(k, {}) for k in ('id', 'question', 'params')} for q in questions]
    branches = []
    for q in questions:
        props = {}
        for key, desc in q.get('params', {}).items():
            props[key] = ({'type': 'string', 'enum': desc['choices']} if desc['type'] == 'choice'
                          else {'type': 'number'} if desc['type'] == 'number' else {'type': 'string'})
        branches.append({'type': 'object', 'properties': {'reason': {'type': 'string', 'maxLength': 160}, 'qid': {'const': q['id']},
                         'params': {'type': 'object', 'properties': props, 'required': list(props),
                                    'additionalProperties': False}},
                         'required': ['reason', 'qid', 'params'], 'additionalProperties': False})
    branches.append({'type': 'object', 'properties': {'reason': {'type': 'string', 'maxLength': 160}, 'qid': {'type': 'null'},
                     'params': {'type': 'object', 'properties': {}, 'additionalProperties': False}},
                     'required': ['reason', 'qid', 'params'], 'additionalProperties': False})
    schema = {'oneOf': branches}
    direct = local_url or os.environ.get('IDLI_9B_URL')
    payload = {'model': 'qwen3.5-9b' if direct else 'idli-9b', 'temperature': 0, 'max_tokens': 400,
               'chat_template_kwargs': {'enable_thinking': False}, 'messages': [
        {'role': 'system', 'content': 'Map the person\'s request to a saved question. Do not answer it. '
         'Choose qid null with params {} if the requested calculation is not supported, the topic is unrelated, '
         'or an explicitly named choice is unavailable. Do not substitute a different question. '
         'Match the requested calculation and measure exactly. A comparison of one measure cannot answer '
         'a comparison of a different measure. A numeric summary cannot explain causes or predict the future. '
         'Paraphrases are fine. Use parameter defaults only when no value is given. '
         'In one short sentence in reason, state the requested measure and calculation and whether a saved question supports both. '
         'Then choose qid and params. Copy explicitly requested numbers and choices, matching choice case. Return JSON only.\n'
         + json.dumps(brief)}, {'role': 'user', 'content': str(text)[:4000]}],
        'response_format': {'type': 'json_schema', 'json_schema': {'name': 'mini_question', 'schema': schema}}}
    # The DGX chat router calls its local 9B; laptop pages use the configured spec router.
    url = (direct or muse.base_url()).rstrip('/')
    try:
        req = urllib.request.Request(url + '/v1/chat/completions', json.dumps(payload).encode(),
                                     {'Content-Type': 'application/json', **({} if direct else muse.headers())})
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(json.load(response)['choices'][0]['message']['content'])
        if result['qid'] is None:
            return {'qid': None, 'params': {}, 'method': 'idli-9b'}
        q = next(q for q in questions if q['id'] == result['qid'])
        values = params_for(q, result['params'])
        # Check only the chosen question, without competing questions that share a word.
        # This catches unsupported measures/forecasts and checks explicit values against defaults.
        param_schema = next(b['properties']['params'] for b in branches if b['properties']['qid'].get('const') == q['id'])
        verification = {'type': 'object', 'properties': {'reason': {'type': 'string', 'maxLength': 160},
                        'supported': {'type': 'boolean'}, 'params': param_schema},
                        'required': ['reason', 'supported', 'params'], 'additionalProperties': False}
        payload['response_format']['json_schema']['schema'] = verification
        payload['messages'] = [
            {'role': 'system', 'content': 'Check one saved calculation against a request. Be strict about support. '
             'The saved question must support the exact requested measure, statistic, operation and time period. '
             'A numeric comparison cannot answer a request for causes. Current data cannot predict future data. '
             'A list cannot provide fields it does not list. Reject unavailable named choices and requests to change data. '
             'Use supported false if the calculation cannot answer the request. If it can, verify the parameters: '
             'correct explicit choices and numbers (including number words); use defaults only for unspecified values. '
             'State the check in one short sentence in reason, then supported and params. Return JSON only.'},
            {'role': 'user', 'content': json.dumps({'request': str(text)[:4000],
                                                  'saved_question': next(b for b in brief if b['id'] == q['id']),
                                                  'proposed_params': values})}]
        req = urllib.request.Request(url + '/v1/chat/completions', json.dumps(payload).encode(),
                                     {'Content-Type': 'application/json', **({} if direct else muse.headers())})
        with urllib.request.urlopen(req, timeout=60) as response:
            checked = json.loads(json.load(response)['choices'][0]['message']['content'])
        if checked.get('supported') is not True:
            return {'qid': None, 'params': {}, 'method': 'idli-9b'}
        return {'qid': q['id'], 'params': params_for(q, checked['params']), 'method': 'idli-9b'}
    except (OSError, ValueError, KeyError, TypeError, StopIteration):
        return {'qid': None, 'params': {}, 'method': 'unavailable'}


def map_question(data_dir, ident, text):
    return map_questions(read(object_path(data_dir, 'minis', ident))['questions'], text)


def plain(text):
    """Shared visible-text contract, including Mini script output and chart titles."""
    return re.sub('[\u2190-\u21ff\u27f0-\u27ff]', ' -> ', str(text)).replace('·', ' - ')


def chart_markdown(data_dir, title, chart, agent=None):
    """Save one computed chart as both a local SVG and an interactive view."""
    if not chart:
        return ''
    import copy
    import vl_convert
    from lib import formserver
    ident = uuid.uuid4().hex
    title = plain(title)
    def clean(value):
        if isinstance(value, dict):
            return {plain(k): clean(v) for k, v in value.items() if k not in ('url', 'href', 'datasets')}
        if isinstance(value, list):
            return [clean(v) for v in value]
        return plain(value) if isinstance(value, str) else value
    spec = clean(copy.deepcopy(chart['vega_lite']))
    rows = clean(chart['data'])
    # Computed rows are authoritative. Never load external URLs from a Mini's spec.
    spec['data'] = {'values': rows}
    svg = vl_convert.vegalite_to_svg(json.dumps(spec))
    out = inside(data_dir, 'views/' + ident + '.svg', exists=False)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg)
    csv_path = out.with_suffix('.csv')
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with csv_path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    write(out.with_suffix('.json'), {'title': title, 'spec': spec,
                                    'data_csv': str(csv_path), 'agent': agent})
    port, token = formserver.ensure(str(data_dir))
    url = f'http://dashboard.localhost:{port}/view?' + urllib.parse.urlencode({'id': ident, 't': token})
    label = title.replace('[', '').replace(']', '').replace('\n', ' ')
    return f'![{label}]({out})\nOpen interactive: {url}'


def mini_open(data_dir, ident):
    m = read(object_path(data_dir, 'minis', ident))
    lines = [m['name'], 'Goal: ' + m['goal'],
             'Source files: ' + ', '.join(x.get('title') or x.get('local') or x.get('id', '') for x in m.get('files', []))]
    for q in m['questions']:
        lines.extend(['', q['question']])
        for key, desc in q.get('params', {}).items():
            options = ', '.join(map(str, desc['choices'])) if desc['type'] == 'choice' else desc['type']
            lines.append(f"{key}: {options}; default = {desc.get('default')}")
        example = run_mini(data_dir, ident, q['id'], {})
        lines.append('Example: ' + example['text'])
        if example['chart']:
            lines.append(chart_markdown(data_dir, q['question'], example['chart'], m.get('agent')))
    return {'id': ident, 'questions': m['questions'], 'reply': plain('\n'.join(lines))}


def mini_ask(data_dir, ident, qid, params):
    m = read(object_path(data_dir, 'minis', ident))
    q = next(q for q in m['questions'] if q['id'] == qid)
    result = run_mini(data_dir, ident, qid, params)
    using = ', '.join(f'{k} = {v}' for k, v in result['params'].items())
    lines = ['Using: ' + q['question'] + (': ' + using if using else ''), result['text']]
    if result['chart']:
        lines.append(chart_markdown(data_dir, q['question'], result['chart'], m.get('agent')))
    return {**result, 'reply': plain('\n'.join(lines))}
