"""A sandbox's building blocks (narrative/SANDBOXES.md).

The Builder (an ordinary Claude Code project outside every sandbox) turns a person's request into a list of blocks
from BLOCKS and makes a sandbox with exactly those. Inside the sandbox:
- the left chat (Idli, the private 9B) calls the blocks on the person's connected accounts and sees real content;
- Sandbox Claude (on the right) sees account content only masked (lib/privacy.mask_account_text), and writes
  scripts that call these same functions; Idli runs them (escalation model A, narrative/ESCALATION_MODELS.md);
- a saved Mini's script can import this module too (it finds its sandbox from the folder it runs in).

Every call checks that the block is one the sandbox was made with and that the account is one of its accounts.
"""
import datetime as dt
import json
import os
import re
from pathlib import Path

BLOCKS = {
    'drive_files': 'Read Drive files and answer questions about them with Minis (as in Drivey).',
    'gmail_search': 'Find emails in an account, for example from one sender or with a word in the subject.',
    'gmail_read': 'Read one email (sender, subject, date, text).',
    'gmail_draft': 'Write a reply or a new email as a draft in Gmail. The person presses Send.',
    'calendar_freebusy': 'Find busy and free times in an account\'s calendar.',
    'calendar_book': 'Put a meeting on the calendar and invite guests by email.',
    'sheet_read': 'Read the rows of a Google Sheet.',
    'nine_b': 'Ask the private model a question about real content (did they agree, which time, which topic).',
}
GOOGLE = {'gmail_search', 'gmail_read', 'gmail_draft', 'calendar_freebusy', 'calendar_book', 'sheet_read'}
# The left chat's tool for each block (sites/accounts/tools.py)
# (named apart from sites/google's page-reading tools of the same kind, which Drivey keeps)
LEFT_TOOLS = {'gmail_search': 'mail_search', 'gmail_read': 'mail_read', 'gmail_draft': 'mail_draft',
              'calendar_freebusy': 'free_times', 'calendar_book': 'book_meeting', 'sheet_read': 'sheet_rows'}


class NotInSandbox(ValueError):
    pass


def sandbox_dir(start=None):
    """The sandbox this code runs for: IDLI_SANDBOX, IDLI_DATA or COWORK_DATA_DIR, else the nearest folder above the
    working folder with a team.json that lists blocks."""
    for key in ('IDLI_SANDBOX', 'IDLI_DATA', 'COWORK_DATA_DIR'):
        v = os.environ.get(key)
        if v and (Path(v) / 'team.json').exists():
            return Path(v).resolve()
    p = Path(start or os.getcwd()).resolve()
    for d in [p, *p.parents]:
        if (d / 'team.json').exists():
            return d
    raise NotInSandbox('This runs only inside a sandbox.')


def meta(data_dir=None):
    d = Path(data_dir) if data_dir else sandbox_dir()
    try:
        return json.loads((d / 'team.json').read_text())
    except (OSError, ValueError):
        return {}


def enabled(data_dir=None):
    return [b for b in meta(data_dir).get('blocks') or [] if b in BLOCKS]


def accounts(data_dir=None):
    """{role: email}: the accounts the person gave this sandbox."""
    a = meta(data_dir).get('accounts') or {}
    return {str(k): str(v) for k, v in a.items() if isinstance(v, str) and '@' in v}


def _need(block, data_dir=None):
    if block not in enabled(data_dir):
        raise NotInSandbox(f'This sandbox was made without "{block}". Ask the Builder to add it.')


def account(role=None, data_dir=None):
    """The email for a role (default: "me", else the only account)."""
    a = accounts(data_dir)
    if not a:
        raise NotInSandbox('This sandbox has no accounts. Ask the Builder to add one.')
    if role is None:
        role = 'me' if 'me' in a else next(iter(a))
    if role in a:
        return a[role]
    if role in a.values():  # an email given instead of a role
        return role
    raise NotInSandbox(f'"{role}" is not one of this sandbox\'s accounts ({", ".join(a)}).')


def _when(s):
    t = dt.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    return t if t.tzinfo else t.astimezone()


# ---- the blocks ----

def gmail_search(query, role=None, limit=10, data_dir=None):
    from lib import google_api
    _need('gmail_search', data_dir)
    email = account(role, data_dir)
    out = []
    for m in google_api.gmail_list(email, str(query), limit=int(limit)):
        msg = google_api.gmail_raw(email, m['id'])
        out.append({'id': m['id'], 'from': msg.get('from', ''), 'subject': msg.get('subject', ''),
                    'date': msg.get('date', ''), 'snippet': ' '.join(str(msg.get('new_text', '')).split())[:160]})
    return out


def gmail_read(msg_id, role=None, data_dir=None):
    from lib import google_api
    _need('gmail_read', data_dir)
    m = google_api.gmail_raw(account(role, data_dir), msg_id)
    return {**{k: m.get(k) for k in ('id', 'thread', 'from', 'to', 'subject', 'date', 'message_id')},
            'text': m.get('new_text') or m.get('text', '')}


def gmail_draft(to, subject, body, reply_to=None, role=None, key=None, data_dir=None):
    """A draft in Gmail; with reply_to (a message id) it is a reply in that thread. The same key never makes a second
    draft."""
    from lib import google_api
    _need('gmail_draft', data_dir)
    email = account(role, data_dir)
    thread = in_reply_to = None
    if reply_to:
        m = google_api.gmail_raw(email, reply_to)
        thread, in_reply_to = m.get('thread'), m.get('message_id')
        if not subject:
            subject = m.get('subject', '')
        if subject and not subject.lower().startswith('re:'):
            subject = 'Re: ' + subject
    return google_api.gmail_create_draft(email, to, subject, body, thread_id=thread, in_reply_to=in_reply_to,
                                         key=key)


def calendar_busy(start, end, role=None, data_dir=None):
    from lib import google_api
    _need('calendar_freebusy', data_dir)
    return google_api.calendar_freebusy(account(role, data_dir), _when(start), _when(end))


def free_times(days=5, minutes=30, count=3, start_hour=10, end_hour=17, role=None, after=None, data_dir=None):
    """A few open times on working days (one a day where possible), avoiding busy times."""
    now = _when(after) if after else dt.datetime.now().astimezone()
    end = now + dt.timedelta(days=int(days) + 3)
    busy = calendar_busy(now, end, role, data_dir)
    out, day = [], now.date() + dt.timedelta(days=1)
    while len(out) < int(count) and day <= end.date():
        if day.weekday() < 5:
            t = dt.datetime.combine(day, dt.time(int(start_hour)), now.tzinfo)
            while t + dt.timedelta(minutes=int(minutes)) <= dt.datetime.combine(day, dt.time(int(end_hour)), now.tzinfo):
                e = t + dt.timedelta(minutes=int(minutes))
                if not any(b0 < e and t < b1 for b0, b1 in busy):
                    out.append(t)
                    break
                t += dt.timedelta(minutes=30)
        day += dt.timedelta(days=1)
    return [{'start': t.isoformat(timespec='minutes'), 'label': t.strftime('%a %d %b, %I:%M %p').replace(' 0', ' ')}
            for t in out]


def calendar_book(title, start, minutes, guests, role=None, key=None, details='', data_dir=None):
    """A meeting with guests, invitations sent. The same key never books twice."""
    from lib import google_api
    _need('calendar_book', data_dir)
    guests = [g for g in (guests if isinstance(guests, list) else [guests]) if g]
    key = key or f'{title}|{start}|{",".join(sorted(guests))}'
    return google_api.calendar_insert(account(role, data_dir), title, _when(start), int(minutes), guests,
                                      details=details, key=key)


def sheet_read(sheet, rng='A:ZZ', role=None, data_dir=None):
    from lib import google_api
    _need('sheet_read', data_dir)
    m = re.search(r'/spreadsheets/d/([A-Za-z0-9_-]+)', str(sheet))
    return google_api.sheet_values(account(role, data_dir), m.group(1) if m else str(sheet), rng)


def nine_b(question, text, schema=None, data_dir=None):
    """The private model's answer about real content, as JSON (escalation model A). Unclear answers say so."""
    from lib import routines
    _need('nine_b', data_dir)
    schema = schema or {'type': 'object', 'properties': {'answer': {'type': 'string'},
                                                         'unclear': {'type': 'boolean'}},
                        'required': ['answer', 'unclear']}
    return routines.judge(f'{question}\n\n---\n{str(text)[:6000]}\n---', schema)


# ---- for the Builder ----

def plan(blocks):
    """Split the Builder's list into known blocks and gaps."""
    known = [b for b in dict.fromkeys(blocks or []) if b in BLOCKS]
    return known, [b for b in blocks or [] if b not in BLOCKS]


def describe(data_dir):
    """The sandbox's own section for the left chat's instructions (appended to its CLAUDE.md)."""
    m = meta(data_dir)
    lines = ['', '## This sandbox', '', f'Made for: {m.get("goal") or m.get("name")}.', '',
             'You can use only these blocks:']
    lines += [f'- {b}: {BLOCKS[b]}' for b in enabled(data_dir)]
    acc = accounts(data_dir)
    if acc:
        lines += ['', 'Accounts (role: email):'] + [f'- {r}: {e}' for r, e in acc.items()]
    lines += ['', 'Try one step at a time when the person asks ("read my emails from x", "offer three free times",',
              '"book it"). Say what you did and what you found in one or two short sentences. Drafts stay in Gmail',
              'until the person presses Send. To keep a workflow, say they can ask Claude on the right to save it as',
              'a Mini.']
    return '\n'.join(lines) + '\n'


def claude_guide(data_dir):
    """Sandbox Claude's section (appended to its CLAUDE.md by desktop/claude-masked.sh)."""
    m = meta(data_dir)
    if m.get('kind') != 'sandbox':
        return ''
    lines = ['', '## This is a sandbox', '', f'Made for: {m.get("goal") or m.get("name")}.',
             'Its blocks (nothing else is available here):']
    lines += [f'- {b}: {BLOCKS[b]}' for b in enabled(data_dir)]
    lines += ['', 'Accounts by role: ' + ', '.join(accounts(data_dir)) + '. You never see their emails or content; '
              'codes stand for them.',
              '',
              'How to help the person build a workflow:',
              '- Look at account content with `account_peek` (masked). Never ask the person for real values.',
              '- Write the workflow as a Python script in your folder. Start it with:',
              '  `import os, sys; sys.path.insert(0, os.environ["IDLI_COWORK"]); from lib import blocks`',
              '  then call blocks.gmail_search, gmail_read, gmail_draft, free_times, calendar_book, sheet_read and,',
              '  for any judgement on real content (did they agree, which time, what topic), blocks.nine_b(question,',
              '  text, schema). Never judge with word rules: the private model reads the real text, you never do.',
              '- Give every draft and booking a key (the email id it answers), so a second run never does it twice.',
              '- Try it with `script_try` (the person is asked; you get the output masked). Print short lines.',
              '- When the person is happy, save it as a Mini with `idli_draft_mini`: one question per step or one',
              '  for the whole workflow, its script and no parameters unless needed. The person runs it from the',
              '  left.',
              '- Anything the blocks can\'t do is a gap: say so plainly. The Builder (outside) makes a new sandbox.']
    return '\n'.join(lines) + '\n'

