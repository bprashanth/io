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
CREATE TABLE IF NOT EXISTS file_pages (file_id TEXT, page INTEGER, text TEXT, PRIMARY KEY (file_id, page));
CREATE TABLE IF NOT EXISTS file_cards (file_id TEXT PRIMARY KEY, modified TIMESTAMP, summary TEXT, key_terms TEXT,
  made_by TEXT, made_at TIMESTAMP);
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
    # presentation before document: a .pptx is "officedocument.presentationml.presentation"
    for k, pat in [('folder', 'folder'), ('sheet', 'spreadsheet'), ('sheet', 'text/csv'), ('pdf', 'pdf'),
                   ('slides', 'presentation'), ('doc', 'document'), ('doc', 'wordprocessing'), ('image', 'image/'),
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


def sync_sheets(con, account, max_bytes=3_000_000, progress=None, on_item=None):
    """Every spreadsheet in Drive (Google Sheets, Excel, CSV) as its own table, first tab, columns as text.
    A sheet read since it last changed is skipped."""
    import pandas as pd
    g, t0 = _g(), time.time()
    rows = con.execute("SELECT f.id, f.name, f.mime, f.size FROM files f LEFT JOIN sheets s ON s.file_id = f.id "
                       "WHERE f.account = ? AND f.kind = 'sheet' AND (s.file_id IS NULL OR s.fetched_at < f.modified) "
                       "ORDER BY f.modified DESC", [account]).fetchall()
    taken = {r[0] for r in con.execute('SELECT tbl FROM sheets').fetchall()}
    n = 0
    for i, (fid, name, mime, size) in enumerate(rows, 1):
        t1 = time.time()
        if progress:
            progress(i - 1, len(rows), 0, time.time() - t0, 'reading sheets')
        if size and size > max_bytes:
            on_item and on_item(name, f'skipped: {size / 1e6:.1f} MB is over the {max_bytes / 1e6:.0f} MB limit')
            continue
        try:
            raw = g.drive_bytes(account, fid, mime)
            if 'spreadsheetml' in mime:
                df = pd.read_excel(io.BytesIO(raw), dtype=str)
            else:
                df = pd.read_csv(io.BytesIO(raw), dtype=str)
        except Exception as e:  # an unreadable file is skipped; it still shows in `files`
            on_item and on_item(name, f'could not be read: {type(e).__name__}')
            continue
        df = df.dropna(how='all').fillna('')
        df.columns = [re.sub(r'\s+', ' ', str(c)).strip() or f'col{i + 1}' for i, c in enumerate(df.columns)]
        old = con.execute('SELECT tbl FROM sheets WHERE file_id = ?', [fid]).fetchall()  # all: a half-read result blocks register
        tbl = old[0][0] if old else _slug(name, taken)
        taken.add(tbl)
        con.register('df_in', df)
        con.execute(f'CREATE OR REPLACE TABLE "{tbl}" AS SELECT row_number() OVER () AS row_no, * FROM df_in')
        con.unregister('df_in')
        con.execute('INSERT OR REPLACE INTO sheets VALUES (?,?,?,?,?,?)',
                    [name, fid, tbl, json.dumps(list(df.columns)), len(df), local(now())])
        n += 1
        on_item and on_item(name, f'{len(df)} rows, {len(df.columns)} columns, {time.time() - t1:.1f} s')
    if progress and rows:
        progress(len(rows), len(rows), 0, time.time() - t0, 'reading sheets')
    _log(con, 'sheets', account, n, t0)
    return n


PAGE_CHARS = 3000  # documents without real pages (Docs, text, sheets) are cut into parts of about this size


def _parts(text):
    out, buf = [], ''
    for para in text.split('\n'):
        if len(buf) + len(para) > PAGE_CHARS and buf:
            out.append(buf); buf = ''
        buf += para + '\n'
    return out + ([buf] if buf.strip() else [])


def file_text(con, account, fid):
    """A file's text, read once per version and kept: the whole (capped) in file_text, and page by page in
    file_pages for search. PDFs keep their pages; other files are cut into parts of about PAGE_CHARS."""
    row = con.execute('SELECT f.modified, t.modified, t.text, f.mime, f.kind, '
                      '(SELECT count(*) FROM file_pages p WHERE p.file_id = f.id) FROM files f LEFT JOIN file_text t '
                      'ON t.file_id = f.id WHERE f.id = ?', [fid]).fetchone()
    if not row:
        raise ValueError('No such file in the store. Run `idli sync files` first.')
    fmod, tmod, text, mime, kind, npages = row
    if text is not None and tmod == fmod and (npages or not text.strip()):  # read; an empty file has no pages
        return text
    if kind == 'sheet':
        pages = [_sheet_text(con, account, fid, mime, rows=2000)]
    else:
        raw = _g().drive_bytes(account, fid, mime)
        if kind == 'pdf':
            from pypdf import PdfReader
            pages = [(p.extract_text() or '') for p in PdfReader(io.BytesIO(raw)).pages[:200]]
        elif 'wordprocessing' in (mime or ''):
            import docx
            pages = ['\n'.join(p.text for p in docx.Document(io.BytesIO(raw)).paragraphs)]
        elif mime == 'application/vnd.google-apps.document' or readable(kind, mime, ''):
            pages = [raw.decode('utf-8', 'replace')]
        else:
            pages = ['']
    pages = [re.sub(r'[ \t]+', ' ', p.replace(BOM, '')) for p in pages]
    if kind != 'pdf':
        pages = _parts('\n'.join(pages)) or ['']
    text = '\n'.join(pages)[:TEXT_CAP]
    con.execute('DELETE FROM file_pages WHERE file_id = ?', [fid])
    rows = [[fid, i + 1, p] for i, p in enumerate(pages) if p.strip()]
    if rows:
        con.executemany('INSERT INTO file_pages VALUES (?,?,?)', rows)
    if tmod is not None and tmod != fmod:  # the file changed: what was judged on the old version no longer holds
        con.execute("DELETE FROM labels WHERE kind = 'file' AND record_id = ?", [fid])
    con.execute('INSERT OR REPLACE INTO file_text VALUES (?,?,?,?)', [fid, fmod, len(pages) if kind == 'pdf' else None, text])
    return text


def to_read(con, account=None):
    """Files whose text hasn't been read for their current version: (id, account, name, size)."""
    acct = 'AND f.account = ?' if account else ''
    return con.execute(
        "SELECT f.id, f.account, f.name, f.size, f.kind, f.mime FROM files f LEFT JOIN file_text t ON t.file_id = f.id "
        f"WHERE f.kind IN ('pdf', 'doc', 'sheet', 'other') {acct} AND (t.file_id IS NULL OR t.modified IS DISTINCT FROM "
        "f.modified OR (length(trim(t.text)) > 0 AND coalesce(t.pages, 0) >= 0 "
        "AND NOT EXISTS (SELECT 1 FROM file_pages p WHERE p.file_id = f.id))) "
        "ORDER BY f.modified DESC",
        [account] if account else []).fetchall()


def read_texts(con, account=None, workers=4, progress=None, limit=None, on_item=None):
    """Read every document not read yet (newest first), in parallel. Ctrl+C keeps what was read. Returns counts."""
    todo = [r for r in to_read(con, account) if readable(r[4], r[5], r[2])][:limit]
    t0, done, failed = time.time(), 0, []

    def one(r):
        cur = con.cursor()
        t1 = time.time()
        try:
            text = _retry_brief(lambda: file_text(cur, r[1], r[0]))
            if on_item:
                np = cur.execute('SELECT count(*) FROM file_pages WHERE file_id = ?', [r[0]]).fetchall()[0][0]
                on_item(r[2], f'{np} pages, {len(text):,} characters, {time.time() - t1:.1f} s')
            return r, None
        except Exception as e:
            if not _transient(e):  # a broken file: note it for this version (pages = -1) so sync doesn't retry it
                cur.execute('INSERT OR REPLACE INTO file_text SELECT id, modified, -1, ? FROM files WHERE id = ?',
                            [f'(could not be read: {type(e).__name__})', r[0]])
            return r, f'{type(e).__name__}: {str(e)[:100]}'
        finally:
            cur.close()
    ex = cf.ThreadPoolExecutor(workers)
    futs = [ex.submit(one, r) for r in todo]
    try:
        for i, fut in enumerate(cf.as_completed(futs), 1):
            r, err = fut.result()
            if err:
                failed.append(f'{r[2]}: {err}')
            else:
                done += 1
            if progress:
                progress(i, len(todo), len(failed), time.time() - t0, 'reading')
    except KeyboardInterrupt:
        ex.shutdown(wait=False, cancel_futures=True)
        raise
    ex.shutdown(wait=True)
    return {'read': done, 'failed': len(failed), 'failed_examples': failed[:3], 'seconds': round(time.time() - t0, 1)}


CARD_SCHEMA = {'type': 'object', 'properties': {
    'summary': {'type': 'string'}, 'key_terms': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 15}},
    'required': ['summary', 'key_terms']}
CARD_PROMPT = """You write a short card about one file so it can be found and sorted later. Answer with JSON:
- summary: 2 or 3 plain sentences on what the file is and what it covers. Keep the file's own words for its subject
  (if it says "Adivasi", write "Adivasi", not a synonym).
- key_terms: up to 15 names, places, groups, species, organisations, programmes and topic words, each exactly as
  written in the file. For a spreadsheet, include its column names.
Use only what is in the text."""


def _card_input(con, fid):
    """The name and a sample of the text: the start, a stretch from the middle and the end, about 6,000 characters."""
    name, kind, path = con.execute('SELECT name, kind, path FROM files WHERE id = ?', [fid]).fetchone()
    pages = [r[0] for r in con.execute('SELECT text FROM file_pages WHERE file_id = ? ORDER BY page', [fid]).fetchall()]
    text = '\n'.join(pages)
    if len(text) > 6000:
        mid = len(text) // 2
        text = text[:3600] + '\n[...]\n' + text[mid - 1000:mid + 1000] + '\n[...]\n' + text[-600:]
    return f'File name: {name}\nKind: {kind}\nFolder: {path}\n\n{text}'


def to_card(con):
    """Files read for their current version that have no card for it."""
    return [r[0] for r in con.execute(
        "SELECT f.id FROM files f JOIN file_text t ON t.file_id = f.id AND t.modified = f.modified "
        "LEFT JOIN file_cards c ON c.file_id = f.id WHERE coalesce(t.pages, 0) >= 0 AND length(trim(t.text)) > 0 "
        "AND (c.file_id IS NULL OR c.modified IS DISTINCT FROM f.modified) ORDER BY f.modified DESC").fetchall()]


def make_cards(con, workers=4, progress=None, limit=None, on_item=None):
    """A card per file version, by the served 9B. Ctrl+C keeps what was made."""
    todo, t0, failed, done = to_card(con)[:limit], time.time(), [], 0

    def one(fid):
        cur = con.cursor()
        t1 = time.time()
        try:
            out = _retry_brief(lambda: _nine([{'role': 'system', 'content': CARD_PROMPT},
                                              {'role': 'user', 'content': _card_input(cur, fid)}], CARD_SCHEMA,
                                             max_tokens=700, timeout=180, variant='nine_compressed'))
            terms = [str(t).strip() for t in out.get('key_terms') or [] if str(t).strip()][:15]
            cur.execute('INSERT OR REPLACE INTO file_cards SELECT id, modified, ?, ?, ?, ? FROM files WHERE id = ?',
                        [str(out.get('summary', '')).strip(), json.dumps(terms, ensure_ascii=False), 'nine_compressed',
                         local(now()), fid])
            if on_item:
                nm = cur.execute('SELECT name FROM files WHERE id = ?', [fid]).fetchall()[0][0]
                on_item(nm, f'{time.time() - t1:.1f} s; key terms: {", ".join(terms[:6])}' + (' ...' if len(terms) > 6 else ''))
            return fid, None
        except Exception as e:
            return fid, f'{type(e).__name__}: {str(e)[:100]}'
        finally:
            cur.close()
    ex = cf.ThreadPoolExecutor(workers)
    futs = [ex.submit(one, f) for f in todo]
    try:
        for i, fut in enumerate(cf.as_completed(futs), 1):
            fid, err = fut.result()
            failed.append(err) if err else None
            done += 0 if err else 1
            if progress:
                progress(i, len(todo), len(failed), time.time() - t0, 'making cards')
    except KeyboardInterrupt:
        ex.shutdown(wait=False, cancel_futures=True)
        raise
    ex.shutdown(wait=True)
    return {'made': done, 'failed': len(failed), 'failed_examples': failed[:3], 'seconds': round(time.time() - t0, 1)}


def card(con, fid):
    r = con.execute('SELECT summary, key_terms FROM file_cards c JOIN files f ON f.id = c.file_id '
                    'AND c.modified = f.modified WHERE c.file_id = ?', [fid]).fetchall()
    return (r[0][0], json.loads(r[0][1] or '[]')) if r else None


def drop_orphans(con):
    """Text, pages and labels of files no longer in Drive."""
    for t, col in (('file_text', 'file_id'), ('file_pages', 'file_id'), ('file_cards', 'file_id')):
        con.execute(f'DELETE FROM {t} WHERE {col} NOT IN (SELECT id FROM files)')
    con.execute("DELETE FROM labels WHERE kind = 'file' AND record_id NOT IN (SELECT id FROM files)")


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
           sheet=None, by=None, count=False, fields=None, order=None, limit=50, show_all=False):
    """Build and run the query for `list`. Returns (columns, rows, sql). Empty files are left out unless show_all."""
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
    if resource == 'files' and not show_all:
        conds.append(f'NOT {EMPTY_SQL}')
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
    found = ''
    if search:
        cols = r.get('text') or [c for c in columns_of(con, src)]
        raw = [w.replace("'", '') for w in re.split(r'\s+', search.strip()) if w]
        # % and _ are wildcards in LIKE: search for them as typed
        words = [w.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') for w in raw]
        lk = "ESCAPE '\\'"
        if r.get('kind') == 'file' and r.get('table') == 'files':  # names and folders, or anywhere in the text
            conds.append('(' + ' AND '.join(
                '(' + ' OR '.join(f"CAST({c} AS TEXT) ILIKE '%{w}%' {lk}" for c in cols) +
                f" OR id IN (SELECT file_id FROM file_pages WHERE text ILIKE '%{w}%' {lk})"
                f" OR id IN (SELECT file_id FROM file_cards WHERE summary || ' ' || key_terms ILIKE '%{w}%' {lk}))"
                for w in words) + ')')
            w0, wl = raw[0], words[0]
            found = (f", (SELECT 'p.' || page || ': ...' || regexp_replace(substr(text, greatest(1, "
                     f"strpos(lower(text), lower('{w0}')) - 70), 160), '\\s+', ' ', 'g') || '...' FROM file_pages p "
                     f"WHERE p.file_id = files.id AND p.text ILIKE '%{wl}%' {lk} ORDER BY page LIMIT 1) AS found")
        else:
            conds.append('(' + ' AND '.join('(' + ' OR '.join(f"CAST({c} AS TEXT) ILIKE '%{w}%' {lk}"
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
        cols = fields or ((', '.join(r['show']) if r.get('show') else '*') + found)
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


# Which models this process uses. idlicli sets them from --mapper and --judge.
#   NINE:  the 9B that maps (with --mapper nine*) and words replies: 'nine' (BF16) or 'nine_compressed' (served Q5)
#   JUDGE: who labels rows: 'nine', 'nine_compressed', or 'clef' (hosted Clef-flash: it sees real content, so
#          test accounts only)
TRACE = None  # idlicli sets this to its `say(level, msg)`; level 3 shows every model call
NINE = os.environ.get('IDLI_NINE', 'nine_compressed')
JUDGE = os.environ.get('IDLI_JUDGE', 'nine_compressed')
NINE_BF16_URL = os.environ.get('IDLI_9B_BF16_URL', 'http://127.0.0.1:8292')  # idli-9b-bf16 on the DGX
CLEF_UNSURE = (0.35, 0.65)  # P(yes) inside this band is unsure; for other answers, a top answer under 0.5 is


def _nine_upstream(variant):
    if variant == 'nine' and not os.environ.get('IDLI_9B_URL'):
        return NINE_BF16_URL, {}, 'qwen3.5-9b-bf16'
    from lib import stackwall
    return stackwall.model_upstream()


def _nine(messages, schema, max_tokens=300, timeout=120, variant=None):
    base, headers, model = _nine_upstream(variant or NINE)
    body = {'model': model, 'temperature': 0, 'stream': False, 'max_tokens': max_tokens, 'messages': messages,
            'response_format': {'type': 'json_schema', 'json_schema': {'name': 'answer', 'schema': schema}},
            'chat_template_kwargs': {'enable_thinking': False}}
    req = urllib.request.Request(base + '/v1/chat/completions', json.dumps(body).encode(),
                                 {**headers, 'Content-Type': 'application/json'})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        txt = json.load(r)['choices'][0]['message']['content']
    if TRACE:
        TRACE(3, f'[9B {variant or NINE} at {base}, {time.time() - t0:.1f} s]\n--- sent:\n' +
              '\n'.join(str(m.get('content'))[:6000] for m in messages) + f'\n--- returned:\n{txt}')
    m = re.search(r'\{.*\}', txt, re.S)
    return json.loads(m.group(0) if m else txt)


def _clef(text, ask, answers, timeout=60):
    """Clef-flash through OpenRouter, Cloudflare as the only provider. Returns (label, detail). It scores each
    allowed answer; `unsure` is ours, never offered to it."""
    from lib import minisql
    opts = [a for a in answers if a != 'unsure']
    yesno = sorted(opts) == ['no', 'yes']
    q = {'type': 'noul', 'instructions': ask} if yesno else \
        {'type': 'choice', 'instructions': ask, 'criteria': {a: a for a in opts}}
    body = {'model': 'cloudflare/clef-flash', 'state': text, 'questions': {'q': q},
            'provider': {'order': ['Cloudflare'], 'allow_fallbacks': False}}
    req = urllib.request.Request('https://openrouter.ai/api/v1/systemone', json.dumps(body).encode(), {
        'Content-Type': 'application/json', 'Authorization': 'Bearer ' + minisql._key(), 'User-Agent': 'idli-scaffold/1'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.load(r)
    if out.get('provider') != 'Cloudflare':
        raise RuntimeError(f'Clef was served by {out.get("provider")}, not Cloudflare')
    if TRACE:
        TRACE(3, f'[clef]\n--- sent:\n{text[:6000]}\n--- question: {json.dumps(q)}\n--- returned: {json.dumps(out["answers"])}')
    a = out['answers']['q']
    if yesno:
        p = a['noul']
        lab = 'unsure' if CLEF_UNSURE[0] < p < CLEF_UNSURE[1] else ('yes' if p >= 0.5 else 'no')
        return lab, f'Clef: P(yes) = {p:.2f}'
    probs = a['probabilities']
    top = max(probs, key=probs.get)
    lab = top if probs[top] >= 0.5 else 'unsure'
    return lab, 'Clef: ' + ', '.join(f'{k} {v:.2f}' for k, v in sorted(probs.items(), key=lambda kv: -kv[1]))


TEXT_KINDS = ('pdf', 'doc', 'sheet', 'other')       # file kinds a text definition reads
TEXTLIKE = re.compile(r'^text/|json|[/+]xml\b|yaml|javascript|x-python|x-sh|x-r\b|markdown|csv|ipynb', re.I)
TEXT_EXT = re.compile(r'\.(txt|md|py|r|ipynb|json|csv|tsv|ya?ml|sh|js|ts|sql|html?|tex)$', re.I)
BOM = chr(0xfeff)
# A file with no content at all: an uploaded file of 0 bytes, or a document whose text came back empty. PDFs with
# pages but no text (scans) are not empty. Listings hide these unless --all; judge skips them.
EMPTY_SQL = ("((kind NOT IN ('folder', 'doc', 'sheet', 'slides', 'form') AND size = 0 AND mime NOT LIKE "
             "'application/vnd.google-apps%') OR (kind <> 'pdf' AND id IN (SELECT file_id FROM file_text WHERE "
             f"length(trim(replace(text, '{BOM}', ''))) = 0)))")


def readable(kind, mime, name):
    """Can a text definition read this file's contents? PDFs, documents, sheets, and text-like files."""
    if kind in ('pdf', 'doc', 'sheet'):
        return True
    return kind == 'other' and bool(TEXTLIKE.search(mime or '') or TEXT_EXT.search(name or ''))


def _sheet_text(con, account, fid, mime, rows=15):
    """A spreadsheet as its header and first rows, from the table sync made, or read now."""
    t = con.execute('SELECT tbl FROM sheets WHERE file_id = ?', [fid]).fetchone()
    if t:
        cur = con.execute(f'SELECT * EXCLUDE (row_no) FROM "{t[0]}" LIMIT {rows}')
        head = [d[0] for d in cur.description]
        return '\n'.join(', '.join(str(v) for v in r) for r in [head] + cur.fetchall())
    raw = _g().drive_bytes(account, fid, mime)
    if 'spreadsheetml' in (mime or ''):
        import pandas as pd
        df = pd.read_excel(io.BytesIO(raw), dtype=str, nrows=rows).fillna('')
        return '\n'.join(', '.join(map(str, r)) for r in [list(df.columns)] + df.values.tolist())
    return '\n'.join(raw.decode('utf-8', 'replace').splitlines()[:rows + 1])


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
    if with_text and readable(r[1], r[3], r[0]):
        try:
            body = _sheet_text(con, account, rid, r[3]) if r[1] == 'sheet' else file_text(con, account, rid)
            body = re.sub(r'[ \t]+', ' ', body.replace(BOM, '')).strip()
            if not body:
                return None  # nothing to judge
            c = card(con, rid)
            if c:
                out += f'\n\nSummary: {c[0]}\nKey terms: {", ".join(c[1])}'
            out += '\n\nStart of the text:\n' + body[:1200]
        except Exception as e:
            if _transient(e):  # the network or the store, not the file: let the caller retry
                raise
            out += '\n\n(The text could not be read; judge from the name and folder.)'
    return out


def _transient(e):
    """Errors worth retrying: rate limits, server errors, timeouts, a busy store. Not a broken file."""
    s = f'{type(e).__name__} {e}'
    return bool(re.search(r'\b(429|500|502|503|504)\b|[Tt]imed? ?out|URLError|Connection(Reset|Refused|Error)|'
                          r'RemoteDisconnected|ResourceInUse|rateLimit|backendError|Quota|Rate Limit', s))


def _retry_brief(fn, tries=3, waits=(2, 6)):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            if i == tries - 1 or not _transient(e):
                raise
            if TRACE:
                TRACE(3, f'[retry {i + 1}] {type(e).__name__}: {str(e)[:200]}')
            time.sleep(waits[min(i, len(waits) - 1)])


class Stopped(Exception):
    """Ctrl+C during judge: what was judged is kept."""
    def __init__(self, result):
        super().__init__('stopped')
        self.result = result


def _names(con, kind, ids):
    if not ids:
        return {}
    tbl, col = {'mail': ('mail', 'subject'), 'event': ('events', 'title'), 'file': ('files', 'name')}[kind]
    return dict(con.execute(f'SELECT id, {col} FROM {tbl} WHERE id IN ({",".join(repr(i) for i in ids)})').fetchall())


def judge(con, resource, name, where=None, since=None, limit=300, account=None, workers=4, progress=None, on_item=None,
          folder=None):
    """Label each matching row once per definition version. Each label is saved as it lands; failures are reported
    and not saved; Ctrl+C keeps what was done (raises Stopped). Returns counts, examples and seconds."""
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
    scope = where
    if on_kind == 'photo':  # pictures only
        scope = f"({where}) AND kind = 'image'" if where else "kind = 'image'"
    elif kind == 'file':  # a text definition: no folders, pictures or videos, nothing empty
        keep = f"kind IN ({','.join(repr(k) for k in TEXT_KINDS)}) AND NOT {EMPTY_SQL}"
        scope = f"({where}) AND {keep}" if where else keep
    _, rows, _ = select(con, res, where=scope, since=since, fields='id', limit=limit, order='id', folder=folder)
    ids = [r[0] for r in rows]
    if kind == 'file' and on_kind != 'photo':  # binary files of kind 'other' (zips, apps) have nothing to read
        meta = {r[0]: r[1:] for r in con.execute('SELECT id, kind, mime, name FROM files').fetchall()}
        ids = [i for i in ids if readable(*meta[i])]
    # failures saved by older versions ("could not judge: ...") are not answers: judge them again
    done = {r[0] for r in con.execute("SELECT record_id FROM labels WHERE kind = ? AND definition = ? AND version = ? "
                                      "AND coalesce(detail, '') NOT LIKE 'could not judge%'", [kind, name, ver]).fetchall()}
    todo = [i for i in ids if i not in done]
    schema = {'type': 'object', 'properties': {'label': {'type': 'string', 'enum': answers},
                                               'why': {'type': 'string'}}, 'required': ['label', 'why']}
    acct = dict(con.execute('SELECT id, account FROM files').fetchall()) if kind == 'file' else {}
    t0 = time.time()

    def one(rid):
        cur = con.cursor()  # a DuckDB connection takes one call at a time; each thread gets its own cursor
        try:
            if on_kind == 'photo':
                mime = cur.execute('SELECT mime FROM files WHERE id = ?', [rid]).fetchone()[0]
                img = _retry_brief(lambda: image_b64(acct.get(rid, account), rid, mime))
                msgs = [{'role': 'user', 'content': [
                    {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + img}},
                    {'type': 'text', 'text': f'{ask}\nAnswer with one of: {", ".join(answers)}, and a short why.'}]}]
            else:
                text = _retry_brief(lambda: _item_text(cur, kind, rid, acct.get(rid, account)))
                if text is None:
                    return rid, 'unsure', 'empty: nothing to read'
                msgs = [{'role': 'system', 'content': 'You label one item for the person. Answer with JSON only. '
                         'If the item does not give enough to tell, answer unsure.'},
                        {'role': 'user', 'content': f'{ask}\nAnswers: {", ".join(answers)}\n\n---\n{text}\n---'}]
            if JUDGE == 'clef' and on_kind != 'photo':
                lab, why = _retry_brief(lambda: _clef(text, ask, answers))
                return rid, lab, why
            out = _retry_brief(lambda: _nine(msgs, schema, variant='nine_compressed' if JUDGE == 'clef' else JUDGE))
            lab = out.get('label') if out.get('label') in answers else 'unsure'
            return rid, lab, str(out.get('why', ''))[:200]
        except Exception as e:  # one item failing never stops the rest, and is not saved as an answer
            return rid, None, f'{type(e).__name__}: {str(e)[:120]}'
        finally:
            cur.close()

    failed, saved = [], 0
    names = _names(con, kind, todo) if on_item else {}

    def summary(stopped=False):
        if failed:  # earlier saved failures for these rows read as not judged yet
            con.execute("DELETE FROM labels WHERE kind = ? AND definition = ? AND version = ? AND detail LIKE "
                        f"'could not judge%' AND record_id IN ({','.join(repr(r) for r, _ in failed)})", [kind, name, ver])
        q = (f'FROM labels WHERE kind = ? AND definition = ? AND version = ? '
             f'AND record_id IN ({",".join(repr(i) for i in ids) or "NULL"})')
        counts = dict(con.execute(f'SELECT label, count(*) {q} GROUP BY label', [kind, name, ver]).fetchall())
        common = max(counts, key=counts.get) if counts else None
        ex = {}
        for lab in counts:
            if lab != common or len(counts) == 1:
                rids = [r[0] for r in con.execute(f'SELECT record_id {q} AND label = ? LIMIT 5', [kind, name, ver, lab]).fetchall()]
                nm = _names(con, kind, rids)
                ex[lab] = [nm.get(r, r) for r in rids]
        return {'definition': name, 'version': ver, 'judge': JUDGE, 'judged_now': saved, 'to_judge': len(todo),
                'already': len(ids) - len(todo), 'failed': len(failed), 'failed_examples': [w for _, w in failed[:3]],
                'counts': counts, 'examples': ex, 'seconds': round(time.time() - t0, 1), 'stopped': stopped}

    ex = cf.ThreadPoolExecutor(workers)
    futs = [ex.submit(one, rid) for rid in todo]
    try:
        for i, fut in enumerate(cf.as_completed(futs), 1):
            rid, lab, why = fut.result()
            if lab is None:
                failed.append((rid, why))
            else:
                con.execute('INSERT OR REPLACE INTO labels VALUES (?,?,?,?,?,?,?)',
                            [kind, rid, name, ver, lab, why, local(now())])
                saved += 1
            if on_item:
                on_item(names.get(rid, rid), lab, why)
            if progress:
                progress(i, len(todo), len(failed), time.time() - t0)
    except KeyboardInterrupt:
        ex.shutdown(wait=False, cancel_futures=True)
        raise Stopped(summary(stopped=True))
    ex.shutdown(wait=True)
    return summary()


def size_report(sandbox, con):
    p = Path(sandbox) / 'store.duckdb'
    tabs = {}
    for t in ['mail', 'events', 'files', 'file_text', 'labels', 'sheets']:
        tabs[t] = con.execute(f'SELECT count(*) FROM {t}').fetchone()[0]
    return {'bytes': p.stat().st_size if p.exists() else 0, 'rows': tabs}
