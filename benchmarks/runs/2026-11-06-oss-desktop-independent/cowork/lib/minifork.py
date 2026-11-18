"""Fork a saved Mini into Sandbox Claude (owner, 2026-11-18; narrative/UX.md "Minis: ask, activate, fork").

Fork on the Mini's card copies the Mini's scripts into Claude's folder (forks/<id>/, with FORK.md and FORK.json) and
starts Sandbox Claude on the right with the current flow and one question: how do you want to change it? Claude edits
the copy on masked data. Every run happens in Idli (script_try, in preview by default) and the real results show in
the left chat; Claude gets them masked. Saving makes a new Mini (journey.draft_mini sees FORK.json); the original
Mini is never changed.
"""
import datetime as dt
import re
import secrets
from pathlib import Path

from lib import home


def _masked(data_dir, text):
    from lib import privacy
    return privacy.mask_free_text(str(data_dir), str(text))


def fork(data_dir, ident, workspace=None):
    from lib import minitalk, uiswitch
    m = home.read(home.object_path(data_dir, 'minis', ident))
    m['id'] = ident
    src = home.object_path(data_dir, 'minis', ident).parent
    new_id = (re.sub('[^a-z0-9]+', '-', str(m.get('name', 'mini')).lower()).strip('-') or 'mini')[:40] + \
        '-fork-' + secrets.token_hex(2)
    work = home.work_dir(data_dir)
    dest = work / 'forks' / new_id
    dest.mkdir(parents=True)
    scripts = []
    from lib import maskcopy, privacy
    mask = maskcopy._masker(privacy.session_vault(str(data_dir)))  # saved scripts hold real values again: code them
    for q in m.get('questions', []):
        name = Path(q['script']).name
        (dest / name).write_text(mask(home.inside(src, name).read_text()))
        scripts.append({'id': q['id'], 'question': q.get('question'), 'script': f'forks/{new_id}/{name}',
                        'params': q.get('params', {})})
    flow = minitalk.steps_text(m)
    home.write(dest / 'FORK.json', {'from': ident, 'from_name': m.get('name'), 'made': dt.datetime.now().isoformat(
        timespec='seconds'), 'questions': scripts})
    (dest / 'FORK.md').write_text('\n'.join([
        f'# Fork of the Mini "{_masked(data_dir, m.get("name", ""))}"', '',
        'The original Mini stays as it is. This folder is your copy to change.', '',
        '## What it does now', '', _masked(data_dir, flow), '',
        '## Its scripts', '', *[f'- `{s["script"]}`: {_masked(data_dir, s["question"] or "")}' for s in scripts], '',
        '## How to work', '',
        '1. Show the person the current flow in a few numbered steps, then ask: "How do you want to change it?"',
        '2. Explain a step when asked (read the script). Change the script here when they ask for a change.',
        '3. Show results with `script_try` (script: the path above, a short `title`). It runs on the real accounts in '
        'preview: nothing is drafted, booked or sent. The person sees the real results in the chat on the left; you '
        'see them masked. Never work out results yourself.',
        '4. When they are happy, save it with `idli_draft_mini` (code: `forks/' + new_id + '`, title: a new name, '
        'for example the old one with what changed). It becomes a new Mini; the original stays.', '']))
    prompt = ' '.join(f'Fork of the Mini "{_masked(data_dir, m.get("name", ""))}". Your copy is in forks/{new_id}/: '
                      'read FORK.md first, show the person the current flow in a few numbered steps, and ask how they '
                      'want to change it.'.split())
    with home._SEND_LOCK:
        wid = home._drivey_workspace(data_dir, workspace or '')
        tid = home._claude_terminal(data_dir, wid)
        if tid:
            home.type_into(tid, prompt)
        else:
            tid = home._start_claude(wid, prompt)
        home._remember(data_dir, wid, tid)
    shown = uiswitch.show_terminal(wid, tid, 'right')
    return {'fork': new_id, 'terminal': tid, 'focused': bool(shown.get('ok')),
            'message': 'Claude has your copy on the right. The original Mini stays as it is.'}
