"""Routines (lib/routines.py): steps, the 9B judge, actions done once, approvals, and google_web's parsers."""
import datetime as dt
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import google_web, routines  # noqa: E402

FEED = """<?xml version="1.0"?><feed><entry><title>Re: Meeting</title><summary>Friday 2 pm works</summary>
<link href="https://mail.google.com/mail/u/0?account_id=a&amp;message_id=1a2b3c4d5e6f&amp;view=conv"/>
<issued>2026-11-18T10:00:00Z</issued><author><name>Lead</name><email>Lead@Example.org</email></author></entry>
<entry><title>Sale</title><summary>buy</summary><link href="x?message_id=ffff0000aaaa"/><author><name>Shop</name>
<email>shop@example.com</email></author></entry></feed>"""

RAW = (b"From: Lead <lead@example.org>\r\nTo: me@example.org\r\nSubject: Re: Meeting\r\nDate: Wed, 18 Nov 2026 10:00:00"
       b" +0530\r\nMessage-ID: <x@y>\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nFriday 2 pm works.\r\n\r\nOn Tue,"
       b" Nov 17, 2026 me wrote:\r\n> Here are three times\r\n")

ICS = """BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nDTSTART:20261119T043000Z\r\nDTEND:20261119T063000Z\r\nSUMMARY:Busy
 morning\r\nEND:VEVENT\r\nBEGIN:VEVENT\r\nDTSTART;VALUE=DATE:20261120\r\nDTEND;VALUE=DATE:20261121\r\nTRANSP:TRANSPARENT
\r\nSUMMARY:Free all day\r\nEND:VEVENT\r\nBEGIN:VEVENT\r\nDTSTART;TZID=Asia/Kolkata:20261120T140000\r\nDTEND;TZID=Asia/Kolkata:20261120T150000\r\nSTATUS:CANCELLED\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"""

SCRIPT = r'''import json, sys
d = json.load(sys.stdin); acts = []
for m in d["context"].get("mail", []):
    v = m["verdict"]
    if v.get("picked"):
        acts.append({"type": "book_event", "key": "book:" + m["id"], "role": "me", "title": "Call", "start":
                     d["context"]["slots"][v["picked"] - 1]["start"], "minutes": 30, "guest": m["from"]})
    elif v.get("agreed"):
        acts.append({"type": "draft_email", "key": "offer:" + m["id"], "role": "me", "to": m["from"],
                     "subject": "Times", "body": "\n".join(s["label"] for s in d["context"]["slots"])})
print(json.dumps({"actions": acts, "memory": {"runs": d["memory"].get("runs", 0) + 1}}))
'''


class Parsers(unittest.TestCase):
    def test_feed_and_message(self):
        f = google_web.parse_feed(FEED)
        self.assertEqual([(m['id'], m['from']) for m in f], [('1a2b3c4d5e6f', 'lead@example.org'),
                                                             ('ffff0000aaaa', 'shop@example.com')])
        m = google_web.parse_message(RAW)
        self.assertEqual((m['from'], m['subject']), ('lead@example.org', 'Re: Meeting'))
        self.assertEqual(m['new_text'], 'Friday 2 pm works.')

    def test_ics_and_free_slots(self):
        busy = google_web.parse_ics_busy(ICS)
        self.assertEqual(len(busy), 1)  # transparent and cancelled events don't count
        tz = dt.timezone(dt.timedelta(hours=5, minutes=30))
        now = dt.datetime(2026, 11, 18, 18, 0, tzinfo=tz)  # Wednesday evening
        slots = google_web.free_slots(busy, now=now, hours='10:00-17:00', count=3, tz=tz)
        self.assertEqual(len(slots), 3)
        self.assertEqual(len({s.date() for s in slots}), 3)  # spread over days
        for s in slots:
            self.assertFalse(any(b0 < s + dt.timedelta(minutes=30) and s < b1 for b0, b1 in busy))
            self.assertLess(s.weekday(), 5)
        self.assertNotEqual(slots[0], dt.datetime(2026, 11, 19, 10, 0, tzinfo=tz))  # 10:00-12:00 Thursday is busy


class Running(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        r = self.d / 'extensions' / 'routines'
        r.mkdir(parents=True)
        (r / 'leads.json').write_text(json.dumps({'title': 'Leads', 'steps': [
            {'type': 'sheet', 'role': 'me', 'sheet': '{config.leads_sheet}', 'as': 'leads'},
            {'type': 'mail', 'role': 'me', 'as': 'mail', 'from_in': 'leads.email'},
            {'type': 'free', 'ical': '{config.ical}', 'as': 'slots'},
            {'type': 'judge', 'each': 'mail', 'prompt': 'Reply: {new_text}', 'as': 'verdict',
             'schema': {'type': 'object', 'properties': {'agreed': {'type': 'boolean'}, 'unclear': {'type': 'boolean'}}}},
            {'type': 'script', 'file': 'decide.py'}]}))
        (r / 'decide.py').write_text(SCRIPT)
        routines.set_config(self.d, 'leads', 'test', 'leads_sheet', 'x' * 30)
        routines.set_config(self.d, 'leads', 'test', 'ical', 'https://calendar.google.com/calendar/ical/a/private-1/basic.ics')
        self.inbox = [{'id': 'aa11', 'from': 'lead@example.org', 'subject': 'Re: Meeting', 'new_text': 'yes'},
                      {'id': 'bb22', 'from': 'other@example.org', 'subject': 'Hi', 'new_text': 'hello'}]
        self.did = []
        tz = dt.datetime.now().astimezone().tzinfo
        slots = [dt.datetime(2026, 11, 19 + i, 10, 0, tzinfo=tz) for i in range(3)]
        self.p = [mock.patch.object(google_web, 'sheet_rows', return_value=[{'Name': 'L', 'Email': 'Lead@example.org'}]),
                  mock.patch.object(google_web, 'mail_feed', side_effect=lambda b: [{'id': m['id'], 'from': m['from']}
                                                                                    for m in self.inbox]),
                  mock.patch.object(google_web, 'mail_message', side_effect=lambda b, i: next(
                      m for m in self.inbox if m['id'] == i)),
                  mock.patch.object(google_web, 'ical_busy', return_value=[]),
                  mock.patch.object(google_web, 'free_slots', return_value=slots),
                  mock.patch.object(google_web, 'compose_draft', side_effect=lambda b, *a: self.did.append(('draft',) + a)),
                  mock.patch.object(google_web, 'calendar_event', side_effect=lambda b, *a: self.did.append(('book',) + a))]
        for p in self.p:
            p.start()
        self.verdicts = {'yes': {'agreed': True, 'unclear': False}}

    def tearDown(self):
        for p in self.p:
            p.stop()
        shutil.rmtree(self.d, ignore_errors=True)

    def go(self, **kw):
        judge = lambda prompt, schema: self.verdicts.get(prompt.split(': ', 1)[1], {'unclear': True})
        return routines.run(self.d, 'leads', 'test', browsers={'me': object()}, judge_fn=judge, **kw)

    def test_check(self):
        self.assertEqual(routines.check(self.d, 'leads'), [])
        bad = json.loads((self.d / 'extensions/routines/leads.json').read_text())
        bad['steps'][3]['schema'] = {'type': 'object', 'properties': {'agreed': {'type': 'boolean'}}}
        (self.d / 'extensions/routines/leads.json').write_text(json.dumps(bad))
        self.assertTrue(any('unclear' in p for p in routines.check(self.d, 'leads')))

    def test_draft_once_then_book_after_yes(self):
        log = self.go()
        self.assertTrue(log['ok'], log)
        self.assertEqual([d[0] for d in self.did], ['draft'])  # the non-lead mail was left alone
        self.assertIn('1 new from the list', log['steps'][1]['note'])
        self.go()
        self.assertEqual(len(self.did), 1)  # done once
        # the lead picks the second time
        self.inbox.append({'id': 'cc33', 'from': 'lead@example.org', 'subject': 'Re: Times', 'new_text': 'pick2'})
        self.verdicts['pick2'] = {'agreed': True, 'picked': 2, 'unclear': False}
        self.go()
        ov = routines.overview(self.d)[0]
        self.assertEqual(len(ov['pending']), 1)
        self.assertEqual(len(self.did), 1)  # booking waits for the person
        routines.decide(self.d, 'leads', ov['pending'][0]['key'], True, browsers={'me': object()})
        self.assertEqual(self.did[-1][0], 'book')
        self.go()
        self.assertEqual(len(self.did), 2)  # never booked twice
        self.assertEqual(routines._read(routines.state_dir(self.d, 'leads') / 'state.json', {})['memory']['runs'], 4)

    def test_unclear_goes_to_the_person_and_dry_run_changes_nothing(self):
        self.inbox[0]['new_text'] = 'hmm'
        self.go(dry_run=True)
        self.assertEqual(routines.overview(self.d)[0]['asks'], [])
        self.go()
        asks = routines.overview(self.d)[0]['asks']
        self.assertEqual(len(asks), 1)
        routines.decide(self.d, 'leads', asks[0]['key'], False)
        self.assertEqual(routines.overview(self.d)[0]['asks'], [])

    def test_real_runs_never_skip_the_yes(self):
        with self.assertRaises(ValueError):
            routines.run(self.d, 'leads', 'real', approve_all=True)
