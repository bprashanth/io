"""Sandboxes (narrative/SANDBOXES.md): made by the Builder, outside, with exactly the blocks a workflow needs.

A sandbox works like Drivey: a sidebar heading whose chats open in two halves, Idli (the private 9B) on the left and
Sandbox Claude (masked) on the right. Its folder sits with the old team folders (~/idli-insights/teams/<slug>), so
the masked-Claude launcher, the privacy proxy, Minis and tools treat it the same way. What makes it a sandbox is in
team.json: "kind": "sandbox", the blocks it may use, and the accounts (role: email) the person gave it.
"""
import json
import os
import re
import secrets
import time

from lib import blocks, teams

COWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADJ = ['wobbly', 'quiet', 'brave', 'sunny', 'clever', 'gentle', 'lucky', 'nimble', 'jolly', 'tidy', 'eager',
       'mellow', 'plucky', 'witty', 'cosy', 'swift', 'calm', 'merry', 'bold', 'keen']
NOUN = ['heron', 'mango', 'otter', 'lotus', 'kite', 'tiger', 'parrot', 'banyan', 'pebble', 'comet', 'falcon',
        'jasmine', 'koel', 'neem', 'peacock', 'river', 'monsoon', 'sparrow', 'turtle', 'lantern']
# The left chat's tools: Drivey's (files, Minis, Claude) and the sandbox's account blocks
BASE_TOOLS = ['drive_fetch', 'privacy_review_open', 'claude_handoff', 'mini_open', 'mini_ask', 'binder_item']
SITES = 'google\nfiles\naccounts\n'


def new_name(word):
    word = re.sub(r'[^a-z]+', '', str(word or '').lower())[:12] or 'work'
    return f'{secrets.choice(ADJ)}-{secrets.choice(NOUN)}-{secrets.token_hex(2)} {word}'


def is_sandbox(folder):
    try:
        return json.load(open(os.path.join(folder, 'team.json'))).get('kind') == 'sandbox'
    except (OSError, ValueError):
        return False


def builder_dir():
    return os.path.join(teams._idli(), 'builder')


def note_gap(gaps, goal):
    """A gap the Builder found: written where our team reads platform requests. No team data, general words only."""
    path = os.path.join(builder_dir(), 'platform-requests.md')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'a') as f:
        f.write(f'- {time.strftime("%Y-%m-%d %H:%M")}: no block for {", ".join(gaps)} (for: {str(goal)[:160]})\n')
    return path


def create(word, goal, block_list, accounts=None, private=True, outside='ask', gaps=None, open_it=True):
    """Make a sandbox with exactly these blocks, or refuse when there is a gap."""
    known, unknown = blocks.plan(block_list)
    gaps = [str(g)[:80] for g in (gaps or [])] + unknown
    if gaps:
        note_gap(gaps, goal)
        return {'ok': False, 'gaps': gaps,
                'message': 'No sandbox was made: Idli has no block for ' + ', '.join(gaps) + '. The request is noted '
                           'for our team.'}
    if not known:
        return {'ok': False, 'error': 'Name at least one block.'}
    accounts = {str(r)[:20]: str(e).strip().lower() for r, e in (accounts or {}).items() if '@' in str(e)}
    if any(b in blocks.GOOGLE for b in known) and not accounts:
        return {'ok': False, 'error': 'These blocks need a Google account. Ask the person which one.'}
    name = new_name(word)
    folder = os.path.join(teams._idli(), 'teams', teams.slug(name.split(' ')[0]))
    os.makedirs(folder, exist_ok=True)
    meta = {'name': name, 'kind': 'sandbox', 'goal': str(goal or '')[:300], 'blocks': known, 'accounts': accounts,
            'private': bool(private), 'outside': teams.outside_choice(outside), 'made': time.strftime('%Y-%m-%d %H:%M')}
    with open(os.path.join(folder, 'team.json'), 'w') as f:
        json.dump(meta, f, indent=2)
    with open(os.path.join(COWORK, 'idli', 'CLAUDE.md')) as src, open(os.path.join(folder, 'CLAUDE.md'), 'w') as dst:
        dst.write(src.read() + blocks.describe(folder))
    tools = BASE_TOOLS + [blocks.LEFT_TOOLS[b] for b in known if b in blocks.LEFT_TOOLS]
    with open(os.path.join(folder, 'cowork.tools'), 'w') as f:
        f.write('\n'.join(tools) + '\n')
    with open(os.path.join(folder, 'cowork.sites'), 'w') as f:
        f.write(SITES)
    teams.set_outside(folder, meta['outside'])
    proj = next((p for p in teams._projects() if teams._same(p.get('path'), folder)), None)
    if not proj:
        teams._paseo('project', 'create', folder, parse=False)
        proj = next((p for p in teams._projects() if teams._same(p.get('path'), folder)), None)
    if not proj:
        return {'ok': False, 'error': 'The sidebar heading did not appear. Try again.'}
    if proj.get('name') != name:
        teams._paseo('project', 'rename', proj['projectId'], name, parse=False)
    from lib import google_api
    missing = [e for e in accounts.values() if not google_api.connected(e)]
    out = {'ok': True, 'name': name, 'folder': folder, 'blocks': known, 'accounts': accounts,
           'connect_first': missing}
    if open_it:
        out['opened'] = bool(teams.open_team(os.path.basename(folder)).get('ok'))
    return out


def connect(email):
    """Google's consent for one account, in the person's own browser (a sandbox's accounts only)."""
    from lib import google_api
    import webbrowser
    if google_api.connected(email):
        return {'ok': True, 'already': True}
    google_api.connect(email, webbrowser.open)
    return {'ok': google_api.connected(email)}


def list_all():
    root = os.path.join(teams._idli(), 'teams')
    out = []
    for d in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        f = os.path.join(root, d)
        if is_sandbox(f):
            m = blocks.meta(f)
            out.append({'id': d, 'name': m.get('name'), 'goal': m.get('goal'), 'blocks': m.get('blocks'),
                        'accounts': list((m.get('accounts') or {}).keys())})
    return out


def remove(sandbox_id):
    """Delete a sandbox: its heading and chats, its tools; the folder goes to the archive (lib/teams.delete_team)."""
    folder = os.path.join(teams._idli(), 'teams', str(sandbox_id))
    if not re.fullmatch(r'[a-z0-9-]{1,40}', str(sandbox_id)) or not is_sandbox(folder):
        return {'ok': False, 'error': 'No such sandbox.'}
    return teams.delete_team(sandbox_id)
