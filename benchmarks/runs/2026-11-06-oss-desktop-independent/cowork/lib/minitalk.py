"""Talking to a saved action Mini in the left chat (owner, 2026-11-18; narrative/UX.md "Minis: ask, activate, fork").

A saved Mini is frozen. The person builds trust in it by asking, then turns it on, or forks it to change it:
- explain: "how are leads picked?", "which sheet does it use?". The private 9B answers from the Mini's steps and its
  script (code, not data).
- preview: "show me the draft you'd write", "who agreed as of today?". Idli runs the Mini on the real accounts with
  IDLI_PREVIEW=1: it reads as usual, but drafts and bookings are only collected, never written. The 9B answers from
  that output, and the drafts are shown in full. Nothing is drafted, booked or sent.
- run: "run it now". The Mini runs for real (it never drafts or books twice).
- activate / deactivate: "turn this on for my account". The Mini is bound to an account from today: its runs read
  nothing older (IDLI_SINCE). Running on a schedule is not a block yet; the reply says so.
- change: "only replies from the last 2 days". A saved Mini doesn't change; Fork on its card opens Claude.
All of this runs on this computer and the 9B. Claude is not involved.
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from lib import home

KINDS = ['explain', 'preview', 'run', 'activate', 'deactivate', 'change', 'unclear']
CLASSIFY = {'type': 'object', 'properties': {'kind': {'type': 'string', 'enum': KINDS},
                                             'answer': {'type': 'string'},
                                             'role': {'type': 'string'}},
            'required': ['kind']}
ANSWER = {'type': 'object', 'properties': {'answer': {'type': 'string'}}, 'required': ['answer']}
NOTHING_WRITTEN = '_A preview on your real accounts. Nothing was drafted, booked or sent._'
FORK_HINT = ('A saved Mini stays as it is. To change how it works, press Fork on its card: Claude opens on the right '
             'with this flow and asks what to change. The original stays as it is.')
NO_SCHEDULE = 'Idli runs it when you ask ("run it"). Running it every morning on its own is not a building block yet.'


def _judge(prompt, schema, max_tokens=700):
    from lib import routines
    return routines.judge(prompt, schema, timeout=180, max_tokens=max_tokens)


def is_action(data_dir, mini):
    """A Mini whose scripts work on accounts (lib.blocks), not on files."""
    if mini.get('files'):
        return False
    base = home.object_path(data_dir, 'minis', mini['id']).parent
    for q in mini.get('questions', []):
        try:
            if 'lib import blocks' in (base / q['script']).read_text():
                return True
        except (OSError, KeyError):
            continue
    return False


def source(data_dir, mini, limit=7000):
    base = home.object_path(data_dir, 'minis', mini['id']).parent
    out = []
    for q in mini.get('questions', []):
        try:
            out.append((base / q['script']).read_text()[:limit])
        except (OSError, KeyError):
            pass
    return '\n\n'.join(out)[:limit]


def steps_text(mini):
    steps = mini.get('steps') or []
    if steps:
        return '\n'.join(f'{i}. {s.get("say") if isinstance(s, dict) else s}' for i, s in enumerate(steps, 1))
    return str(mini.get('goal') or '')


def state(mini):
    """How the Mini is turned on, in words for its card and replies."""
    on = mini.get('active') or {}
    if on.get('email'):
        return f'On for {on["email"]} from {_day(on.get("since"))}.'
    return 'Not on for an account yet. It runs on the test accounts.'


def _day(iso):
    try:
        return dt.date.fromisoformat(str(iso)).strftime('%d %b').lstrip('0')
    except ValueError:
        return str(iso)


def _save(data_dir, mini):
    home.write(home.object_path(data_dir, 'minis', mini['id']), mini)


def classify(data_dir, mini, question):
    prompt = (
        'A person is looking at a saved workflow (a "Mini") and typed a message. Decide what they want.\n'
        '- explain: a question about how it works or what it uses (which sheet, how leads are picked, what it '
        'drafts). Write the answer in "answer", in two to four plain sentences, from the steps and code below only.\n'
        '- preview: they want to see results on their data: what it would draft, who replied, who agreed, which '
        'meetings it would book, a list of leads.\n'
        '- run: they ask to run it now for real.\n'
        '- activate: they want it turned on for their account (put the account role, e.g. "me", in "role").\n'
        '- deactivate: they want it turned off.\n'
        '- change: they want it to work differently (a new rule, other leads, a different time window).\n'
        '- unclear: none of these.\n\n'
        f'Mini: {mini.get("name")}\nWhat it does: {mini.get("goal")}\nSteps:\n{steps_text(mini)}\n\n'
        f'Its code:\n---\n{source(data_dir, mini)}\n---\n\nThe person typed: "{str(question)[:500]}"')
    got = _judge(prompt, CLASSIFY)
    kind = got.get('kind') if got.get('kind') in KINDS else 'unclear'
    return {**got, 'kind': kind}


def _script_env(data_dir, mini, preview_log=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith('PASEO_')}
    env.update({'IDLI_COWORK': str(Path(__file__).resolve().parent.parent), 'IDLI_SANDBOX': str(Path(data_dir))})
    on = mini.get('active') or {}
    if on.get('since'):
        env['IDLI_SINCE'] = str(on['since'])
    if preview_log:
        env.update({'IDLI_PREVIEW': '1', 'IDLI_PREVIEW_LOG': str(preview_log)})
    return env


def run_preview(data_dir, mini, timeout=300):
    """Run the Mini's first question on the real accounts in preview. Returns (output, [drafts and bookings])."""
    q = mini['questions'][0]
    script = home.inside(home.object_path(data_dir, 'minis', mini['id']).parent, q['script'])
    args = [sys.executable, '-I', str(script)]
    for key, value in home.params_for(q, {}).items():
        args += ['--' + key, str(value)]
    fd, log = tempfile.mkstemp(prefix='idli-preview-', suffix='.jsonl')
    os.close(fd)
    try:
        r = subprocess.run(args, cwd=script.parent, env=_script_env(data_dir, mini, log), capture_output=True,
                           text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        if r.returncode:
            raise ValueError('The Mini stopped with an error. Fork it to ask Claude to check it.')
        items = [json.loads(line) for line in Path(log).read_text().splitlines() if line.strip()]
    finally:
        os.unlink(log)
    return r.stdout.strip(), items


def _items_text(items, limit=3):
    lines = []
    drafts = [i for i in items if i.get('kind') == 'draft']
    books = [i for i in items if i.get('kind') == 'booking']
    for d in drafts[:limit]:
        body = '\n'.join('> ' + line if line else '>' for line in str(d.get('body', '')).splitlines())
        lines += ['', f'**Draft to {d.get("to")}**, "{d.get("subject")}"', '', body]
    if len(drafts) > limit:
        lines += ['', f'{len(drafts) - limit} more drafts not shown.']
    for b in books[:5]:
        lines += ['', f'**Would book** "{b.get("title")}" at {b.get("start")} for {b.get("minutes")} minutes, '
                      f'with {", ".join(b.get("guests") or [])}.']
    return '\n'.join(lines)


def answer_from(question, output, items):
    prompt = ('Below is what a workflow found on the person\'s accounts in a preview run (nothing was written). '
              'Answer their question from it in two to five plain sentences or a short list. Use names and emails '
              'as they appear. If the output does not say, say so.\n\n'
              f'Question: "{str(question)[:500]}"\n\nOutput:\n---\n{output[-6000:]}\n---\n'
              f'Drafts and bookings it would make: {len(items)}')
    return str(_judge(prompt, ANSWER).get('answer') or '').strip()


def activate(data_dir, mini, role=None):
    from lib import blocks
    accounts = blocks.accounts(data_dir)
    role = role if role in accounts else ('me' if 'me' in accounts else next(iter(accounts), None))
    if not role:
        raise ValueError('This sandbox has no account to turn it on for. Ask the Builder to add one.')
    mini['active'] = {'role': role, 'email': accounts[role], 'since': dt.date.today().isoformat()}
    _save(data_dir, mini)
    return mini


def talk(data_dir, ident, question, workspace=None):
    """The left chat's reply to anything typed while an action Mini is open."""
    mini = home.read(home.object_path(data_dir, 'minis', ident))
    mini['id'] = ident
    got = classify(data_dir, mini, question)
    kind = got['kind']
    if kind == 'explain' and str(got.get('answer') or '').strip():
        return {'kind': kind, 'reply': home.plain(str(got['answer']).strip())}
    if kind in ('preview', 'explain'):
        output, items = run_preview(data_dir, mini)
        text = answer_from(question, output, items) or 'Here is what it found.'
        shown = _items_text(items) if (items and re.search(r'(?i)draft|write|reply|send|book|meeting|invite',
                                                           str(question))) else ''
        return {'kind': 'preview', 'reply': '\n'.join([text, shown, '', NOTHING_WRITTEN]).strip(),
                'items': len(items)}
    if kind == 'run':
        out = home.mini_ask(data_dir, ident, mini['questions'][0]['id'], {}, workspace)
        return {'kind': kind, 'reply': out['reply']}
    if kind == 'activate':
        mini = activate(data_dir, mini, got.get('role'))
        on = mini['active']
        return {'kind': kind, 'reply': f'Turned on for {on["email"]}, starting from today ({_day(on["since"])}). It '
                                       'reads nothing from before today. ' + NO_SCHEDULE}
    if kind == 'deactivate':
        mini.pop('active', None)
        _save(data_dir, mini)
        return {'kind': kind, 'reply': 'Turned off. It runs on the test accounts again when you ask.'}
    if kind == 'change':
        return {'kind': kind, 'reply': FORK_HINT}
    return {'kind': 'unclear', 'reply': 'I can explain how this Mini works, show what it would do on your accounts '
                                        '(nothing is written), run it, or turn it on for your account. To change '
                                        'it, press Fork on its card.'}
