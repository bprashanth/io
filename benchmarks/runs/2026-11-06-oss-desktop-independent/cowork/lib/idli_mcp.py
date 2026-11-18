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
    browsers = None
    if teamcaps.profile_roles(cap):
        # A site tool works in the REAL account's Chrome profile, opened by Idli; the Builder never drives it.
        # TODO(real accounts): chromeprofiles.real_profile_for_role refuses until the real-account step is built.
        from lib import chromeprofiles
        browsers = {r: chromeprofiles.open_for_work(chromeprofiles.real_profile_for_role(str(data_dir()), r))
                    for r in teamcaps.profile_roles(cap)}
    res = teamcaps.run_tool(str(data_dir()), cap, [_original(f) for f in (files or [])], instructions,
                            browsers=browsers)
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


def _catalog_install(tools):
    """Catalog tools for this team (lib/toolhome.py), in a separate process like the old installs."""
    code = ('import json, sys; sys.path.insert(0, sys.argv[1]); from lib import toolhome\n'
            'try:\n    out = toolhome.install(sys.argv[2], json.loads(sys.argv[3]))\n'
            'except ValueError as exc:\n    out = {"ok": False, "refused": str(exc)}\n'
            'print(json.dumps(out))')
    p = subprocess.run([sys.executable, '-I', '-c', code, str(HERE), str(data_dir()), json.dumps(tools)],
                       capture_output=True, text=True, timeout=7200)
    try:
        res = json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise ValueError('The install stopped: ' + (p.stderr or '').strip()[-400:]) from None
    if res.get('refused'):
        return {'ok': False, 'refused': res['refused'],
                'next': 'Tell the person plainly why, and offer a smaller tool from the catalog, a platform_request, '
                        'or a catalog_request.'}
    out = {k: res[k] for k in ('ok', 'tools', 'steps', 'size') if k in res}
    if res.get('ok'):
        out['use'] = ('Run your code with stack_run. Model files are at $IDLI_MODEL_<NAME> (and $IDLI_MODEL_PATHS, '
                      'JSON). Call catalog with example=<id> for how to use a tool.')
    else:
        out['log_tail'] = res.get('log_tail', '')[-1800:]
    return out


def stack_install(tools=None):
    """Install tools from Idli's catalog for this team (tools=[ids]); with no tools, reinstall what the team already
    lists (a teammate), or an older hand-made stack. Claude Code asks the person first, with a summary Idli writes
    (a PreToolUse hook), so Claude can't word the consent."""
    from lib import toolhome
    if tools:
        if isinstance(tools, str):
            tools = [tools]
        return _catalog_install([str(t) for t in tools])
    listed = toolhome.catalog_tools(str(data_dir()))
    if listed:
        return _catalog_install(listed)
    if not (data_dir() / 'extensions' / 'stack' / 'pixi.toml').exists():
        raise ValueError('Name the tools to install from the catalog: stack_install(tools=["<id>", ...]).')
    # An older team's hand-made stack (before the catalog): installed as before.
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
    from lib import capmenu, catalog
    return (capmenu.describe() + '\n\nThis computer:\n' + catalog.describe_computer() +
            "\nTools from the internet come only from Idli's vetted catalog: call `catalog` to see what fits here, "
            'and `catalog_request` when nothing does.')


def catalog_tool(example=None):
    """Idli's vetted tools that run on this computer's system, each with whether it fits here (disk, memory, GPU)."""
    from lib import catalog, toolhome
    cat = catalog.load()
    if example:
        return {'tool': example, 'example': catalog.example(example, cat)[:20000]}
    team = toolhome.team_id(data_dir())
    reg = toolhome.installs()
    rows, other = catalog.fitting(cat, registry=reg)
    have = {r['tool'] for r in reg if r['team'] == team}
    for r in rows:
        r['installed_for_this_team'] = r['id'] in have
    res = catalog.resources()
    return {'this_computer': catalog.describe_computer(res).strip(), 'platform': res['platform'], 'tools': rows,
            'only_on_other_systems': other, 'catalog_updated': cat.get('updated'),
            **({'note': 'The catalog server did not answer; this is the last copy Idli saw.'} if cat.get('stale')
               else {}),
            'how': 'Install with stack_install(tools=[ids]). Never install anything that is not here. If nothing '
                   'fits, call catalog_request.'}


def catalog_request(need, why, tools_considered=None):
    """Ask Idli's team to vet a tool the catalog doesn't have. General words only, never the team's data."""
    from lib import catalog, teamcaps, toolhome
    out = catalog.request(need, why, tools_considered or [], toolhome.team_id(data_dir()))
    teamcaps.platform_request(str(data_dir()), f'catalog request: {need}: {why}')
    out['tell_person'] = ("Our team will look for a safe tool for this and add it to Idli's list. Meanwhile, say what "
                          'you can do now.')
    return out


# ---- the Builder's browser: real Chrome profiles signed in to TEST accounts (narrative/BUILDER_JOURNEY.md) ----

def _test_browser(profile):
    """The profile's Chrome with DevTools on, after checking that every Google account in it is a confirmed test
    account of this team. Checked again at every call."""
    from lib import chromectl, chromeprofiles
    chromeprofiles.check_test_profile(str(data_dir()), profile)
    return chromectl.Browser(port=chromeprofiles.open_for_work(profile))


def profiles():
    """Chrome profiles on this computer, and which are confirmed test accounts of this team. Emails are shown only
    for confirmed profiles: for the others, ask the person which email is signed in."""
    from lib import chromeprofiles
    team = chromeprofiles.test_accounts(str(data_dir()))
    rows = []
    for p in chromeprofiles.list_profiles():
        if p['kind'] == 'real':
            continue  # the real account's profile is Idli's alone
        mine = [a for a in team if a['profile'] == p['profile']]
        ok = bool(p['emails']) and all(any(a['email'] == e for a in team) for e in p['emails'])
        row = {'profile': p['profile'], 'label': p['label'], 'signed_in_accounts': len(p['emails']),
               'confirmed_test_account': ok, 'open': p['running']}
        if ok:
            row['emails'] = p['emails']
            row['roles'] = [a['role'] for a in mine]
        elif p['emails']:
            row['next'] = 'Ask the person which email is signed in here, then call test_account_set.'
        else:
            row['next'] = 'Nobody is signed in yet. Ask the person to sign in in this profile\'s window.'
        rows.append(row)
    return {'profiles': rows, 'how': 'Use only confirmed test accounts. Make a new one with profile_new.'}


def profile_new(label):
    from lib import chromeprofiles
    label = ' '.join(str(label or '').split())[:60]
    if not label:
        raise ValueError('Give the profile a short name, such as "Leads test me".')
    slug = chromeprofiles.slug_for(label)
    chromeprofiles.create(slug, label)
    chromeprofiles.open_for_sign_in(slug)
    return {'profile': slug, 'label': label,
            'tell_person': f'A new Chrome window opened for "{label}". Sign in there with a TEST Google account, not '
                           'your real one. If you need a new test account, make it in that window. Then tell me the '
                           'email you signed in with.',
            'next': 'When the person gives the email, call test_account_set with this profile, the email and a role.'}


def test_account_set(profile, email, role):
    """Idli asks the person first (a PreToolUse hook Idli words: desktop/idli-test-account-consent.py)."""
    from lib import chromeprofiles
    rows = chromeprofiles.set_test_account(str(data_dir()), profile, email, role)
    return {'saved': True, 'test_accounts': [{'role': r['role'], 'email': r['email'], 'profile': r['profile']}
                                             for r in rows]}


def browser_open(profile, url, new_tab=False):
    return _test_browser(profile).open(url, bool(new_tab))


def browser_read(profile, save_as=None):
    page = _test_browser(profile).read()
    if save_as:  # a page from the TEST account, kept as a sample for a site plugin's test (chromectl.Replay)
        from lib import teamcaps
        name = re.sub(r'[^a-z0-9-]+', '-', str(save_as).lower()).strip('-')[:40]
        if not name:
            raise ValueError('save_as is a short name such as gmail-inbox.')
        dest = teamcaps.ensure(str(data_dir())) / 'samples' / 'pages' / (name + '.json')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(page, indent=1))
        page = {**page, 'saved_as': f'samples/pages/{name}.json'}
    return page


def browser_click(profile, ref=None, text=None):
    if not ref and not text:
        raise ValueError('Give a ref from browser_read, or the text on the button or link.')
    return _test_browser(profile).click(ref=ref, text=text)


def browser_type(profile, ref, text, enter=False, clear=False):
    return _test_browser(profile).type(ref, text, enter=bool(enter), clear=bool(clear))


def browser_shot(profile):
    from lib import teamcaps
    folder = teamcaps.ensure(str(data_dir())) / '.idli-shots'
    folder.mkdir(exist_ok=True)
    for old in sorted(folder.glob('*.png'))[:-10]:  # keep the last few
        old.unlink(missing_ok=True)
    import time as _time
    path = folder / (_time.strftime('%Y%m%d-%H%M%S') + '.png')
    _test_browser(profile).shot(path)
    return {'path': str(path), 'next': 'Read this file to see the page.'}


def browser_tabs(profile, use=None):
    b = _test_browser(profile)
    return {'tabs': b.use_tab(int(use)) if use is not None else b.tabs(),
            'note': 'Tab 0 is the one the browser tools act on.'}


def rehearse(capability, instructions=None, files=None):
    """Run one of the team's tools on the TEST accounts (each role it declares gets the confirmed test profile for
    that role) and on samples, so the Builder can check a workflow end to end. Output stays in .idli-out/."""
    import shutil as _shutil
    from lib import chromeprofiles, teamcaps
    caps, problems = teamcaps.manifest(str(data_dir()))
    cap = next((c for c in caps if c['id'] == capability and c['kind'] == 'tool'), None)
    if not cap:
        raise ValueError('That is not a tool in manifest.json. ' + '; '.join(problems)[:200])
    ext = teamcaps.ext_dir(str(data_dir()))
    inputs = []
    for f in files or []:
        p = (ext / str(f)).resolve()
        if not p.is_relative_to(ext / 'samples') or not p.is_file():
            raise ValueError('Rehearse with files in samples/ only.')
        inputs.append(p)
    browsers = {r: chromeprofiles.open_for_work(chromeprofiles.profile_for_role(str(data_dir()), r))
                for r in teamcaps.profile_roles(cap)}
    out = ext / '.idli-out'
    _shutil.rmtree(out, ignore_errors=True)
    try:
        res = teamcaps.run_tool(str(data_dir()), cap, inputs, instructions or {}, timeout=900, browsers=browsers,
                                out=out)
    except ValueError as exc:
        return {'ok': False, 'error': str(exc), 'output': getattr(exc, 'output', '')}
    return {'ok': True, 'result': res['result'], 'files_in_.idli-out': res['files'][:50]}


BROWSER_TOOLS = {
    'profiles': (profiles, 'Chrome profiles on this computer and which are confirmed test accounts of this team.',
                 {}, []),
    'profile_new': (profile_new, 'Make a Chrome profile for one test account and open it for the person to sign in. '
                    'One profile per account.',
                    {'label': {'type': 'string', 'description': 'A short name the person will recognise, such as '
                                                                '"Leads test me"'}}, ['label']),
    'test_account_set': (test_account_set, 'After the person tells you the email signed in to a profile: record it '
                         'as a TEST account of this team with a role (me, lead). Idli asks the person to confirm.',
                         {'profile': {'type': 'string'}, 'email': {'type': 'string'},
                          'role': {'type': 'string', 'description': 'A short lowercase role, such as me or lead'}},
                         ['profile', 'email', 'role']),
    'browser_open': (browser_open, 'Open a web address in a test profile\'s Chrome (tab 0, or a new tab).',
                     {'profile': {'type': 'string'}, 'url': {'type': 'string'}, 'new_tab': {'type': 'boolean'}},
                     ['profile', 'url']),
    'browser_read': (browser_read, 'Read the page in a test profile: visible text, links and controls with refs '
                     '(e12). save_as keeps the page in samples/pages/ for a plugin test.',
                     {'profile': {'type': 'string'}, 'save_as': {'type': 'string'}}, ['profile']),
    'browser_click': (browser_click, 'Click a link or control in a test profile, by ref from browser_read or by '
                      'its text.', {'profile': {'type': 'string'}, 'ref': {'type': 'string'},
                                    'text': {'type': 'string'}}, ['profile']),
    'browser_type': (browser_type, 'Type into a field in a test profile (ref from browser_read). enter presses '
                     'Enter; clear empties the field first.',
                     {'profile': {'type': 'string'}, 'ref': {'type': 'string'}, 'text': {'type': 'string'},
                      'enter': {'type': 'boolean'}, 'clear': {'type': 'boolean'}}, ['profile', 'ref', 'text']),
    'browser_shot': (browser_shot, 'A picture of the page in a test profile. Returns a PNG path to Read.',
                     {'profile': {'type': 'string'}}, ['profile']),
    'browser_tabs': (browser_tabs, 'List a test profile\'s tabs, or switch with use=<n>.',
                     {'profile': {'type': 'string'}, 'use': {'type': 'integer'}}, ['profile']),
    'rehearse': (rehearse, 'Run one of the team\'s tools on the test accounts and samples (each role it declares '
                 'gets that role\'s test profile). For checking a workflow end to end.',
                 {'capability': {'type': 'string'}, 'instructions': {'type': 'object'},
                  'files': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Files in samples/'}},
                 ['capability']),
}


# ---- routines: the workflow Idli runs every day (lib/routines.py, narrative/BUILDER_JOURNEY.md) ----

def routine_check(name):
    from lib import routines
    problems = routines.check(str(data_dir()), name)
    return {'ok': not problems, 'problems': problems,
            'settings_for_test': sorted(routines.config(str(data_dir()), name, 'test'))}


def routine_config_set(name, key, value):
    """A setting of the routine for the TEST accounts (a sheet id, the calendar's secret iCal address). value
    "@ical:<role>" makes Idli read that test account's secret calendar address itself."""
    from lib import chromeprofiles, routines
    value = str(value)
    m = re.fullmatch(r'@ical:([a-z0-9-]{1,20})', value)
    if m:
        from lib import google_web
        row = next((r for r in chromeprofiles.test_accounts(str(data_dir())) if r['role'] == m.group(1)), None)
        if not row:
            raise ValueError(f'No test account has the role {m.group(1)}.')
        value = google_web.calendar_secret_ical(_test_browser(row['profile']), row['email'])
        keys = routines.set_config(str(data_dir()), name, 'test', key, value)
        return {'ok': True, 'set': key, 'note': 'Idli read the secret calendar address and keeps it to itself.',
                'settings_for_test': keys}
    return {'ok': True, 'settings_for_test': routines.set_config(str(data_dir()), name, 'test', key, value)}


def routine_rehearse(name, approve_all=True, dry_run=False):
    """Run the routine on the TEST accounts, with the private model, step by step. approve_all books without asking
    (test accounts only), so the Builder can check the whole flow; the person's Runs page asks in real use."""
    # in a fresh process: the run uses Idli's code as it is now, not as it was when this server started
    code = ('import json, sys; from lib import routines; '
            'print(json.dumps(routines.run(sys.argv[1], sys.argv[2], "test", dry_run=sys.argv[3] == "1", '
            'approve_all=sys.argv[4] == "1"), default=str))')
    res = subprocess.run([sys.executable, '-c', code, str(data_dir()), str(name), '1' if dry_run else '0',
                          '1' if approve_all else '0'], cwd=str(Path(__file__).resolve().parent.parent),
                         capture_output=True, text=True, timeout=1800)
    if res.returncode != 0:
        raise ValueError((res.stderr.strip().splitlines() or ['The rehearsal failed.'])[-1][:400])
    return json.loads(res.stdout.strip().splitlines()[-1])


CONNECT_SAY = ('A Google page opened in the Chrome window for {email}. It may say "Google hasn\'t verified this app": '
               'click Advanced, then Go to Idli (unsafe). It is our own app. Then tick the boxes and click Continue.')


def google_connect(role):
    """Sign a confirmed TEST account in to Idli's Google app (Gmail, Calendar, Sheets through Google's APIs), in its
    own Chrome profile. Waits until the person has said yes on Google's page (up to 10 minutes)."""
    from lib import chromeprofiles, google_api
    row = next((r for r in chromeprofiles.test_accounts(str(data_dir())) if r['role'] == role), None)
    if not row:
        raise ValueError(f'No test account has the role {role}. Confirm one with test_account_set first.')
    chromeprofiles.check_test_profile(str(data_dir()), row['profile'])
    if google_api.connected(row['email']):
        return {'ok': True, 'email': row['email'], 'note': 'Already connected.'}
    out = google_api.connect(row['email'], lambda url: chromeprofiles.open_for_sign_in(row['profile'], url))
    out['told_the_person'] = CONNECT_SAY.format(email=row['email'])
    return out


ROUTINE_TOOLS = {
    'google_connect': (google_connect, 'Connect a confirmed TEST account to Idli\'s Google app, so routines can use '
                       'Gmail, Calendar and Sheets through Google\'s APIs. BEFORE calling, tell the person: ' +
                       CONNECT_SAY.format(email='<the account>') + ' Then call it; it waits for them.',
                       {'role': {'type': 'string', 'description': 'The test account\'s role, such as me or lead'}},
                       ['role']),
    'routine_check': (routine_check, 'Check routines/<name>.json: the steps, the 9B judge (with "unclear"), the '
                      'scripts, and which test settings are set.', {'name': {'type': 'string'}}, ['name']),
    'routine_config_set': (routine_config_set, 'Set a routine setting for the TEST accounts, used as {config.<key>} '
                           'in the routine (for example leads_sheet). value "@ical:me" reads that test account\'s '
                           'secret calendar address for you.',
                           {'name': {'type': 'string'}, 'key': {'type': 'string'}, 'value': {'type': 'string'}},
                           ['name', 'key', 'value']),
    'routine_rehearse': (routine_rehearse, 'Run a routine on the TEST accounts, as Idli will run it every day: each '
                         'step\'s result, the private model\'s answers, the drafts and bookings it made. Run it '
                         'again to check nothing is done twice.',
                         {'name': {'type': 'string'}, 'approve_all': {'type': 'boolean'},
                          'dry_run': {'type': 'boolean'}}, ['name']),
}


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
    'stack_install': (stack_install, "Install tools from Idli's vetted catalog for this team (tools: catalog ids). "
                      'Idli checks this computer first and refuses with reasons; then the person is asked. With no '
                      'tools, reinstalls what the team already has.',
                      {'tools': {'type': 'array', 'items': {'type': 'string'},
                                 'description': 'Catalog tool ids, from the catalog tool.'}}, []),
    'catalog': (catalog_tool, "Idli's vetted tools for this computer's system, with whether each fits here (disk, "
                'memory, GPU) and why not. Pass example=<id> for that tool\'s example script.',
                {'example': {'type': 'string', 'description': 'A tool id, to get its example script.'}}, []),
    'catalog_request': (catalog_request, 'When no catalog tool fits a need: ask Idli\'s team to vet one. General '
                        'words only (no names, places or team data).',
                        {'need': {'type': 'string', 'description': 'What kind of tool, e.g. "speech to text for '
                                                                   'Marathi voice notes"'},
                         'why': {'type': 'string', 'description': 'What it is for, in general words'},
                         'tools_considered': {'type': 'array', 'items': {'type': 'string'},
                                              'description': 'Catalog ids or tool names you looked at'}},
                        ['need', 'why']),
    'stack_run': (stack_run, 'Run a command in the installed stack inside the run wall (no internet), from stack/. '
                  'samples/ is at ../samples. Files written to $IDLI_OUT come back in .idli-out/.',
                  {'command': {'type': 'string'}, 'timeout': {'type': 'integer'}}, ['command']),
}
BUILDER_TOOLS.update(BROWSER_TOOLS)
BUILDER_TOOLS.update(ROUTINE_TOOLS)
if os.environ.get('IDLI_ROLE') == 'builder':
    TOOLS = BUILDER_TOOLS


# ---- sandboxes (narrative/SANDBOXES.md) ----

def _masked_account(obj, depth=0):
    """Account content for Sandbox Claude: every string masked (lib/privacy.mask_account_text), codes kept."""
    from lib import privacy
    if depth > 5:
        return None
    if isinstance(obj, str):
        return privacy.mask_account_text(str(data_dir()), obj[:4000])
    if isinstance(obj, (int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, dict):
        return {str(k)[:60]: _masked_account(v, depth + 1) for k, v in list(obj.items())[:60]}
    if isinstance(obj, (list, tuple)):
        return [_masked_account(v, depth + 1) for v in list(obj)[:60]]
    return None


PEEK = {'gmail_search': lambda a: blocks_mod().gmail_search(a.get('query', ''), a.get('role'), a.get('limit', 10)),
        'gmail_read': lambda a: blocks_mod().gmail_read(a['id'], a.get('role')),
        'free_times': lambda a: blocks_mod().free_times(a.get('days', 5), a.get('minutes', 30), a.get('count', 3),
                                                        role=a.get('role')),
        'sheet_read': lambda a: blocks_mod().sheet_read(a['sheet'], role=a.get('role'))[:100]}


def blocks_mod():
    from lib import blocks
    return blocks


def account_peek(block, args=None):
    """Read account content through one of this sandbox's read blocks, masked. Never real values."""
    b = blocks_mod()
    if block not in PEEK:
        raise ValueError('account_peek reads only: ' + ', '.join(PEEK))
    need = 'calendar_freebusy' if block == 'free_times' else block
    if need not in b.enabled(data_dir()):
        raise ValueError(f'This sandbox was made without {need}.')
    return {'masked': True, 'result': _masked_account(PEEK[block](args or {}))}


def script_try(script, args=None, preview=True, title=None):
    """Run one of your scripts (in your folder) on the sandbox's real accounts; you get its output masked, and the
    person sees the real output in the chat on the left. In preview (the default) drafts and bookings are only
    collected, never written (lib/blocks.preview). The person is asked first."""
    import tempfile
    import time as _time
    work = Path(os.environ.get('IDLI_CLAUDE_WORK') or '.').resolve()
    p = (work / str(script)).resolve()
    if not p.is_relative_to(work) or p.suffix != '.py' or not p.is_file():
        raise ValueError('Give a .py file in your folder.')
    argv = [sys.executable, '-I', str(p)]
    for k, v in (args or {}).items():
        argv += ['--' + re.sub(r'[^a-z0-9_]', '', str(k).lower()), str(v)]
    env = {k: v for k, v in os.environ.items() if not k.startswith('PASEO_')}
    env.update({'IDLI_SANDBOX': str(data_dir()), 'IDLI_COWORK': str(Path(__file__).resolve().parent.parent)})
    fd, log = tempfile.mkstemp(prefix='idli-preview-', suffix='.jsonl')
    os.close(fd)
    if preview:
        env.update({'IDLI_PREVIEW': '1', 'IDLI_PREVIEW_LOG': log})
    try:
        r = subprocess.run(argv, cwd=str(data_dir()), env=env, capture_output=True, text=True, timeout=300,
                           stdin=subprocess.DEVNULL)
        items = [json.loads(x) for x in Path(log).read_text().splitlines() if x.strip()]
    finally:
        os.unlink(log)
    # The real output goes to the left chat (Idli's side); Claude gets it masked.
    workspace = os.environ.get('IDLI_WORKSPACE')
    shown = False
    name = ' '.join(str(title or f'{p.stem} {_time.strftime("%H:%M:%S")}').split())[:120]
    runs = Path(data_dir()) / '.idli' / 'runs'
    runs.mkdir(parents=True, exist_ok=True)
    home.write(runs / f'{int(_time.time() * 1000)}.json', {'title': name, 'workspace': workspace, 'preview': bool(preview),
               'output': r.stdout[-6000:], 'error': bool(r.returncode), 'items': items[:20]})
    if workspace:
        try:
            home.post_to_left(workspace, 'Run', name)
            shown = True
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    masked_items = _masked_account([{k: v for k, v in i.items()} for i in items[:10]])
    return {'exit': r.returncode, 'output': _masked_account(r.stdout[-4000:]),
            'error': _masked_account(r.stderr[-1500:]) if r.returncode else '',
            'preview': bool(preview), 'would_write': masked_items,
            'shown_left': shown, 'note': ('The person sees the real output in the chat on the left, titled "' + name +
                                          '". Point them there in one short line.') if shown else ''}


def _is_sandbox():
    try:
        return json.loads((data_dir() / 'team.json').read_text()).get('kind') == 'sandbox'
    except (OSError, ValueError):
        return False


if os.environ.get('IDLI_ROLE') not in ('builder', 'outside') and _is_sandbox():
    TOOLS['account_peek'] = (account_peek, "Read this sandbox's accounts through its blocks (gmail_search, gmail_read, "
                             'free_times, sheet_read). You get the content masked: codes stand for names, emails and '
                             'other private values.', {'block': {'type': 'string'}, 'args': {'type': 'object'}},
                             ['block'])
    TOOLS['script_try'] = (script_try, 'Run your script (a .py in your folder that imports lib.blocks) on the real '
                           'accounts and get its output masked; the person sees the real output on the left. '
                           'preview (default true) collects drafts and bookings without writing them. The person '
                           'is asked first.',
                           {'script': {'type': 'string'}, 'args': {'type': 'object'},
                            'preview': {'type': 'boolean'}, 'title': {'type': 'string', 'description':
                                        'A short title for this run, shown on the left'}}, ['script'])


# ---- the Builder outside every sandbox (IDLI_ROLE=outside, ~/idli-insights/builder) ----

def sandbox_blocks():
    from lib import blocks
    return {'blocks': blocks.BLOCKS, 'note': 'A sandbox can use only these. Anything else is a gap: say so plainly '
            'and pass it in gaps (no sandbox is made).'}


def sandbox_create(word, goal, blocks, accounts=None, private=True, outside='ask', gaps=None):
    from lib import sandboxes
    return sandboxes.create(word, goal, blocks, accounts, private, outside, gaps)


def sandbox_connect(email):
    from lib import sandboxes
    return sandboxes.connect(email)


def sandbox_list():
    from lib import sandboxes
    return {'sandboxes': sandboxes.list_all()}


OUTSIDE_TOOLS = {
    'sandbox_blocks': (sandbox_blocks, 'The building blocks a sandbox can have, with what each does.', {}, []),
    'sandbox_create': (sandbox_create, 'Make a sandbox with exactly these blocks and accounts, after the person agreed '
                       'to the plan. With gaps (needs no block covers), no sandbox is made and the gap is noted.',
                       {'word': {'type': 'string', 'description': 'One word for the workflow, e.g. leads'},
                        'goal': {'type': 'string', 'description': 'The workflow in one plain sentence'},
                        'blocks': {'type': 'array', 'items': {'type': 'string'}},
                        'accounts': {'type': 'object', 'description': 'role: email, e.g. {"me": "x@gmail.com"}'},
                        'private': {'type': 'boolean', 'description': 'Data has names, places or phone numbers'},
                        'outside': {'type': 'string', 'enum': ['ask', 'never', 'always']},
                        'gaps': {'type': 'array', 'items': {'type': 'string'}}},
                       ['word', 'goal', 'blocks']),
    'sandbox_connect': (sandbox_connect, "Connect a sandbox account to Google: opens Google's page in the person's "
                        'browser. Tell them: click Advanced, then Go to idli, then Select all and Continue.',
                        {'email': {'type': 'string'}}, ['email']),
    'sandbox_list': (sandbox_list, 'The sandboxes made so far.', {}, []),
}
if os.environ.get('IDLI_ROLE') == 'outside':
    TOOLS = OUTSIDE_TOOLS


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
