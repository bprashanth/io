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


def _fetch_text(b, path):
    """fetch() a same-origin path in the profile's current tab; returns (status, text)."""
    res = b.evaluate("(async () => { const r = await fetch(%s, {credentials: 'include'}); "
                     "return {s: r.status, t: await r.text()}; })()" % json.dumps(path))
    return int(res['s']), res['t']


def _on(b, origin, url):
    """Make sure the tab is on this origin (fetch must be same-origin)."""
    try:
        here = b.evaluate('location.origin')
    except (ValueError, OSError, TimeoutError):
        here = ''
    if here != origin:
        b.open(url)


# ---- Gmail ----

def _ik(b):
    _on(b, 'https://mail.google.com', MAIL + '#inbox')
    for _ in range(20):
        ik = b.evaluate('(window.GLOBALS || [])[9] || null')
        if ik:
            return ik
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
    _ik(b)
    status, xml = _fetch_text(b, '/mail/u/0/feed/atom')
    if status != 200:
        raise ValueError(f'Gmail did not give its mail feed ({status}).')
    return parse_feed(xml)


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
    ik = _ik(b)
    status, raw = _fetch_text(b, f'/mail/u/0/?ik={ik}&view=att&th={msg_id}&attid=0&disp=comp&safe=1&zw')
    if status != 200 or 'From:' not in raw[:20000]:
        raise ValueError(f'Gmail did not give that message ({status}).')
    return {'id': msg_id, **parse_message(raw.encode('utf-8', 'surrogateescape'))}


def compose_draft(b, to, subject, body, send=False):
    """Gmail's compose page, filled in, saved as a draft. send=True presses Send: only for rehearsals between a team's
    own test accounts (lib/routines.py checks that); a real account's mail is always left as a draft."""
    q = urllib.parse.urlencode({'view': 'cm', 'fs': '1', 'to': to, 'su': subject, 'body': body})
    b.open(MAIL + '?' + q)
    for _ in range(30):  # the compose box needs a moment; Gmail saves a draft once it has a change to save
        if b.evaluate("!!document.querySelector('div[aria-label=\"Message Body\"], div[role=textbox]')"):
            break
        time.sleep(0.5)
    else:
        raise ValueError('Gmail did not open its compose box.')
    if send:
        b.read()
        b.click(text='Send')
        time.sleep(3)
        return {'sent': True}
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
            return {'draft': True}
        time.sleep(0.5)
    raise ValueError('Gmail did not say the draft was saved.')


def drafts_count(b, subject):
    """How many drafts have this subject (Gmail's drafts search page, read by its result rows)."""
    b.open(MAIL + '#search/' + urllib.parse.quote(f'in:drafts subject:"{subject}"'))
    time.sleep(2.5)
    return int(b.evaluate("document.querySelectorAll('div[role=main] tr.zA').length") or 0)


# ---- Sheets ----

def sheet_rows(b, sheet_id, gid=None):
    """A Google Sheet's tab as a list of dicts (first row as headings), by its CSV export address."""
    if not re.fullmatch(r'[A-Za-z0-9_-]{20,80}', str(sheet_id)):
        raise ValueError('Not a Google Sheet id.')
    _on(b, 'https://docs.google.com', f'https://docs.google.com/spreadsheets/d/{sheet_id}/edit')
    path = f'/spreadsheets/d/{sheet_id}/export?format=csv' + (f'&gid={int(gid)}' if gid is not None else '')
    status, text = _fetch_text(b, path)
    if status != 200 or text.lstrip().startswith('<'):
        raise ValueError(f'Google Sheets did not give that sheet ({status}). Is it in this account?')
    return list(csv.DictReader(io.StringIO(text)))


# ---- Calendar ----

def calendar_secret_ical(b, calendar_email):
    """The calendar's secret iCal address, read from its settings (Google shows a warning first: answered OK)."""
    import base64
    cid = base64.b64encode(calendar_email.encode()).decode().rstrip('=')
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
    b.open('https://calendar.google.com/calendar/render?' + q)
    for _ in range(30):
        if b.evaluate("[...document.querySelectorAll('button,[role=button]')].some(e => e.textContent.trim() === 'Save')"):
            break
        time.sleep(0.5)
    else:
        raise ValueError('Calendar did not open its new-event page.')
    _press(b, 'Save')
    for _ in range(20):  # "Send invitation emails to Google Calendar guests?"
        if _press(b, 'Send', must=False):
            break
        if not b.evaluate("location.href.includes('eventedit')"):
            break
        time.sleep(0.5)
    time.sleep(2)
    if b.evaluate("location.href.includes('eventedit')"):
        raise ValueError('Calendar did not save the event.')
    return {'saved': True}


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
