"""The chain for questions about a workflow Mini (lib/minitalk.py, lib/miniscope.py, lib/modes.py; owner 2026-11-18):
the 9B answers only what maps cleanly; the rest is mapped to the Mini's steps and the sandbox's read blocks (by the
outside service with consent, or the 9B on No); what can't be mapped ends at Fork. A sandbox question with no Mini
goes to Claude, masked."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

STEP_SCRIPT = '''import os, sys; sys.path.insert(0, os.environ["IDLI_COWORK"]); from lib import blocks

def read_leads(ctx):
    ctx["leads"] = ["lead@x.org", "other@x.org"]
    for e in ctx["leads"]:
        print("lead:", e)

def find_replies(ctx):
    ctx["replied"] = ctx["leads"][:1]
    print("replied:", ", ".join(ctx["replied"]))

def offer_times(ctx):
    for e in ctx["replied"]:
        blocks.gmail_draft(e, "Re: meeting", "Hello, would Fri 2 PM work?", key="k-" + e)
        print(e, "-> drafted")

blocks.run_steps([("Read the leads sheet", read_leads), ("Find who replied", find_replies),
                  ("Offer three times", offer_times)])
'''


def _sandbox(outside=None):
    dd = Path(tempfile.mkdtemp())
    (dd / 'team.json').write_text(json.dumps({
        'kind': 'sandbox', 'blocks': ['gmail_search', 'gmail_read', 'gmail_draft', 'calendar_freebusy',
                                     'calendar_book', 'sheet_read', 'nine_b'],
        'accounts': {'me': '87profligate@gmail.com', 'lead': '88profligate@gmail.com'}}))
    if outside == 'never':
        (dd / 'no-query-service').write_text('x')
    if outside == 'always':
        (dd / 'query-service-always').write_text('x')
    m = dd / 'minis' / 'lead-steps-1'
    m.mkdir(parents=True)
    (m / 'q.py').write_text(STEP_SCRIPT + '\nSHEET = "1oeGEi5xWx2tO7ExK_RzZmnyBU1t61w04jXJbWzv_jfk"\n')
    (m / 'mini.json').write_text(json.dumps({
        'id': 'lead-steps-1', 'name': 'Lead replies', 'goal': 'Offer times to leads who replied.',
        'questions': [{'id': 'all', 'question': 'Handle lead replies', 'script': 'q.py', 'params': {}}],
        'steps': ['Read the leads sheet', 'Find who replied', 'Offer three times'], 'files': [], 'charts': []}))
    return dd


class StepsTests(unittest.TestCase):
    def setUp(self):
        self.dd = _sandbox()
        self.no_write = patch('lib.google_api.gmail_create_draft', side_effect=AssertionError('wrote a draft'))
        self.no_write.start()

    def tearDown(self):
        self.no_write.stop()
        shutil.rmtree(self.dd)

    def run_script(self, *args):
        env = {**os.environ, 'IDLI_COWORK': str(Path(__file__).resolve().parents[1]), 'IDLI_SANDBOX': str(self.dd)}
        return subprocess.run([sys.executable, '-I', str(self.dd / 'minis/lead-steps-1/q.py'), *args], env=env,
                              capture_output=True, text=True, timeout=60)

    def test_list_steps_reads_nothing(self):
        r = self.run_script('--list-steps')
        self.assertEqual(json.loads(r.stdout), ['Read the leads sheet', 'Find who replied', 'Offer three times'])

    def test_one_step_shows_only_its_own_output(self):
        r = self.run_script('--step', '2')
        self.assertIn('== Step 2: Find who replied', r.stdout)
        self.assertIn('replied: lead@x.org', r.stdout)
        self.assertNotIn('lead: other@x.org', r.stdout)
        self.assertNotIn('Step 3', r.stdout)

    def test_run_step_n_is_direct_and_writes_nothing(self):
        from lib import minitalk
        with patch.object(minitalk, '_judge', side_effect=AssertionError('no model for a plain command')):
            out = minitalk.talk(str(self.dd), 'lead-steps-1', 'run step 3')
        self.assertEqual(out['kind'], 'step')
        self.assertIn('**Step 3: Offer three times**', out['reply'])
        self.assertIn('lead@x.org -> would draft', out['reply'])
        self.assertIn('**Would draft to lead@x.org**', out['reply'])
        self.assertIn('Nothing was drafted, booked or sent', out['reply'])

    def test_a_missing_step_says_which_there_are(self):
        from lib import minitalk
        out = minitalk.talk(str(self.dd), 'lead-steps-1', 'show step 7')
        self.assertIn('no step 7', out['reply'])
        self.assertIn('2. Find who replied', out['reply'])


class MappingTests(unittest.TestCase):
    def setUp(self):
        self.patches = [patch('lib.privacy.Scanner', return_value=lambda text: []),
                        patch('lib.google_api.gmail_create_draft', side_effect=AssertionError('wrote')),
                        patch('lib.google_api.calendar_insert', side_effect=AssertionError('booked'))]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def talk(self, dd, said, judged=({'kind': 'other'},), **kw):
        from lib import minitalk
        answers = iter(judged)
        with patch.object(minitalk, '_judge', side_effect=lambda *a, **k: next(answers)):
            return minitalk.talk(str(dd), 'lead-steps-1', said, **kw)

    def test_ask_each_time_shows_the_masked_question_and_the_menu(self):
        dd = _sandbox()
        out = self.talk(dd, 'show my emails from 88profligate@gmail.com this week')
        self.assertEqual(out['kind'], 'consent')
        c = out['consent']
        self.assertNotIn('88profligate', c['masked_question'])
        self.assertIn('step:2: Step 2 of the Mini: Find who replied', c['menu'])
        self.assertIn('- meetings:', c['menu'])
        self.assertIn('- mail_search:', c['menu'])
        self.assertIn('- sheet_rows:', c['menu'])
        self.assertNotIn('gmail_draft', c['menu'])  # writes are never on the menu
        shutil.rmtree(dd)

    def test_the_service_gets_codes_and_idli_runs_the_real_search(self):
        dd = _sandbox()
        sent = {}

        def service(body):
            sent['text'] = json.dumps(body)
            q = body['messages'][1]['content'].split('Question: ')[1]
            code = next(w for w in q.replace('.', ' ').split() if w.startswith('EMAIL_'))
            return {'use': [{'item': 'mail_search', 'args': {'query': f'from:{code} newer_than:7d'}}],
                    'title': 'Emails from the lead this week'}
        searched = {}

        def gmail_list(email, q, limit=10):
            searched['q'] = q
            return [{'id': 'm1'}]
        with patch('lib.minisql._count_call'), \
                patch('lib.google_api.gmail_list', side_effect=gmail_list), \
                patch('lib.google_api.gmail_raw', return_value={'from': '88profligate@gmail.com', 'subject': 'Re: meeting',
                                                               'date': '2026-11-18T09:00:00+00:00',
                                                               'new_text': 'Yes, Friday works'}):
            from lib import miniscope, home
            mini = {**home.read(dd / 'minis/lead-steps-1/mini.json'), 'id': 'lead-steps-1'}
            out = miniscope.answer(str(dd), mini, 'show my emails from 88profligate@gmail.com this week', 'service',
                                   call=service)
        self.assertNotIn('88profligate', sent['text'])
        self.assertEqual(searched['q'], 'from:88profligate@gmail.com newer_than:7d')
        self.assertIn('Yes, Friday works', out['reply'])
        self.assertIn('An outside service', out['reply'])
        self.assertIn('Nothing was drafted, booked or sent', out['reply'])
        shutil.rmtree(dd)

    def test_never_maps_with_the_9b_and_lists_meetings(self):
        dd = _sandbox('never')
        from lib import miniscope
        events = [{'id': 'e1', 'title': 'Board call', 'start': '2026-11-17T10:00:00+05:30',
                   'end': '2026-11-17T10:30:00+05:30', 'attendees': ['a@x.org'], 'declined': False},
                  {'id': 'e2', 'title': 'Declined: Meeting', 'start': '2026-11-17T13:00:00+05:30',
                   'end': '2026-11-17T13:30:00+05:30', 'attendees': [], 'declined': True}]
        with patch.object(miniscope, 'map_local', return_value={
                'use': [{'item': 'meetings', 'args': {'start': '2026-11-17', 'end': '2026-11-17'}}]}), \
                patch('lib.google_api.calendar_events', return_value=events):
            out = self.talk(dd, 'show me all my meetings from yesterday')
        self.assertEqual(out['kind'], 'mapped')
        self.assertIn('**Board call**, with a@x.org', out['reply'])
        self.assertIn('(you declined)', out['reply'])
        self.assertIn("Idli's own model picked the calendar", out['reply'])
        shutil.rmtree(dd)

    def test_menu_items_only_and_none_ends_at_fork(self):
        dd = _sandbox('never')
        from lib import miniscope
        with patch.object(miniscope, 'map_local', return_value={'use': [{'item': 'gmail_draft', 'args': {}}]}):
            out = self.talk(dd, 'send all leads a reminder')
        self.assertEqual(out['kind'], 'none')
        self.assertIn('Fork it to continue with Claude', out['reply'])
        with patch.object(miniscope, 'map_local', return_value={'none': 'It needs a new step that posts online.'}):
            out = self.talk(dd, 'post this to instagram')
        self.assertIn("can't answer that: it needs a new step", out['reply'])
        shutil.rmtree(dd)

    def test_fork_carries_the_masked_question(self):
        dd = _sandbox()
        work = Path(tempfile.mkdtemp())
        from lib import home
        with patch.dict(os.environ, {'IDLI_CLAUDE_WORK': str(work)}), \
                patch.object(home, '_drivey_workspace', return_value='wks1'), \
                patch.object(home, '_claude_terminal', return_value='t1'), \
                patch.object(home, 'type_into') as typed, patch.object(home, '_remember'), \
                patch('lib.uiswitch.show_terminal', return_value={'ok': True}):
            out = self.talk(dd, 'which leads emailed 88profligate@gmail.com twice?', fork=True)
        prompt = typed.call_args[0][1]
        self.assertEqual(out['kind'], 'fork')
        self.assertNotIn('88profligate', prompt)
        self.assertIn('could not answer', prompt)
        fork_md = (work / 'forks' / out['fork'] / 'FORK.md').read_text()
        self.assertIn('1. Read the leads sheet', fork_md)
        self.assertIn('ask the Builder', fork_md)
        shutil.rmtree(work)
        shutil.rmtree(dd)


def _route(msgs, extra=('mini_talk', 'mail_search', 'block_run')):
    from lib import modes
    tools = [{'name': 'mcp__cowork__' + t} for t in
             ('drive_fetch', 'privacy_review_open', 'claude_handoff', 'mini_open', 'mini_ask', 'binder_item') + extra]
    return modes.drivey_route({'messages': msgs, 'tools': tools, 'model': 'idli-9b'})


def _turn(name, inp, res, uid):
    return [{'role': 'assistant', 'content': [{'type': 'tool_use', 'id': uid, 'name': 'mcp__cowork__' + name,
                                               'input': inp}]},
            {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': uid,
                                          'content': [{'type': 'text', 'text': json.dumps(res)}]}]}]


def _card_answer(header, answer, uid):
    return [{'role': 'assistant', 'content': [{'type': 'tool_use', 'id': uid, 'name': 'AskUserQuestion',
                                               'input': {'questions': [{'header': header, 'question': 'q',
                                                                        'options': []}]}}]},
            {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': uid,
                                          'content': f'User has answered your questions: "q"="{answer}". You can now continue with the user\'s answers in mind.'}]}]


def _uses(out):
    return [c for c in out['content'] if c.get('type') == 'tool_use']


class RouterTests(unittest.TestCase):
    OPENED = {'id': 'lead-steps-1', 'questions': [{'id': 'q'}], 'actions': True, 'reply': 'x'}

    def opened(self):
        return [{'role': 'user', 'content': 'Open Mini: Lead replies [lead-steps-1]'}] + \
            _turn('mini_open', {'id': 'lead-steps-1'}, self.OPENED, 'u1') + \
            [{'role': 'assistant', 'content': [{'type': 'text', 'text': 'x'}]}]

    def test_a_blind_sandbox_question_goes_to_claude_not_the_9b(self):
        out = _route([{'role': 'user', 'content': 'show my busy times this week'}])
        use = _uses(out)[0]
        self.assertEqual(use['name'], 'mcp__cowork__claude_handoff')
        self.assertEqual(use['input'], {'files': [], 'question': 'show my busy times this week', 'preview': True})

    def test_the_claude_card_then_sends_it(self):
        msgs = [{'role': 'user', 'content': 'show my busy times this week'}] + \
            _turn('claude_handoff', {'files': [], 'question': 'show my busy times this week', 'preview': True},
                  {'preview_only': True, 'masked_question': 'show my busy times this week'}, 'u1')
        out = _route(msgs)
        self.assertEqual(_uses(out)[0]['name'], 'AskUserQuestion')
        self.assertEqual(_uses(out)[0]['input']['questions'][0]['header'], 'Claude')
        out = _route(msgs + _card_answer('Claude', 'Switch to Claude', 'u2'))
        self.assertEqual(_uses(out)[0]['input'], {'files': [], 'question': 'show my busy times this week'})

    def test_consent_card_yes_and_no(self):
        msgs = self.opened() + [{'role': 'user', 'content': 'list my leads'}] + \
            _turn('mini_talk', {'id': 'lead-steps-1', 'question': 'list my leads'},
                  {'kind': 'consent', 'consent': {'masked_question': 'list my leads', 'menu': 'Menu:\n- step:1',
                                                  'service': 'deepseek'}}, 'u2')
        out = _route(msgs)
        card = _uses(out)[0]['input']['questions'][0]
        self.assertEqual(card['header'], 'Mapping')
        self.assertIn('Never your emails', out['content'][0]['text'])
        yes = _uses(_route(msgs + _card_answer('Mapping', 'Yes', 'u3')))[0]
        self.assertEqual(yes['input'], {'id': 'lead-steps-1', 'question': 'list my leads', 'route': 'service'})
        no = _uses(_route(msgs + _card_answer('Mapping', 'No, Idli picks', 'u3')))[0]
        self.assertEqual(no['input']['route'], 'local')

    def test_none_offers_fork(self):
        msgs = self.opened() + [{'role': 'user', 'content': 'post to instagram'}] + \
            _turn('mini_talk', {'id': 'lead-steps-1', 'question': 'post to instagram'},
                  {'kind': 'none', 'reply': "This Mini can't answer that."}, 'u2')
        out = _route(msgs)
        self.assertEqual(_uses(out)[0]['input']['questions'][0]['header'], 'Fork')
        fork = _uses(_route(msgs + _card_answer('Fork', 'Fork it', 'u3')))[0]
        self.assertEqual(fork['input'], {'id': 'lead-steps-1', 'question': 'post to instagram', 'fork': True})

    def test_drivey_is_unchanged_for_a_typed_question(self):
        out = _route([{'role': 'user', 'content': 'show my busy times this week'}], extra=())
        self.assertFalse(_uses(out))
        self.assertIn('Add files', out['content'][0]['text'])


class DocsTests(unittest.TestCase):
    def test_pdf_text_is_masked_for_claude(self):
        from lib import docmask
        dd = _sandbox()
        work = Path(tempfile.mkdtemp())
        pdf = dd / 'drive' / 'report.pdf'
        pdf.parent.mkdir()
        pdf.write_bytes(b'%PDF')
        with patch.dict(os.environ, {'IDLI_CLAUDE_WORK': str(work)}), \
                patch('lib.privacy.Scanner', return_value=lambda text: []), \
                patch('lib.transforms.fetch_drive', return_value={'files': [{'title': 'report.pdf',
                                                                             'path': str(pdf)}]}), \
                patch.object(docmask, 'pdf_text', return_value='[page 1]\nWrite to field.lead@example.org for the data.'):
            got = docmask.prepare(str(dd), ['Drive/My Drive/study'])
        text = (work / 'docs' / 'report.txt').read_text()
        self.assertEqual(got['docs'][0]['local'], 'docs/report.txt')
        self.assertNotIn('field.lead@example.org', text)
        self.assertIn('masked by Idli', text)
        self.assertIn('docs/report.txt', docmask.note_for_claude(got['docs']))
        shutil.rmtree(work)
        shutil.rmtree(dd)


if __name__ == '__main__':
    unittest.main()
