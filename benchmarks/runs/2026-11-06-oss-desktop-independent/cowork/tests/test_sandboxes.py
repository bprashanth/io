"""Sandboxes (narrative/SANDBOXES.md): the Builder makes them outside with exactly the blocks a workflow needs; a
gap means no sandbox; the left chat and Mini scripts call only the sandbox's blocks on its accounts; Sandbox Claude
sees account content masked."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib import blocks, sandboxes, teams  # noqa: E402


class Sandboxes(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.projects = []

        def paseo(*args, parse=True):
            if args[:2] == ('project', 'create'):
                self.projects.append({'projectId': 'p1', 'path': args[2], 'name': 'x'})
            if args[:2] == ('project', 'rename'):
                self.projects[0]['name'] = args[3]
            return self.projects if args[:2] == ('project', 'ls') else None
        self.patches = [mock.patch.object(teams, '_idli', return_value=str(self.tmp)),
                        mock.patch.object(teams, '_paseo', side_effect=paseo),
                        mock.patch.object(teams, '_projects', side_effect=lambda: self.projects),
                        mock.patch.object(teams, 'open_team', return_value={'ok': True}),
                        mock.patch('lib.google_api.connected', return_value=True)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def make(self, **kw):
        args = dict(word='leads', goal='Offer times to leads who reply and book the one they pick',
                    block_list=['gmail_search', 'gmail_read', 'gmail_draft', 'calendar_freebusy', 'calendar_book',
                                'nine_b'], accounts={'me': '87profligate@gmail.com', 'lead': '88profligate@gmail.com'})
        args.update(kw)
        return sandboxes.create(**args)

    def test_made_with_exactly_its_blocks(self):
        out = self.make()
        self.assertTrue(out['ok'], out)
        self.assertRegex(out['name'], r'^[a-z]+-[a-z]+-[0-9a-f]{4} leads$')
        folder = Path(out['folder'])
        meta = json.loads((folder / 'team.json').read_text())
        self.assertEqual(meta['kind'], 'sandbox')
        tools = (folder / 'cowork.tools').read_text().split()
        self.assertIn('mail_search', tools)
        self.assertIn('book_meeting', tools)
        self.assertNotIn('sheet_rows', tools)  # not one of its blocks
        self.assertNotIn('builder_open', tools)
        self.assertIn('accounts', (folder / 'cowork.sites').read_text())
        self.assertIn('## This sandbox', (folder / 'CLAUDE.md').read_text())
        self.assertEqual(self.projects[0]['name'], out['name'])
        self.assertEqual(sandboxes.list_all()[0]['accounts'], ['me', 'lead'])

    def test_a_gap_makes_no_sandbox(self):
        out = self.make(block_list=['gmail_read'], gaps=['post to Instagram'])
        self.assertFalse(out['ok'])
        self.assertEqual(out['gaps'], ['post to Instagram'])
        self.assertFalse((self.tmp / 'teams').exists() and any((self.tmp / 'teams').iterdir()))
        self.assertIn('Instagram', (self.tmp / 'builder' / 'platform-requests.md').read_text())
        self.assertFalse(self.make(block_list=['instagram_post'])['ok'])  # an unknown block is a gap too

    def test_google_blocks_need_an_account(self):
        self.assertFalse(self.make(accounts={})['ok'])

    def test_blocks_check_block_and_account(self):
        folder = self.make()['folder']
        with self.assertRaises(blocks.NotInSandbox):
            blocks.sheet_read('x' * 30, data_dir=folder)  # not one of its blocks
        with self.assertRaises(blocks.NotInSandbox):
            blocks.account('boss', folder)
        self.assertEqual(blocks.account(None, folder), '87profligate@gmail.com')
        self.assertEqual(blocks.account('lead', folder), '88profligate@gmail.com')
        with mock.patch('lib.google_api.gmail_list', return_value=[{'id': 'abc123'}]), \
                mock.patch('lib.google_api.gmail_raw', return_value={'from': '88profligate@gmail.com',
                                                                     'subject': 'Hi', 'new_text': 'Yes, let us talk'}):
            got = blocks.gmail_search('from:88profligate@gmail.com', 'me', data_dir=folder)
        self.assertEqual(got[0]['snippet'], 'Yes, let us talk')

    def test_booking_has_a_fixed_key(self):
        folder = self.make()['folder']
        with mock.patch('lib.google_api.calendar_insert', return_value={'saved': True}) as ins:
            blocks.calendar_book('Call', '2026-11-20T14:00:00+05:30', 30, ['88profligate@gmail.com'], data_dir=folder)
            blocks.calendar_book('Call', '2026-11-20T14:00:00+05:30', 30, ['88profligate@gmail.com'], data_dir=folder)
        keys = {c.kwargs['key'] for c in ins.call_args_list}
        self.assertEqual(len(keys), 1)

    def test_free_times_avoid_busy(self):
        import datetime as dt
        folder = self.make()['folder']
        after = dt.datetime(2026, 11, 18, 9, 0).astimezone()
        busy_day = after.date() + dt.timedelta(days=1)
        busy = [(dt.datetime.combine(busy_day, dt.time(9), after.tzinfo),
                 dt.datetime.combine(busy_day, dt.time(18), after.tzinfo))]
        with mock.patch('lib.google_api.calendar_freebusy', return_value=busy):
            got = blocks.free_times(count=3, after=after.isoformat(), data_dir=folder)
        self.assertEqual(len(got), 3)
        self.assertNotIn(busy_day.isoformat(), [g['start'][:10] for g in got])

    def test_existing_team_tools_leave_sandboxes_alone(self):
        folder = Path(self.make()['folder'])
        before = (folder / 'cowork.tools').read_text()
        teams.refresh_team_tools(str(self.tmp / 'teams'))
        self.assertEqual((folder / 'cowork.tools').read_text(), before)

    def test_role_label(self):
        from lib import rolelabels
        self.assertEqual(rolelabels.role_for(self.make()['folder']), 'sandbox')
        self.assertEqual(rolelabels.role_for(str(self.tmp)), 'analyst')
        self.assertIn('This is a sandbox', blocks.claude_guide(self.make()['folder']))


class McpRoles(unittest.TestCase):
    def tools(self, env):
        code = 'import sys; sys.path.insert(0, "."); from lib import idli_mcp; print(sorted(idli_mcp.TOOLS))'
        out = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True,
                             env={**os.environ, **env}, timeout=60)
        return out.stdout

    def test_outside_builder_gets_only_sandbox_tools(self):
        out = self.tools({'IDLI_ROLE': 'outside'})
        self.assertIn('sandbox_create', out)
        self.assertNotIn('unmask', out)
        self.assertNotIn('account_peek', out)

    def test_sandbox_claude_gets_masked_account_tools(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / 'team.json').write_text(json.dumps({'kind': 'sandbox', 'blocks': ['gmail_read'],
                                                   'accounts': {'me': 'a@b.com'}}))
        out = self.tools({'IDLI_DATA': str(tmp), 'IDLI_ROLE': ''})
        self.assertIn('account_peek', out)
        self.assertIn('script_try', out)
        drivey = self.tools({'IDLI_DATA': tempfile.mkdtemp(), 'IDLI_ROLE': ''})
        self.assertNotIn('account_peek', drivey)

    def test_account_text_is_masked(self):
        from lib import privacy
        tmp = tempfile.mkdtemp()
        with mock.patch.dict(os.environ, {'IDLI_HOME': tmp}):
            out = privacy.mask_account_text(tmp, 'From asha.verma@example.org: yes, Friday 2 pm works.')
        self.assertNotIn('asha.verma@example.org', out)
        self.assertIn('Friday', out)


if __name__ == '__main__':
    unittest.main()
