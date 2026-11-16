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
