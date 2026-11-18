"""Transform blocks (lib/transforms.py, narrative/SANDBOXES.md "Three levels"): the Builder writes readers and
transforms; Idli checks them once (scan plus fake-data test) and adds them to a sandbox; the left chat runs them on
the real files. The same scan keeps Sandbox Claude's Mini scripts to trusted imports and the sandbox's blocks."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib import transforms  # noqa: E402

TEMPLATE = ROOT / 'idli' / 'builder-outside' / 'block-template' / 'read_pdfs'
MINI_HEAD = 'import os, sys; sys.path.insert(0, os.environ["IDLI_COWORK"]); from lib import blocks\n'


class Scan(unittest.TestCase):
    def problems(self, code, kind='block'):
        return transforms.scan(code, kind)

    def test_trusted_code_passes(self):
        self.assertEqual(self.problems('import io, json\nfrom pypdf import PdfReader\nimport pandas as pd\n'), [])

    def test_untrusted_things_are_refused_plainly(self):
        for code, word in [('import requests', 'requests'), ('import socket', 'socket'),
                           ('import subprocess', 'subprocess'), ('import os', 'os'), ('open("x")', 'open'),
                           ('eval("1")', 'eval'), ('kit._model', '_model'), ('x = "https://a.b"', 'web address'),
                           ('p = "/etc/passwd"', 'path'), ('p = "../x"', 'path'), ('().__class__', '__class__'),
                           ('import urllib.request', 'urllib'), ('from . import x', 'relative')]:
            got = ' '.join(self.problems(code))
            self.assertIn(word, got, code)

    def test_mini_scripts_keep_their_header_and_blocks(self):
        self.assertEqual(self.problems(MINI_HEAD + 'import argparse, json\nblocks.gmail_search("x")\n', 'mini'), [])
        self.assertTrue(self.problems(MINI_HEAD + 'os.system("ls")', 'mini'))
        self.assertTrue(self.problems(MINI_HEAD + 'blocks.os.system("ls")', 'mini'))
        self.assertTrue(self.problems(MINI_HEAD + 'import subprocess', 'mini'))
        self.assertTrue(self.problems('from lib import google_api', 'mini'))
        self.assertTrue(self.problems('import os\nos.path.exists("x")', 'mini'))

    def test_os_is_not_for_blocks(self):
        self.assertTrue(self.problems(MINI_HEAD, 'block'))


class Blocks(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.block = self.tmp / 'builder' / 'read_pdfs'
        shutil.copytree(TEMPLATE, self.block)
        self.sandbox = self.tmp / 'sb'
        self.sandbox.mkdir()
        (self.sandbox / 'team.json').write_text(json.dumps({'kind': 'sandbox', 'blocks': ['drive_files']}))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_the_example_passes_and_its_card_is_plain(self):
        res = transforms.check(self.block)
        self.assertTrue(res['ok'], res)
        self.assertEqual(res['card'], 'Add block: Read PDFs. Uses pypdf. Reads PDFs you give it. Sends nothing.')
        self.assertLess(res['seconds'], 10)

    def test_a_bad_import_is_refused_before_anyone_is_asked(self):
        p = self.block / 'block.py'
        p.write_text('import requests\n' + p.read_text())
        res = transforms.check(self.block)
        self.assertFalse(res['ok'])
        self.assertIn('requests, which is not on the trusted list', ' '.join(res['problems']))
        self.assertFalse(transforms.add(self.sandbox, self.block)['ok'])

    def test_an_action_is_not_a_transform(self):
        m = json.loads((self.block / 'manifest.json').read_text())
        m['level'] = 'action'
        (self.block / 'manifest.json').write_text(json.dumps(m))
        self.assertIn('actions are built by our team', ' '.join(transforms.check(self.block)['problems']))

    def test_a_failing_test_is_refused(self):
        (self.block / 'test_block.py').write_text('def test(kit, run):\n    assert run()["used"] == ["nope"]\n')
        res = transforms.check(self.block)
        self.assertFalse(res['ok'])
        self.assertIn('its test failed', res['problems'][0])

    def test_added_then_run_on_the_real_files(self):
        self.assertTrue(transforms.add(self.sandbox, self.block)['ok'])
        self.assertIn('read_pdfs', json.loads((self.sandbox / 'team.json').read_text())['transforms'])
        self.assertEqual(transforms.for_kinds(self.sandbox, ['pdf'])[0], 'read_pdfs')
        from lib.transformkit import Kit
        pdf = self.tmp / 'a.pdf'
        pdf.write_bytes(Kit.fake_pdf('Strategy is about choosing what not to do.'))
        files = {'files': [{'title': 'A.pdf', 'kind': 'pdf', 'path': str(pdf), 'id': 'x1'}]}
        # the run's 9B calls are answered by a stand-in model
        answers = iter(['- choosing what not to do', 'Main theme: trade-offs (A.pdf)'])
        with mock.patch.object(transforms, 'fetch_drive', return_value=files), \
                mock.patch.dict(os.environ, {'IDLI_9B_URL': 'http://127.0.0.1:9'}), \
                mock.patch('lib.stackwall.ModelDoor._forward', side_effect=lambda *a: (200, json.dumps(
                    {'choices': [{'message': {'content': next(answers)}}]}).encode())):
            out = transforms.run(self.sandbox, 'read_pdfs', {'paths': ['Drive/x'], 'question': 'themes?'})
        self.assertEqual(out['used'], ['A.pdf'])
        self.assertIn('trade-offs', out['reply'])
        cached = list((self.sandbox / '.idli' / 'blocks' / 'read_pdfs' / 'cache').glob('*.json'))
        self.assertEqual(len(cached), 2)  # the text and the summary are kept for next time

    def test_a_block_changed_after_its_check_does_not_run(self):
        transforms.add(self.sandbox, self.block)
        p = self.sandbox / 'blocks' / 'read_pdfs' / 'block.py'
        p.write_text(p.read_text() + '\n# changed\n')
        self.assertIn('changed after it was checked', transforms.run(self.sandbox, 'read_pdfs', {})['error'])


class Router(unittest.TestCase):
    TOOLS = [{'name': 'mcp__cowork__' + t} for t in
             ('drive_fetch', 'privacy_review_open', 'claude_handoff', 'mini_open', 'mini_ask', 'binder_item',
              'mini_talk', 'block_run')]

    def result(self, uid, obj):
        return {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': uid,
                                             'content': [{'type': 'text', 'text': json.dumps(obj)}]}]}

    def use(self, uid, name, inp):
        return {'role': 'assistant', 'content': [{'type': 'tool_use', 'id': uid, 'name': 'mcp__cowork__' + name,
                                                  'input': inp}]}

    def route(self, msgs):
        from lib import modes
        out = modes.drivey_route({'messages': msgs, 'tools': self.TOOLS, 'model': 'idli-9b'})
        return out['content']

    def test_pdfs_go_to_the_sandbox_block_then_follow_ups_too(self):
        fetch = {'paths': ['Drive/Strategy Classics'], 'question': 'what are the main themes?'}
        msgs = [{'role': 'user', 'content': '@"Drive/Strategy Classics" what are the main themes?'},
                self.use('u1', 'drive_fetch', fetch),
                self.result('u1', {'files': [], 'unsupported': ['a.pdf'], 'missing': ['pdf'], 'skipped': {'PDF': 18},
                                   'folders': ['Strategy Classics'], 'block': {'name': 'read_pdfs',
                                                                               'title': 'Read PDFs'}})]
        out = self.route(msgs)
        self.assertIn('Reading 18 PDFs with Read PDFs', out[0]['text'])
        self.assertEqual(out[1]['name'], 'mcp__cowork__block_run')
        self.assertEqual(out[1]['input'], {'name': 'read_pdfs', **fetch})
        msgs += [self.use('u2', 'block_run', out[1]['input']), self.result('u2', {'reply': 'Themes: ...'})]
        self.assertEqual(self.route(msgs)[0]['text'], 'Themes: ...')
        msgs += [{'role': 'assistant', 'content': [{'type': 'text', 'text': 'Themes: ...'}]},
                 {'role': 'user', 'content': 'which ones talk about competition?'}]
        out = self.route(msgs)
        self.assertEqual(out[1]['input'], {'name': 'read_pdfs', 'paths': ['Drive/Strategy Classics'],
                                           'question': 'which ones talk about competition?'})

    def test_without_a_block_it_still_points_to_the_builder(self):
        msgs = [{'role': 'user', 'content': '@"Drive/S" themes?'},
                self.use('u1', 'drive_fetch', {'paths': ['Drive/S'], 'question': 'themes?'}),
                self.result('u1', {'files': [], 'unsupported': ['a.pdf'], 'missing': ['pdf'], 'skipped': {'PDF': 2},
                                   'folders': ['S']})]
        self.assertIn('ask the Builder', self.route(msgs)[0]['text'])


class Mcp(unittest.TestCase):
    def test_mini_scripts_are_checked_in_a_sandbox(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / 'team.json').write_text(json.dumps({'kind': 'sandbox', 'blocks': ['gmail_read']}))
        bad = tmp / 'bad.py'
        bad.write_text('import subprocess\n')
        with mock.patch.dict(os.environ, {'IDLI_DATA': str(tmp), 'IDLI_CLAUDE_WORK': str(tmp), 'IDLI_ROLE': ''}):
            from lib import idli_mcp
            with self.assertRaises(ValueError) as e:
                idli_mcp.script_try('bad.py')
        self.assertIn('not on the trusted list', str(e.exception))
        shutil.rmtree(tmp)


if __name__ == '__main__':
    unittest.main()
