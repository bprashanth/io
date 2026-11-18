"""2026-11-18 owner round: @ a folder for insights, "entirely withheld" on the privacy page, and Minis that can be
asked, activated and forked (narrative/UX.md)."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _xlsx(path, rows):
    import pandas as pd
    pd.DataFrame(rows).to_excel(path, index=False)


class FolderFetchTests(unittest.TestCase):
    def setUp(self):
        self.dd = tempfile.mkdtemp()
        self.fake = Path(tempfile.mkdtemp())
        _xlsx(self.fake / 's1.xlsx', {'Ward': ['A', 'B'], 'Debt': [1, 2]})
        _xlsx(self.fake / 's2.xlsx', {'Ward': ['C'], 'Debt': [3]})
        self.entries = {
            'My Drive/Survey/round1': {'id': 's1', 'url': 'x', 'kind': 'Google Sheets', 'title': 'round1'},
            'My Drive/Survey/round2': {'id': 's2', 'url': 'x', 'kind': 'Google Sheets', 'title': 'round2'},
            'My Drive/Survey/notes.pdf': {'id': 'p1', 'url': 'x', 'kind': 'PDF', 'title': 'notes.pdf'},
            'My Drive/Papers/a.pdf': {'id': 'p2', 'url': 'x', 'kind': 'PDF', 'title': 'a.pdf'},
            'My Drive/Papers/b.pdf': {'id': 'p3', 'url': 'x', 'kind': 'PDF', 'title': 'b.pdf'},
            'My Drive/Survey summary': {'id': 's2', 'url': 'x', 'kind': 'Google Sheets', 'title': 'Survey summary'},
        }

    def tearDown(self):
        shutil.rmtree(self.dd)
        shutil.rmtree(self.fake)

    def fetch(self, paths):
        from lib import drivestubs
        with patch.dict(os.environ, {'IDLI_DRIVE_FAKE': str(self.fake)}), \
                patch.object(drivestubs, 'refresh', return_value=self.entries):
            return drivestubs.fetch(self.dd, paths, spreadsheets_only=True)

    def test_a_folder_without_its_slash_is_a_folder(self):
        out = self.fetch(['Drive/My Drive/Survey'])
        self.assertEqual(sorted(f['title'] for f in out['files']), ['round1', 'round2'])
        self.assertEqual(out['folders'], ['Survey'])
        self.assertEqual(out['skipped'], {'PDF': 1})

    def test_a_file_named_like_the_folder_is_still_that_file(self):
        out = self.fetch(['Drive/My Drive/Survey summary'])
        self.assertEqual([f['title'] for f in out['files']], ['Survey summary'])
        self.assertNotIn('folders', out)

    def test_router_words(self):
        from lib import modes
        self.assertEqual(modes._kinds_words({'PDF': 18, 'Image': 1}), '18 PDFs and 1 image')
        out = self.fetch(['Drive/My Drive/Papers'])
        self.assertEqual(out['files'], [])
        self.assertEqual(out['folders'], ['Papers'])
        self.assertEqual(out['skipped'], {'PDF': 2})


class WithheldColumnTests(unittest.TestCase):
    def test_review_rows_show_filled_cells_and_say_withheld(self):
        from lib import privacy
        d = tempfile.mkdtemp()
        path = os.path.join(d, 'visits.xlsx')
        notes = [''] * 4 + ['Met the family at home and talked about the loan for a long time'] * 2
        _xlsx(path, {'Ward': ['A', 'B', 'C', 'D', 'E', 'F'], 'Visits': [1, 2, 3, 4, 5, 6], 'Notes': notes})
        rows = [{'column': 'Ward', 'mask': False, 'reason': 'x', 'samples': [], 'as_sent': []},
                {'column': 'Visits', 'mask': False, 'reason': 'x', 'samples': [], 'as_sent': []},
                {'column': 'Notes', 'mask': True, 'reason': 'free-text', 'samples': ['', '', ''], 'as_sent': []}]
        with patch.object(privacy, 'suggest', return_value=rows):
            got = privacy.review(d, 'visits.xlsx', path, columns={'Notes': True})
        note = next(r for r in got['suggestions'] if r['column'] == 'Notes')
        self.assertTrue(note['samples'][0].startswith('Met the family'))  # not the blank top rows
        self.assertTrue(note['withheld'])  # each note became one code: the page says "Notes entirely withheld"
        ward = next(r for r in got['suggestions'] if r['column'] == 'Ward')
        self.assertFalse(ward['withheld'])
        shutil.rmtree(d)


ACTION_SCRIPT = """import os, sys; sys.path.insert(0, os.environ["IDLI_COWORK"]); from lib import blocks
import argparse
ap = argparse.ArgumentParser(); ap.add_argument("--dry", default="no"); ap.parse_args()
print("since", os.environ.get("IDLI_SINCE", "-"), "|", blocks._since("from:x@y.z"))
blocks.gmail_draft("lead@x.org", "Re: meeting", "Hello Asha, would Fri 2 PM work?", key="k1")
blocks.calendar_book("Meeting", "2026-11-20T13:00+05:30", 30, ["lead@x.org"], key="b1")
print("Done: times drafted 1, booked 1")
"""


class ActionMiniTests(unittest.TestCase):
    """Ask, preview, run, turn on and fork a saved action Mini (lib/minitalk.py, lib/minifork.py)."""

    def setUp(self):
        import json
        self.dd = Path(tempfile.mkdtemp())
        (self.dd / 'team.json').write_text(json.dumps({
            'kind': 'sandbox', 'blocks': ['gmail_search', 'gmail_draft', 'calendar_book', 'nine_b'],
            'accounts': {'me': '87profligate@gmail.com', 'lead': '88profligate@gmail.com'}}))
        m = self.dd / 'minis' / 'lead-replies-1'
        m.mkdir(parents=True)
        (m / 'q.py').write_text(ACTION_SCRIPT)
        (m / 'mini.json').write_text(json.dumps({
            'id': 'lead-replies-1', 'name': 'Lead replies', 'goal': 'Draft times for leads who agreed; book picks.',
            'questions': [{'id': 'lead_replies', 'question': 'Handle lead replies', 'script': 'q.py',
                           'params': {'dry': {'type': 'choice', 'choices': ['no', 'yes'], 'default': 'no'}}}],
            'files': [], 'charts': []}))
        self.google = [patch('lib.google_api.gmail_create_draft', side_effect=AssertionError('wrote a draft')),
                       patch('lib.google_api.calendar_insert', side_effect=AssertionError('booked'))]
        for g in self.google:
            g.start()

    def tearDown(self):
        for g in self.google:
            g.stop()
        shutil.rmtree(self.dd)

    def talk(self, said, judged):
        from lib import minitalk
        answers = iter(judged)
        with patch.object(minitalk, '_judge', side_effect=lambda *a, **k: next(answers)):
            return minitalk.talk(str(self.dd), 'lead-replies-1', said)

    def test_open_says_it_is_an_action_mini(self):
        from lib import home, journey
        with patch.object(journey, 'page_url', return_value='http://x'):
            out = home.mini_open(str(self.dd), 'lead-replies-1')
        self.assertTrue(out['actions'])
        self.assertIn('Fork', out['reply'])

    def test_explain_answers_from_the_steps_without_running(self):
        from lib import minitalk
        with patch.object(minitalk, 'run_preview', side_effect=AssertionError('ran')):
            out = self.talk('how are leads picked?', [{'kind': 'explain', 'answer': 'Leads are rows of the sheet.'}])
        self.assertEqual(out['reply'], 'Leads are rows of the sheet.')

    def test_preview_shows_the_draft_and_writes_nothing(self):
        out = self.talk('show me the draft you would write',
                        [{'kind': 'preview'}, {'answer': 'It would offer Asha three times.'}])
        self.assertEqual(out['kind'], 'preview')
        self.assertIn('**Draft to lead@x.org**', out['reply'])
        self.assertIn('> Hello Asha, would Fri 2 PM work?', out['reply'])
        self.assertIn('Nothing was drafted, booked or sent', out['reply'])

    def test_turn_on_from_today_and_runs_read_nothing_older(self):
        import datetime as dt
        out = self.talk('activate this mini on my account', [{'kind': 'activate', 'role': 'me'}])
        self.assertIn('Turned on for 87profligate@gmail.com', out['reply'])
        self.assertIn('not a building block yet', out['reply'])
        from lib import minitalk
        mini = __import__('json').loads((self.dd / 'minis/lead-replies-1/mini.json').read_text())
        self.assertEqual(mini['active']['since'], dt.date.today().isoformat())
        output, items = minitalk.run_preview(str(self.dd), {**mini, 'id': 'lead-replies-1'})
        self.assertIn('after:' + dt.date.today().isoformat().replace('-', '/'), output)
        self.assertEqual([i['kind'] for i in items], ['draft', 'booking'])

    def test_change_points_to_fork(self):
        out = self.talk('only replies from the last 2 days', [{'kind': 'change'}])
        self.assertIn('press Fork', out['reply'])

    def test_fork_copies_without_touching_the_original(self):
        from lib import home, minifork, journey
        work = Path(tempfile.mkdtemp())
        before = (self.dd / 'minis/lead-replies-1/q.py').read_text()
        with patch.dict(os.environ, {'IDLI_CLAUDE_WORK': str(work)}), \
                patch.object(home, '_drivey_workspace', return_value='wks1'), \
                patch.object(home, '_claude_terminal', return_value='t1'), \
                patch.object(home, 'type_into') as typed, \
                patch.object(home, '_remember'), \
                patch('lib.uiswitch.show_terminal', return_value={'ok': True}):
            out = minifork.fork(str(self.dd), 'lead-replies-1', 'wks1')
            fork = work / 'forks' / out['fork']
            self.assertTrue((fork / 'q.py').exists())
            self.assertIn('How do you want to change it?', (fork / 'FORK.md').read_text())
            self.assertIn('read FORK.md first', typed.call_args[0][1])
            self.assertEqual(journey._fork_of(str(self.dd), f'forks/{out["fork"]}'), 'lead-replies-1')
        self.assertEqual((self.dd / 'minis/lead-replies-1/q.py').read_text(), before)
        shutil.rmtree(work)


class RouterTests(unittest.TestCase):
    def test_an_open_action_mini_routes_to_mini_talk(self):
        from lib import modes
        tools = [{'name': 'mcp__cowork__' + t} for t in
                 ('drive_fetch', 'privacy_review_open', 'claude_handoff', 'mini_open', 'mini_ask', 'binder_item',
                  'mini_talk', 'mail_search')]
        opened = {'id': 'lead-replies-1', 'questions': [{'id': 'q'}], 'actions': True, 'reply': 'x'}
        msgs = [{'role': 'user', 'content': 'Open Mini: Lead replies [lead-replies-1]'},
                {'role': 'assistant', 'content': [{'type': 'tool_use', 'id': 'u1', 'name': 'mcp__cowork__mini_open',
                                                   'input': {'id': 'lead-replies-1'}}]},
                {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': 'u1',
                                              'content': [{'type': 'text', 'text': __import__('json').dumps(opened)}]}]},
                {'role': 'assistant', 'content': [{'type': 'text', 'text': 'x'}]},
                {'role': 'user', 'content': 'show me the draft you would write'}]
        out = modes.drivey_route({'messages': msgs, 'tools': tools, 'model': 'idli-9b'})
        uses = [c for c in out['content'] if c.get('type') == 'tool_use']
        self.assertEqual(uses[0]['name'], 'mcp__cowork__mini_talk')
        self.assertEqual(uses[0]['input']['question'], 'show me the draft you would write')


if __name__ == '__main__':
    unittest.main()
