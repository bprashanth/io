"""Open the team's Builder (narrative/MODEL_TYPES.md): the person's own Claude Code, working on the team's
extensions/ folder, in a terminal on the right of this workspace. Its request is masked first; it never gets files."""
import json
import shlex
import subprocess
from pathlib import Path

from lib import home, teamcaps

LAUNCHER = Path(__file__).resolve().parent.parent / 'desktop' / 'claude-builder.sh'


def check(data_dir, request, kinds=None):
    """What the team is missing for this request (kinds of file it can't read yet)."""
    team = teamcaps.team_name(data_dir)
    wanted = [k for k in (kinds or teamcaps.kinds_in_words(request)) if k in teamcaps.KINDS or k == 'other']
    have = teamcaps.readable(data_dir)
    missing = [k for k in wanted if k not in have]
    return {'team': team, 'missing': missing, 'labels': [teamcaps.label(k) if k != 'other' else 'these files'
                                                          for k in missing]}


def _terminal(wid):
    terms = json.loads(home.cli('terminal', 'ls', '--all', '--json') or '[]')
    return next((t.get('id') or t.get('terminalId') for t in terms
                 if (t.get('workspaceId') or t.get('workspace')) == wid and t.get('name') == 'Builder'), None)


def _start(wid, data_dir, prompt):
    made = json.loads(home.cli('terminal', 'create', '--workspace', wid, '--name', 'Builder', '--json'))
    tid = made.get('id') or made.get('terminalId')
    if not tid:
        raise ValueError('Paseo did not create a terminal')
    cmd = ('IDLI_WORKSPACE=' + shlex.quote(wid) + ' IDLI_DATA=' + shlex.quote(str(Path(data_dir).resolve())) +
           ' exec ' + shlex.quote(str(LAUNCHER)) + ' ' + shlex.quote(prompt))
    home.cli('terminal', 'send-keys', '-l', tid, cmd)
    home.cli('terminal', 'send-keys', '-l', tid, '\r')
    return tid


def prompt_for(data_dir, request, kinds=None, files=None):
    from lib import privacy
    info = check(data_dir, request, kinds)
    masked = ' '.join(privacy.mask_free_text(data_dir, request).split())[:1200]
    text = f"Request from the {info['team']} team: \"{masked}\""
    if info['labels']:
        text += f" {info['team']} can't read {', '.join(info['labels'])} yet"
        if files:
            text += ' (' + ', '.join(Path(str(f)).suffix.lower() or str(f) for f in files[:6]) + ' files)'
        text += '.'
    return text + ' Read the build-team skill first.'


def open_builder(data_dir, request, workspace='', kinds=None, files=None):
    from lib import uiswitch
    if not str(request or '').strip():
        raise ValueError('Say what the team should be able to do.')
    teamcaps.ensure(data_dir)
    prompt = prompt_for(data_dir, request, kinds, files)
    try:
        wid = home._drivey_workspace(data_dir, workspace)
        tid = _terminal(wid)
        if tid:
            home.type_into(tid, prompt)
        else:
            tid = _start(wid, data_dir, prompt)
        shown = uiswitch.show_terminal(wid, tid, 'right')
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError):
        raise ValueError('Idli could not open the Builder in this workspace. Open the team from Start here > Teams '
                         'and try again.') from None
    team = teamcaps.team_name(data_dir)
    return {'terminal': tid, 'focused': bool(shown.get('ok')),
            'reply': f'The Builder has your request on the right. It works on {team} itself, with fake samples. '
                     'Your files are not sent.'}


def setup_prompt(data_dir):
    """The new team's answers, as the Builder's first message (the goal is the person's own words, so masked)."""
    from lib import privacy
    try:
        meta = json.loads((Path(data_dir) / 'team.json').read_text())
    except (OSError, ValueError):
        meta = {}
    name = meta.get('name') or teamcaps.team_name(data_dir)
    goal = ' '.join(privacy.mask_free_text(data_dir, meta.get('goal') or '').split())[:300]
    outside = {'always': 'yes (only masked data is sent)', 'ask': 'ask each time (only masked data is sent)'}.get(
        meta.get('outside'), 'no')
    lines = [f'New team: {name}. Setup answers:',
             f'- Works towards: {goal or "(left blank)"}',
             f'- Data kept in: {meta.get("data") or "not said"}',
             f'- Used by: {meta.get("people") or "not said"}',
             f'- Files have names, places or phone numbers: {meta.get("private") or "not said"}',
             f'- Outside service when a Mini cannot answer: {outside}',
             'Read the setup-team skill, then start the conversation.']
    return ' '.join(lines)


BUILDER_CHAT = 'Builder'


def setup_workspace(data_dir, project):
    """The new team's one chat, titled "Builder", under the team's heading (a Paseo workspace holding only the
    Builder's terminal: no Idli chat and no Analyst). Made once; found again by its title."""
    folder = Path(data_dir).resolve()

    def mine():
        rows = json.loads(home.cli('workspace', 'ls', '--json') or '[]')
        return next((w for w in rows if w.get('name') == BUILDER_CHAT and
                     Path(w.get('cwd') or '.').expanduser().resolve() == folder), None)
    found = mine()
    if found:
        return found['workspaceId']
    out = home.cli('workspace', 'create', '--isolation', 'local', '--project', str(project), '--path', str(folder),
                   '--title', BUILDER_CHAT, '--json')
    try:
        made = json.loads(out or '{}')
        made = made.get('workspace', made) if isinstance(made, dict) else {}
        wid = made.get('workspaceId') or made.get('id')
    except ValueError:
        wid = None
    if not wid:
        wid = (mine() or {}).get('workspaceId')
    if not wid:
        raise ValueError('Paseo did not make the Builder chat')
    return wid


def open_setup(data_dir, workspace=None, project=None):
    """Start the Builder with a new team's setup answers, in one chat titled "Builder" under the team's heading
    (narrative/BUILDER_JOURNEY.md). With a workspace (older callers), the Builder goes on its right as before."""
    from lib import uiswitch
    teamcaps.ensure(data_dir)
    prompt = setup_prompt(data_dir)
    try:
        if workspace:
            tid = _terminal(workspace) or _start(workspace, data_dir, prompt)
            shown = uiswitch.show_terminal(workspace, tid, 'right')
        else:
            workspace = setup_workspace(data_dir, project)
            tid = _terminal(workspace) or _start(workspace, data_dir, prompt)
            shown = uiswitch.show_alone(workspace, tid)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError):
        raise ValueError('Idli could not open the Builder. Open the team and type "open the Builder".') from None
    return {'terminal': tid, 'workspace': workspace, 'focused': bool(shown.get('ok'))}
