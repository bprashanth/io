"""Plays a sandbox's left chat for a blind tester, on the real test accounts (87profligate = me, 88profligate = a
lead), read-only and preview only. Nothing is drafted, booked, sent, labelled or changed in Drive.

  python harness.py serve --port 8791 --mapper remote|nine --world leads|insights --data <dir> --log <file.jsonl>

The production way, with the follow-up grammar (narrative/CLI_CHOICES.md, condition 4b):
- idli-remote gets the question and menu masked with production's account masking (privacy.mask_account_text);
  the local 9B gets them as they are (as miniscope.map_local does). Codes in the chosen commands are put back
  (home.rehydrate) before Idli runs them on the real data.
- Output shown to the person is real, as the code wrote it.
- Insights questions no command answers go to Sandbox Claude after a consent turn: spreadsheets as masked copies
  (privacy.suggest + maskcopy.build, "Accept Idli's choices"), PDFs as masked text (docmask), the question masked.
  Claude writes a script; Idli puts real values back into it (maskcopy.rehydrate_script), runs it on the real
  files, shows the real output, and gives Claude the output masked; Claude's explanation is unmasked for the person.
- Every payload that leaves for idli-remote or Claude goes to <data>/wire.jsonl, and is checked against the vault's
  real values (privacy.known_leaks) plus the leads' names and emails.
"""
import argparse
import datetime as dt
import http.server
import io
import json
import os
import re
import shlex
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
COWORK = HERE.parent / '2026-11-06-oss-desktop-independent' / 'cowork'
BENCH = HERE.parent / '2026-11-19-capability-cli-mapping'
sys.path[:0] = [str(COWORK), str(BENCH)]
from lib import google_api as g, routines, privacy, home, maskcopy, docmask  # noqa: E402
import menus  # noqa: E402

ME, LEAD = '87profligate@gmail.com', '88profligate@gmail.com'
IST = ZoneInfo('Asia/Kolkata')
NOTICE = re.compile(r'^(Accepted|Declined|Tentatively accepted|Invitation|Updated invitation|Canceled event|'
                    r'Cancelled event)\b', re.I)
JUDGE_Q = 'did they agree to meet, and did they pick a time?'
JUDGE_A = ['picked', 'agreed', 'other']
NOTHING = '_A preview: nothing was saved to Gmail or your calendar, and nothing was sent._'
PY = str(COWORK / '.venv' / 'bin' / 'python')


def today():
    return dt.datetime.now(IST).date()


def _fmt(t):
    return t.strftime('%a %d %b, %I:%M %p').replace(' 0', ' ') if t else ''


def _when(iso):
    try:
        return dt.datetime.fromisoformat(str(iso).replace('Z', '+00:00')).astimezone(IST)
    except ValueError:
        return None


def _day(s, default=None):
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return default


def _ist(d, end=False):
    return dt.datetime.combine(d + dt.timedelta(days=1) if end else d, dt.time(0), IST)


class World:
    def __init__(self, kind, data):
        self.kind = kind
        self.dd = Path(data).resolve()
        (self.dd / 'drive').mkdir(parents=True, exist_ok=True)
        self.work = self.dd.parent / (self.dd.name + '-claude')  # Claude's folder: masked copies only
        self.work.mkdir(parents=True, exist_ok=True)
        self.wire = self.dd / 'wire.jsonl'
        self.pending = None   # an escalation waiting for the person's yes
        self.ambiguous = None
        self.context = []     # the Drive files and folders the conversation is about (Drive file dicts)
        self.leads = []
        self.sheet = None
        if kind == 'leads':
            s = [f for f in g.drive_files(ME, kind='sheet', name_words='Leads', limit=10) if f['name'] == 'Leads (test)']
            self.sheet = s[0]['id'] if s else None
            self.leads = g.sheet_values(ME, self.sheet) if self.sheet else []
            # The sheet's rows go through account masking once, as they would on their way to Claude, so their
            # people have codes before any question mentions them.
            for r in self.leads:
                privacy.mask_account_text(str(self.dd), f'{r.get("Name", "")} <{r.get("Email", "")}>')

    # ---- masking, the production way ----
    def mask(self, text):
        return privacy.mask_account_text(str(self.dd), str(text))

    def unmask(self, text):
        return home.rehydrate(str(self.dd), str(text))

    def send_log(self, to, payload):
        vault = privacy._session_map(str(self.dd))
        known = privacy.known_leaks(payload, vault)
        extra = [v for r in self.leads for v in (r.get('Name', ''), r.get('Email', ''))
                 if v and re.search(re.escape(v), payload, re.I)]
        rec = {'to': to, 'at': dt.datetime.now(IST).isoformat(timespec='seconds'), 'chars': len(payload),
               'leaks': sorted(set(known + extra)), 'payload': payload}
        with self.wire.open('a') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        return rec['leaks']

    def lead_emails(self):
        return [r['Email'].lower() for r in self.leads if r.get('Email')]

    def name_of(self, addr):
        return next((r.get('Name', '') for r in self.leads if r.get('Email', '').lower() == str(addr).lower()), '')


# ---- the menu ----

def folders_line():
    fs = g.drive_files(ME, kind='folder', limit=40)
    return 'Folders in Drive: ' + '; '.join(f'"{f["name"]}"' for f in fs)


def menu(world):
    t = today()
    if world.kind == 'leads':
        system, text, _ = menus.prompt('4', 'steps')
        text = text.replace('--since 2026-11-05', f'--since {(t - dt.timedelta(days=14)).isoformat()}')
        text = text.replace('  run step N [flags]', '  explain mini | explain step N   what the Mini does, step by step, '
                            'with the exact sheet, columns, dates and rules it uses (questions about how it works)\n'
                            '  run step N [flags]')
    else:
        system, text, _ = menus.prompt('4b', 'fixity')
        text = text.replace(menus.MINIS['fixity']['goal'], 'No Mini is open. This sandbox reads your Drive files.')
        text = text.replace('The Mini: ', '')
        text = text.replace("  files      Drive files:", "  folders    Drive folders: list folders\n  files      Drive files:")
        text = text.replace(menus.DRIVE_FILES, folders_line() + '\nName folders and files by their names, in quotes '
                            '(--where in="NAME", get file "NAME"). Analysis, charts and comparisons across files are '
                            'not a command: answer none.')
        text = re.sub(r'FOLDER_2|FILE_7|FILE_8|FILE_9', lambda m: {'FOLDER_2': '"Reports"', 'FILE_7': '"Budget.xlsx"',
                                                                   'FILE_8': '"Plan.pdf"', 'FILE_9': '"Notes.pdf"'}[
            m.group(0)], text)
        system = system.replace('a saved workflow (a "Mini")', 'their Drive files in a sandbox')
    text = text.replace(menus.TODAY_LINE, f'Today is {t.strftime("%A")} {t.isoformat()}, time zone UTC+05:30.')
    return system, text


def map_question(world, question, mapper):
    system, text = menu(world)
    t0 = time.time()
    if mapper == 'remote':
        from lib import minisql
        masked_q, masked_menu = world.mask(question), world.mask(text)
        payload = masked_menu + '\n\nQuestion: ' + masked_q
        leaks = world.send_log('idli-remote', system + '\n\n' + payload)
        body = {'model': minisql.MODEL, 'temperature': 0, 'max_tokens': 1200,
                'response_format': {'type': 'json_object'},
                'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': payload}]}
        if 'openrouter.ai' in minisql.URL:
            body['provider'] = {'data_collection': 'deny'}
        req = urllib.request.Request(minisql.URL, json.dumps(body).encode(), {
            'Content-Type': 'application/json', 'Authorization': 'Bearer ' + minisql._key(),
            'User-Agent': 'idli-blindtest/1'})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = json.load(r)['choices'][0]['message']['content'] or ''
            out = json.loads(re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip()))
        except Exception as e:  # noqa: BLE001
            out = {'_error': type(e).__name__}
        out = json.loads(world.unmask(json.dumps(out, ensure_ascii=False)))
        return masked_q, out, round(time.time() - t0, 2), leaks
    out = routines.judge(system + '\n\n' + text + '\n\nQuestion: ' + question[:600], menus.G_SCHEMA, timeout=180,
                         max_tokens=400)
    return question, out, round(time.time() - t0, 2), []


# ---- commands ----

def parse(line):
    try:
        toks = shlex.split(str(line))
    except ValueError:
        toks = str(line).split()
    if toks and toks[0] == 'idli':
        toks = toks[1:]
    pos, flags, where = [], {}, {}
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.startswith('--'):
            k, eq, v = t[2:].partition('=')
            if not eq:
                if i + 1 < len(toks) and not toks[i + 1].startswith('--'):
                    v = toks[i + 1]
                    i += 1
                else:
                    v = True
            if k == 'where':
                wk, _, wv = str(v).partition('=')
                where[wk.strip().lower()] = wv.strip().strip('"')
            else:
                flags[k.replace('-', '_')] = v
        else:
            pos.append(t)
        i += 1
    return pos, flags, where


_RAW = {}


def mails(query, limit=10):
    out = []
    for m in g.gmail_list(ME, query, limit=limit):
        if m['id'] not in _RAW:
            _RAW[m['id']] = g.gmail_raw(ME, m['id'])
        out.append(_RAW[m['id']])
    return out


def no_reply_line(world, items):
    got = {r.get('from', '').lower() for r in items}
    missing = [r.get('Name', '') for r in world.leads if r.get('Email', '').lower() not in got]
    return [f'No reply in this time from: {", ".join(missing)}.'] if missing else []


def mail_query(since=None, until=None, frm=None, search=None, leads=None):
    q = []
    if leads:
        q.append('from:(' + ' OR '.join(leads) + ')')
    elif frm:
        q.append(f'from:{frm}')
    if since:
        q.append(f'after:{int(_ist(since).timestamp())}')
    if until:
        q.append(f'before:{int(_ist(until, end=True).timestamp())}')
    if search:
        q.append('{' + ' '.join(str(search).split()) + '}')
    return ' '.join(q) or 'in:inbox'


def mail_lines(items):
    out = []
    for r in items:
        notice = bool(NOTICE.match(r.get('subject', '')))
        first = ' '.join((r.get('new_text') or r.get('text') or '').split())[:140]
        out.append(f'- {_fmt(_when(r.get("date")))}, from {r.get("from")}: **{r.get("subject", "")}**'
                   + (' (a calendar notice)' if notice else '') + (' (already answered)' if r.get('handled') else '')
                   + f'. {first}')
    return out


_HANDLED = []


def handled_label():
    """The Idli/handled label's id, looked up read-only (production's _label_id creates it when missing)."""
    if not _HANDLED:
        ls = g.call(ME, 'GET', g.GMAIL + '/labels').get('labels') or []
        _HANDLED.append(next((x['id'] for x in ls if x.get('name') == g.HANDLED), None))
    return _HANDLED[0]


def replies(world, since=None, until=None, search=None, open_only=False):
    """Mail from leads, calendar notices left out. open_only (the Mini's step 2): only the newest reply per thread,
    and not ones already answered (labelled Idli/handled), as the Mini does."""
    since = since or today() - dt.timedelta(days=14)
    items = mails(mail_query(since, until, search=search, leads=world.lead_emails()), limit=20)
    items = [r for r in items if not NOTICE.match(r.get('subject', ''))]
    lab = handled_label()
    for r in items:
        r['handled'] = bool(lab and lab in (r.get('labels') or []))
    if not open_only:
        return items
    seen, out = set(), []
    for r in items:  # newest first
        if r.get('thread') in seen:
            continue
        seen.add(r.get('thread'))
        if not r['handled']:
            out.append(r)
    return out


def judge_items(items, question, answers):
    out = []
    for r in items:
        text = (r.get('new_text') or r.get('text') or '')[:2000]
        sent = _when(r.get('date'))
        a = routines.judge(f'Email from {r.get("from")}, subject "{r.get("subject")}", sent {sent.strftime("%A %Y-%m-%d") if sent else ""}:'
                           f'\n\n{text}\n\nQuestion: {question}\nAnswer with one of: {", ".join(answers)}. If they '
                           'picked a time, give "time" as YYYY-MM-DDTHH:MM (India time).',
                           {'type': 'object', 'properties': {'answer': {'type': 'string', 'enum': answers},
                                                             'time': {'type': 'string'}}, 'required': ['answer']},
                           timeout=180, max_tokens=200)
        out.append((r, a.get('answer', 'unclear'), a.get('time', '')))
    return out


def free_slots(days=5, minutes=30, count=3):
    now = dt.datetime.now(IST)
    end = now + dt.timedelta(days=int(days) + 7)
    busy = g.calendar_freebusy(ME, now, end)
    out, day, seen = [], now.date() + dt.timedelta(days=1), 0
    while len(out) < int(count) and seen < int(days) + 7:
        if day.weekday() < 5:
            seen += 1
            t = dt.datetime.combine(day, dt.time(10), IST)
            while t + dt.timedelta(minutes=int(minutes)) <= dt.datetime.combine(day, dt.time(17), IST):
                if not any(b0 < t + dt.timedelta(minutes=int(minutes)) and t < b1 for b0, b1 in busy):
                    out.append(t)
                    break
                t += dt.timedelta(minutes=30)
        day += dt.timedelta(days=1)
    return out[:int(count)]


def run_steps(world, n, flags):
    since, until = _day(flags.get('since')), _day(flags.get('until'))
    if n == 1:
        return ['**Step 1: Read the leads sheet**', ''] + [f'- {r.get("Name")}, {r.get("Email")}, {r.get("Status", "")}'
                                                          for r in world.leads]
    reps = replies(world, since, until, flags.get('search'), open_only=True)
    if n == 2:
        s0 = since or today() - dt.timedelta(days=14)
        return ['**Step 2: Find their replies**', f'From {s0.isoformat()} to {(until or today()).isoformat()}; the newest '
                'reply in each thread, not ones already answered.', ''] + (
            mail_lines(reps) or ['No new replies from leads in that time.']) + [''] + no_reply_line(world, reps)
    judged = judge_items(reps, JUDGE_Q + ' If they picked one, give the time as written.', JUDGE_A)
    if n == 3:
        return ['**Step 3: Read each reply**', ''] + ([f'- {r.get("from")}: "{r.get("subject")}": **{a}**'
                                                       + (f' ({t})' if t else '') for r, a, t in judged]
                                                      or ['No replies to read.'])
    out = []
    if n in (4, 7):
        slots = free_slots()
        drafts = []
        for r, a, _ in judged:
            if a == 'agreed':
                first = (world.name_of(r.get('from')) or '').split(' ')[0] or 'there'
                drafts += [f'To {r.get("from")}, re: {r.get("subject")}', '```',
                           f'Hi {first},\n\nThank you for your reply. Here are three times that work for me:\n'
                           + '\n'.join(f'- {_fmt(s)} (30 minutes)' for s in slots) + '\n\nWhich suits you best?', '```']
        out += ['**Step 4: Draft open times for leads who agreed**', 'Would draft (not saved to Gmail):', ''] + (drafts or ['No lead agreed without '
                                                                                        'picking a time.'])
        if n == 4:
            return out
    if n in (5, 7):
        upcoming = g.calendar_events(ME, dt.datetime.now(IST) - dt.timedelta(days=1),
                                     dt.datetime.now(IST) + dt.timedelta(days=30))
        books = []
        for r, a, t in judged:
            if a != 'picked':
                continue
            try:
                when = dt.datetime.fromisoformat(str(t)[:16]).replace(tzinfo=IST)
            except ValueError:
                when = None
            who = world.name_of(r.get('from')) or r.get('from')
            same = [e for e in upcoming if when and _when(e['start']) == when and r.get('from') in (e.get('attendees') or [])]
            if same:
                books.append(f'- {who} picked {_fmt(when)}: already on your calendar at that time ("{same[0]["title"]}"), '
                             'so it would not book again')
            elif when:
                books.append(f'- Would book (not saved): "Meeting with {who}", {_fmt(when)}, 30 minutes, with '
                             f'{r.get("from")} invited')
            else:
                books.append(f'- {who} picked a time, but it could not be read ("{t}"): it would ask you first')
        out += ['', '**Step 5: Book the time for leads who picked one**', ''] + (books or ['No lead picked a time.'])
        if n == 5:
            return out
    counts = {k: sum(a == k for _, a, _ in judged) for k in JUDGE_A}
    return out + ['', '**Step 6: Totals**', '', ', '.join(f'{k}: {v}' for k, v in counts.items())]


KIND = {'application/pdf': 'PDF', 'text/csv': 'CSV', 'application/vnd.google-apps.spreadsheet': 'Google Sheet',
        'application/vnd.google-apps.folder': 'folder', 'application/vnd.google-apps.document': 'Google Doc',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word'}


def kind(f):
    return KIND.get(f.get('mimeType'), f.get('mimeType', '').split('/')[-1])


def find(world, name, folder=False):
    """A Drive file or folder by its name (exact first, then contains)."""
    name = str(name or '').strip().strip('"')
    if not name:
        return None
    words = [w for w in re.findall(r'\w+', name.lower()) if len(w) > 1]
    pool = g.drive_files(ME, kind='folder' if folder else None, name_words=' '.join(words[:4]), limit=100)
    exact = [f for f in pool if f['name'].lower() == name.lower()]
    near = [f for f in pool if name.lower() in f['name'].lower()]
    every = [f for f in pool if all(w in f['name'].lower() for w in words)]
    cands = exact or near or every
    mine = [f for f in cands if any(o.get('emailAddress') == ME for o in f.get('owners') or [])]
    hit = (mine or cands or [None])[0]
    world.ambiguous = len(exact) > 1 and f'{len(exact)} items in Drive are called "{hit["name"]}"; this is the one in ' \
        f'{"your" if hit in mine else "a shared"} Drive.' if hit else None
    if hit:
        world.context = [x for x in world.context if x['id'] != hit['id']] + [hit]
    return hit


def local_copy(world, f):
    """Download a file into the sandbox (real data stays here). Google Sheets come as CSV."""
    ext = '.csv' if f['mimeType'] in ('text/csv', 'application/vnd.google-apps.spreadsheet') else (
        '.pdf' if f['mimeType'] == 'application/pdf' else '.xlsx' if 'spreadsheetml' in f['mimeType'] else '.bin')
    name = re.sub(r'[^\w .()-]+', '_', Path(f['name']).stem)[:80] + ext
    p = world.dd / 'drive' / name
    if not p.is_file():
        p.write_bytes(g.drive_bytes(ME, f['id'], f['mimeType']))
    return p


def pdf_pages(p):
    from pypdf import PdfReader
    rd = PdfReader(str(p))
    return rd, len(rd.pages)


def describe(world, f):
    if f['mimeType'] == 'application/vnd.google-apps.folder':
        fs = g.drive_files(ME, folder=f['id'], limit=100)
        by = {}
        for x in fs:
            by[kind(x)] = by.get(kind(x), 0) + 1
        return [f'**{f["name"]}** (a folder): {len(fs)} files: ' + ', '.join(f'{v} {k}' for k, v in by.items())]
    p = local_copy(world, f)
    if p.suffix == '.pdf':
        rd, n = pdf_pages(p)
        title = (rd.metadata or {}).get('/Title') if rd.metadata else ''
        return [f'**{f["name"]}** (a PDF): {n} pages' + (f', titled "{title}"' if title else '') + '.']
    if p.suffix in ('.csv', '.xlsx'):
        import pandas as pd
        df = pd.read_csv(p, low_memory=False) if p.suffix == '.csv' else pd.read_excel(p)
        cols = [str(c) for c in df.columns]
        return [f'**{f["name"]}** ({kind(f)}): {len(df)} rows, {len(cols)} columns:', ''] + [f'{i}. {c}' for i, c in
                                                                                             enumerate(cols, 1)]
    return [f'**{f["name"]}** ({kind(f)}), changed {_fmt(_when(f["modifiedTime"]))}.']


def get_file(world, f):
    p = local_copy(world, f)
    if p.suffix == '.pdf':
        rd, n = pdf_pages(p)
        text = '\n'.join((rd.pages[i].extract_text() or '') for i in range(min(2, n)))
        return [f'**{f["name"]}**: {n} pages. The first {min(2, n)}:', '', '```', text[:3000], '```']
    if p.suffix in ('.csv', '.xlsx'):
        import pandas as pd
        df = pd.read_csv(p, low_memory=False) if p.suffix == '.csv' else pd.read_excel(p)
        return [f'**{f["name"]}**: {len(df)} rows. The first 5:', '', '```', df.head(5).to_string()[:3000], '```']
    return ['I can show PDFs and spreadsheets here.']


def summarise(world, f, question=None):
    p = local_copy(world, f)
    if p.suffix != '.pdf':
        return describe(world, f) + ['', 'Summaries are for PDFs; for a spreadsheet, ask about its columns or ask for '
                                         'analysis.']
    rd, n = pdf_pages(p)
    text = '\n'.join((rd.pages[i].extract_text() or '') for i in range(min(n, 12)))[:14000]
    if not text.strip():
        return [f'**{f["name"]}** has no text to read (probably a scan).']
    ask = question or 'What is this document about? Give its main points.'
    out = routines.judge(f'Document "{f["name"]}" ({n} pages; the first {min(n, 12)} are below).\n\n{text}\n\n'
                         f'{ask} Answer in 4 to 6 short bullet points, plainly.',
                         {'type': 'object', 'properties': {'points': {'type': 'array', 'items': {'type': 'string'}}},
                          'required': ['points']}, timeout=300, max_tokens=700)
    pts = out.get('points') or []
    return [f'**{f["name"]}** ({n} pages), read here by Idli' + (' (the first 12 pages)' if n > 12 else '') + ':',
            ''] + [f'- {x}' for x in pts] if pts else ['The private model could not summarise it.']


def explain(world, what, n=None):
    t = today()
    s0 = t - dt.timedelta(days=14)
    cols = list(world.leads[0].keys()) if world.leads else []
    steps = [
        f'1. Read the leads sheet: "Leads (test)" in your Drive, columns {", ".join(cols)} ({len(world.leads)} people).',
        f'2. Find their replies: emails from those people from {s0.isoformat()} (two weeks ago) to today, the newest in '
        'each thread, leaving out calendar notices (accepted, declined, invitations) and replies already answered.',
        f'3. Read each reply: the private model on this computer answers "{JUDGE_Q}" with one of: '
        + ', '.join(JUDGE_A) + '.',
        '4. Draft open times for leads who agreed: a reply offering three open 30-minute times on the next working '
        'days, between 10 AM and 5 PM, saved as a Gmail draft for you to send.',
        '5. Book the time for leads who picked one: a 30-minute event on your calendar with them invited, skipped if '
        'one is already there.',
        '6. Totals: how many replies in each group.']
    if n and str(n).isdigit() and 1 <= int(n) <= 6:
        return [steps[int(n) - 1]]
    return ['**Lead replies in steps**', ''] + steps + ['', 'Nothing is drafted, booked or sent until you say "run it".']


def execute(world, line):
    pos, flags, where = parse(line)
    if len(pos) >= 1 and pos[0].lower() == 'explain' and world.kind == 'leads':
        return explain(world, pos[1] if len(pos) > 1 else 'mini', pos[2] if len(pos) > 2 else None)
    if len(pos) < 2:
        return None
    verb, res = pos[0].lower(), pos[1].lower()
    name = ' '.join(pos[2:]) if len(pos) > 2 else None
    since, until = _day(flags.get('since')), _day(flags.get('until'))
    if verb == 'run':
        if res == 'mini':
            return run_steps(world, 7, flags)
        if res == 'step' and name and name.isdigit():
            return run_steps(world, int(name), flags)
        return None
    if res in ('files', 'file', 'folder', 'folders'):
        if verb in ('describe', 'get', 'summarise', 'summarize'):
            f = find(world, name, folder=res.startswith('folder')) or find(world, name)
            if not f:
                return [f'I could not find "{name}" in Drive.']
            if verb == 'describe' or f['mimeType'] == 'application/vnd.google-apps.folder':
                return describe(world, f)
            if verb == 'get':
                return get_file(world, f)
            return summarise(world, f, flags.get('question') if isinstance(flags.get('question'), str) else None)
        folder = None
        if where.get('in'):
            folder = find(world, where['in'], folder=True)
            if not folder:
                return [f'I could not find a folder called "{where["in"]}".']
        fs = g.drive_files(ME, folder=folder['id'] if folder else None,
                           kind='folder' if res.startswith('folder') else where.get('type'),
                           since=_ist(since).isoformat() if since else None,
                           until=_ist(until, end=True).isoformat() if until else None,
                           name_words=flags.get('search') if isinstance(flags.get('search'), str) else None,
                           shared=str(where.get('shared', '')).lower() == 'true', limit=50)
        head = [f'{len(fs)} in "{folder["name"]}":' if folder else f'{len(fs)} found:', ''] if fs else []
        return head + [f'- {f["name"]} ({kind(f)}), changed {_fmt(_when(f["modifiedTime"]))}' for f in fs] or [
            'No files match.']
    if world.kind != 'leads':
        return None
    if res in ('leads', 'lead') or (res in ('rows', 'row') and verb == 'list'):
        return [f'- {r.get("Name")}, {r.get("Email")}, {r.get("Status", "")}' for r in world.leads]
    if verb == 'judge' and res in ('replies', 'mail'):
        items = replies(world, since, until) if res == 'replies' else mails(mail_query(since, until), 10)
        answers = [a.strip() for a in str(flags.get('answers', 'yes,no')).split(',') if a.strip()]
        return [f'- {r.get("from")}: "{r.get("subject")}": **{a}**' for r, a, _ in
                judge_items(items, str(flags.get('question', '')), answers)] or ['Nothing to read.']
    if res in ('replies', 'reply'):
        reps = replies(world, since, until, flags.get('search'))
        return (mail_lines(reps) or ['No replies from leads in that time.']) + [''] + no_reply_line(world, reps)
    if res in ('mail', 'email', 'emails'):
        frm = where.get('from')
        if frm and frm != 'leads' and '@' not in frm:  # a person's name: their address from the leads sheet
            hit = next((r for r in world.leads if frm.lower() in r.get('Name', '').lower()), None)
            frm = hit['Email'] if hit else f'"{frm}"'
        leads = world.lead_emails() if frm == 'leads' else None
        if verb == 'get':
            items = mails(mail_query(since, until, None if leads else frm, flags.get('search'), leads), 1)
            if not items:
                return ['No email like that.']
            r = items[0]
            return [f'From {r.get("from")}, {_fmt(_when(r.get("date")))}: **{r.get("subject")}**'
                    + (' (a calendar notice)' if NOTICE.match(r.get('subject', '')) else ''), '', '```',
                    (r.get('text') or '').strip()[:3000], '```']
        lim = int(flags['limit']) if str(flags.get('limit', '')).isdigit() else 10
        return mail_lines(mails(mail_query(since, until, None if leads else frm, flags.get('search'), leads),
                                min(lim, 20))) or ['No emails match.']
    if res in ('events', 'event', 'meetings'):
        s = since or today()
        u = until or s
        ev = g.calendar_events(ME, _ist(s), _ist(u, end=True))
        if where.get('guest'):
            want = world.lead_emails() if where['guest'] == 'leads' else [where['guest'].lower()]
            ev = [e for e in ev if any(a and a.lower() in want for a in e.get('attendees') or [])]
        return [f'- {_fmt(_when(e["start"]))}: **{e["title"]}**' + (f', with {", ".join(e["attendees"])}' if e.get(
            'attendees') else '') + (' (you declined)' if e.get('declined') else '') for e in ev] or [
            f'No meetings from {s.isoformat()} to {u.isoformat()}.']
    if res in ('freetimes', 'freetime', 'slots'):
        sl = free_slots(int(flags.get('days') or 5), int(flags.get('minutes') or 30), int(flags.get('count') or 3))
        return [f'- {_fmt(t)}' for t in sl] or ['No open times.']
    return None


# ---- escalation to Sandbox Claude (insights) ----

def claude(world, prompt):
    world.send_log('sandbox-claude', prompt)
    r = subprocess.run(['claude', '-p', '--model', 'sonnet', '--tools', '', '--no-session-persistence',
                        '--output-format', 'text', prompt], cwd=str(world.work), capture_output=True, text=True,
                       timeout=600)
    return r.stdout.strip()


def masked_inputs(world, files):
    """Masked copies the production way: spreadsheets with Idli's suggested columns (privacy.suggest, as "Accept
    Idli's choices"), built by maskcopy into Claude's folder; PDFs as masked text (docmask)."""
    parts = []
    for f in files:
        p = local_copy(world, f)
        rel = p.relative_to(world.dd).as_posix()
        if p.suffix in ('.csv', '.xlsx'):
            from lib import filekit as fk
            sheets, _ = fk.raw_sheets(str(p))
            tab = next(iter(sheets))
            rows = privacy.suggest(str(p), tab)
            privacy.set(str(world.dd), rel, mode='mask', review='auto', columns={r['column']: bool(r['mask'])
                                                                                  for r in rows})
    maskcopy.build(str(world.dd), str(world.work))
    for f in files:
        p = local_copy(world, f)
        rel = p.relative_to(world.dd).as_posix()
        if p.suffix in ('.csv', '.xlsx'):
            import pandas as pd
            mp = world.work / rel
            df = pd.read_csv(mp, low_memory=False) if mp.suffix == '.csv' else pd.read_excel(mp)
            parts.append(f'File {rel} ({len(df)} rows; masked copy, codes stand for private values). Columns and the '
                         f'first 8 rows:\n{df.head(8).to_csv(index=False)[:6000]}')
        elif p.suffix == '.pdf':
            text = docmask.pdf_text(str(p))[:8000]
            parts.append(f'PDF "{world.mask(f["name"])}" (masked text, the first part):\n{docmask._mask(str(world.dd), text)}')
    return '\n\n'.join(parts)


def escalate(world, question, files):
    t0 = time.time()
    masked_q = world.mask(question)
    data = masked_inputs(world, files)
    first = claude(world, f"""You are Sandbox Claude in Idli. You only ever see masked data: codes like NAME_003 stand
for private values. Idli runs your Python on the person's real files and shows them the real output.

The person asked (masked): {masked_q}

Their files (paths are relative to the working folder; read them from there):
{data}

Reply with JSON only: {{"plan": "<one or two plain sentences on what you will work out>", "script": "<a Python 3
script using pandas (and pypdf for PDFs) that reads the files at the paths above and prints the answer as short
tables and lines; no charts, no files written, no network>"}}""")
    m = re.search(r'\{.*\}', first, re.S)
    try:
        plan = json.loads(m.group(0)) if m else {}
    except ValueError:
        plan = {}
    script = plan.get('script') or ''
    if not script:
        return {'reply': 'Claude could not write the analysis. Ask again in other words.', 'secs': round(time.time() - t0, 1)}
    vault = privacy.session_vault(str(world.dd))
    real_script, n = maskcopy.rehydrate_script(script, vault)
    sp = world.dd / 'analysis.py'
    sp.write_text(real_script)
    run = subprocess.run([PY, str(sp)], cwd=str(world.dd), capture_output=True, text=True, timeout=180)
    out = (run.stdout or '')[-6000:] or ('Error: ' + (run.stderr or '')[-1500:])
    masked_out = world.mask(out)
    second = claude(world, f"""You are Sandbox Claude. Idli ran your script on the real files. Its output, masked:

{masked_out}

The person asked (masked): {masked_q}
In 3 to 6 plain sentences, tell them what this shows. Keep the codes as they are; Idli shows them the real values.""")
    reply = '\n'.join([f'**Claude worked on masked copies; Idli ran its analysis on your real files.**', '',
                       f'Plan: {world.unmask(plan.get("plan", ""))}', '', 'Result (real values, from your files):', '```',
                       out.strip()[:4000], '```', '', world.unmask(second)])
    return {'reply': reply, 'secs': round(time.time() - t0, 1), 'script_values_put_back': n,
            'script_ok': run.returncode == 0}


# ---- a turn ----

CONSENT = ('No command answers that here. Claude can work on it with your files as masked copies: names and other '
           'private values become codes, and Idli runs its analysis on your real files here.\n\n'
           'Claude would get your question as: "{q}"\nand these files, masked: {files}.\n\nSend it to Claude? Reply yes '
           'or no.')


def answer(world, question, mapper):
    turn = {'question': question, 'mapper': mapper}
    if world.pending and question.strip().lower().rstrip('.!') in ('yes', 'y', 'ok', 'sure', 'go ahead', 'yes please'):
        q, files = world.pending
        world.pending = None
        res = escalate(world, q, files)
        turn.update({'route': 'claude', **{k: v for k, v in res.items() if k != 'reply'}, 'reply': res['reply']})
        return turn
    if world.pending and question.strip().lower().startswith('no'):
        world.pending = None
        turn.update({'route': 'declined', 'reply': 'Nothing was sent. Ask something else.'})
        return turn
    world.pending = None
    masked, out, secs, leaks = map_question(world, question, mapper)
    turn.update({'masked': masked, 'mapped': out, 'map_secs': secs, 'wire_leaks': leaks})
    if isinstance(out, dict) and out.get('none'):
        if world.kind == 'insights':
            readable = lambda x: x['mimeType'] in ('text/csv', 'application/pdf',  # noqa: E731
                                                   'application/vnd.google-apps.spreadsheet') or 'spreadsheetml' in x['mimeType']
            ql = question.lower()
            files = [f for f in world.context if readable(f) and Path(f['name']).stem.lower() in ql]
            if not files:
                folders = [f for f in world.context if f['mimeType'] == 'application/vnd.google-apps.folder']
                if folders:
                    files = [x for x in g.drive_files(ME, folder=folders[-1]['id'], limit=30) if readable(x)]
            if not files:
                files = [f for f in world.context if readable(f)][-3:]
            seen, uniq = set(), []
            for f in files:
                if f['id'] not in seen:
                    seen.add(f['id'])
                    uniq.append(f)
            if not uniq:
                turn.update({'route': 'none', 'reply': 'Which folder or files should Claude look at? Name them.'})
                return turn
            world.pending = (question, uniq[:6])
            turn.update({'route': 'consent', 'reply': CONSENT.format(q=world.mask(question), files=', '.join(
                f['name'] for f in uniq[:6]))})
            return turn
        turn.update({'route': 'none', 'reply': f"This Mini can't answer that: {out['none'].rstrip('.')}. Fork it to "
                     'continue with Claude: Claude gets your question with private values as codes, and can add or '
                     'change a step.'})
        return turn
    if isinstance(out, dict) and isinstance(out.get('run'), list) and out['run']:
        parts = [f'### {out.get("title")}'] if out.get('title') else []
        ran = []
        world.ambiguous = None
        for line in out['run'][:2]:
            try:
                body = execute(world, line)
            except Exception as e:  # noqa: BLE001 - a failed read is shown plainly
                body = [f'Could not read that: {type(e).__name__}: {str(e)[:120]}']
            ran.append(str(line))
            parts += [''] + (body if body is not None else ["I couldn't run that part."])
            if getattr(world, 'ambiguous', None):
                parts += ['', f'_Note: {world.ambiguous}_']
                world.ambiguous = None
        turn.update({'route': 'commands', 'ran': ran,
                     'reply': '\n'.join(parts + ['', NOTHING if world.kind == 'leads' else '_Read here; nothing in '
                                                 'Drive was changed._'])})
        return turn
    turn.update({'route': 'unmapped', 'reply': "I couldn't work out what answers that. Ask it another way."})
    return turn


def opening(world):
    if world.kind == 'insights':
        return ('This sandbox reads your Google Drive files. Ask about your folders and files: what is in a folder, a '
                "spreadsheet's columns, a PDF's pages or a summary. For analysis, Idli can ask Claude, which only sees "
                'masked copies.')
    return ('Opened Mini: Lead replies in steps. It reads a sheet, reads your email, sees your calendar, asks the '
            'private model about what it reads, writes email drafts and books meetings. Every morning: read the leads '
            "sheet, find each lead's replies from the last two weeks, let the private model read each reply, draft "
            'three open 30-minute times for leads who agreed, and book the time for leads who picked one. Six named '
            'steps: 1 Read the leads sheet, 2 Find their replies, 3 Read each reply, 4 Draft open times for leads who '
            'agreed, 5 Book the time for leads who picked one, 6 Totals. Nothing is written until you say "run it".')


def serve(a):
    world = World(a.world, a.data)
    log = Path(a.log)
    log.parent.mkdir(parents=True, exist_ok=True)
    lock = __import__('threading').Lock()

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *x):
            pass

        def do_POST(self):
            n = int(self.headers.get('Content-Length') or 0)
            q = json.loads(self.rfile.read(n) or b'{}').get('q', '')
            t0 = time.time()
            with lock:
                if q.strip().lower() in ('', 'hi', 'hello', 'open', 'start'):
                    turn = {'question': q, 'reply': opening(world), 'route': 'opening'}
                else:
                    try:
                        turn = answer(world, q, a.mapper)
                    except Exception as e:  # noqa: BLE001
                        turn = {'question': q, 'route': 'error', 'reply': f'Something went wrong: {type(e).__name__}.'}
                turn['wall_secs'] = round(time.time() - t0, 2)
                turn['at'] = dt.datetime.now(IST).isoformat(timespec='seconds')
                with log.open('a') as f:
                    f.write(json.dumps(turn, ensure_ascii=False, default=str) + '\n')
            body = turn['reply'].encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(body)

    srv = http.server.ThreadingHTTPServer(('127.0.0.1', a.port), H)
    print(f'serving {a.world} with {a.mapper} on 127.0.0.1:{a.port}', flush=True)
    srv.serve_forever()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('serve')
    s.add_argument('--port', type=int, default=8791)
    s.add_argument('--mapper', default='remote')
    s.add_argument('--world', default='leads')
    s.add_argument('--data', required=True)
    s.add_argument('--log', required=True)
    t = sub.add_parser('ask')
    t.add_argument('--mapper', default='remote')
    t.add_argument('--world', default='leads')
    t.add_argument('--data', required=True)
    t.add_argument('q', nargs='+')
    a = p.parse_args()
    if a.cmd == 'serve':
        serve(a)
    else:
        w = World(a.world, a.data)
        for q in a.q:
            print(json.dumps(answer(w, q, a.mapper), indent=1, ensure_ascii=False, default=str)[:3000])
