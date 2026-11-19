"""Questions inside a saved workflow Mini's scope that none of its steps answers directly (owner, 2026-11-18;
narrative/SANDBOXES.md "Routing in a sandbox", narrative/ESCALATION_MODELS.md "The chain").

The person checks a Mini before trusting it: "list my leads", "show me my meetings yesterday", "what would step 2
give?". The 9B never chooses freely. Here a model only MAPS the question to a short fixed menu:
- the Mini's steps (run up to that step, in preview), or the whole Mini in preview;
- the sandbox's read blocks (a sheet the Mini uses, a Gmail search, the meetings in some days, free times).
It answers with one or two menu items and their arguments, or "none". Idli runs them here on the real accounts and
shows the output as it is (written by code, not by a model). Nothing is drafted, booked or sent.

Who maps:
- the outside service (lib/minisql's endpoint), when the sandbox allows it: it gets the question with private values
  as codes and the menu, never account content. "Ask each time" shows the person exactly that first;
- the private 9B, when the person says No or the sandbox was made without the outside service (a quality choice
  the person makes).
"none" ends at: fork this Mini and continue with Claude (lib/minifork.py).
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from lib import home

READS = {  # menu id: (the block it needs, what it does, its arguments)
    'sheet_rows': ('sheet_read', 'the rows of a sheet the Mini uses', 'sheet (one of the sheet codes below)'),
    'mail_search': ('gmail_search', 'emails that match a Gmail search, newest first (date, sender, subject, '
                    'first words)', 'query (Gmail search words, e.g. "from:EMAIL_001 newer_than:7d" or '
                    '"subject:meeting after:2026/11/10"), limit (at most 20), from_sheet (optional, a sheet code: only '
                    'mail from the people listed on that sheet, with calendar notices left out)'),
    'meetings': ('calendar_freebusy', 'the meetings on the calendar between two days (title, time, guests)',
                 'start (YYYY-MM-DD), end (YYYY-MM-DD, the last day included)'),
    'free_times': ('calendar_freebusy', 'open times on the next working days', 'days, minutes, count'),
}
MAP_SYSTEM = """You map a person's question about a saved workflow (a "Mini") to the one or two menu items that
answer it. You never see their data. Private values are codes like EMAIL_002 or NAME_004: copy them exactly.

Answer with JSON only, one of:
{"use": [{"item": "<a menu id>", "args": {<the item's arguments>}, "role": "<an account role>"}],
 "title": "<the question, made specific, as a short heading>"}
{"none": "<one plain sentence: what the Mini and the menu cannot do>"}

Rules:
- Use only menu ids. One item, two at most.
- Prefer a step of the Mini when it is what the question asks about ("who replied", "what would step 2 give").
- Use a read item for a plain look at the account the Mini works on ("my meetings yesterday", "list my leads").
- "whole" only for what the Mini would do overall (what it would draft or book).
- When the question is about the Mini's own people ("lead replies", "did any lead write"), give mail_search a
  from_sheet with the sheet code. Leave it out only when the question is broad ("all my emails today").
- If nothing on the menu answers it (it needs a new step, a change, a write, another account), answer none."""
MAP_SCHEMA = {'type': 'object', 'properties': {
    'use': {'type': 'array', 'items': {'type': 'object', 'properties': {
        'item': {'type': 'string'}, 'args': {'type': 'object'}, 'role': {'type': 'string'}}, 'required': ['item']}},
    'title': {'type': 'string'}, 'none': {'type': 'string'}}}
NOTHING_WRITTEN = 'It ran on this computer. Nothing was drafted, booked or sent.'
CALENDAR_NOTICE = re.compile(r'(?i)^\s*(declined|accepted|tentatively accepted|invitation|updated invitation|'
                             r'canceled event|cancelled event)\b[^:]{0,40}:')


# ---- what the Mini is made of ----

def script_path(data_dir, mini):
    q = (mini.get('questions') or [{}])[0]
    return home.inside(home.object_path(data_dir, 'minis', mini['id']).parent, q['script'])


def source(data_dir, mini):
    try:
        return script_path(data_dir, mini).read_text()
    except (OSError, KeyError, ValueError):
        return ''


def steps(data_dir, mini):
    """[(n, title)]: the Mini's named steps (lib/blocks.run_steps), from mini.json or, for older drafts, the script."""
    got = mini.get('steps')
    if not got and 'run_steps(' in source(data_dir, mini):
        got = list_steps(data_dir, mini)
    return [(i, str(t)) for i, t in enumerate(got or [], 1)]


def list_steps(data_dir, mini, timeout=30):
    try:
        r = subprocess.run([sys.executable, '-I', str(script_path(data_dir, mini)), '--list-steps'],
                           cwd=script_path(data_dir, mini).parent, env=_env(data_dir, mini), capture_output=True,
                           text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        titles = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else []
        return [str(t)[:120] for t in titles if str(t).strip()][:12]
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return []


def sheets(data_dir, mini):
    """The Google Sheets the Mini reads (their ids, from its script)."""
    text = source(data_dir, mini)
    ids = re.findall(r'/spreadsheets/d/([A-Za-z0-9_-]{25,})', text)
    ids += re.findall(r'["\']([A-Za-z0-9_-]{40,46})["\']', text)
    return list(dict.fromkeys(ids))[:4]


def uses(data_dir, mini):
    """What the Mini can see and do, from the blocks its script calls (for its card and the menu)."""
    called = set(re.findall(r'blocks\.(\w+)\(', source(data_dir, mini)))
    words = []
    if called & {'sheet_read'}:
        words.append('reads a sheet')
    if called & {'gmail_search', 'gmail_read'}:
        words.append('reads your email')
    if called & {'meetings', 'calendar_busy', 'free_times'}:
        words.append('sees your calendar')
    if 'nine_b' in called:
        words.append('asks the private model about what it reads')
    if 'gmail_draft' in called:
        words.append('writes email drafts')
    if 'calendar_book' in called:
        words.append('books meetings')
    return words


def outside(data_dir):
    """The sandbox's outside service setting: 'never', 'always' or 'ask'."""
    if os.path.exists(os.path.join(data_dir, 'no-query-service')):
        return 'never'
    if os.path.exists(os.path.join(data_dir, 'query-service-always')):
        return 'always'
    return 'ask'


def menu(data_dir, mini):
    """[(id, line)]: everything the mapping may choose from. Short and fixed."""
    from lib import blocks
    items = [(f'step:{n}', f'Step {n} of the Mini: {t} (runs steps 1 to {n} in preview and shows step {n})')
             for n, t in steps(data_dir, mini)]
    items.append(('whole', 'The whole Mini, in preview: what it finds and what it would draft or book'))
    on = set(blocks.enabled(data_dir))
    for ident, (need, what, args) in READS.items():
        if need in on and (ident != 'sheet_rows' or sheets(data_dir, mini)):
            items.append((ident, f'{what}. Arguments: {args}'))
    return items


def menu_text(data_dir, mini, masked_goal):
    from lib import blocks
    lines = [f'The Mini: {masked_goal}', '', 'Menu:']
    lines += [f'- {i}: {line}' for i, line in menu(data_dir, mini)]
    codes = sheets(data_dir, mini)
    if codes:
        lines += ['', 'Sheet codes: ' + ', '.join(f'SHEET_{k} (sheet {k} the Mini reads)' for k in
                                                range(1, len(codes) + 1))]
    roles = list(blocks.accounts(data_dir))
    if roles:
        lines += ['', 'Account roles (give one as "role"): ' + ', '.join(roles) + '. Default: '
                  + ('me' if 'me' in roles else roles[0]) + '.']
    now = dt.datetime.now().astimezone()
    lines += ['', f'Today is {now.strftime("%A %Y-%m-%d")}, time zone UTC{now.strftime("%z")[:3]}:'
                  f'{now.strftime("%z")[3:]}.']
    return '\n'.join(lines)


# ---- masking the question ----

def masked(data_dir, text):
    from lib import privacy
    return privacy.mask_account_text(str(data_dir), str(text)[:600])


def consent(data_dir, mini, question):
    """Exactly what the outside service would get, for the person's card."""
    q = masked(data_dir, question)
    goal = masked(data_dir, mini.get('goal') or mini.get('name') or '')
    return {'masked_question': q, 'menu': menu_text(data_dir, mini, goal), 'service': _service_name()}


def _service_name():
    from lib import minisql
    return minisql.MODEL.split('/')[0]


# ---- mapping ----

def map_service(data_dir, question_masked, menu_masked, call=None):
    from lib import minisql
    minisql._count_call(data_dir)
    body = {'model': minisql.MODEL, 'temperature': 0, 'max_tokens': 400,
            'response_format': {'type': 'json_object'},
            'messages': [{'role': 'system', 'content': MAP_SYSTEM},
                         {'role': 'user', 'content': menu_masked + '\n\nQuestion: ' + question_masked}]}
    if 'openrouter.ai' in minisql.URL:
        body['provider'] = {'data_collection': 'deny'}
    if call:
        return call(body)
    req = urllib.request.Request(minisql.URL, json.dumps(body).encode(), {
        'Content-Type': 'application/json', 'Authorization': 'Bearer ' + minisql._key(),
        'User-Agent': 'idli-miniscope/1'})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = json.load(r)['choices'][0]['message']['content']
    return json.loads(re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip()))


def map_local(question, menu_real):
    from lib import routines
    return routines.judge(MAP_SYSTEM + '\n\n' + menu_real + '\n\nQuestion: ' + str(question)[:600], MAP_SCHEMA,
                          timeout=120, max_tokens=400)


def checked(choice, data_dir, mini):
    """Keep only menu items, at most two, with arguments of the right shape."""
    allowed = {i for i, _ in menu(data_dir, mini)}
    out = []
    for u in (choice.get('use') or [])[:2] if isinstance(choice, dict) else []:
        if isinstance(u, dict) and u.get('item') in allowed:
            out.append({'item': u['item'], 'args': u.get('args') if isinstance(u.get('args'), dict) else {},
                        'role': str(u.get('role') or '')[:20]})
    return out


# ---- running what was chosen ----

def _env(data_dir, mini, preview_log=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith('PASEO_')}
    env.update({'IDLI_COWORK': str(Path(__file__).resolve().parent.parent), 'IDLI_SANDBOX': str(Path(data_dir))})
    on = mini.get('active') or {}
    if on.get('since'):
        env['IDLI_SINCE'] = str(on['since'])
    if preview_log:
        env.update({'IDLI_PREVIEW': '1', 'IDLI_PREVIEW_LOG': str(preview_log)})
    return env


def run_script(data_dir, mini, step=None, timeout=300):
    """The Mini (or steps 1 to `step`) on the real accounts in preview. Returns (output, [drafts and bookings])."""
    script = script_path(data_dir, mini)
    args = [sys.executable, '-I', str(script)]
    q = mini['questions'][0]
    for key, value in home.params_for(q, {}).items():
        args += ['--' + key, str(value)]
    if step:
        args += ['--step', str(int(step))]
    fd, log = tempfile.mkstemp(prefix='idli-preview-', suffix='.jsonl')
    os.close(fd)
    try:
        r = subprocess.run(args, cwd=script.parent, env=_env(data_dir, mini, log), capture_output=True, text=True,
                           timeout=timeout, stdin=subprocess.DEVNULL)
        if r.returncode:
            raise ValueError('The Mini stopped with an error. Fork it to ask Claude to check it.')
        items = [json.loads(line) for line in Path(log).read_text().splitlines() if line.strip()]
    finally:
        os.unlink(log)
    return r.stdout.strip(), items


def _local(t):
    try:
        d = dt.datetime.fromisoformat(str(t).replace('Z', '+00:00'))
    except ValueError:
        return str(t)
    if len(str(t)) <= 10:  # an all-day event
        return d.strftime('%a %d %b').replace(' 0', ' ') + ', all day'
    d = d.astimezone() if d.tzinfo else d
    return d.strftime('%a %d %b, %I:%M %p').replace(' 0', ' ')


def _day(s, default):
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        return default


def preview_words(text):
    """A Mini's own lines say what it did; in a preview it only would have."""
    text = re.sub(r'(->|:)\s*drafted\b', r'\1 would draft', str(text))
    return re.sub(r'(->|:)\s*booked\b', r'\1 would book', text)


def items_text(items, limit=3):
    lines = []
    drafts = [i for i in items if i.get('kind') == 'draft']
    books = [i for i in items if i.get('kind') == 'booking']
    for d in drafts[:limit]:
        body = '\n'.join('> ' + line if line else '>' for line in str(d.get('body', '')).splitlines())
        lines += ['', f'**Would draft to {d.get("to")}**, "{d.get("subject")}"', '', body]
    if len(drafts) > limit:
        lines += ['', f'{len(drafts) - limit} more drafts not shown.']
    for b in books[:5]:
        lines += ['', f'**Would book** "{b.get("title")}" at {_local(b.get("start"))} for {b.get("minutes")} '
                      f'minutes, with {", ".join(b.get("guests") or [])}.']
    return '\n'.join(lines).strip()


def run_item(data_dir, mini, use):
    """(heading, markdown) for one chosen menu item, written by code."""
    from lib import blocks
    item, args, role = use['item'], use['args'], use.get('role') or None
    accounts = blocks.accounts(data_dir)
    role = role if role in accounts else None
    who = role or ('me' if 'me' in accounts else next(iter(accounts), ''))
    if item.startswith('step:') or item == 'whole':
        n = int(item.split(':')[1]) if item.startswith('step:') else None
        out, made = run_script(data_dir, mini, n)
        titles = dict(steps(data_dir, mini))
        head = f'Step {n}: {titles.get(n, "")}' if n else 'The whole Mini'
        text = preview_words(re.sub(r'^== Step \d+: [^\n]*\n?', '', out).strip() if n else out)
        text = '\n'.join(f'- {line}' if line.strip() and not line.startswith(('- ', '== ')) else line
                         for line in text.splitlines()) or 'It found nothing.'
        shown = items_text(made)
        return head, (text + ('\n\n' + shown if shown else '')).strip()
    if item == 'sheet_rows':
        ids = sheets(data_dir, mini)
        code = str(args.get('sheet') or 'SHEET_1')
        k = int(re.sub(r'\D', '', code) or 1)
        sheet = ids[min(max(k, 1), len(ids)) - 1]
        rows = blocks.sheet_read(sheet, role=role, data_dir=data_dir) or []
        if not rows:
            return 'The sheet', 'The sheet has no rows.'
        cols = list(rows[0].keys())[:6]
        cell = lambda v: str(v).replace('|', '/').replace('\n', ' ')[:60]  # noqa: E731
        md = ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)]
        md += ['| ' + ' | '.join(cell(r.get(c, '')) for c in cols) + ' |' for r in rows[:25]]
        more = f'\n\n{len(rows) - 25} more rows not shown.' if len(rows) > 25 else ''
        return f'The sheet ({len(rows)} rows)', '\n'.join(md) + more
    if item == 'mail_search':
        query = str(args.get('query') or '').strip() or 'newer_than:7d'
        limit = max(1, min(int(args.get('limit') or 10), 20))
        people = None
        if args.get('from_sheet'):
            ids = sheets(data_dir, mini)
            k = int(re.sub(r'\D', '', str(args['from_sheet'])) or 1)
            rows = blocks.sheet_read(ids[min(max(k, 1), len(ids)) - 1], role=role, data_dir=data_dir) if ids else []
            people = sorted({e.lower() for r in rows or [] for v in r.values()
                             for e in re.findall(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+', str(v))})
            if not people:
                return 'Email from the sheet', 'The sheet lists no email addresses.'
            query = (re.sub(r'\bfrom:\S+', '', query).strip() + ' from:(' + ' OR '.join(people) + ')').strip()
        found = blocks.gmail_search(query, role=role, limit=limit, data_dir=data_dir) or []
        if people is not None:
            found = [m for m in found if not CALENDAR_NOTICE.match(str(m.get('subject') or ''))]
        head = f'Email ({who}) from the people on the sheet' if people is not None else f'Email ({who}): {query}'
        if not found:
            return head, 'No emails match.'
        def line(m):
            subject = m.get('subject') or '(no subject)'
            note = ' (a calendar notice)' if CALENDAR_NOTICE.match(str(subject)) else ''
            return (f'- {_local(_mail_date(m.get("date")))}, from {m.get("from")}: **{subject}**{note}.'
                    f' {m.get("snippet", "")[:120]}')
        return head, '\n'.join(line(m) for m in found)
    if item == 'meetings':
        today = dt.date.today()
        a = _day(args.get('start'), today)
        b = _day(args.get('end'), a)
        if b < a:
            a, b = b, a
        tz = dt.datetime.now().astimezone().tzinfo
        start = dt.datetime.combine(a, dt.time(0), tz)
        end = dt.datetime.combine(b + dt.timedelta(days=1), dt.time(0), tz)
        got = blocks.meetings(start.isoformat(), end.isoformat(), role=role, data_dir=data_dir) or []
        span = a.strftime('%a %d %b').replace(' 0', ' ') + ('' if a == b else ' to ' +
                                                            b.strftime('%a %d %b').replace(' 0', ' '))
        if not got:
            return f'Meetings ({who}), {span}', 'No meetings.'
        lines = []
        for m in got:
            guests = ', '.join(m.get('attendees') or [])
            end_t = _local(m.get('end')).split(', ')[-1] if m.get('end') and len(str(m.get('end'))) > 10 else ''
            lines.append(f'- {_local(m.get("start"))}' + (f' to {end_t}' if end_t else '') +
                         f': **{m.get("title") or "(no title)"}**' + (f', with {guests}' if guests else '') +
                         (' (you declined)' if m.get('declined') else ''))
        return f'Meetings ({who}), {span}', '\n'.join(lines)
    if item == 'free_times':
        got = blocks.free_times(days=int(args.get('days') or 5), minutes=int(args.get('minutes') or 30),
                                count=max(1, min(int(args.get('count') or 5), 10)), role=role, data_dir=data_dir)
        return f'Free times ({who})', '\n'.join(f'- {t["label"]}' for t in got) or 'No free times found.'
    raise ValueError('Not on the menu.')


def _mail_date(s):
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(str(s)).isoformat()
    except (TypeError, ValueError):
        return str(s)


def _label(use, data_dir, mini):
    if use['item'].startswith('step:'):
        n = int(use['item'].split(':')[1])
        return f'step {n} ({dict(steps(data_dir, mini)).get(n, "")})'
    return {'whole': 'the whole Mini', 'sheet_rows': 'the sheet', 'mail_search': 'an email search',
            'meetings': 'the calendar', 'free_times': 'free times'}.get(use['item'], use['item'])


def answer(data_dir, mini, question, route, call=None):
    """Map the question (route 'service' or 'local'), run what was chosen and show its output."""
    real_menu = menu_text(data_dir, mini, mini.get('goal') or mini.get('name') or '')
    if route == 'service':
        c = consent(data_dir, mini, question)
        choice = map_service(data_dir, c['masked_question'], c['menu'], call)
        who = None  # the person already said yes on the card
    else:
        choice = map_local(question, real_menu)
        who = "Idli's own model picked"
    choice = home.rehydrate(data_dir, choice) if isinstance(choice, dict) else {}
    chosen = checked(choice, data_dir, mini)
    if not chosen:
        why = str(choice.get('none') or '').strip().rstrip('.')
        return {'kind': 'none', 'reply': home.plain(
            "This Mini can't answer that" + (f': {why[0].lower() + why[1:]}' if why else '') + '. ' + FORK_OFFER)}
    parts = []
    for use in chosen:
        head, body = run_item(data_dir, mini, use)
        parts += [f'**{head}**', '', body, '']
    title = str(choice.get('title') or '').strip()
    lines = ([f'### {title}', ''] if title else []) + parts + [
        (f'_{who} {" and ".join(_label(u, data_dir, mini) for u in chosen)}. {NOTHING_WRITTEN}_' if who
         else '_Nothing was drafted, booked or sent._')]
    return {'kind': 'mapped', 'reply': home.plain('\n'.join(lines).strip()), 'used': [u['item'] for u in chosen]}


FORK_OFFER = ('Fork it to continue with Claude: Claude gets your question with private values as codes, and can add '
              'or change a step. The original stays as it is.')
