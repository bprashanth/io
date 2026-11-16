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
    maskcopy.build(data_dir(), home.work_dir(data_dir()))
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
    return idli_draft_mini(name, goal, questions, str(home.work_dir(data_dir())))


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


def builder_open(request):
    """The Analyst was asked for something outside the team's capabilities and the person said yes."""
    from lib import builder
    return builder.open_builder(str(data_dir()), request, os.environ.get('IDLI_WORKSPACE', ''))


TOOLS['builder_open'] = (builder_open, "After the person says yes, open this team's Builder with their request: for "
                         "something the team can't do yet (a new kind of file, tool or site). Not for Mini changes.",
                         {'request': {'type': 'string', 'description': 'What the team should be able to do, in one or '
                                                                       'two plain sentences.'}}, ['request'])


def _original(name):
    """The original file behind a name the Analyst knows (a masked copy, a table read from it, or the file)."""
    from lib import teamcaps
    base = data_dir()
    rel = str(name).strip().lstrip('/')
    rel = rel[6:] if rel.startswith('Drive/') else rel
    for cand in (rel, 'drive/' + rel):
        p = (base / cand).resolve()
        while p.is_relative_to(base) and p != base:
            if p.is_file() and teamcaps.kind_of(p) and not p.name.endswith('.csv') or (
                    p.is_file() and p.suffix == '.csv' and not p.name.count('.') > 1):
                return p
            if p.suffix:
                p = p.with_name(p.stem)  # talk.mp4.table.csv -> talk.mp4.table -> talk.mp4
            else:
                break
    raise ValueError(f'{name} is not one of the files in this workspace.')


def _masked(obj, depth=0):
    """A tool's short result, with free text masked the way Claude's requests are (lib/privacy.mask_free_text)."""
    from lib import privacy
    if depth > 4:
        return None
    if isinstance(obj, str):
        return ' '.join(privacy.mask_free_text(str(data_dir()), obj[:500]).split())
    if isinstance(obj, (int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, dict):
        return {str(k)[:60]: _masked(v, depth + 1) for k, v in list(obj.items())[:40]}
    if isinstance(obj, (list, tuple)):
        return [_masked(v, depth + 1) for v in list(obj)[:40]]
    return None


def team_run(capability, files, instructions=None):
    """Run one of the team's tools on the original files, on this computer."""
    from lib import teamcaps
    cap = next((c for c in teamcaps.tools(str(data_dir())) if c['id'] == capability), None)
    if not cap:
        raise ValueError('That is not one of this team\'s tested tools. See the list in your instructions.')
    instructions = home.rehydrate(data_dir(), [instructions or {}])[0]  # codes back to real values, locally
    res = teamcaps.run_tool(str(data_dir()), cap, [_original(f) for f in (files or [])], instructions)
    rel = Path(res['folder']).relative_to(data_dir())
    return {'done': True, 'folder': str(rel), 'files': res['files'],
            'result': _masked(res['result']),
            'tell_person': f'The result is in {rel}. Open it from the team folder.'}


def app_open(capability):
    """Open a page the team serves (an app capability) in the person's browser tab, on this computer."""
    from lib import stackwall, teamcaps, uiswitch
    cap = next((c for c in teamcaps.capabilities(str(data_dir())) if c.get('kind') == 'app' and
                c['id'] == capability), None)
    if not cap:
        raise ValueError('That is not one of this team\'s tested pages.')
    page = stackwall.serve(str(data_dir()), cap['serve'], data_dir() / 'apps' / cap['id'])
    shown = {}
    if os.environ.get('IDLI_WORKSPACE'):
        try:
            shown = uiswitch.open_url(os.environ['IDLI_WORKSPACE'], page['url'], side='left')
        except Exception:
            shown = {}
    return {'opened': bool(shown.get('ok')), 'tell_person': f"{cap['title']} is open in a tab on the left." if
            shown.get('ok') else f"{cap['title']} is running. Open {page['url']} in the browser."}


def team_capabilities():
    """What this team can do now (the Builder may have added abilities since you started)."""
    from lib import teamcaps
    return teamcaps.describe(str(data_dir()), teamcaps.team_name(str(data_dir())))


TOOLS['team_capabilities'] = (team_capabilities, "What this team knows how to do right now, including what its "
                              "Builder added after you started. Check it before saying the team can't do something.",
                              {}, [])
TOOLS['team_run'] = (team_run, "Run one of this team's tested tools (your instructions list them) on the original "
                     'files, on this computer. Only file names and a short result come back.',
                     {'capability': {'type': 'string'},
                      'files': {'type': 'array', 'items': {'type': 'string'},
                                'description': 'Files as you know them in this workspace (a table read from a video '
                                               'names that video).'},
                      'instructions': {'type': 'object', 'description': 'What the tool asks for (its line in your '
                                       'instructions says).'}}, ['capability', 'files'])
TOOLS['app_open'] = (app_open, "Open one of this team's pages (apps) for the person, on this computer.",
                     {'capability': {'type': 'string'}}, ['capability'])


# ---- the Builder's tools (IDLI_ROLE=builder, desktop/claude-builder.sh): it never gets the Analyst's ----

def team_check():
    """Check the manifest and run every capability's test in Idli's wall. Only passing ones count."""
    from lib import teamcaps
    out = teamcaps.run_tests(str(data_dir()))
    out['team_can_now'] = [c['title'] for c in teamcaps.capabilities(str(data_dir()))]
    return out


def team_save(summary):
    """Save a checkpoint (the team card's Versions) after the tests pass."""
    from lib import teamcaps
    out = teamcaps.run_tests(str(data_dir()))
    failing = [k for k, v in out['results'].items() if not v['ok']]
    if failing or out['problems']:
        raise ValueError('Fix these first: ' + '; '.join(failing + out['problems'])[:280])
    rev = teamcaps.checkpoint(str(data_dir()), summary)
    return {'saved': bool(rev), 'version': rev, 'message': 'Saved. The team uses this from the next message.'}


def platform_request(need, why):
    """Something only the platform can add (a package, a model, a Paseo change). Never install it yourself."""
    from lib import teamcaps
    return teamcaps.platform_request(str(data_dir()), f'{need}: {why}')


def stack_install():
    """Install the stack (stack/pixi.toml, stack/stack.json) inside Idli's install wall. Claude Code asks the person
    first, with a summary Idli writes from the files (a PreToolUse hook), so Claude can't word the consent."""
    # A separate process: a long install never holds this server, and it always runs the platform's current code
    code = ('import json, sys; sys.path.insert(0, sys.argv[1]); from lib import stackwall; '
            'print(json.dumps(stackwall.install(sys.argv[2])))')
    p = subprocess.run([sys.executable, '-I', '-c', code, str(HERE), str(data_dir())], capture_output=True,
                       text=True, timeout=4000)
    try:
        res = json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise ValueError('The install stopped: ' + (p.stderr or '').strip()[-400:]) from None
    blocked = [h['host'] for h in res['hosts'] if not h['allowed']]
    out = {'ok': res['ok'], 'steps': res['steps'], 'size': res['size'],
           'hosts_used': [h['host'] for h in res['hosts'] if h['allowed']]}
    if blocked:
        out['blocked_hosts'] = blocked
        out['note'] = ('These hosts were refused. If one is needed, add it to "hosts" in stack.json; the person sees '
                       'it at the next install.')
    if not res['ok']:
        out['log_tail'] = res.get('log_tail', '')[-1800:]
    return out


def stack_run(command, timeout=600):
    """Run a command in the installed stack, inside the run wall (no internet), from stack/, with samples/ readable.
    Files it writes to $IDLI_OUT come back in extensions/.idli-out/ for you to look at."""
    import shlex
    import shutil
    from lib import stackwall, teamcaps
    ext = teamcaps.ext_dir(str(data_dir()))
    out = ext / '.idli-out'
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir()
    cmd = shlex.split(str(command))
    if not cmd:
        raise ValueError('Give a command, for example: python tools/vad.py ../samples/talk.wav')
    code = ('import json, sys; sys.path.insert(0, sys.argv[1]); from lib import stackwall; '
            'print(json.dumps(stackwall.run(sys.argv[2], json.loads(sys.argv[3]), out_dir=sys.argv[4], '
            'timeout=int(sys.argv[5]), extra_ro=json.loads(sys.argv[6]))))')
    p = subprocess.run([sys.executable, '-I', '-c', code, str(HERE), str(data_dir()), json.dumps(cmd), str(out),
                        str(min(int(timeout), 3600)), json.dumps([str(ext), str(teamcaps.ROOT / 'lib')])],
                       capture_output=True, text=True, timeout=3700)
    try:
        res = json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise ValueError((p.stderr or 'The stack did not run.').strip()[-400:]) from None
    return {'ok': res['ok'], 'seconds': res['seconds'], 'output': res['output'][-3000:],
            'files_in_.idli-out': res['files'][:50], 'model_calls': res['model_calls']}


def capability_menu():
    """What the platform offers on this computer right now (it can change while you work: check before choosing)."""
    from lib import capmenu
    return capmenu.describe()


BUILDER_TOOLS = {
    'capability_menu': (capability_menu, 'The platform\'s capability menu as it is on this computer now (local '
                        'tools, the private model with or without vision). Check it before choosing how to build.',
                        {}, []),
    'team_check': (team_check, 'Run every capability test of this team in Idli\'s sandbox and list what the team can do.',
                   {}, []),
    'team_save': (team_save, 'After team_check passes, save a version with a one-line summary for the person.',
                  {'summary': {'type': 'string'}}, ['summary']),
    'platform_request': (platform_request, 'Record a platform feature request: something the platform must give '
                         '(a login or an action on an account, sending messages, a change to the app).',
                         {'need': {'type': 'string'}, 'why': {'type': 'string'}}, ['need', 'why']),
    'stack_install': (stack_install, 'Install stack/ (pixi.toml packages, stack.json repos and downloads) inside '
                      "Idli's install wall. The person is asked first. Pins everything on the first install.", {}, []),
    'stack_run': (stack_run, 'Run a command in the installed stack inside the run wall (no internet), from stack/. '
                  'samples/ is at ../samples. Files written to $IDLI_OUT come back in .idli-out/.',
                  {'command': {'type': 'string'}, 'timeout': {'type': 'integer'}}, ['command']),
}
if os.environ.get('IDLI_ROLE') == 'builder':
    TOOLS = BUILDER_TOOLS


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
