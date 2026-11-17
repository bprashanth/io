"""Google through a signed-in Chrome profile, by stable addresses, not by reading the page (narrative/BUILDER_JOURNEY.md,
"Routines").

Each call takes a lib.chromectl.Browser for one profile. Reads run fetch() inside the profile's own Google session, so
nothing here holds a password or a cookie:
- mail_feed: the inbox's unread mail (Gmail's Atom feed, /mail/u/0/feed/atom);
- mail_message: one message's original (the "Download original" address), parsed with Python's email module;
- sheet_rows: a Google Sheet as rows (its CSV export address);
- ical_busy: busy times from a calendar's secret iCal address (no browser needed);
- free_slots: open times between the busy ones.
Writes open Google's own prefilled pages, and a person stays in charge of what leaves:
- compose_draft: Gmail's compose page with to/subject/body filled in, saved as a draft (the person presses Send);
- calendar_event: Calendar's new-event page filled in, then Save and "Send" (invitations), after the person approved;
- calendar_secret_ical: reads a calendar's secret iCal address from its settings, once, at setup.
"""
import csv
import datetime as dt
import email
import email.policy
import io
import json
import re
import time
import urllib.parse
import urllib.request
from email.utils import parseaddr, parsedate_to_datetime

MAIL = 'https://mail.google.com/mail/u/0/'


def _tab(b, origin, url):
    """This profile's tab on a Google site (origin), opened at url if there is none. Every call below works in its
    own site's tab, so a Gmail read never runs in the Calendar tab."""
    for t in b._pages():
        if str(t.get('url', '')).startswith(origin + '/'):
            return b.pin(t)
    t = b._http('/json/new?' + urllib.parse.quote(url, safe=':/?#[]@!$&\'()*+,;=%'), 'PUT')
    for _ in range(60):
        try:
            if b.evaluate('document.readyState', target=t) == 'complete':
                break
        except (ValueError, OSError, TimeoutError, ConnectionError):
            pass
        time.sleep(0.5)
    time.sleep(1)
    return b.pin(t)


def _fetch_text(b, path, target):
    """fetch() a same-origin path in that tab; returns (status, text)."""
    res = b.evaluate("(async () => { try { const r = await fetch(%s, {credentials: 'include'}); "
                     "return {s: r.status, t: await r.text()}; } catch (e) { return {s: 0, t: String(e)}; } })()"
                     % json.dumps(path), target=target)
    return int(res['s']), res['t']


# ---- Gmail ----

def _ik(b):
    """Gmail's tab and its account key (ik)."""
    t = _tab(b, 'https://mail.google.com', MAIL + '#inbox')
    for _ in range(40):
        ik = b.evaluate('(window.GLOBALS || [])[9] || null', target=t)
        if ik:
            return t, ik
        time.sleep(0.5)
    raise ValueError('Gmail did not load in this profile. Is it signed in?')


def parse_feed(xml):
    """Gmail's Atom feed as [{id, from, name, subject, summary, issued}] (newest first)."""
    out = []
    for e in re.findall(r'<entry>(.*?)</entry>', xml, re.S):
        def tag(t, s=e):
            m = re.search(r'<%s>(.*?)</%s>' % (t, t), s, re.S)
            return _unxml(m.group(1)) if m else ''
        mid = re.search(r'message_id=([0-9a-f]+)', e)
        author = re.search(r'<author>(.*?)</author>', e, re.S)
        out.append({'id': mid.group(1) if mid else '', 'from': tag('email', author.group(1) if author else '').lower(),
                    'name': tag('name', author.group(1) if author else ''), 'subject': tag('title'),
                    'summary': tag('summary'), 'issued': tag('issued')})
    return [m for m in out if m['id']]


def _unxml(s):
    return (s.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
            .replace('&amp;', '&')).strip()


def mail_feed(b):
    """Unread mail in the inbox (Gmail's feed lists only unread mail, at most 20)."""
    t, _ = _ik(b)
    status, xml = _fetch_text(b, '/mail/u/0/feed/atom', t)
    if status != 200:
        raise ValueError(f'Gmail did not give its mail feed ({status}).')
    return parse_feed(xml)


def mail_search(b, senders, days=7):
    """Mail threads with a message from any of these senders in the last `days`, read or unread, as
    [{"id": <the thread's last message>, "thread"}]. Gmail's own search, read from its result rows' message ids."""
    senders = [x for x in dict.fromkeys(str(x).strip().lower() for x in senders) if re.fullmatch(r'[^\s()"]+@[^\s()"]+', x)]
    out, seen = [], set()
    for i in range(0, len(senders), 20):
        q = 'from:(' + ' OR '.join(senders[i:i + 20]) + f') newer_than:{int(days)}d'
        t, _ = _ik(b)
        # the same search address twice doesn't search again: go to the inbox first, so Gmail asks its server anew
        b.open(MAIL + '#inbox')
        time.sleep(1)
        b.open(MAIL + '#search/' + urllib.parse.quote(q))
        rows, last = None, None
        for _ in range(40):  # until the result list has drawn and stopped changing
            time.sleep(0.5)
            now = b.evaluate("""(() => { const main = document.querySelector('div[role=main]');
              if (!main || !/^Search results/.test(document.title)) return null;
              const r = [...main.querySelectorAll('tr.zA')].map(tr => { const s = tr.querySelector(
              '[data-legacy-last-non-draft-message-id]'); return s ? [s.getAttribute('data-legacy-last-non-draft-message-id'),
              s.getAttribute('data-legacy-thread-id')] : null; }).filter(Boolean);
              const empty = /No messages matched/i.test(main.innerText); return {r, empty}; })()""")
            if now and (now['r'] or now['empty']):
                if now == last:
                    rows = now['r']
                    break
                last = now
        for mid, th in rows or (last or {}).get('r', []):
            if mid and mid not in seen:
                seen.add(mid)
                out.append({'id': mid, 'thread': th})
    return out


QUOTE = re.compile(r'(?im)^(on .{0,200}wrote:\s*$|-{2,} ?original message|from: .*\n(sent|date): )')


def parse_message(raw):
    """A message's original as {from, name, to, subject, date, message_id, in_reply_to, text, new_text}.
    new_text drops the quoted earlier mail ("On ... wrote:" and lines starting with ">")."""
    msg = email.message_from_bytes(raw if isinstance(raw, bytes) else raw.encode(), policy=email.policy.default)
    body = msg.get_body(preferencelist=('plain', 'html'))
    text = body.get_content() if body else ''
    if body is not None and body.get_content_type() == 'text/html':
        text = re.sub(r'(?s)<(script|style).*?</\1>', ' ', text)
        text = re.sub(r'<br\s*/?>|</p>|</div>', '\n', text)
        text = _unxml(re.sub(r'<[^>]+>', '', text))
    m = QUOTE.search(text)
    new = text[:m.start()] if m else text
    new = '\n'.join(l for l in new.splitlines() if not l.lstrip().startswith('>')).strip()
    name, addr = parseaddr(str(msg.get('From', '')))
    try:
        date = parsedate_to_datetime(str(msg.get('Date'))).isoformat()
    except (TypeError, ValueError):
        date = ''
    return {'from': addr.lower(), 'name': name, 'to': str(msg.get('To', '')), 'subject': str(msg.get('Subject', '')),
            'date': date, 'message_id': str(msg.get('Message-ID', '')), 'in_reply_to': str(msg.get('In-Reply-To', '')),
            'text': text.strip()[:20000], 'new_text': new[:8000]}


def mail_message(b, msg_id):
    """One message by its Gmail id (from mail_feed), parsed."""
    if not re.fullmatch(r'[0-9a-f]{6,24}', str(msg_id)):
        raise ValueError('Not a Gmail message id.')
    t, ik = _ik(b)
    status, raw = _fetch_text(b, f'/mail/u/0/?ik={ik}&view=att&th={msg_id}&attid=0&disp=comp&safe=1&zw', t)
    if status != 200 or 'From:' not in raw[:20000]:
        raise ValueError(f'Gmail did not give that message ({status}).')
    return {'id': msg_id, **parse_message(raw.encode('utf-8', 'surrogateescape'))}


def compose_draft(b, to, subject, body, send=False):
    """Gmail's compose page, filled in, saved as a draft. send=True presses Send: only for rehearsals between a team's
    own test accounts (lib/routines.py checks that); a real account's mail is always left as a draft."""
    if not send and drafts_count(b, subject):  # a retry after a run that stopped: the draft is already there
        return {'draft': True, 'already': True}
    q = urllib.parse.urlencode({'view': 'cm', 'fs': '1', 'to': to, 'su': subject, 'body': body})
    _tab(b, 'https://mail.google.com', MAIL + '#inbox')
    b.open(MAIL + '?' + q)
    for _ in range(30):  # the compose box needs a moment; Gmail saves a draft once it has a change to save
        if b.evaluate("!!document.querySelector('div[aria-label=\"Message Body\"], div[role=textbox]')"):
            break
        time.sleep(0.5)
    else:
        raise ValueError('Gmail did not open its compose box.')
    if send:  # rehearsals between test accounts only: press Gmail's Send, then make sure it went
        for attempt in range(3):
            time.sleep(1.5)
            spot = b.evaluate("""(() => { const o = [...document.querySelectorAll('div[role=button]')].find(e =>
              /^Send/.test(e.getAttribute('aria-label') || e.getAttribute('data-tooltip') || '') &&
              e.getBoundingClientRect().width > 0); if (!o) return null; const r = o.getBoundingClientRect();
              return {x: r.x + r.width / 2, y: r.y + r.height / 2}; })()""")
            if spot:
                b._mouse(spot['x'], spot['y'])
            for _ in range(20):
                if re.search(r'(?i)message sent', b.evaluate('document.body.innerText') or '') or not b.evaluate(
                        "!!document.querySelector('div[aria-label=\"Message Body\"]')"):
                    return {'sent': True}
                time.sleep(0.3)
        raise ValueError('Gmail did not send the message.')
    # Gmail saves a prefilled message once it is edited: add and remove a space at the end of the body
    b.evaluate("""(() => { const box = document.querySelector('div[aria-label="Message Body"], div[role=textbox]');
      box.focus(); const sel = getSelection(); sel.selectAllChildren(box); sel.collapseToEnd(); })()""")
    c = b._cdp()
    try:
        c.call('Input.insertText', {'text': ' '})
        c.call('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Backspace', 'code': 'Backspace',
                                          'windowsVirtualKeyCode': 8})
        c.call('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Backspace', 'code': 'Backspace',
                                          'windowsVirtualKeyCode': 8})
    finally:
        c.close()
    for _ in range(30):
        txt = b.evaluate('document.body.innerText') or ''
        if re.search(r'(?i)draft saved|saved to drafts', txt):
            break
        time.sleep(0.5)
    else:
        raise ValueError('Gmail did not say the draft was saved.')
    # "Draft saved" shows before Gmail has finished: leaving at once lost the draft (laptop, 2026-11-18). Wait, then
    # look in Drafts; if it isn't there, fail so the routine tries again next run instead of marking it done.
    time.sleep(5)
    for _ in range(6):  # Drafts' search catches up within seconds
        if drafts_count(b, subject):
            return {'draft': True}
        time.sleep(4)
    raise ValueError('The draft did not reach Drafts. It will be tried again on the next run.')


def drafts_count(b, subject):
    """How many drafts have this subject (for checks). Gmail's search ignores a leading "Re:"."""
    subject = re.sub(r'(?i)^\s*(re|fwd?):\s*', '', subject)
    _tab(b, 'https://mail.google.com', MAIL + '#inbox')
    b.open(MAIL + '#inbox')
    time.sleep(1)
    b.open(MAIL + '#search/' + urllib.parse.quote(f'in:drafts subject:"{subject}"'))
    last = None
    for _ in range(20):
        time.sleep(0.5)
        if not str(b.evaluate('document.title')).startswith('Search results'):
            continue
        n = int(b.evaluate("document.querySelectorAll('div[role=main] tr.zA').length") or 0)
        if n == last:
            return n
        last = n
    return last or 0


# ---- Sheets ----

def sheet_rows(b, sheet_id, gid=None):
    """A Google Sheet's tab as a list of dicts (first row as headings), by its CSV export address."""
    if not re.fullmatch(r'[A-Za-z0-9_-]{20,80}', str(sheet_id)):
        raise ValueError('Not a Google Sheet id.')
    t = _tab(b, 'https://docs.google.com', f'https://docs.google.com/spreadsheets/d/{sheet_id}/edit')
    # gviz answers on docs.google.com itself; the export address redirects to another site, which fetch can't follow
    path = f'/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv' + (f'&gid={int(gid)}' if gid is not None else '')
    status, text = _fetch_text(b, path, t)
    if status != 200 or text.lstrip().startswith('<'):
        raise ValueError(f'Google Sheets did not give that sheet ({status}). Is it in this account?')
    return list(csv.DictReader(io.StringIO(text)))


# ---- Calendar ----

def calendar_secret_ical(b, calendar_email):
    """The calendar's secret iCal address, read from its settings (Google shows a warning first: answered OK)."""
    import base64
    cid = base64.b64encode(calendar_email.encode()).decode().rstrip('=')
    _tab(b, 'https://calendar.google.com', 'https://calendar.google.com/calendar/u/0/r')
    b.open('https://calendar.google.com/calendar/u/0/r/settings/calendar/' + cid)
    time.sleep(3)
    find = """(() => { const lab = [...document.querySelectorAll('*')].find(e => e.children.length === 0 &&
      e.textContent.trim() === 'Secret address in iCal format'); if (!lab) return null;
      let box = lab; for (let i = 0; i < 6 && box; i++) { const v = [...box.querySelectorAll('*')].find(e =>
      e.children.length === 0 && e.textContent.trim() === 'visibility'); if (v) { const t = v.closest('button,[role=button]')
      || v; t.scrollIntoView({block: 'center', inline: 'center'}); const r = t.getBoundingClientRect();
      return {x: r.x + r.width / 2, y: r.y + r.height / 2}; } box = box.parentElement; } return null; })()"""
    value = """[...document.querySelectorAll('*')].filter(e => e.children.length === 0).map(e => (e.value ||
      e.textContent || '').trim()).find(v => /^https:\\/\\/calendar\\.google\\.com\\/calendar\\/ical\\/.*\\/private-/.test(v))
      || null"""
    for _ in range(3):
        url = b.evaluate(value)
        if url:
            return url
        spot = b.evaluate(find)
        if spot:
            b._mouse(spot['x'], spot['y'])
            time.sleep(1.5)
        ok = b.evaluate("""(() => { const o = [...document.querySelectorAll('button,[role=button]')].find(e =>
          e.textContent.trim() === 'OK'); if (!o) return null; const r = o.getBoundingClientRect();
          return {x: r.x + r.width / 2, y: r.y + r.height / 2}; })()""")
        if ok:
            b._mouse(ok['x'], ok['y'])
            time.sleep(1.5)
    raise ValueError('Could not read the calendar\'s secret address from its settings.')


def _ics_time(value, params):
    """An iCal date or date-time as an aware datetime (UTC 'Z', a TZID, or floating = local)."""
    from zoneinfo import ZoneInfo
    v = value.strip()
    if re.fullmatch(r'\d{8}', v):
        d = dt.datetime.strptime(v, '%Y%m%d')
        return d.replace(tzinfo=_local_tz()), True
    d = dt.datetime.strptime(v.rstrip('Z'), '%Y%m%dT%H%M%S')
    if v.endswith('Z'):
        return d.replace(tzinfo=dt.timezone.utc), False
    tzid = re.search(r'TZID=([^;:]+)', params or '')
    try:
        return d.replace(tzinfo=ZoneInfo(tzid.group(1)) if tzid else _local_tz()), False
    except Exception:
        return d.replace(tzinfo=_local_tz()), False


def _local_tz():
    return dt.datetime.now().astimezone().tzinfo


def parse_ics_busy(text):
    """Busy (start, end) pairs from iCal text. Cancelled and transparent (free) events don't count. Repeating events
    count only on their first date (RRULE is not expanded; noted in narrative/BUILDER_JOURNEY.md)."""
    text = re.sub(r'\r?\n[ \t]', '', text)  # unfold long lines
    busy = []
    for ev in re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', text, re.S):
        props = {}
        for line in ev.strip().splitlines():
            m = re.match(r'([A-Z-]+)((?:;[^:]*)?):(.*)', line)
            if m:
                props.setdefault(m.group(1), (m.group(2), m.group(3)))
        if props.get('STATUS', ('', ''))[1].upper() == 'CANCELLED' or \
                props.get('TRANSP', ('', ''))[1].upper() == 'TRANSPARENT' or 'DTSTART' not in props:
            continue
        start, allday = _ics_time(props['DTSTART'][1], props['DTSTART'][0])
        if 'DTEND' in props:
            end, _ = _ics_time(props['DTEND'][1], props['DTEND'][0])
        else:
            end = start + (dt.timedelta(days=1) if allday else dt.timedelta(0))
        busy.append((start, end))
    return sorted(busy)


def ical_busy(url):
    if not re.match(r'https://calendar\.google\.com/calendar/ical/[^/]+/private-[0-9a-f]+/basic\.ics$', str(url)):
        raise ValueError('Not a secret Google Calendar iCal address.')
    with urllib.request.urlopen(url, timeout=30) as r:
        return parse_ics_busy(r.read().decode('utf-8', 'replace'))


def free_slots(busy, now=None, days=5, hours='10:00-17:00', minutes=30, count=3, weekdays=True, tz=None, gap=60):
    """Up to `count` open times of `minutes`, within working hours over the next `days`, not overlapping `busy`,
    at most one per day first (spread over days), starting on the hour or half hour, at least `gap` minutes ahead."""
    tz = tz or _local_tz()
    now = (now or dt.datetime.now(tz)).astimezone(tz)
    h0, h1 = [dt.time.fromisoformat(x) for x in hours.split('-')]
    length = dt.timedelta(minutes=minutes)
    found = []
    day, open_days = now.date(), 0
    for _ in range(days * 3):
        if open_days >= days:
            break
        if not weekdays or day.weekday() < 5:
            open_days += 1
            t = dt.datetime.combine(day, h0, tz)
            end_day = dt.datetime.combine(day, h1, tz)
            while t + length <= end_day:
                if t >= now + dt.timedelta(minutes=gap) and not any(s < t + length and t < e for s, e in busy):
                    found.append(t)
                t += dt.timedelta(minutes=30)
        day += dt.timedelta(days=1)
    spread, used = [], set()
    for t in found:  # one per day first
        if t.date() not in used:
            spread.append(t)
            used.add(t.date())
        if len(spread) == count:
            break
    for t in found:
        if len(spread) == count:
            break
        if t not in spread:
            spread.append(t)
    return sorted(spread)[:count]


def slot_label(t):
    """"Fri 20 Nov, 2:00 pm" (the wording offered to a lead)."""
    return t.strftime('%a %d %b, ') + t.strftime('%I:%M %p').lstrip('0').lower()


def calendar_event(b, title, start, minutes, guest, details=''):
    """Calendar's new-event page filled in; Save; then Send (invitations to the guest). Returns {'saved': True}."""
    end = start + dt.timedelta(minutes=minutes)
    f = '%Y%m%dT%H%M%SZ'
    q = urllib.parse.urlencode({'action': 'TEMPLATE', 'text': title, 'details': details, 'add': guest,
                                'dates': start.astimezone(dt.timezone.utc).strftime(f) + '/' +
                                end.astimezone(dt.timezone.utc).strftime(f)})
    _tab(b, 'https://calendar.google.com', 'https://calendar.google.com/calendar/u/0/r')
    b.open('https://calendar.google.com/calendar/render?' + q)
    for _ in range(30):
        if b.evaluate("[...document.querySelectorAll('button,[role=button]')].some(e => e.textContent.trim() === 'Save')"):
            break
        time.sleep(0.5)
    else:
        raise ValueError('Calendar did not open its new-event page.')
    time.sleep(2)  # the page keeps drawing (the Meet link) for a moment; a Save pressed too soon is lost
    for attempt in range(4):  # Save, answer "Send invitations?", and check the page closed; a tip can eat a click
        _close_tips(b)
        _press(b, 'Save', must=False)
        for _ in range(16):
            if _press(b, 'Send', must=False) or not b.evaluate("location.href.includes('eventedit')"):
                break
            time.sleep(0.5)
        time.sleep(2)
        if not b.evaluate("location.href.includes('eventedit')"):
            return {'saved': True}
    raise ValueError('Calendar did not save the event.')


TIPS = ('Got it', 'Dismiss', 'No thanks', 'Not now')


def _close_tips(b):
    """Google's one-time tips ("Manage Meet call settings ... Got it") dim the page and swallow the next click."""
    closed = False
    for label in TIPS:
        while _press(b, label, must=False):
            closed = True
    return closed


def _press(b, label, must=True):
    spot = b.evaluate("""(() => { const o = [...document.querySelectorAll('button,[role=button]')].filter(e =>
      e.textContent.trim() === %s && e.getBoundingClientRect().width > 0).pop(); if (!o) return null;
      const r = o.getBoundingClientRect(); return {x: r.x + r.width / 2, y: r.y + r.height / 2}; })()""" % json.dumps(label))
    if not spot:
        if must:
            raise ValueError(f'No "{label}" button on the page.')
        return False
    b._mouse(spot['x'], spot['y'])
    time.sleep(1.2)
    return True


def events_on(url, day):
    """Titles of events in a secret iCal feed on a date (for checks)."""
    with urllib.request.urlopen(url, timeout=30) as r:
        text = re.sub(r'\r?\n[ \t]', '', r.read().decode('utf-8', 'replace'))
    out = []
    for ev in re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', text, re.S):
        m = re.search(r'DTSTART([^:]*):(\S+)', ev)
        s = re.search(r'SUMMARY:(.*)', ev)
        if m:
            start, _ = _ics_time(m.group(2), m.group(1))
            if start.astimezone(_local_tz()).date() == day:
                out.append((start.astimezone(_local_tz()).isoformat(), s.group(1).strip() if s else ''))
    return out
