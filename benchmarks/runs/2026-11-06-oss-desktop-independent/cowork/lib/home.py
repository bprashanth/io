"""Local home, chart views and script Minis. No model is used for privacy review."""
import csv
import json
import time
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
from lib.minimap import params_for, map_questions, plain  # noqa: F401  (light: the router uses them)

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


def update_state(data_dir, change):
    """Keep workspace records intact across the MCP, page server and download processes."""
    with privacy.session_lock(data_dir):
        path = inside(data_dir, '.idli/home.json', exists=False)
        state = read(path) if path.exists() else {}
        change(state)
        write(path, state)
        return state


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
    if not isinstance(files, list) or not files:
        raise ValueError('Choose at least one file')
    root = Path(data_dir).resolve()
    out = []
    for item in files:
        if item.get('local'):
            path = inside(root, item['local'])
            if not path.is_relative_to(root / 'drive') or path.suffix.lower() not in ('.xlsx', '.csv'):
                raise ValueError('Choose a spreadsheet in drive/')
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
            if privacy.get(data_dir, rel)['mode'] != 'mask':
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
    env = {k: v for k, v in os.environ.items() if not k.startswith('PASEO_') or k == 'PASEO_HOME'}
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


def left_chat(workspace):
    if not isinstance(workspace, str) or not re.fullmatch(r'[\w-]{1,80}', workspace):
        raise ValueError('Invalid workspace')
    chats = json.loads(cli('ls', '--json', '--label', 'idli.ws=' + workspace))
    if isinstance(chats, dict):
        chats = chats.get('agents', [])
    # Paseo has already filtered by workspace; older versions omit labels in JSON.
    left = next((c for c in chats if (c.get('labels') or {}).get('idli.left') == '1'), None) or next(
        (c for c in chats if str(c.get('provider', '')).startswith('t4gc-cowork')), None) or (chats[0] if chats else None)
    if not left:
        raise ValueError('No left chat in this workspace')
    return left.get('id') or left['agentId']


def claude_insert(data_dir, workspace, text):
    """Insert chart context into this workspace's existing Claude, leaving it unsubmitted."""
    from lib import uiswitch
    if not isinstance(workspace, str) or not re.fullmatch(r'[\w-]{1,80}', workspace):
        raise ValueError('Invalid workspace')
    if (not isinstance(text, str) or not text.strip() or len(text) > 16000
            or any(ord(c) < 32 or ord(c) == 127 for c in text)):
        raise ValueError('Supply one line of chart context')
    with _SEND_LOCK:
        tid = _claude_terminal(data_dir, workspace)
        if not tid:
            raise ValueError('No Claude terminal in this workspace')
        cli('terminal', 'send-keys', '-l', tid, text)
    shown = uiswitch.show_terminal(workspace, tid, 'right')
    return {'inserted': True, 'terminal': tid, 'focused': bool(shown.get('ok'))}


def _drivey_workspace(data_dir, workspace=''):
    workspaces = json.loads(cli('workspace', 'ls', '--json'))
    mine = [w for w in workspaces if Path(w.get('cwd') or '.').expanduser().resolve() == Path(data_dir).resolve()]
    if workspace and any(w.get('workspaceId') == workspace for w in mine):
        return workspace
    if workspace or not mine:
        raise ValueError('Open this chat in its Drivey workspace and try again.')
    return sorted(mine, key=lambda w: w.get('name') != 'Drivey')[0]['workspaceId']


def _claude_terminal(data_dir, wid):
    """The live Claude terminal recorded for this workspace, or None."""
    state_path = Path(data_dir) / '.idli/home.json'
    state = read(state_path) if state_path.exists() else {}
    tid = (state.get('terminals') or {}).get(wid) or (state.get('terminal') if state.get('workspace') == wid else None)
    terms = json.loads(cli('terminal', 'ls', '--all', '--json') or '[]')
    live = {t.get('id') or t.get('terminalId') for t in terms
            if (t.get('workspaceId') or t.get('workspace')) == wid}
    if tid in live:
        return tid
    # Drivey's "+" (Paseo P18) starts the Claude terminal itself: use that one
    return next((t.get('id') or t.get('terminalId') for t in terms
                 if (t.get('workspaceId') or t.get('workspace')) == wid and t.get('name') == 'Claude'), None)


def _remember(data_dir, wid, tid, **more):
    def change(state):
        state.setdefault('terminals', {})[wid] = tid
        state.update(terminal=tid, workspace=wid, **more)
    update_state(data_dir, change)


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
        prompt = ('Files (masked by Idli): ' + ', '.join(x['local'] for x in chosen) + '. ' + ' '.join(str(question).split()))
        tid = _claude_terminal(data_dir, wid)
        if tid:
            type_into(tid, prompt)
        else:
            tid = _start_claude(wid, prompt)
        _remember(data_dir, wid, tid, files=chosen)
        update_state(data_dir, lambda state: state.setdefault('workspace_files', {}).update({wid: chosen}))
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
            # Minis saved before date/author were recorded: the file's date, and the same author rule Claude uses
            date = m.get('date') or time.strftime('%Y-%m-%d', time.localtime(path.stat().st_mtime))
            author = m.get('author')
            if not author:
                from lib import idli_mcp
                author = idli_mcp.mini_author()
            out.append({'id': path.parent.name, 'name': plain(m['name']), 'goal': plain(m['goal']),
                        'heading': plain(m.get('heading') or m['goal']), 'date': date,
                        'author': plain(author or ''), 'questions': len(m['questions'])})
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
    return {**v, 'id': ident, 'data': data}


def chart_sources(data_dir, sources=None):
    if sources is None:
        return []
    if not isinstance(sources, list) or any(not isinstance(s, str) for s in sources):
        raise ValueError('Sources must be a list of files in drive/')
    root = Path(data_dir).resolve()
    return list(dict.fromkeys(str(inside(root / 'drive', root / s).relative_to(root)) for s in sources))


def run_mini(data_dir, ident, qid, params):
    return run_manifest(data_dir, object_path(data_dir, 'minis', ident), qid, params)


def run_manifest(data_dir, manifest, qid, params):
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
    return {'text': '\n'.join(lines), 'chart': chart, 'qid': qid, 'params': values, 'agent': m.get('agent'),
            'sources': chart_sources(data_dir, [f['local'] for f in m.get('files', []) if f.get('local')]),
            'script': str(script)}


def map_question(data_dir, ident, text):
    return map_questions(read(object_path(data_dir, 'minis', ident))['questions'], text)


def chart_markdown(data_dir, title, chart, agent=None, sources=None, script=None, workspace=None):
    """Save one computed chart as both a local SVG and an interactive view."""
    if not chart:
        return ''
    sources = chart_sources(data_dir, sources)
    script = str(allowed_path(data_dir, script)) if script else None
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
                                    'data_csv': str(csv_path), 'agent': agent, 'sources': sources, 'script': script,
                                    'workspace': workspace})
    port, token = formserver.ensure(str(data_dir))
    url = f'http://dashboard.localhost:{port}/view?' + urllib.parse.urlencode({'id': ident, 't': token})
    label = title.replace('[', '').replace(']', '').replace('\n', ' ')
    return f'![{label}]({out})\n[Open interactive]({url})'


def mini_open(data_dir, ident, workspace=None):
    m = read(object_path(data_dir, 'minis', ident))
    if workspace:
        def change(state):
            state.setdefault('workspace_minis', {})[workspace] = ident
            state.setdefault('workspace_files', {})[workspace] = m.get('files', [])
        update_state(data_dir, change)
    lines = [m['name'], 'Goal: ' + m['goal'],
             'Source files: ' + ', '.join(x.get('title') or x.get('local') or x.get('id', '') for x in m.get('files', []))]
    from lib import journey
    for chart in m.get('charts', []):
        lines.append('[Pinned chart: ' + plain(chart['title']) + '](' + journey.page_url(
            data_dir, 'view', id=chart['id'], embed=1, ws=workspace or '') + ')')
    for q in m['questions']:
        lines.extend(['', q['question']])
        for key, desc in q.get('params', {}).items():
            options = ', '.join(map(str, desc['choices'])) if desc['type'] == 'choice' else desc['type']
            lines.append(f"{key}: {options}; default = {desc.get('default')}")
        example = run_mini(data_dir, ident, q['id'], {})
        lines.append('Example: ' + example['text'])
        if example['chart']:
            lines.append(chart_markdown(data_dir, q['question'], example['chart'], m.get('agent'),
                                        example['sources'], example['script'], workspace))
    return {'id': ident, 'files': m.get('files', []), 'questions': m['questions'], 'reply': plain('\n'.join(lines))}


def mini_ask(data_dir, ident, qid, params, workspace=None):
    m = read(object_path(data_dir, 'minis', ident))
    q = next(q for q in m['questions'] if q['id'] == qid)
    result = run_mini(data_dir, ident, qid, params)
    using = ', '.join(f'{k} = {v}' for k, v in result['params'].items())
    lines = ['Using: ' + q['question'] + (': ' + using if using else ''), result['text']]
    if result['chart']:
        lines.append(chart_markdown(data_dir, q['question'], result['chart'], m.get('agent'),
                                    result['sources'], result['script'], workspace))
    return {**result, 'reply': plain('\n'.join(lines))}
