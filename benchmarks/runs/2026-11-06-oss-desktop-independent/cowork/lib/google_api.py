"""Google's own APIs (Gmail, Calendar, Sheets) with OAuth, per account (narrative/BUILDER_JOURNEY.md, "Routines").

Why APIs and not the web pages: driving Gmail and Calendar's pages needed a dozen fixes for page quirks in one
evening (2026-11-18): the wrong tab, a redirecting export, a lagging unread feed, a search that didn't refresh, a
Save lost while the page drew, tips over buttons, background tabs ignoring clicks, drafts not yet saved. The APIs
answer the same way every time.

Sign-in: Idli's own OAuth client ("Desktop app", ~/.config/idlisseus/io_oauth_client_gcp.json, never shown). The
consent page opens in the account's own Chrome profile, so the right signed-in account says yes. The app is
published but not verified by Google: the person clicks "Advanced", then "Go to Idli (unsafe)". An unverified app
can have at most 100 users. Each account's refresh token is kept in ~/.config/idlisseus/google-tokens/<email>.json
(0600), which Claude and the Builder can't read. Nothing here prints a token.
"""
import base64
import datetime as dt
import hashlib
import http.server
import json
import os
import re
import secrets
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/calendar.events',
          'https://www.googleapis.com/auth/calendar.freebusy',
          'https://www.googleapis.com/auth/spreadsheets.readonly']
HANDLED = 'Idli/handled'
EMAIL = re.compile(r'[^@\s/\\]+@[^@\s/\\]+\.[a-z]{2,}', re.I)


class SignInNeeded(ValueError):
    """The account has no token, or Google refused it (revoked, expired): the person signs in again."""


def _cfg():
    return Path(os.environ.get('IDLI_GOOGLE_CONFIG') or Path.home() / '.config' / 'idlisseus')


def client():
    p = _cfg() / 'io_oauth_client_gcp.json'
    try:
        c = json.loads(p.read_text())['installed']
        return c['client_id'], c['client_secret']
    except (OSError, ValueError, KeyError):
        raise ValueError('Idli\'s Google sign-in is not set up on this computer (its OAuth client file is missing).')


def token_file(email):
    if not EMAIL.fullmatch(str(email)):
        raise ValueError('Not an email address.')
    return _cfg() / 'google-tokens' / f'{str(email).lower()}.json'


def connected(email):
    return token_file(email).is_file()


def _save(email, tok):
    p = token_file(email)
    p.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(p.parent, 0o700)
    tmp = p.with_suffix('.tmp')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(tok, f)
    os.replace(tmp, p)


def _post_form(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(),
                                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return {'error': json.load(e).get('error', 'http_%d' % e.code)}
        except ValueError:
            return {'error': 'http_%d' % e.code}


TOKEN_URL = 'https://oauth2.googleapis.com/token'
AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'


# ---- consent ----

def consent_url(email, port, state, challenge):
    cid, _ = client()
    return AUTH_URL + '?' + urllib.parse.urlencode({
        'client_id': cid, 'redirect_uri': f'http://127.0.0.1:{port}/', 'response_type': 'code',
        'scope': ' '.join(SCOPES), 'access_type': 'offline', 'prompt': 'consent', 'login_hint': email,
        'state': state, 'code_challenge': challenge, 'code_challenge_method': 'S256'})


def connect(email, open_url, timeout=600):
    """Sign this account in to Idli's Google app: a one-time page on 127.0.0.1 waits for Google's answer, the consent
    page opens through open_url (the account's Chrome profile), the code is exchanged (with PKCE), and the token is
    kept only if Google says it belongs to this email."""
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    state = secrets.token_urlsafe(24)
    got = {}

    class H(http.server.BaseHTTPRequestHandler):
        timeout = 5  # Chrome keeps spare connections open; an idle one must not hold the page up

        def log_message(self, *a):
            pass

        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if (q.get('state') or [''])[0] != state:
                self.send_response(400)
                self.end_headers()
                return
            got['code'], got['error'] = (q.get('code') or [''])[0], (q.get('error') or [''])[0]
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            msg = 'Done. You can close this tab and go back to Idli.' if got['code'] else \
                'Google did not give Idli access. Go back to Idli and try again.'
            self.wfile.write(f'<!doctype html><title>Idli</title><p style="font:16px system-ui">{msg}</p>'.encode())

    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H)
    srv.daemon_threads = True
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        open_url(consent_url(email, port, state, challenge))
        end = time.time() + timeout
        while not got and time.time() < end:
            time.sleep(0.5)
    finally:
        srv.shutdown()
    if not got.get('code'):
        raise ValueError('Google sign-in did not finish' + (f' ({got["error"]}).' if got.get('error') else ' in time.'))
    cid, secret = client()
    tok = _post_form(TOKEN_URL, {'code': got['code'], 'client_id': cid, 'client_secret': secret,
                                 'redirect_uri': f'http://127.0.0.1:{port}/', 'grant_type': 'authorization_code',
                                 'code_verifier': verifier})
    if not tok.get('refresh_token'):
        raise ValueError('Google did not give a lasting sign-in. Try again.')
    tok['expires_at'] = time.time() + int(tok.get('expires_in', 3600))
    granted = set(str(tok.get('scope', '')).split())
    who = _get('https://gmail.googleapis.com/gmail/v1/users/me/profile', tok['access_token']).get('emailAddress', '')
    if who.lower() != str(email).lower():
        revoke_token(tok)
        raise ValueError(f'Google signed in {who or "another account"}, not {email}. Sign in with {email} in that '
                         'window and try again.')
    missing = [s.rsplit('/', 1)[1] for s in SCOPES if s not in granted]
    if missing:  # Google lets the person untick boxes; half a sign-in would fail later, mid-run
        revoke_token(tok)
        raise ValueError('Google gave Idli only part of what it needs. Sign in again and tick every box on Google\'s '
                         'page (or "Select all").')
    _save(email, {k: tok[k] for k in ('refresh_token', 'access_token', 'expires_at', 'scope') if k in tok})
    return {'ok': True, 'email': email}


def revoke_token(tok):
    try:
        _post_form('https://oauth2.googleapis.com/revoke', {'token': tok.get('refresh_token') or tok['access_token']})
    except Exception:
        pass


def disconnect(email):
    p = token_file(email)
    if p.is_file():
        revoke_token(json.loads(p.read_text()))
        p.unlink()


# ---- calls ----

def access_token(email):
    p = token_file(email)
    if not p.is_file():
        raise SignInNeeded(f'Sign in to Google for {email} first (the Builder\'s google_connect, or the Runs page).')
    tok = json.loads(p.read_text())
    if tok.get('access_token') and tok.get('expires_at', 0) > time.time() + 60:
        return tok['access_token']
    cid, secret = client()
    new = _post_form(TOKEN_URL, {'refresh_token': tok.get('refresh_token', ''), 'client_id': cid,
                                 'client_secret': secret, 'grant_type': 'refresh_token'})
    if not new.get('access_token'):
        raise SignInNeeded(f'Sign in to Google again for {email}.')
    tok.update(access_token=new['access_token'], expires_at=time.time() + int(new.get('expires_in', 3600)))
    _save(email, tok)
    return tok['access_token']


def _get(url, at):
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + at})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def call(email, method, url, body=None, params=None, ok=(200,)):
    """One API call as this account. A 401 refreshes once; a refused refresh says to sign in again."""
    if params:
        url += '?' + urllib.parse.urlencode(params, doseq=True)
    for attempt in (0, 1):
        at = access_token(email)
        req = urllib.request.Request(url, method=method, data=None if body is None else json.dumps(body).encode(),
                                     headers={'Authorization': 'Bearer ' + at, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            if e.code == 401 and attempt == 0:
                p = token_file(email)
                tok = json.loads(p.read_text())
                tok['expires_at'] = 0
                _save(email, tok)
                continue
            if e.code in ok:
                return {'_status': e.code}
            try:
                why = json.load(e).get('error', {})
                why = why.get('message', '') if isinstance(why, dict) else str(why)
            except ValueError:
                why = ''
            if e.code == 403 and 'insufficient' in why.lower():
                raise SignInNeeded(f'Sign in to Google again for {email} (Idli needs one more permission).')
            raise ValueError(f'Google said {e.code}: {why[:200]}') from None
    raise SignInNeeded(f'Sign in to Google again for {email}.')


GMAIL = 'https://gmail.googleapis.com/gmail/v1/users/me'
CAL = 'https://www.googleapis.com/calendar/v3'


# ---- Sheets ----

def sheet_values(email, sheet_id, rng='A:ZZ'):
    """A sheet's rows as dicts (the first row gives the headings)."""
    if not re.fullmatch(r'[A-Za-z0-9_-]{20,80}', str(sheet_id)):
        raise ValueError('Not a Google Sheet id.')
    v = call(email, 'GET', f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/'
             + urllib.parse.quote(rng)).get('values') or []
    if not v:
        return []
    head = [str(h).strip() for h in v[0]]
    return [{h: (row[i] if i < len(row) else '') for i, h in enumerate(head)} for row in v[1:]]


# ---- Gmail ----

def gmail_list(email, q, limit=100):
    out, page = [], None
    while len(out) < limit:
        r = call(email, 'GET', GMAIL + '/messages', params={'q': q, 'maxResults': min(100, limit),
                                                           **({'pageToken': page} if page else {})})
        out += r.get('messages') or []
        page = r.get('nextPageToken')
        if not page:
            break
    return out[:limit]


def gmail_raw(email, msg_id):
    from lib import google_web
    if not re.fullmatch(r'[0-9a-f]{6,24}', str(msg_id)):
        raise ValueError('Not a Gmail message id.')
    r = call(email, 'GET', f'{GMAIL}/messages/{msg_id}', params={'format': 'raw'})
    raw = base64.urlsafe_b64decode(r['raw'] + '=' * (-len(r['raw']) % 4))
    return {'id': msg_id, 'thread': r.get('threadId'), 'labels': r.get('labelIds') or [],
            **google_web.parse_message(raw)}


def _mime(sender, to, subject, body, in_reply_to=None, message_id=None):
    m = EmailMessage()
    m['To'], m['Subject'] = to, subject
    if sender:
        m['From'] = sender
    if in_reply_to:
        m['In-Reply-To'] = in_reply_to
        m['References'] = in_reply_to
    if message_id:
        m['Message-ID'] = message_id
    m.set_content(body)
    return base64.urlsafe_b64encode(m.as_bytes()).decode()


def idli_message_id(key):
    return f'<idli-{hashlib.sha1(str(key).encode()).hexdigest()[:24]}@idli.local>'


def gmail_create_draft(email, to, subject, body, thread_id=None, in_reply_to=None, key=None):
    """A draft (a reply in the thread when thread_id and in_reply_to are given); the person presses Send. With a key,
    a draft or sent message with the same key is found instead of writing a second one."""
    mid = idli_message_id(key) if key else None
    if mid:
        for q in (f'in:drafts rfc822msgid:{mid}', f'in:sent rfc822msgid:{mid}'):
            if gmail_list(email, q, 1):
                return {'draft': True, 'already': True}
    msg = {'raw': _mime(email, to, subject, body, in_reply_to, mid)}
    if thread_id:
        msg['threadId'] = thread_id
    d = call(email, 'POST', GMAIL + '/drafts', {'message': msg})
    return {'draft': True, 'id': d.get('id')}


def gmail_send(email, to, subject, body, thread_id=None, in_reply_to=None, rehearsal=False):
    """Send mail. Only for a rehearsal between a team's own test accounts (the lead's simulated replies); a routine on
    a real account never sends: it leaves drafts."""
    if not rehearsal:
        raise ValueError('Idli does not send mail for you. It leaves a draft for you to send.')
    msg = {'raw': _mime(email, to, subject, body, in_reply_to)}
    if thread_id:
        msg['threadId'] = thread_id
    return call(email, 'POST', GMAIL + '/messages/send', msg)


def gmail_send_draft(email, draft_id, rehearsal=False):
    """The person's Send on a draft, done by a rehearsal (test accounts only)."""
    if not rehearsal:
        raise ValueError('Only the person sends drafts.')
    return call(email, 'POST', GMAIL + '/drafts/send', {'id': draft_id})


def gmail_drafts(email, q=''):
    r = call(email, 'GET', GMAIL + '/drafts', params={'q': q, 'maxResults': 50})
    return r.get('drafts') or []


def _label_id(email, name=HANDLED):
    for l in call(email, 'GET', GMAIL + '/labels').get('labels') or []:
        if l.get('name') == name:
            return l['id']
    return call(email, 'POST', GMAIL + '/labels', {'name': name, 'labelListVisibility': 'labelShow',
                                                  'messageListVisibility': 'show'})['id']


def gmail_mark_handled(email, msg_ids):
    if not msg_ids:
        return
    call(email, 'POST', GMAIL + '/messages/batchModify', {'ids': list(msg_ids), 'addLabelIds': [_label_id(email)]},
         ok=(200, 204))


# ---- Calendar ----

def _rfc3339(t):
    return t.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def calendar_freebusy(email, start, end):
    r = call(email, 'POST', CAL + '/freeBusy', {'timeMin': _rfc3339(start), 'timeMax': _rfc3339(end),
                                               'items': [{'id': 'primary'}]})
    busy = ((r.get('calendars') or {}).get('primary') or {}).get('busy') or []
    p = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00'))  # noqa: E731
    return [(p(b['start']), p(b['end'])) for b in busy]


def event_id(key):
    """A Calendar event id from the action's key (letters a-v and digits): the same key can't book twice."""
    return 'idli' + base64.b32hexencode(hashlib.sha1(str(key).encode()).digest()).decode().lower().rstrip('=')


def calendar_insert(email, title, start, minutes, attendees, details='', key=None):
    """An event with guests, invitations sent. With a key the event id is fixed, so a retry finds it instead of
    booking again."""
    body = {'summary': title, 'description': details, 'start': {'dateTime': _rfc3339(start)},
            'end': {'dateTime': _rfc3339(start + dt.timedelta(minutes=int(minutes)))},
            'attendees': [{'email': a} for a in attendees]}
    if key:
        body['id'] = event_id(key)
        body['extendedProperties'] = {'private': {'idli_key': str(key)[:200]}}
    r = call(email, 'POST', CAL + '/calendars/primary/events', body, params={'sendUpdates': 'all'}, ok=(200, 409))
    if r.get('_status') == 409:
        return {'saved': True, 'already': True, 'id': body.get('id')}
    return {'saved': True, 'id': r.get('id')}


def calendar_events(email, start, end, q=None):
    r = call(email, 'GET', CAL + '/calendars/primary/events',
             params={'timeMin': _rfc3339(start), 'timeMax': _rfc3339(end), 'singleEvents': 'true',
                     **({'q': q} if q else {})})
    return [{'id': e.get('id'), 'title': e.get('summary', ''), 'start': (e.get('start') or {}).get('dateTime'),
             'attendees': [a.get('email') for a in e.get('attendees') or []]} for e in r.get('items') or []]
