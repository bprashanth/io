"""`idli`: the record store on the command line, and `idli ask`, the left chat on top of it.

    idli sync [mail|events|files|sheets|all]        read your Google account into this sandbox's store
    idli list RESOURCE [--where ..] [--since ..]    rows: mail, threads, events, files, folders, photos, sheets,
                                                    rows --sheet NAME, labels, definitions, or a view
    idli get RESOURCE ID|NAME                       one item in full
    idli explain [RESOURCE]                         fields and examples (the man page)
    idli describe file|sheet NAME                   what's inside: pages, columns, value ranges
    idli read file NAME                             a PDF's or document's text
    idli summarise file NAME [--question Q]         the 9B's summary of a file
    idli define NAME --on mail|event|file|photo --ask "..." --answers yes,no
    idli judge RESOURCE --def NAME [--where ..]     the 9B labels each row once per definition version
    idli query "SELECT ..."                         any read-only SQL over the store
    idli view NAME --sql "SELECT ..."               save a query as a resource you can list
    idli draft mail --reply-to THREAD --ask "..."   a draft, previewed only (nothing is saved or sent)
    idli ask "question"                             ask in your own words; it picks the commands and answers

Nothing here changes your accounts. narrative/GOALS_v0.md and narrative/EXAMPLES_V0.md explain the design.
"""
import argparse
import datetime as dt
import json
import os
import re
import shlex
import sys
import time
from pathlib import Path

from lib import recstore as rs

ACCOUNTS = {'me': '87profligate@gmail.com', 'lead': '88profligate@gmail.com'}


def sandbox():
    return os.environ.get('IDLI_SANDBOX') or str(Path.home() / 'idli-insights' / 'scaffold')


def account(role=None):
    return ACCOUNTS.get(role or 'me', role or ACCOUNTS['me'])


class Result:
    def __init__(self, cols=None, rows=None, text='', kind='table', sql='', note=''):
        self.cols, self.rows, self.text, self.kind, self.sql, self.note = cols or [], rows or [], text, kind, sql, note

    def render(self, max_rows=20):
        if self.kind == 'text':
            return self.text
        if not self.rows:
            return (self.note + '\n' if self.note else '') + 'Nothing matches.'
        out = []
        for i, r in enumerate(self.rows[:max_rows], 1):
            vals = [_fmt(v) for v in r]
            out.append(f'{i}. ' + ' | '.join(v for v in vals if v != ''))
        more = f'\n... and {len(self.rows) - max_rows} more' if len(self.rows) > max_rows else ''
        head = f'{len(self.rows)} row{"s" if len(self.rows) != 1 else ""} ({", ".join(self.cols)})'
        return (self.note + '\n' if self.note else '') + head + '\n' + '\n'.join(out) + more


def _fmt(v):
    if isinstance(v, dt.datetime):
        v = rs.local(v)
        return v.strftime('%a %d %b %Y %H:%M') if (v.hour, v.minute) != (0, 0) else v.strftime('%a %d %b %Y')
    if isinstance(v, float):
        return f'{v:.2f}'.rstrip('0').rstrip('.')
    s = '' if v is None else str(v)
    return s if len(s) <= 90 else s[:87] + '...'


# ---- the parser: one grammar for people, scripts and the mapper ----

class Err(ValueError):
    pass


class P(argparse.ArgumentParser):
    def error(self, message):
        raise Err(f'{message}. Try `idli {self.prog.split()[-1]} --help` or `idli explain`.')


def parser():
    p = P(prog='idli', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, add_help=True)
    sub = p.add_subparsers(dest='verb')
    s = sub.add_parser('sync', help='read your Google account into the store')
    s.add_argument('what', nargs='?', default='all', choices=['all', 'mail', 'events', 'files', 'sheets'])
    s.add_argument('--as', dest='role', default='me')
    for verb in ('list', 'count'):
        l = sub.add_parser(verb, help='rows of a resource' if verb == 'list' else 'how many rows match')
        l.add_argument('resource')
        l.add_argument('--where', help="filter, e.g. \"direction = 'in' and subject ~ 'visit'\" or \"label.urgent = 'yes'\"")
        l.add_argument('--since', help='today, yesterday, 7d, last week, monday, 2026-11-12')
        l.add_argument('--until')
        l.add_argument('--on', help='one day or range: yesterday, next monday, this week')
        l.add_argument('--search', help='words that must all appear')
        l.add_argument('--label', help='DEFINITION or DEFINITION=VALUE, e.g. urgent or funder=yes')
        l.add_argument('--in', dest='folder', help='Drive folder name (files, photos, folders)')
        l.add_argument('--sheet', help='which sheet, for rows')
        l.add_argument('--by', help='count by these fields, e.g. kind or folder,kind')
        l.add_argument('--fields', help='which fields to show')
        l.add_argument('--order', help='e.g. "date desc"')
        l.add_argument('--limit', type=int, default=50)
        l.add_argument('-o', dest='out', default='table', choices=['table', 'json'])
    g = sub.add_parser('get', help='one item in full')
    g.add_argument('resource', choices=['mail', 'thread', 'event', 'file'])
    g.add_argument('ref', help='an id, or words from its name or subject')
    e = sub.add_parser('explain', help='fields and examples')
    e.add_argument('resource', nargs='?')
    for verb in ('describe', 'read', 'summarise'):
        d = sub.add_parser(verb, help={'describe': "what's inside a file or sheet", 'read': "a file's text",
                                       'summarise': "the 9B's summary of a file"}[verb])
        d.add_argument('what', choices=['file', 'sheet'] if verb == 'describe' else ['file'])
        d.add_argument('ref', help='a name (or words from it) or an id')
        if verb == 'summarise':
            d.add_argument('--question', default='')
        if verb == 'read':
            d.add_argument('--chars', type=int, default=3000)
    d = sub.add_parser('define', help='your own category, applied by judge')
    d.add_argument('name')
    d.add_argument('--on', required=True, choices=['mail', 'event', 'file', 'photo'])
    d.add_argument('--ask', required=True, help='the question for each item')
    d.add_argument('--answers', default='yes,no')
    j = sub.add_parser('judge', help='label each row with a definition')
    j.add_argument('resource')
    j.add_argument('--def', dest='defn', required=True)
    j.add_argument('--where')
    j.add_argument('--since')
    j.add_argument('--limit', type=int, default=300)
    q = sub.add_parser('query', help='read-only SQL over the store')
    q.add_argument('sql')
    v = sub.add_parser('view', help='save a query as a resource')
    v.add_argument('name')
    v.add_argument('--sql', required=True)
    v.add_argument('--on', default='mail')
    v.add_argument('--about', default='')
    w = sub.add_parser('draft', help='a draft email, previewed only')
    w.add_argument('what', choices=['mail'])
    w.add_argument('--reply-to', help='thread id or words from its subject')
    w.add_argument('--to')
    w.add_argument('--subject', default='')
    w.add_argument('--ask', default='', help='what the draft should say')
    dd = sub.add_parser('date', help='what a date phrase means: next monday, last week, 7d')
    dd.add_argument('phrase', nargs='+')
    a = sub.add_parser('ask', help='ask in your own words')
    a.add_argument('question', nargs='+')
    a.add_argument('--mapper', default=os.environ.get('IDLI_MAPPER', 'remote'), choices=['remote', 'nine', 'nine_compressed'],
                   help='remote: idli-remote maps (masked). nine: the full 9B (BF16) maps and words the reply. '
                        'nine_compressed: the served 9B (Q5) does both')
    a.add_argument('--new', action='store_true', help='start a new conversation')
    sub.add_parser('size', help="the store's size")
    return p


# ---- running a command ----

def run_argv(con, argv):
    if argv and argv[0] == 'idli':
        argv = argv[1:]
    # `--label people = 'yes'` arrives as three words: join them
    out = []
    for t in argv:
        if out and (t.startswith('=') or out[-1].endswith('=')) and len(out) >= 2 and out[-2] == '--label':
            out[-1] += t
        else:
            out.append(t)
    argv = out
    if not argv:
        return Result(kind='text', text=__doc__)
    a = parser().parse_args(argv)
    v = a.verb
    if v == 'sync':
        acct, out = account(a.role), []
        for what in (['mail', 'events', 'files', 'sheets'] if a.what == 'all' else [a.what]):
            n = getattr(rs, f'sync_{what}')(con, acct)
            out.append(f'{what}: {n} new or updated')
        return Result(kind='text', text='Synced ' + acct + '. ' + '; '.join(out) + '.')
    if v in ('list', 'count'):
        cols, rows, sql = rs.select(con, a.resource, where=a.where, since=a.since, until=a.until, on=a.on,
                                    search=a.search, label=a.label, folder=a.folder, sheet=a.sheet, by=a.by,
                                    count=(v == 'count'), fields=a.fields, order=a.order, limit=a.limit)
        if getattr(a, 'out', 'table') == 'json':
            return Result(kind='text', text=json.dumps([dict(zip(cols, map(_fmt, r))) for r in rows], ensure_ascii=False))
        return Result(cols, rows, sql=sql)
    if v == 'get':
        return get(con, a.resource, a.ref)
    if v == 'explain':
        return Result(kind='text', text=explain(con, a.resource))
    if v == 'describe':
        return describe(con, a.what, a.ref)
    if v == 'read':
        fid, name = find_file(con, a.ref)
        t = rs.file_text(con, file_account(con, fid), fid)
        return Result(kind='text', text=f'{name} ({len(t)} characters):\n\n' + t[:a.chars])
    if v == 'summarise':
        return summarise(con, a.ref, a.question)
    if v == 'define':
        name, ver = rs.define(con, a.name, a.on, a.ask, a.answers)
        return Result(kind='text', text=f'Definition "{name}" version {ver}: {a.ask} ({a.answers}). '
                                        f'Next: idli judge {"photos" if a.on == "photo" else {"mail": "mail", "event": "events", "file": "files"}[a.on]} --def {name}')
    if v == 'judge':
        r = rs.judge(con, a.resource, a.defn, where=a.where, since=a.since, limit=a.limit, account=account())
        return Result(kind='text', text=f'Judged {r["judged_now"]} now ({r["already"]} already judged), {r["seconds"]} s. '
                                        f'Labels: ' + ', '.join(f'{k} {n}' for k, n in sorted(r['counts'].items())) +
                                        (f'. {r["failed"]} could not be judged (run judge again to retry): '
                                         f'{r["failed_examples"][0]}' if r.get('failed') else ''),
                      note=json.dumps(r))
    if v == 'query':
        cols, rows = rs.query(con, a.sql)
        return Result(cols, rows, sql=a.sql)
    if v == 'view':
        rs.query(con, a.sql, limit=1)
        con.execute('INSERT OR REPLACE INTO views VALUES (?,?,?,?)', [a.name, a.on, a.sql, a.about])
        return Result(kind='text', text=f'Saved view "{a.name}". List it with: idli list {a.name}')
    if v == 'draft':
        return draft(con, a)
    if v == 'date':
        ph = ' '.join(a.phrase)
        x, y = rs.day_range(ph)
        y = y - dt.timedelta(days=1)
        return Result(kind='text', text=f'{ph} = {x:%A %d %B %Y}' + ('' if x == y else f' to {y:%A %d %B %Y}') +
                      f' (today is {rs.now():%A %d %B %Y}).')
    if v == 'size':
        return Result(kind='text', text=json.dumps(rs.size_report(sandbox(), con)))
    raise Err('Try `idli --help`.')


def file_account(con, fid):
    r = con.execute('SELECT account FROM files WHERE id = ?', [fid]).fetchone()
    return r[0] if r else account()


def find_file(con, ref, kinds=None):
    r = con.execute('SELECT id, name FROM files WHERE id = ?', [ref]).fetchone()
    if r:
        return r
    words = [w for w in re.split(r'\s+', ref.strip()) if w]
    cond = ' AND '.join(f"(name || ' ' || path) ILIKE '%{w.replace(chr(39), '')}%'" for w in words)
    k = f" AND kind IN ({','.join(repr(x) for x in kinds)})" if kinds else " AND kind != 'folder'"
    rows = con.execute(f'SELECT id, name, path FROM files WHERE {cond}{k} ORDER BY modified DESC').fetchall()
    if not rows:
        raise Err(f'No file matching "{ref}". Try `idli list files --search "{words[0] if words else ""}"`.')
    if len(rows) > 1 and not any(r[1].lower() == ref.lower() for r in rows):
        exact = [r for r in rows if all(w.lower() in r[1].lower() for w in words)]
        rows = exact or rows
    return rows[0][0], rows[0][1]


def get(con, what, ref):
    if what == 'file':
        fid, _ = find_file(con, ref, kinds=None)
        cols = rs.columns(con, 'files')
        r = con.execute('SELECT * FROM files WHERE id = ?', [fid]).fetchone()
        return Result(kind='text', text='\n'.join(f'{c}: {_fmt(x)}' for c, x in zip(cols, r) if x not in (None, '')))
    if what == 'event':
        r = con.execute("SELECT * FROM events WHERE id = ? OR title ILIKE ? ORDER BY start LIMIT 1",
                        [ref, f'%{ref}%']).fetchone()
        if not r:
            raise Err(f'No event matching "{ref}". Try `idli list events --search "{ref}"`.')
        cols = rs.columns(con, 'events')
        return Result(kind='text', text='\n'.join(f'{c}: {_fmt(x)}' for c, x in zip(cols, r) if x not in (None, '')))
    if what == 'thread':
        tid = con.execute('SELECT thread_id FROM mail WHERE thread_id = ? OR id = ? OR subject ILIKE ? '
                          'ORDER BY date DESC LIMIT 1', [ref, ref, f'%{ref}%']).fetchone()
        if not tid:
            raise Err(f'No thread matching "{ref}". Try `idli list threads --search "{ref}"`.')
        rows = con.execute('SELECT date, direction, from_name, from_addr, subject, substr(body_text, 1, 600) FROM mail '
                           'WHERE thread_id = ? ORDER BY date', [tid[0]]).fetchall()
        return Result(kind='text', text='\n\n'.join(f'{_fmt(d)} {"me" if dr == "out" else (n or a)}: {s}\n{b}'
                                                     for d, dr, n, a, s, b in rows))
    r = con.execute("SELECT date, direction, from_name, from_addr, to_addrs, subject, body_text, thread_id FROM mail "
                    "WHERE id = ? OR subject ILIKE ? ORDER BY date DESC LIMIT 1", [ref, f'%{ref}%']).fetchone()
    if not r:
        raise Err(f'No email matching "{ref}". Try `idli list mail --search "{ref}"`.')
    return Result(kind='text', text=f'{_fmt(r[0])} from {r[2]} <{r[3]}> to {r[4]}\nSubject: {r[5]}\nThread: {r[7]}\n\n'
                                    f'{(r[6] or "")[:3000]}')


def describe(con, what, ref):
    if what == 'sheet':
        row = con.execute('SELECT name, tbl, nrows FROM sheets WHERE name ILIKE ? OR tbl = ? ORDER BY nrows DESC',
                          [f'%{ref}%', ref]).fetchone()
        if not row:
            raise Err(f'No sheet matching "{ref}". `idli list sheets` shows them.')
        return _describe_table(con, row[1], f'{row[0]}: {row[2]} rows')
    fid, name = find_file(con, ref)
    f = con.execute('SELECT kind, mime, size, modified, path FROM files WHERE id = ?', [fid]).fetchone()
    head = f'{name} ({f[0]}, {f[2] or "?"} bytes, changed {_fmt(f[3])}, in {f[4] or "My Drive"})'
    if f[0] == 'sheet':
        t = con.execute('SELECT tbl, nrows FROM sheets WHERE file_id = ?', [fid]).fetchone()
        if t:
            return _describe_table(con, t[0], head + f'\n{t[1]} rows')
    if f[0] in ('pdf', 'doc'):
        t = rs.file_text(con, file_account(con, fid), fid)
        pages = con.execute('SELECT pages FROM file_text WHERE file_id = ?', [fid]).fetchone()[0]
        words = len(t.split())
        first = re.sub(r'\s+', ' ', t[:400])
        return Result(kind='text', text=head + f'\n{pages or "?"} pages, about {words} words read.\nStarts: {first}')
    return Result(kind='text', text=head)


def _describe_table(con, tbl, head):
    cols = [c for c in rs.columns_of(con, f'"{tbl}"') if c != 'row_no']
    lines = [head, f'{len(cols)} columns:']
    for c in cols[:40]:
        r = con.execute(f'SELECT count(DISTINCT "{c}"), count(*) FILTER (WHERE "{c}" != \'\'), '
                        f'string_agg(DISTINCT "{c}", \', \') FILTER (WHERE "{c}" != \'\') FROM (SELECT "{c}" FROM "{tbl}" LIMIT 500)').fetchone()
        ex = (r[2] or '')[:80]
        lines.append(f'- {c}: {r[1]} filled, {r[0]} different (e.g. {ex})')
    if len(cols) > 40:
        lines.append(f'... and {len(cols) - 40} more columns')
    return Result(kind='text', text='\n'.join(lines))


def summarise(con, ref, question=''):
    fid, name = find_file(con, ref)
    kind = con.execute('SELECT kind FROM files WHERE id = ?', [fid]).fetchone()[0]
    if kind == 'sheet':
        return describe(con, 'file', fid)
    t = rs.file_text(con, file_account(con, fid), fid)
    if not t.strip():
        return Result(kind='text', text=f'{name} has no text I can read (it may be a scan).')
    chunks = [t[i:i + 7000] for i in range(0, min(len(t), 35000), 7000)]
    schema = {'type': 'object', 'properties': {'summary': {'type': 'string'}}, 'required': ['summary']}
    import concurrent.futures as cf
    def part(c):
        return rs._nine([{'role': 'user', 'content': f'Summarise this part of "{name}" in 3 sentences'
                          + (f', focusing on: {question}' if question else '') + f'.\n\n{c}'}], schema,
                        max_tokens=300)['summary']
    with cf.ThreadPoolExecutor(4) as ex:  # the parts at once: a 96-page report took over a minute one by one
        parts = list(ex.map(part, chunks))
    if len(parts) > 1:
        final = rs._nine([{'role': 'user', 'content': f'Combine these notes on "{name}" into one summary of 4-6 '
                           f'sentences{", focusing on: " + question if question else ""}. Keep only what the notes say.'
                           '\n\n' + '\n'.join(parts)}], schema, max_tokens=400)['summary']
    else:
        final = parts[0]
    return Result(kind='text', text=f'{name}: {final}\n(Read {min(len(t), 35000)} of {len(t)} characters.)')


def draft(con, a):
    """A draft, previewed only. --reply-to must match one conversation (all its words in the sender or subject);
    a new email to someone with no conversation needs --to ADDRESS."""
    to, subject, context = a.to or '', a.subject, ''
    if a.reply_to:
        ref = a.reply_to.strip()
        r = con.execute('SELECT thread_id, subject, from_addr, from_name, body_text FROM mail WHERE thread_id = ? OR id = ? '
                        'ORDER BY date DESC LIMIT 1', [ref, ref]).fetchone()
        if not r:
            words = [w.replace("'", '') for w in ref.split() if w]
            cond = ' AND '.join(f"(coalesce(from_name, '') || ' ' || from_addr || ' ' || subject) ILIKE '%{w}%'" for w in words)
            r = con.execute(f"SELECT thread_id, subject, from_addr, from_name, body_text FROM mail WHERE direction = 'in' "
                            f"AND {cond} ORDER BY date DESC LIMIT 1").fetchone()
        if not r:
            if not to:
                raise Err(f'No conversation with "{ref}". For a new email, give --to ADDRESS (for example from the leads '
                          'sheet) and --subject.')
        else:
            to = to or r[2]
            subject = subject or ('Re: ' + r[1] if not r[1].lower().startswith('re:') else r[1])
            context = f'Their last email ({r[3] or r[2]}):\n{(r[4] or "")[:1500]}'
    if not to:
        raise Err('Say who the draft is to: --reply-to a conversation, or --to ADDRESS.')
    schema = {'type': 'object', 'properties': {'body': {'type': 'string'}}, 'required': ['body']}
    body = rs._nine([{'role': 'user', 'content': f'Write a short, polite email body (no subject line) from me to {to}. '
                      f'{a.ask}\n{context}\nSign off as "Me".'}], schema, max_tokens=400)['body']
    return Result(kind='text', text=f'Would draft (not saved):\nTo: {to}\nSubject: {subject or "(none)"}\n\n{body}')


# ---- explain: the man page, with real dates ----

def explain(con, resource=None):
    today = rs.now().date()
    lw = rs.day_range('last week')
    if not resource:
        lines = ['What you can list (idli list RESOURCE), one row per item:']
        for k, r in rs.RESOURCES.items():
            lines.append(f'- {k}: {r["about"]}')
        lines.append('- rows --sheet NAME: the rows of one spreadsheet (`idli list sheets` shows the names)')
        views = con.execute('SELECT name, about FROM views').fetchall()
        for n, ab in views:
            lines.append(f'- {n}: your view. {ab}')
        lines += ['', 'Examples:',
                  f'  idli list mail --since yesterday --where "direction = \'in\' and not is_bulk"',
                  f'  idli count files --in "NDSA fixity study"',
                  f'  idli list files --by kind',
                  f'  idli list events --on "next monday"   (= {rs.day_range("next monday")[0]})',
                  '  idli define urgent --on mail --ask "Does this email ask me to act soon?" --answers yes,no',
                  '  idli judge mail --def urgent --where "not is_bulk"   then   idli list threads --label urgent',
                  'More: idli explain mail (or any resource).']
        return '\n'.join(lines)
    if resource == 'rows':
        return 'rows --sheet NAME: the rows of one spreadsheet. `idli describe sheet NAME` lists its columns.'
    if resource not in rs.RESOURCES:
        raise Err(f'No resource "{resource}". `idli explain` lists them.')
    r = rs.RESOURCES[resource]
    cols = rs.columns(con, resource)
    ex = {
        'mail': [f'idli list mail --since "last week" --where "direction = \'in\' and not is_bulk"   (last week = {lw[0]} to {lw[1] - dt.timedelta(days=1)})',
                 "idli list mail --search \"reading programme\"",
                 "idli count mail --since 7d --by is_bulk,is_calendar_notice",
                 "idli list mail --where \"from_addr ~ 'linkedin'\""],
        'threads': ["idli list threads --where \"last_direction = 'in' and not is_bulk\"",
                    "idli list threads --label urgent    (after define and judge)"],
        'events': [f'idli list events --on yesterday   (= {today - dt.timedelta(days=1)})',
                   "idli list events --since today --where \"guests ~ '@'\"",
                   "idli list events --where \"my_response = 'declined'\""],
        'files': ['idli list files --in "NDSA fixity study"', 'idli count files --in "Strategy Classics" --where "kind = \'pdf\'"',
                  'idli list files --by kind', "idli list files --search caste"],
        'folders': ['idli list folders', "idli list folders --where \"path ~ 'Strategy'\""],
        'photos': ['idli list photos', 'idli define has_people --on photo --ask "Are there people in this photo?"'],
        'sheets': ['idli list sheets', 'idli describe sheet "Leads (test)"', 'idli list rows --sheet "Leads (test)"'],
    }.get(resource, [])
    return (f'{resource}: {r["about"]}.\nFields: {", ".join(cols)}.\n'
            f'Dates filter on {r["date"]}. --where takes SQL-like conditions; field ~ \'x\' means contains; '
            f"label.NAME = 'yes' uses your definitions.\nExamples:\n" + '\n'.join('  ' + e for e in ex))


# ---- ask: the left chat. The mapper picks commands; Idli runs them; the 9B words a short reply ----

GRAMMAR_HEAD = """You turn a person's request into `idli` commands that read their own Google data from a local store.
Answer with JSON only: {"commands": ["idli ...", ...]} (add "continue": true to see results before the next
commands) or {"cannot": "<one sentence>", "needs": "<kind>"}.

Commands (read only unless said):
  idli list RESOURCE [--where COND] [--since D] [--until D] [--on D] [--search WORDS] [--label DEF[=VAL]]
                     [--in FOLDER] [--sheet NAME] [--by FIELDS] [--fields F] [--order "F desc"] [--limit N]
  idli count RESOURCE [same filters]          how many
  idli get mail|thread|event|file REF          one item in full (REF: id, or words from its name/subject)
  idli describe file|sheet REF                 pages, or columns with examples
  idli read file REF                           a PDF/document's text
  idli summarise file REF [--question Q]       a summary of one file
  idli define NAME --on mail|event|file|photo --ask "QUESTION" --answers a,b,c   the person's own category
  idli judge RESOURCE --def NAME [--where COND] [--since D]                       label each row (slow: ~1 s a row)
  idli query "SELECT ..."                      read-only SQL for joins and anything else
  idli draft mail --reply-to REF --ask "WHAT TO SAY"   preview only; nothing is saved or sent
  idli date PHRASE                             what "next monday", "last week" mean (for questions about dates)
Dates D: today, yesterday, tomorrow, 7d, last week, this week, next week, monday, next monday, YYYY-MM-DD.
COND is SQL over the resource's fields; field ~ 'x' means contains; label.NAME = 'yes' uses a definition.

Rules:
- Use only the resources and fields listed below. Prefer list/count with flags; use query only for joins.
- A category the person has in mind ("urgent", "about caste", "funder meeting", "photos with people") that is not
  a field: define it (a clear yes/no question), judge the relevant rows (narrow first with --where, --in or
  --since so fewer rows are judged), then list with --label. Reuse an existing definition when it fits.
- A greeting, or "what can you do / what can you see": idli explain (it lists what Idli can read).
- Exact words or names the person gives: --search.  "How many": count.  "By X" or a breakdown: --by.
- Follow-ups refer to the previous answer (shown below with its rows and ids): use the ids, or narrow the
  previous command.
- Moving, renaming, sending, booking, posting or deleting are not available: answer cannot, needs "new_write_action".
  Drafting an email reply is available as a preview.
- WhatsApp, Slack, Mattermost, Canva, LinkedIn, Amazon, funder portals are not connected: cannot, needs
  "new_connector".
- If the data simply isn't there, cannot, needs "not_in_data". Prefer a reasonable reading of a vague request
  (and act on it) over asking back; use cannot, needs "clarify", only when no reading makes sense.
- When a later command needs a value from an earlier result (an id, a name, a thread), don't guess or write a
  placeholder: give only the earlier commands with "continue": true. You'll see their results and give the rest.
- A period ("yesterday", "last week", "next Monday") is --on PERIOD. --since D means from D until now.
- Time of day: hour(start) >= 13 (after lunch), hour(date) < 12 (morning). Booleans: not is_bulk, is_unread.
"""


def grammar():
    lw = rs.day_range('last week')
    return GRAMMAR_HEAD + f"""
Examples (today is {rs.now():%A %Y-%m-%d}):
  "emails I got last week" -> idli list mail --on "last week" --where "direction = 'in'"
  "how many PDFs in Strategy Classics" -> idli count files --in "Strategy Classics" --where "kind = 'pdf'"
  "meetings next monday" -> idli list events --on "next monday"
  "urgent emails" -> idli define urgent --on mail --ask "Does this email ask me to act or reply soon?" --answers yes,no ;
                     idli judge mail --def urgent --where "direction = 'in' and not is_bulk" ; idli list threads --label urgent
  "leads who haven't replied" -> idli query "SELECT l.Name, l.Email FROM sheet_leads_x l WHERE lower(l.Email) NOT IN
                     (SELECT from_addr FROM mail WHERE direction = 'in')"   (use the real sheet table: idli list sheets)
"""


def menu(con, mask=None):
    m = mask or (lambda s: s)
    lines = ['Resources and fields:']
    for k, r in rs.RESOURCES.items():
        if k in ('labels',):
            continue
        lines.append(f'- {k}: {r["about"]}. Fields: {", ".join(rs.columns(con, k))}' + _values(con, k))
    sheets = con.execute('SELECT name, columns, nrows, tbl FROM sheets ORDER BY name').fetchall()
    lines.append('- rows --sheet NAME. Sheets: ' + '; '.join(
        f'"{m(n)}" (SQL table {t}, {nr} rows; columns: {", ".join(m(c) for c in json.loads(cs)[:8])})' for n, cs, nr, t in sheets))
    folders = con.execute("SELECT path || CASE WHEN path = '' THEN '' ELSE '/' END || name FROM files "
                          "WHERE kind = 'folder' ORDER BY 1").fetchall()
    lines.append('Drive folders: ' + '; '.join(m(f[0]) for f in folders))
    defs = con.execute('SELECT name, max(version), any_value(on_kind), arg_max(ask, version) FROM definitions GROUP BY name').fetchall()
    if defs:
        lines.append('Definitions already made: ' + '; '.join(f'{n} (on {k}): {a}' for n, v, k, a in defs))
    views = con.execute('SELECT name, about FROM views').fetchall()
    if views:
        lines.append('Views: ' + '; '.join(f'{n}: {a}' for n, a in views))
    lines.append(f'Today is {rs.now():%A %Y-%m-%d}, time zone Asia/Kolkata. All data is from my own account '
                 f'({account()}); "account" is always that.')
    return '\n'.join(lines)


def _values(con, resource):
    """The values of short, few-valued text fields (direction: in, out), so filters use real values."""
    r = rs.RESOURCES[resource]
    if r.get('filter') or resource in ('definitions', 'sheets'):
        return ''
    out = []
    for c, t in con.execute(f'SELECT column_name, column_type FROM (DESCRIBE SELECT * FROM "{r["table"]}")').fetchall():
        if t != 'VARCHAR' or c in ('id', 'thread_id', 'account'):
            continue
        n, mx = con.execute(f'SELECT count(DISTINCT "{c}"), max(length("{c}")) FROM "{r["table"]}"').fetchone()
        if n and n <= 10 and (mx or 0) <= 24:
            vals = [v[0] for v in con.execute(f'SELECT DISTINCT "{c}" FROM "{r["table"]}" ORDER BY 1').fetchall()]
            out.append(f'{c} is one of: {", ".join(repr(v) for v in vals)}')
    return ('. ' + '; '.join(out)) if out else ''


def _remote(system, user, max_tokens=5000):
    from lib import minisql
    import urllib.request
    # reasoning is capped: uncapped, it used all of 1500 tokens on workflow asks and the JSON came back cut off
    body = {'model': minisql.MODEL, 'temperature': 0, 'max_tokens': max_tokens, 'response_format': {'type': 'json_object'},
            'reasoning': {'effort': 'low'},
            'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]}
    if 'openrouter.ai' in minisql.URL:
        body['provider'] = {'data_collection': 'deny'}
    req = urllib.request.Request(minisql.URL, json.dumps(body).encode(), {
        'Content-Type': 'application/json', 'Authorization': 'Bearer ' + minisql._key(), 'User-Agent': 'idli-scaffold/1'})
    for attempt in (0, 1):
        with urllib.request.urlopen(req, timeout=120) as r:
            txt = json.load(r)['choices'][0]['message']['content'] or ''
        m = re.search(r'\{.*\}', txt, re.S)
        txt = m.group(0) if m else txt
        for t in (txt, txt.replace("\\'", "'")):  # the model sometimes writes \' inside JSON strings
            try:
                return json.loads(t)
            except ValueError:
                pass
        log = os.environ.get('IDLI_MAPPER_LOG')
        if log:
            open(log, 'a').write(json.dumps({'bad_json': txt[:4000]}) + '\n')
    raise ValueError('The mapper did not answer in JSON twice.')


PLAN_SCHEMA = {'type': 'object', 'properties': {'commands': {'type': 'array', 'items': {'type': 'string'}},
                                                'continue': {'type': 'boolean'},
                                                'cannot': {'type': 'string'}, 'needs': {'type': 'string'}}}


def map_question(con, question, history, mapper='remote', data_dir=None, failed=None, so_far=None):
    """The plan: idli commands for this question. Remote mapping sees masked text only. `failed` is a repair
    round: the commands that failed and why, so the mapper corrects them."""
    ctx = []
    for h in history[-2:]:
        ctx.append(f'Earlier question: {h["q"]}\nCommands run: {json.dumps(h.get("commands", []))}\n'
                   f'Result shown:\n{h.get("shown", "")[:1500]}')
    note = rs.dates_note(question)
    user = (menu(con) + '\n\n' + ('\n\n'.join(ctx) + '\n\n' if ctx else '') +
            f'Request: {question}' + (f'\nDates in this request: {note}' if note else ''))
    if so_far:
        user += ('\n\nYou already ran these for this request; their results:\n' + so_far[:5000] +
                 '\nNow give the remaining commands (or none, as {"commands": []}, if the results already answer it).')
    if failed:
        user += ('\n\nYour commands for this request failed:\n' + '\n'.join(failed) +
                 '\nGive the full corrected list of commands (same JSON shape).')
    if mapper == 'remote':
        from lib import privacy
        user = privacy.mask_account_text(data_dir, user)  # once, over everything that leaves (0.2 s)
        plan = _remote(grammar(), user)
        from lib import home
        plan = home.rehydrate(data_dir, plan)
    else:
        plan = rs._nine([{'role': 'system', 'content': grammar()}, {'role': 'user', 'content': user}], PLAN_SCHEMA,
                        max_tokens=1500, timeout=180)
    return plan, len(user)


STYLE = """You are Idli, answering the person in a chat. Write 1-3 short sentences that answer what they just said,
using only the result below. Rules:
- If they corrected you or pointed at something ("no, the one from...", "the second one"), acknowledge that first in
  a few words, then answer.
- Don't repeat the wording of your previous reply. Don't list the rows (they are shown under your words); mention
  at most two items by name.
- Don't mention how it was worked out (seconds, judging, definitions, commands) unless they asked. Never tell
  them to run a command. If a step failed, say in plain words what you couldn't find.
- Only use numbers that appear in the result. If the result is empty, say so plainly and suggest one next step.
- Talk like a colleague about their data ("4 files are in the fixity folder"), never about rows or results.
- Don't end with a question or an offer ("Would you like...") unless their request was unclear.
- Plain words, no headings, no bullet points, no "As an AI"."""


NUM = re.compile(r'(?<![\w.])\d+(?:[.,]\d+)?(?![\w])')


def compose(question, shown, history, plan_note=''):
    prev = history[-1]['reply'] if history else ''
    schema = {'type': 'object', 'properties': {'reply': {'type': 'string'}}, 'required': ['reply']}
    msg = (f'Their previous question: {history[-1]["q"]}\nYour previous reply: {prev}\n\n' if history else '') + \
          f'What they said now: {question}\n{plan_note}\nResult:\n{shown[:4000]}'
    try:
        reply = rs._nine([{'role': 'system', 'content': STYLE}, {'role': 'user', 'content': msg}], schema,
                         max_tokens=220)['reply'].strip()
    except Exception:
        return '', 'compose_failed'
    allowed = set(NUM.findall(shown)) | set(NUM.findall(question)) | {'1', '2', '3'}
    allowed |= {str(len(shown.splitlines()))}
    bad = [n for n in NUM.findall(reply) if n not in allowed and n.replace(',', '') not in allowed]
    if bad:
        return '', 'number_not_in_result:' + ','.join(bad)
    return reply, ''


def ask(con, question, history, mapper='remote', data_dir=None, show_commands=True):
    """One turn. Returns a dict with the reply and everything the bench needs."""
    t0 = time.time()
    rec = {'q': question, 'mapper': mapper}
    try:
        plan, rec['prompt_chars'] = map_question(con, question, history, mapper, data_dir)
    except Exception as e:
        plan = {'cannot': f'I could not work out the steps ({type(e).__name__}).', 'needs': 'mapper_failed'}
    rec['map_s'] = round(time.time() - t0, 2)
    rec['plan'] = plan
    if not plan.get('commands'):
        needs = plan.get('needs', 'clarify')
        why = plan.get('cannot') or 'I am not sure what to look up.'
        nxt = {'new_connector': ' The Builder can ask for a connector for it; until then I only see your Google account.',
               'new_write_action': ' I can read and show previews (a draft reply, for example), but changing things '
                                   'in your accounts needs an action our team adds.'}.get(needs, '')
        rec.update(reply=why.rstrip() + nxt, shown='', commands=[], needs=needs, total_s=round(time.time() - t0, 2))
        return rec
    shown_parts, cmds, judge_s, errors = run_plan(con, plan)
    if errors:  # one repair round: the mapper sees what failed and why
        try:
            plan2, _ = map_question(con, question, history, mapper, data_dir, failed=errors)
            if plan2.get('commands'):
                rec['repaired'] = plan = plan2
                shown_parts, cmds, judge_s2, errors = run_plan(con, plan2)
                judge_s += judge_s2
        except Exception:
            pass
    rounds = 0
    while plan.get('continue') and rounds < 2 and not errors:  # the mapper asked to see results first
        rounds += 1
        so_far = '\n'.join(f'$ {c}\n{p}' for c, p in zip(cmds, shown_parts))
        try:
            plan, _ = map_question(con, question, history, mapper, data_dir, so_far=so_far)
        except Exception:
            break
        if not plan.get('commands'):
            break
        more_parts, more_cmds, js, errors = run_plan(con, plan)
        shown_parts += more_parts; cmds += more_cmds; judge_s += js
    rec['rounds'] = rounds
    shown = '\n\n'.join(shown_parts)
    t1 = time.time()
    reply, why = compose(question, shown, history)
    rec['compose_s'] = round(time.time() - t1, 2)
    rec['compose_fallback'] = why
    final_rows = shown_parts[-1] if shown_parts else ''
    body = (reply + '\n\n' if reply else '') + (final_rows if final_rows else '')
    if show_commands:
        body += '\n\n(Ran: ' + ' ; '.join(cmds) + ')'
    rec.update(reply=body.strip(), words=reply, shown=shown, commands=cmds, errors=errors, judge_s=round(judge_s, 1),
               total_s=round(time.time() - t0, 2))
    return rec


PLACEHOLDER = re.compile(r'<[A-Za-z_][A-Za-z0-9_ .\-]{1,60}>')


def run_plan(con, plan):
    shown_parts, cmds, judge_s, errors = [], [], 0.0, []
    for c in plan['commands'][:6]:
        if PLACEHOLDER.search(c):  # it needs a value from the results so far: stop here and ask for the rest
            plan['continue'] = True
            break
        try:
            argv = shlex.split(c)
        except ValueError:
            errors.append(f'{c}: could not read the command')
            continue
        cmds.append(c)
        try:
            r = run_argv(con, argv)
        except (Err, ValueError) as e:
            errors.append(f'{c}: {e}')
            shown_parts.append(f'(That step failed: {e})')
            continue
        except Exception as e:
            errors.append(f'{c}: {type(e).__name__}: {e}')
            shown_parts.append(f'(That step failed: {type(e).__name__})')
            continue
        if argv[1:2] == ['judge'] or argv[:1] == ['judge']:
            try:
                judge_s += json.loads(r.note)['seconds']
            except Exception:
                pass
        if argv[1:2] in (['define'], ['judge']) or argv[:1] in (['define'], ['judge']):
            shown_parts.append(r.render())
        else:
            shown_parts.append(r.render())
    return shown_parts, cmds, judge_s, errors


NINE_BF16_URL = os.environ.get('IDLI_9B_BF16_URL', 'http://127.0.0.1:8292')  # idli-9b-bf16 on the DGX


def use_nine(mapper):
    """Which 9B this run talks to, for mapping, wording and judging. `nine` is the full (BF16) model; anything else
    keeps the served, compressed one (Q5, port 8291 on the DGX, or silo from a laptop). IDLI_9B_URL, if set, wins."""
    if mapper == 'nine' and not os.environ.get('IDLI_9B_URL'):
        os.environ['IDLI_9B_URL'] = NINE_BF16_URL


def _session_path():
    return Path(sandbox()) / 'session.json'


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    con = rs.connect(sandbox())
    try:
        if argv[:1] == ['ask']:
            a = parser().parse_args(argv)
            use_nine(a.mapper)
            sp = _session_path()
            hist = [] if a.new or not sp.exists() else json.loads(sp.read_text())
            rec = ask(con, ' '.join(a.question), hist, a.mapper, data_dir=sandbox())
            hist.append({k: rec.get(k) for k in ('q', 'commands', 'shown', 'reply')})
            sp.write_text(json.dumps(hist[-6:], default=str))
            print(rec['reply'])
            return 0
        print(run_argv(con, argv).render(max_rows=50))
        return 0
    except (Err, ValueError) as e:
        print(f'idli: {e}', file=sys.stderr)
        return 2
    finally:
        con.close()


if __name__ == '__main__':
    sys.exit(main())
