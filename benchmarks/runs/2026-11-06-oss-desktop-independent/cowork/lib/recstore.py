"""A record store per sandbox (narrative/GOALS_v0.md section 4, narrative/EXAMPLES_V0.md).

One DuckDB file per sandbox, one row per natural item (an email, a calendar event, a Drive file, a sheet row).
Connectors fill it from Google's APIs (read only). Definitions are a person's own categories; `judge` has the
private 9B label each row once per definition version, kept in one shared `labels` table. Nothing here writes to
an account.
"""
import base64
import concurrent.futures as cf
import datetime as dt
import email.utils
import io
import json
import os
import re
import time
import urllib.request
from pathlib import Path

import duckdb

TZ = dt.timezone(dt.timedelta(hours=5, minutes=30))  # Asia/Kolkata, the person's zone
BODY_CAP = 8000
TEXT_CAP = 60000

DDL = """
CREATE TABLE IF NOT EXISTS mail (id TEXT PRIMARY KEY, thread_id TEXT, account TEXT, date TIMESTAMP,
  direction TEXT, from_addr TEXT, from_name TEXT, to_addrs TEXT, subject TEXT, snippet TEXT, body_text TEXT,
  gmail_labels TEXT, is_unread BOOLEAN, is_bulk BOOLEAN, is_calendar_notice BOOLEAN, fetched_at TIMESTAMP);
CREATE TABLE IF NOT EXISTS events (id TEXT, account TEXT, start TIMESTAMP, "end" TIMESTAMP, all_day BOOLEAN,
  title TEXT, location TEXT, organizer TEXT, my_response TEXT, guests TEXT, description TEXT,
  fetched_at TIMESTAMP, PRIMARY KEY (id, account));
CREATE TABLE IF NOT EXISTS event_guests (event_id TEXT, account TEXT, email TEXT, response TEXT);
CREATE TABLE IF NOT EXISTS files (id TEXT PRIMARY KEY, account TEXT, name TEXT, kind TEXT, mime TEXT,
  folder TEXT, path TEXT, size BIGINT, modified TIMESTAMP, owner TEXT, shared BOOLEAN, taken_at TEXT,
  width INTEGER, height INTEGER, fetched_at TIMESTAMP);
CREATE TABLE IF NOT EXISTS file_text (file_id TEXT PRIMARY KEY, modified TIMESTAMP, pages INTEGER, text TEXT);
CREATE TABLE IF NOT EXISTS sheets (name TEXT, file_id TEXT PRIMARY KEY, tbl TEXT, columns TEXT, nrows INTEGER,
  fetched_at TIMESTAMP);
CREATE TABLE IF NOT EXISTS definitions (name TEXT, version INTEGER, on_kind TEXT, ask TEXT, answers TEXT,
  examples TEXT, created TIMESTAMP, PRIMARY KEY (name, version));
CREATE TABLE IF NOT EXISTS labels (kind TEXT, record_id TEXT, definition TEXT, version INTEGER, label TEXT,
  detail TEXT, judged_at TIMESTAMP, PRIMARY KEY (kind, record_id, definition, version));
CREATE TABLE IF NOT EXISTS views (name TEXT PRIMARY KEY, on_kind TEXT, sql TEXT, about TEXT);
CREATE TABLE IF NOT EXISTS sync_log (what TEXT, account TEXT, rows INTEGER, seconds DOUBLE, at_time TIMESTAMP);
"""

# what each resource is, for `list`, `explain` and the mapper's menu
RESOURCES = {
    'mail': {'table': 'mail', 'date': 'date', 'kind': 'mail', 'text': ['subject', 'snippet', 'from_name', 'from_addr'],
             'show': ['date', 'from_name', 'from_addr', 'subject', 'direction'],
             'about': 'one row per email (sent and received, about the last 60 days)'},
    'threads': {'table': 'threads', 'date': 'last_date', 'kind': 'mail', 'id': 'thread_id',
                'text': ['subject', 'people'], 'show': ['last_date', 'subject', 'people', 'messages', 'last_from'],
                'about': 'one row per email conversation (made from mail)'},
    'events': {'table': 'events', 'date': 'start', 'kind': 'event', 'text': ['title', 'location', 'guests', 'description'],
               'show': ['start', 'title', 'guests', 'my_response', 'location'],
               'about': 'one row per calendar event (about 60 days back and 60 ahead)'},
    'files': {'table': 'files', 'date': 'modified', 'kind': 'file', 'text': ['name', 'path'],
              'show': ['name', 'kind', 'path', 'modified'], 'about': 'one row per Drive file or folder'},
    'folders': {'table': 'files', 'date': 'modified', 'kind': 'file', 'text': ['name', 'path'], 'filter': "kind = 'folder'",
                'show': ['name', 'path'], 'about': 'Drive folders (files with kind folder)'},
    'photos': {'table': 'files', 'date': 'modified', 'kind': 'file', 'text': ['name', 'path'], 'filter': "kind = 'image'",
               'show': ['name', 'path', 'modified'], 'about': 'Drive images (files with kind image)'},
    'sheets': {'table': 'sheets', 'date': None, 'kind': 'sheet', 'id': 'file_id', 'text': ['name'],
               'show': ['name', 'columns', 'nrows'], 'about': 'one row per spreadsheet that was read; its rows are `rows --sheet NAME`'},
    'labels': {'table': 'labels', 'date': 'judged_at', 'kind': 'label', 'id': 'record_id', 'text': ['label', 'detail'],
               'show': ['kind', 'record_id', 'definition', 'label', 'detail'], 'about': 'what judge decided'},
    'definitions': {'table': 'definitions', 'date': 'created', 'kind': 'definition', 'id': 'name', 'text': ['ask'],
                    'show': ['name', 'version', 'on_kind', 'ask', 'answers'], 'about': 'your own categories'},
}
KIND_TABLE = {'mail': ('mail', 'id'), 'event': ('events', 'id'), 'file': ('files', 'id')}


def now():
    return dt.datetime.now(TZ)


def local(t):
    """Stored times are the person's local time (Asia/Kolkata), without a zone."""
    if t is None:
        return None
    return t.astimezone(TZ).replace(tzinfo=None) if t.tzinfo else t


def connect(sandbox, read_only=False):
    p = Path(sandbox)
    p.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(p / 'store.duckdb'), read_only=read_only)
    if not read_only:
        con.execute(DDL)
        con.execute("""CREATE OR REPLACE VIEW threads AS SELECT thread_id, arg_min(subject, date) AS subject,
          min(date) AS first_date, max(date) AS last_date, count(*) AS messages,
          string_agg(DISTINCT CASE WHEN direction = 'in' THEN coalesce(nullif(from_name, ''), from_addr) END, ', ') AS people,
          arg_max(coalesce(nullif(from_name, ''), from_addr), date) AS last_from, arg_max(direction, date) AS last_direction,
          sum(CASE WHEN is_unread THEN 1 ELSE 0 END) AS unread, bool_and(is_bulk) AS is_bulk,
          bool_and(is_calendar_notice) AS is_calendar_notice FROM mail GROUP BY thread_id""")
    return con


# ---- dates, worked out in code (the 9B's last mapping misses were dates) ----

DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']


def day_range(phrase, today=None):
    """A phrase like 'yesterday', 'last week', 'next monday', '2026-11-12', '7d' as [start, end) dates."""
    today = today or now().date()
    p = str(phrase).strip().lower().replace('_', ' ')
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', p):
        d = dt.date.fromisoformat(p)
        return d, d + dt.timedelta(days=1)
    m = re.fullmatch(r'(?:last |past )?(\d+)\s*(d|days?|w|weeks?|m|months?)', p)
    if m:
        n, u = int(m.group(1)), m.group(2)[0]
        days = n * {'d': 1, 'w': 7, 'm': 30}[u]
        return today - dt.timedelta(days=days - 1), today + dt.timedelta(days=1)
    monday = today - dt.timedelta(days=today.weekday())
    simple = {'today': (today, today + dt.timedelta(days=1)),
              'yesterday': (today - dt.timedelta(days=1), today),
              'tomorrow': (today + dt.timedelta(days=1), today + dt.timedelta(days=2)),
              'this week': (monday, monday + dt.timedelta(days=7)),
              'last week': (monday - dt.timedelta(days=7), monday),
              'next week': (monday + dt.timedelta(days=7), monday + dt.timedelta(days=14)),
              'this month': (today.replace(day=1), (today.replace(day=28) + dt.timedelta(days=4)).replace(day=1)),
              'last month': ((today.replace(day=1) - dt.timedelta(days=1)).replace(day=1), today.replace(day=1))}
    if p in simple:
        return simple[p]
    m = re.fullmatch(r'(last|next|this|since)?\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', p)
    if m:
        wd = DAYS.index(m.group(2))
        if m.group(1) == 'next':
            d = today + dt.timedelta(days=(wd - today.weekday()) % 7 or 7)
        elif m.group(1) == 'this':
            d = monday + dt.timedelta(days=wd)
        else:  # 'last monday', 'since monday', 'monday': the most recent one, today included
            d = today - dt.timedelta(days=(today.weekday() - wd) % 7)
            if m.group(1) == 'last' and d == today:
                d -= dt.timedelta(days=7)
        return d, d + dt.timedelta(days=1)
    raise ValueError(f'Not a date I know: "{phrase}". Try today, yesterday, last week, next monday, 7d or '
                     f'{today.isoformat()}.')


PHRASES = re.compile(r'\b(today|yesterday|tomorrow|(?:this|last|next) (?:week|month)|(?:last|next|this|since) '
                     r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|(?:last|past) \d+ (?:days|weeks)'
                     r'|this morning|tonight)\b', re.I)


def dates_note(question, today=None):
    """The date phrases in a question, worked out: 'yesterday = 2026-11-18'. Empty when there are none."""
    out = []
    for m in PHRASES.finditer(question or ''):
        ph = m.group(1).lower()
        key = {'this morning': 'today', 'tonight': 'today'}.get(ph, ph)
        try:
            a, b = day_range(key, today)
        except ValueError:
            continue
        span = a.isoformat() if (b - a).days == 1 else f'{a.isoformat()} to {(b - dt.timedelta(days=1)).isoformat()}'
        out.append(f'"{ph}" = {span}')
    return '; '.join(dict.fromkeys(out))


# ---- connectors (read only) ----

def _g():
    from lib import google_api
    return google_api


def _log(con, what, account, rows, t0):
    con.execute('INSERT INTO sync_log VALUES (?, ?, ?, ?, ?)', [what, account, rows, time.time() - t0, local(now())])


CAL_NOTICE = re.compile(r'^(accepted|declined|tentatively accepted|invitation|updated invitation|canceled event|'
                        r'cancelled event|new event|invitation from google calendar)\b', re.I)
BULK_FROM = re.compile(r'(no-?reply|noreply|notifications?|mailer-daemon|news(letter)?|updates?|digest|info)@', re.I)


def sync_mail(con, account, days=60, limit=600):
    g, t0 = _g(), time.time()
    ids = [m['id'] for m in g.gmail_list(account, f'newer_than:{int(days)}d -in:chats', limit=limit)]
    have = {r[0] for r in con.execute('SELECT id FROM mail WHERE account = ?', [account]).fetchall()}
    todo = [i for i in ids if i not in have]

    def one(mid):
        r = _retry(lambda: g.call(account, 'GET', f'{g.GMAIL}/messages/{mid}', params={'format': 'full'}))
        h = {x['name'].lower(): x['value'] for x in (r.get('payload') or {}).get('headers') or []}
        labels = r.get('labelIds') or []
        name, addr = email.utils.parseaddr(h.get('from', ''))
        try:
            when = email.utils.parsedate_to_datetime(h.get('date', '')).astimezone(dt.timezone.utc)
        except (TypeError, ValueError):
            when = dt.datetime.fromtimestamp(int(r.get('internalDate', 0)) / 1000, dt.timezone.utc)
        body = _body(r.get('payload') or {})
        subject = h.get('subject', '')
        bulk = bool(h.get('list-unsubscribe') or BULK_FROM.search(addr or '') or
                    set(labels) & {'CATEGORY_PROMOTIONS', 'CATEGORY_SOCIAL', 'CATEGORY_UPDATES', 'CATEGORY_FORUMS'})
        notice = bool(CAL_NOTICE.match(subject) or 'text/calendar' in json.dumps(r.get('payload') or {})[:200000])
        return [mid, r.get('threadId'), account, local(when), 'out' if 'SENT' in labels else 'in', (addr or '').lower(),
                name, h.get('to', ''), subject, r.get('snippet', ''), body[:BODY_CAP], ','.join(labels),
                'UNREAD' in labels, bulk and not notice, notice, local(now())]

    rows = []
    with cf.ThreadPoolExecutor(3) as ex:
        for row in ex.map(one, todo):
            rows.append(row)
            if len(rows) % 50 == 0:  # keep what we have if Google stops us part way
                con.executemany('INSERT OR REPLACE INTO mail VALUES (' + ','.join('?' * 16) + ')', rows[-50:])
    tail = rows[len(rows) - len(rows) % 50:]
    if tail:
        con.executemany('INSERT OR REPLACE INTO mail VALUES (' + ','.join('?' * 16) + ')', tail)
    _log(con, 'mail', account, len(rows), t0)
    return len(rows)


def _retry(fn, tries=6):
    """Google's per-minute quota: wait and try again rather than fail the sync."""
    for i in range(tries):
        try:
            return fn()
        except ValueError as e:
            if ('Quota' in str(e) or ' 429' in str(e) or 'Rate' in str(e)) and i < tries - 1:
                time.sleep(min(60, 5 * 2 ** i))
                continue
            raise


def _body(payload):
    """The plain text of a Gmail message payload (text/plain first, else stripped HTML)."""
    plain, html = [], []

    def walk(p):
        mt = p.get('mimeType', '')
        data = (p.get('body') or {}).get('data')
        if data and mt == 'text/plain':
            plain.append(base64.urlsafe_b64decode(data + '==').decode('utf-8', 'replace'))
        elif data and mt == 'text/html':
            html.append(base64.urlsafe_b64decode(data + '==').decode('utf-8', 'replace'))
        for q in p.get('parts') or []:
            walk(q)
    walk(payload)
    if plain:
        return '\n'.join(plain).strip()
    t = re.sub(r'(?s)<(script|style).*?</\1>', ' ', '\n'.join(html))
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', t)).strip()


def sync_events(con, account, back=60, ahead=60):
    g, t0 = _g(), time.time()
    a, b = now() - dt.timedelta(days=back), now() + dt.timedelta(days=ahead)
    items, page = [], None
    while True:
        r = g.call(account, 'GET', g.CAL + '/calendars/primary/events',
                   params={'timeMin': a.isoformat(), 'timeMax': b.isoformat(), 'singleEvents': 'true',
                           'orderBy': 'startTime', 'maxResults': '250', **({'pageToken': page} if page else {})})
        items += r.get('items') or []
        page = r.get('nextPageToken')
        if not page:
            break
    con.execute('DELETE FROM events WHERE account = ?', [account])
    con.execute('DELETE FROM event_guests WHERE account = ?', [account])
    for e in items:
        if e.get('status') == 'cancelled':
            continue
        s, en = e.get('start') or {}, e.get('end') or {}
        all_day = 'date' in s and 'dateTime' not in s
        start = dt.datetime.fromisoformat(s.get('dateTime') or (s.get('date') + 'T00:00:00+05:30'))
        end = dt.datetime.fromisoformat(en.get('dateTime') or (en.get('date') + 'T00:00:00+05:30'))
        att = e.get('attendees') or []
        me = next((x for x in att if x.get('self')), {})
        guests = [x.get('email', '') for x in att if not x.get('self')]
        con.execute('INSERT OR REPLACE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                    [e['id'], account, local(start), local(end), all_day, e.get('summary', ''), e.get('location', ''),
                     (e.get('organizer') or {}).get('email', ''),
                     me.get('responseStatus', 'organizer' if (e.get('organizer') or {}).get('self') else ''),
                     ', '.join(guests), (e.get('description') or '')[:2000], local(now())])
        for x in att:
            if not x.get('self'):
                con.execute('INSERT INTO event_guests VALUES (?,?,?,?)',
                            [e['id'], account, x.get('email', ''), x.get('responseStatus', '')])
    _log(con, 'events', account, len(items), t0)
    return len(items)


def _kind(mime):
    m = mime or ''
    for k, pat in [('folder', 'folder'), ('sheet', 'spreadsheet'), ('sheet', 'text/csv'), ('pdf', 'pdf'),
                   ('doc', 'document'), ('doc', 'wordprocessing'), ('slides', 'presentation'), ('image', 'image/'),
                   ('video', 'video/'), ('form', 'form')]:
        if pat in m:
            return k
    return 'other'


def sync_files(con, account):
    g, t0 = _g(), time.time()
    files, page = [], None
    while True:
        r = g.call(account, 'GET', g.DRIVE + '/files', params={
            'q': 'trashed=false', 'pageSize': '1000', 'supportsAllDrives': 'true', 'includeItemsFromAllDrives': 'true',
            'fields': 'nextPageToken,files(id,name,mimeType,parents,modifiedTime,size,owners(emailAddress),shared,'
                      'imageMediaMetadata(time,width,height))', **({'pageToken': page} if page else {})})
        files += r.get('files') or []
        page = r.get('nextPageToken')
        if not page:
            break
    by_id = {f['id']: f for f in files}

    def path(f, depth=0):
        ps = f.get('parents') or []
        if not ps or depth > 12:
            return ''
        par = by_id.get(ps[0])
        if not par:
            return 'Shared with me' if f.get('shared') else 'My Drive'
        return (path(par, depth + 1) + '/' if path(par, depth + 1) else '') + par['name']
    con.execute('DELETE FROM files WHERE account = ?', [account])
    rows = []
    for f in files:
        im = f.get('imageMediaMetadata') or {}
        p = path(f)
        rows.append([f['id'], account, f['name'], _kind(f.get('mimeType')), f.get('mimeType', ''),
                     p.split('/')[-1] if p else '', p, int(f.get('size') or 0),
                     local(dt.datetime.fromisoformat(f['modifiedTime'].replace('Z', '+00:00'))),
                     ((f.get('owners') or [{}])[0]).get('emailAddress', ''), bool(f.get('shared')),
                     im.get('time', ''), im.get('width'), im.get('height'), local(now())])
    if rows:
        con.executemany('INSERT OR REPLACE INTO files VALUES (' + ','.join('?' * 15) + ')', rows)
    _log(con, 'files', account, len(rows), t0)
    return len(rows)


def _slug(name, taken):
    s = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')[:40] or 'sheet'
    s = 'sheet_' + s
    base, i = s, 2
    while s in taken:
        s, i = f'{base}_{i}', i + 1
    return s


def sync_sheets(con, account, max_bytes=3_000_000):
    """Every spreadsheet in Drive (Google Sheets, Excel, CSV) as its own table, first tab, columns as text."""
    import pandas as pd
    g, t0 = _g(), time.time()
    rows = con.execute("SELECT id, name, mime, size FROM files WHERE account = ? AND kind = 'sheet'", [account]).fetchall()
    taken = {r[0] for r in con.execute('SELECT tbl FROM sheets').fetchall()}
    n = 0
    for fid, name, mime, size in rows:
        if size and size > max_bytes:
            continue
        try:
            raw = g.drive_bytes(account, fid, mime)
            if 'spreadsheetml' in mime:
                df = pd.read_excel(io.BytesIO(raw), dtype=str)
            else:
                df = pd.read_csv(io.BytesIO(raw), dtype=str)
        except Exception:  # an unreadable file is skipped; it still shows in `files`
            continue
        df = df.dropna(how='all').fillna('')
        df.columns = [re.sub(r'\s+', ' ', str(c)).strip() or f'col{i + 1}' for i, c in enumerate(df.columns)]
        old = con.execute('SELECT tbl FROM sheets WHERE file_id = ?', [fid]).fetchone()
        tbl = old[0] if old else _slug(name, taken)
        taken.add(tbl)
        con.register('df_in', df)
        con.execute(f'CREATE OR REPLACE TABLE "{tbl}" AS SELECT row_number() OVER () AS row_no, * FROM df_in')
        con.unregister('df_in')
        con.execute('INSERT OR REPLACE INTO sheets VALUES (?,?,?,?,?,?)',
                    [name, fid, tbl, json.dumps(list(df.columns)), len(df), local(now())])
        n += 1
    _log(con, 'sheets', account, n, t0)
    return n


def file_text(con, account, fid):
    """A PDF's or document's text, read once and kept (capped)."""
    row = con.execute('SELECT f.modified, t.modified, t.text, f.mime, f.kind FROM files f LEFT JOIN file_text t '
                      'ON t.file_id = f.id WHERE f.id = ?', [fid]).fetchone()
    if not row:
        raise ValueError('No such file in the store. Run `idli sync files` first.')
    fmod, tmod, text, mime, kind = row
    if text is not None and tmod == fmod:
        return text
    raw = _g().drive_bytes(account, fid, mime)
    pages = None
    if kind == 'pdf':
        from pypdf import PdfReader
        rd = PdfReader(io.BytesIO(raw))
        pages = len(rd.pages)
        text = '\n'.join((p.extract_text() or '') for p in rd.pages[:80])
    elif 'wordprocessing' in (mime or ''):
        import docx
        text = '\n'.join(p.text for p in docx.Document(io.BytesIO(raw)).paragraphs)
    else:
        text = raw.decode('utf-8', 'replace')
    text = re.sub(r'[ \t]+', ' ', text)[:TEXT_CAP]
    con.execute('INSERT OR REPLACE INTO file_text VALUES (?,?,?,?)', [fid, fmod, pages, text])
    return text


def image_b64(account, fid, mime, side=512):
    from PIL import Image
    raw = _g().drive_bytes(account, fid, mime)
    im = Image.open(io.BytesIO(raw)).convert('RGB')
    im.thumbnail((side, side))
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=80)
    return base64.b64encode(buf.getvalue()).decode()


# ---- `--where` and `list`: SQL over a resource's fields ----

def columns(con, resource):
    r = RESOURCES[resource]
    return [c[0] for c in con.execute(f'DESCRIBE SELECT * FROM "{r["table"]}"').fetchall()]


LABEL_REF = re.compile(r'label\.([a-z0-9_]+)\s*(!=|=|<>)\s*\'([^\']*)\'', re.I)


def compile_where(con, resource, where):
    """A filter over the resource's fields. label.NAME = 'yes' reads judge's labels; field ~ 'x' means contains."""
    if not where:
        return ''
    if ';' in where or re.search(r'\b(insert|update|delete|drop|create|alter|attach|copy|pragma|install|load)\b', where, re.I):
        raise ValueError('A filter can only compare fields, for example: subject ~ \'visit\' and direction = \'in\'.')
    r = RESOURCES[resource]
    idcol = r.get('id', 'id')
    kind = r['kind']

    def lab(m):
        name, op, val = m.group(1).lower(), m.group(2), m.group(3)
        ver = con.execute('SELECT max(version) FROM definitions WHERE name = ?', [name]).fetchone()[0]
        if ver is None:
            raise ValueError(f'There is no definition called "{name}". `idli list definitions` shows them; '
                             f'`idli define {name} ...` makes one.')
        if resource == 'threads':  # a thread matches when any of its emails does
            sub = (f"SELECT m.thread_id FROM mail m JOIN labels l ON l.record_id = m.id AND l.kind = 'mail' "
                   f"WHERE l.definition = '{name}' AND l.version = {ver} AND l.label = '{val}'")
            return f"thread_id {'NOT ' if op != '=' else ''}IN ({sub})"
        sub = (f"SELECT record_id FROM labels WHERE kind = '{kind}' AND definition = '{name}' AND version = {ver} "
               f"AND label = '{val}'")
        return f"{idcol} {'NOT ' if op != '=' else ''}IN ({sub})"
    w = LABEL_REF.sub(lab, where)
    w = re.sub(r'([A-Za-z_][A-Za-z0-9_]*)\s*~\s*\'([^\']*)\'', lambda m: f"{m.group(1)} ILIKE '%{m.group(2)}%'", w)
    return w


def select(con, resource, where=None, since=None, until=None, on=None, search=None, label=None, folder=None,
           sheet=None, by=None, count=False, fields=None, order=None, limit=50):
    """Build and run the query for `list`. Returns (columns, rows, sql)."""
    if resource == 'rows':
        if not sheet:
            raise ValueError('Say which sheet: `idli list rows --sheet "Leads (test)"`. `idli list sheets` shows them.')
        t = con.execute('SELECT tbl FROM sheets WHERE name ILIKE ? OR tbl = ? ORDER BY fetched_at DESC',
                        [f'%{sheet}%', sheet]).fetchone()
        if not t:
            raise ValueError(f'No sheet matching "{sheet}". `idli list sheets` shows the ones that were read.')
        r = {'table': t[0], 'date': None, 'kind': 'row', 'text': None, 'show': None}
    elif resource in RESOURCES:
        r = RESOURCES[resource]
    else:
        v = con.execute('SELECT on_kind, sql FROM views WHERE name = ?', [resource]).fetchone()
        if not v:
            raise ValueError(f'"{resource}" is not something I can list. Try: ' + ', '.join(list(RESOURCES) + ['rows']) +
                             ', or a view (`idli list views`).')
        r = {'table': None, 'date': None, 'kind': v[0], 'text': None, 'show': None, 'sql': v[1]}
    src = f'({r["sql"]})' if r.get('sql') else f'"{r["table"]}"'
    conds = [r['filter']] if r.get('filter') else []
    if where:
        conds.append(compile_where(con, resource if resource in RESOURCES else 'files', where))
    dcol = r.get('date')
    if on:
        a, b = day_range(on)
        conds.append(f"{dcol} >= TIMESTAMP '{a} 00:00:00' AND {dcol} < TIMESTAMP '{b} 00:00:00'")
    if since:
        a, _ = day_range(since)
        conds.append(f"{dcol} >= TIMESTAMP '{a} 00:00:00'")
    if until:
        a, b = day_range(until)
        conds.append(f"{dcol} < TIMESTAMP '{b} 00:00:00'")
    if (on or since or until) and not dcol:
        raise ValueError(f'{resource} has no date to filter on.')
    if search:
        cols = r.get('text') or [c for c in columns_of(con, src)]
        words = [w for w in re.split(r'\s+', search.strip()) if w]
        conds.append('(' + ' AND '.join('(' + ' OR '.join(f"CAST({c} AS TEXT) ILIKE '%{w.replace(chr(39), '')}%'"
                                                         for c in cols) + ')' for w in words) + ')')
    if folder:
        conds.append(f"(path ILIKE '%{folder.replace(chr(39), '')}%')")
    if label:  # "urgent", "urgent=yes", "urgent = 'yes'", "label.urgent='no'"
        m = re.match(r"\s*(?:label\.)?([A-Za-z0-9_]+)\s*(?:=\s*'?([^']*)'?)?\s*$", label)
        if not m:
            raise ValueError(f'--label takes NAME or NAME=VALUE, for example --label urgent=yes (got "{label}").')
        name, val = m.group(1), (m.group(2) or 'yes')
        conds.append(compile_where(con, resource if resource in RESOURCES else 'files',
                                   f"label.{name.strip()} = '{(val or 'yes').strip()}'"))
    wh = (' WHERE ' + ' AND '.join(f'({c})' for c in conds)) if conds else ''
    if by:
        bys = [b.strip() for b in by.split(',')]
        sql = f'SELECT {", ".join(bys)}, count(*) AS n FROM {src}{wh} GROUP BY ALL ORDER BY n DESC'
    elif count:
        sql = f'SELECT count(*) AS n FROM {src}{wh}'
    else:
        cols = fields or (', '.join(r['show']) if r.get('show') else '*')
        ordr = order or (f'{dcol} DESC' if dcol else '1')
        sql = f'SELECT {cols} FROM {src}{wh} ORDER BY {ordr} LIMIT {int(limit)}'
    cur = con.execute(sql)
    return [d[0] for d in cur.description], cur.fetchall(), sql


def columns_of(con, src):
    return [c[0] for c in con.execute(f'DESCRIBE SELECT * FROM {src}').fetchall()]


def query(con, sql, limit=200):
    s = sql.strip().rstrip(';')
    if not re.match(r'(?is)^\s*(select|with)\b', s) or ';' in s:
        raise ValueError('Only one SELECT is allowed here, for example: '
                         "idli query \"SELECT kind, count(*) FROM files GROUP BY kind\"")
    cur = con.execute(s + ('' if re.search(r'(?i)\blimit\s+\d+\s*$', s) else f' LIMIT {limit}'))
    return [d[0] for d in cur.description], cur.fetchall()


# ---- definitions and judge ----

def define(con, name, on_kind, ask, answers, examples=None):
    name = re.sub(r'[^a-z0-9_]+', '_', name.lower()).strip('_')
    if on_kind not in ('mail', 'event', 'file', 'photo'):
        raise ValueError('A definition is on mail, event, file or photo.')
    answers = [a.strip() for a in (answers if isinstance(answers, list) else str(answers).split(',')) if a.strip()]
    if 'unsure' not in answers:
        answers.append('unsure')
    last = con.execute('SELECT version, on_kind, ask, answers FROM definitions WHERE name = ? ORDER BY version DESC',
                       [name]).fetchone()
    if last and last[1] == on_kind and last[2] == ask and json.loads(last[3]) == answers:
        return name, last[0]
    ver = (last[0] + 1) if last else 1
    con.execute('INSERT INTO definitions VALUES (?,?,?,?,?,?,?)',
                [name, ver, on_kind, ask, json.dumps(answers), json.dumps(examples or []), local(now())])
    return name, ver


def _nine(messages, schema, max_tokens=300, timeout=120):
    from lib import stackwall
    base, headers, model = stackwall.model_upstream()
    body = {'model': model, 'temperature': 0, 'stream': False, 'max_tokens': max_tokens, 'messages': messages,
            'response_format': {'type': 'json_schema', 'json_schema': {'name': 'answer', 'schema': schema}},
            'chat_template_kwargs': {'enable_thinking': False}}
    req = urllib.request.Request(base + '/v1/chat/completions', json.dumps(body).encode(),
                                 {**headers, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        txt = json.load(r)['choices'][0]['message']['content']
    m = re.search(r'\{.*\}', txt, re.S)
    return json.loads(m.group(0) if m else txt)


def _item_text(con, kind, rid, account, with_text=True):
    if kind == 'mail':
        r = con.execute('SELECT date, from_name, from_addr, direction, subject, body_text FROM mail WHERE id = ?',
                        [rid]).fetchone()
        return (f'Date: {r[0]:%Y-%m-%d %H:%M}\nFrom: {r[1]} <{r[2]}> ({"sent by me" if r[3] == "out" else "received"})\n'
                f'Subject: {r[4]}\n\n{(r[5] or "")[:1500]}')
    if kind == 'event':
        r = con.execute('SELECT start, title, location, guests, my_response, description FROM events WHERE id = ?',
                        [rid]).fetchone()
        return f'When: {r[0]:%Y-%m-%d %H:%M}\nTitle: {r[1]}\nWhere: {r[2]}\nGuests: {r[3]}\nMy response: {r[4]}\n{r[5][:800]}'
    r = con.execute('SELECT name, kind, path, mime FROM files WHERE id = ?', [rid]).fetchone()
    out = f'File name: {r[0]}\nKind: {r[1]}\nFolder: {r[2]}'
    if with_text and r[1] in ('pdf', 'doc'):
        try:
            out += '\n\nStart of the text:\n' + file_text(con, account, rid)[:1200]
        except Exception as e:
            if _transient(e):  # the network or the store, not the file: let the caller retry
                raise
            out += '\n\n(The text could not be read; judge from the name and folder.)'
    return out


def _transient(e):
    """Errors worth retrying: rate limits, server errors, timeouts, a busy store. Not a broken file."""
    s = f'{type(e).__name__} {e}'
    return bool(re.search(r'\b(429|500|502|503|504)\b|[Tt]imed? ?out|URLError|Connection(Reset|Refused|Error)|'
                          r'RemoteDisconnected|ResourceInUse|rateLimit|backendError', s))


def _retry(fn, tries=3, waits=(2, 6)):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            if i == tries - 1 or not _transient(e):
                raise
            time.sleep(waits[min(i, len(waits) - 1)])


def judge(con, resource, name, where=None, since=None, limit=300, account=None, workers=4, progress=None):
    """Label each matching row with the 9B, once per definition version. Returns counts and seconds spent."""
    d = con.execute('SELECT version, on_kind, ask, answers FROM definitions WHERE name = ? ORDER BY version DESC',
                    [name]).fetchone()
    if not d:
        raise ValueError(f'No definition "{name}". Make one: idli define {name} --on mail --ask "..." --answers yes,no')
    ver, on_kind, ask, answers = d[0], d[1], d[2], json.loads(d[3])
    kind = 'file' if on_kind in ('file', 'photo') else on_kind
    res = resource if resource in RESOURCES else {'mail': 'mail', 'event': 'events', 'file': 'files'}[kind]
    if RESOURCES[res]['kind'] != kind:
        raise ValueError(f'"{name}" is a definition on {on_kind}, so judge it on '
                         f'{ {"mail": "mail", "event": "events", "file": "files or photos"}[kind] }.')
    idcol = 'id'
    _, rows, _ = select(con, res, where=where, since=since, fields=idcol, limit=limit, order=idcol)
    ids = [r[0] for r in rows]
    # failures saved by older versions ("could not judge: ...") are not answers: judge them again
    done = {r[0] for r in con.execute("SELECT record_id FROM labels WHERE kind = ? AND definition = ? AND version = ? "
                                      "AND coalesce(detail, '') NOT LIKE 'could not judge%'", [kind, name, ver]).fetchall()}
    todo = [i for i in ids if i not in done]
    schema = {'type': 'object', 'properties': {'label': {'type': 'string', 'enum': answers},
                                               'why': {'type': 'string'}}, 'required': ['label', 'why']}
    acct = {}
    if kind == 'file':
        acct = dict(con.execute('SELECT id, account FROM files').fetchall())
    t0 = time.time()

    def one(rid):
        cur = con.cursor()  # a DuckDB connection takes one call at a time; each thread gets its own cursor
        try:
            if on_kind == 'photo':
                mime = cur.execute('SELECT mime FROM files WHERE id = ?', [rid]).fetchone()[0]
                if not str(mime).startswith('image/'):
                    return rid, 'unsure', 'not an image'
                img = _retry(lambda: image_b64(acct.get(rid, account), rid, mime))
                msgs = [{'role': 'user', 'content': [
                    {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + img}},
                    {'type': 'text', 'text': f'{ask}\nAnswer with one of: {", ".join(answers)}, and a short why.'}]}]
            else:
                text = _retry(lambda: _item_text(cur, kind, rid, acct.get(rid, account)))
                msgs = [{'role': 'system', 'content': 'You label one item for the person. Answer with JSON only. '
                         'If the item does not give enough to tell, answer unsure.'},
                        {'role': 'user', 'content': f'{ask}\nAnswers: {", ".join(answers)}\n\n---\n{text}\n---'}]
            out = _retry(lambda: _nine(msgs, schema))
            lab = out.get('label') if out.get('label') in answers else 'unsure'
            return rid, lab, str(out.get('why', ''))[:200]
        except Exception as e:  # one item failing never stops the rest, and is not saved as an answer
            return rid, None, f'{type(e).__name__}: {str(e)[:120]}'
        finally:
            cur.close()
    results = []
    with cf.ThreadPoolExecutor(workers) as ex:
        for i, r in enumerate(ex.map(one, todo)):
            results.append(r)
            if progress and (i + 1) % 20 == 0:
                progress(i + 1, len(todo))
    failed = [(rid, why) for rid, lab, why in results if lab is None]
    for rid, lab, why in results:
        if lab is not None:
            con.execute('INSERT OR REPLACE INTO labels VALUES (?,?,?,?,?,?,?)', [kind, rid, name, ver, lab, why, local(now())])
    if failed:  # drop earlier saved failures for these rows so they read as not judged yet
        con.execute("DELETE FROM labels WHERE kind = ? AND definition = ? AND version = ? AND detail LIKE 'could not judge%' "
                    f"AND record_id IN ({','.join(repr(r) for r, _ in failed)})", [kind, name, ver])
    counts = dict(con.execute('SELECT label, count(*) FROM labels WHERE kind = ? AND definition = ? AND version = ? '
                              f'AND record_id IN ({",".join(repr(i) for i in ids) or "NULL"}) GROUP BY label',
                              [kind, name, ver]).fetchall())
    return {'definition': name, 'version': ver, 'judged_now': len(todo) - len(failed), 'already': len(ids) - len(todo),
            'failed': len(failed), 'failed_examples': [w for _, w in failed[:3]],
            'counts': counts, 'seconds': round(time.time() - t0, 1)}


def size_report(sandbox, con):
    p = Path(sandbox) / 'store.duckdb'
    tabs = {}
    for t in ['mail', 'events', 'files', 'file_text', 'labels', 'sheets']:
        tabs[t] = con.execute(f'SELECT count(*) FROM {t}').fetchone()[0]
    return {'bytes': p.stat().st_size if p.exists() else 0, 'rows': tabs}
