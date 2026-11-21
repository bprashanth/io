"""lib/google_api.py against a fake Google (no network): sign-in, refresh, a revoked sign-in, idempotent drafts and
bookings, and the rule that a routine never sends mail."""
import base64
import datetime as dt
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import google_api as api  # noqa: E402


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeGoogle:
    def __init__(self):
        self.calls, self.refresh_ok, self.events, self.drafts, self.sent = [], True, {}, [], []
        self.access = 'AT1'

    def __call__(self, req, timeout=None):
        url = req.full_url if hasattr(req, 'full_url') else req
        method = req.get_method() if hasattr(req, 'get_method') else 'GET'
        body = req.data
        self.calls.append((method, url))
        u = urllib.parse.urlparse(url)
        if u.path == '/token':
            form = urllib.parse.parse_qs(body.decode())
            if form['grant_type'][0] == 'refresh_token':
                if not self.refresh_ok:
                    raise urllib.error.HTTPError(url, 400, 'bad', {}, io.BytesIO(b'{"error": "invalid_grant"}'))
                self.access = 'AT2'
                return Resp(json.dumps({'access_token': 'AT2', 'expires_in': 3600}).encode())
            return Resp(json.dumps({'access_token': 'AT1', 'refresh_token': 'RT', 'expires_in': 3600,
                                    'scope': ' '.join(api.SCOPES)}).encode())
        auth = req.headers.get('Authorization', '') if hasattr(req, 'headers') else ''
        if auth and auth != 'Bearer ' + self.access:
            raise urllib.error.HTTPError(url, 401, 'expired', {}, io.BytesIO(b'{}'))
        if u.path.endswith('/profile'):
            return Resp(b'{"emailAddress": "me@example.org"}')
        if u.path.endswith('/messages') and method == 'GET':
            q = urllib.parse.parse_qs(u.query)['q'][0]
            hits = [d for d in self.drafts + self.sent if d['mid'] and d['mid'] in q]
            return Resp(json.dumps({'messages': [{'id': 'm1'}] if hits else []}).encode())
        if u.path.endswith('/drafts') and method == 'POST':
            raw = json.loads(body)['message']['raw']
            text = base64.urlsafe_b64decode(raw + '==').decode()
            mid = next((l.split(': ', 1)[1] for l in text.splitlines() if l.startswith('Message-ID')), '')
            self.drafts.append({'mid': mid, 'thread': json.loads(body)['message'].get('threadId'), 'text': text})
            return Resp(b'{"id": "d1"}')
        if u.path.endswith('/messages/send'):
            self.sent.append({'mid': '', 'text': ''})
            return Resp(b'{"id": "s1"}')
        if u.path.endswith('/events'):
            ev = json.loads(body)
            if ev['id'] in self.events:
                raise urllib.error.HTTPError(url, 409, 'dup', {}, io.BytesIO(b'{"error": {"message": "duplicate"}}'))
            self.events[ev['id']] = ev
            return Resp(json.dumps({'id': ev['id']}).encode())
        if u.path.endswith('/freeBusy'):
            return Resp(b'{"calendars": {"primary": {"busy": [{"start": "2026-11-19T04:30:00Z", "end": "2026-11-19T06:30:00Z"}]}}}')
        if '/values/' in u.path:
            return Resp(b'{"values": [["Name", "Email"], ["Asha", "a@example.org"], ["Ravi"]]}')
        raise AssertionError('unexpected call ' + url)


class Base(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / 'io_oauth_client_gcp.json').write_text(json.dumps({'installed': {'client_id': 'cid', 'client_secret': 'cs'}}))
        self.env = mock.patch.dict(os.environ, {'IDLI_GOOGLE_CONFIG': str(self.d)})
        self.env.start()
        self.g = FakeGoogle()
        self.net = mock.patch.object(urllib.request, 'urlopen', side_effect=self.g)
        self.net.start()

    def tearDown(self):
        self.net.stop()
        self.env.stop()
        shutil.rmtree(self.d, ignore_errors=True)

    def signed_in(self, expires_in=3600):
        api._save('me@example.org', {'refresh_token': 'RT', 'access_token': 'AT1', 'expires_at': time.time() + expires_in})


class SignIn(Base):
    def test_consent_keeps_the_token_private_and_checks_the_account(self):
        real_urlopen = self.net.temp_original

        def browser(url):  # the person says yes in their Chrome profile: Google redirects to Idli's local page
            q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            self.assertEqual(q['login_hint'], ['me@example.org'])
            self.assertEqual(q['code_challenge_method'], ['S256'])
            back = q['redirect_uri'][0] + '?' + urllib.parse.urlencode({'code': 'C', 'state': q['state'][0]})
            threading.Thread(target=lambda: real_urlopen(back, timeout=5).read(), daemon=True).start()
        out = api.connect('me@example.org', browser, timeout=10)
        self.assertEqual(out, {'ok': True, 'email': 'me@example.org'})
        f = api.token_file('me@example.org')
        self.assertEqual(oct(f.stat().st_mode)[-3:], '600')
        self.assertEqual(json.loads(f.read_text())['refresh_token'], 'RT')

    def test_wrong_account_is_refused(self):
        real_urlopen = self.net.temp_original

        def browser(url):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            back = q['redirect_uri'][0] + '?' + urllib.parse.urlencode({'code': 'C', 'state': q['state'][0]})
            threading.Thread(target=lambda: real_urlopen(back, timeout=5).read(), daemon=True).start()
        with mock.patch.object(api, 'revoke_token'):
            with self.assertRaisesRegex(ValueError, 'not other@example.org'):
                api.connect('other@example.org', browser, timeout=10)
        self.assertFalse(api.connected('other@example.org'))


class Calls(Base):
    def test_refresh_then_revoked_says_sign_in_again(self):
        self.signed_in(expires_in=-10)  # expired: refreshed on the next call
        self.assertEqual(api.sheet_values('me@example.org', 'x' * 30), [{'Name': 'Asha', 'Email': 'a@example.org'},
                                                                        {'Name': 'Ravi', 'Email': ''}])
        self.assertTrue(any(u.endswith('/token') for _, u in self.g.calls))
        self.g.refresh_ok, self.g.access = False, 'AT3'  # Google refuses the old token, and the refresh too
        with self.assertRaisesRegex(api.SignInNeeded, 'Sign in to Google again for me@example.org'):
            api.sheet_values('me@example.org', 'x' * 30)

    def test_no_token_says_sign_in(self):
        with self.assertRaisesRegex(api.SignInNeeded, 'Sign in to Google for me@example.org'):
            api.calendar_freebusy('me@example.org', dt.datetime.now(dt.timezone.utc), dt.datetime.now(dt.timezone.utc))

    def test_booking_twice_books_once(self):
        self.signed_in()
        start = dt.datetime(2026, 11, 20, 10, 30, tzinfo=dt.timezone.utc)
        a = api.calendar_insert('me@example.org', 'Call', start, 30, ['lead@example.org'], key='book:lead:x')
        b = api.calendar_insert('me@example.org', 'Call', start, 30, ['lead@example.org'], key='book:lead:x')
        self.assertEqual(len(self.g.events), 1)
        self.assertTrue(b.get('already'))
        ev = next(iter(self.g.events.values()))
        self.assertRegex(ev['id'], r'^[a-v0-9]{5,1024}$')
        self.assertEqual(ev['attendees'], [{'email': 'lead@example.org'}])
        self.assertIn('sendUpdates=all', [u for m, u in self.g.calls if u.endswith('sendUpdates=all') or 'sendUpdates' in u][0])

    def test_draft_is_a_reply_and_written_once(self):
        self.signed_in()
        api.gmail_create_draft('me@example.org', 'lead@example.org', 'Re: Hi', 'Times', thread_id='t1',
                               in_reply_to='<x@y>', key='offer:1')
        again = api.gmail_create_draft('me@example.org', 'lead@example.org', 'Re: Hi', 'Times', thread_id='t1',
                                       in_reply_to='<x@y>', key='offer:1')
        self.assertEqual(len(self.g.drafts), 1)
        self.assertTrue(again.get('already'))
        self.assertEqual(self.g.drafts[0]['thread'], 't1')
        self.assertIn('In-Reply-To: <x@y>', self.g.drafts[0]['text'])

    def test_routines_never_send(self):
        self.signed_in()
        with self.assertRaises(ValueError):
            api.gmail_send('me@example.org', 'lead@example.org', 'Hi', 'x')
        with self.assertRaises(ValueError):
            api.gmail_send_draft('me@example.org', 'd1')
        api.gmail_send('me@example.org', 'lead@example.org', 'Hi', 'x', rehearsal=True)
        self.assertEqual(len(self.g.sent), 1)

    def test_freebusy(self):
        self.signed_in()
        busy = api.calendar_freebusy('me@example.org', dt.datetime(2026, 11, 19, tzinfo=dt.timezone.utc),
                                     dt.datetime(2026, 11, 20, tzinfo=dt.timezone.utc))
        self.assertEqual(busy[0][0], dt.datetime(2026, 11, 19, 4, 30, tzinfo=dt.timezone.utc))


if __name__ == '__main__':
    unittest.main()
