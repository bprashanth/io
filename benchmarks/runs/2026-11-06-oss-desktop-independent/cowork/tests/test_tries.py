"""script_try's two gates in the left chat (lib/tries.py, owner 2026-11-19): nothing reaches Claude before the
second yes, a No at either gate gives Claude a plain note, and the router shows both cards."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))


def _sandbox():
    dd = Path(tempfile.mkdtemp())
    (dd / 'team.json').write_text(json.dumps({'kind': 'sandbox', 'blocks': []}))
    work = Path(tempfile.mkdtemp())
    (work / 'step.py').write_text('print("Lead Asha Verma replied: yes, Friday")\n')
    return dd, work


class Gates(unittest.TestCase):
    def run_try(self, answers):
        """Claude's script_try in a thread; the left chat answers like the router would."""
        from lib import idli_mcp, tries, home
        dd, work = _sandbox()
        posted, out = [], {}
        env = {'IDLI_DATA': str(dd), 'IDLI_CLAUDE_WORK': str(work), 'IDLI_WORKSPACE': 'wks_test'}
        with mock.patch.dict(os.environ, env), \
                mock.patch.object(home, 'post_to_left', lambda ws, kind, title: posted.append((kind, title))), \
                mock.patch.object(idli_mcp, '_script_problems', lambda p: None), \
                mock.patch.object(idli_mcp, '_masked_account', lambda v, *a: str(v).replace('Asha Verma', 'NAME_001')
                                  if isinstance(v, str) else v), \
                mock.patch.object(tries, 'GATE_WAIT', 20):
            t = threading.Thread(target=lambda: out.update(r=idli_mcp.script_try('step.py', title='Sort the replies')))
            t.start()
            while not posted:
                time.sleep(0.05)
            kind, title = posted[0]
            self.assertEqual(kind, 'Try')
            first = home.binder_item(dd, 'Try', title)
            self.assertEqual(first['gate'], 1)
            self.assertIn('Sort the replies', first['text'])
            self.assertIn('Nothing is written', first['text'])
            second = home.binder_item(dd, 'Try', title, answer=answers[0])
            if answers[0] == 'run':
                self.assertEqual(second['gate'], 2)
                self.assertIn('Asha Verma', second['shown'])        # the real output, on the left
                self.assertIn('NAME_001', second['sample'])         # what Claude would get
                self.assertNotIn('Asha', second['sample'])
                home.binder_item(dd, 'Try', title, answer=answers[1])
            t.join(10)
        return out['r']

    def test_yes_yes_sends_masked(self):
        r = self.run_try(['run', 'send'])
        self.assertIn('NAME_001', r['output'])
        self.assertNotIn('Asha', json.dumps(r))

    def test_no_at_gate_two_sends_nothing(self):
        r = self.run_try(['run', 'keep'])
        self.assertNotIn('output', r)
        self.assertIn('chose not to share', r['note'])

    def test_no_at_gate_one_runs_nothing(self):
        r = self.run_try(['no'])
        self.assertFalse(r['ran'])
        self.assertIn('chose not to run', r['note'])


class Router(unittest.TestCase):
    def test_cards(self):
        from lib import modes
        tools = [{'name': 'mcp__cowork__' + n} for n in modes.DRIVEY_TOOLS | {'binder_item', 'mini_talk', 'block_run'}]
        def turn(name, inp, res, uid):
            return [{'role': 'assistant', 'content': [{'type': 'tool_use', 'id': uid, 'name': 'mcp__cowork__' + name,
                                                       'input': inp}]},
                    {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': uid,
                                                  'content': json.dumps(res)}]}]
        msgs = [{'role': 'user', 'content': 'Try from Claude: Sort the replies [1763540000000]'}]
        out = modes.drivey_route({'messages': msgs, 'tools': tools, 'model': 'idli-9b'})
        use = [b for b in out['content'] if b.get('type') == 'tool_use'][0]
        self.assertEqual(use['input'], {'kind': 'Try', 'title': 'Sort the replies [1763540000000]'})
        msgs += turn('binder_item', use['input'], {'gate': 1, 'id': '1763540000000', 'text': 'Claude wants Idli...'}, 'u1')
        out = modes.drivey_route({'messages': msgs, 'tools': tools, 'model': 'idli-9b'})
        q = [b for b in out['content'] if b.get('type') == 'tool_use'][0]['input']['questions'][0]
        self.assertEqual(q['header'], modes.TRY_HEAD)
        msgs += [{'role': 'assistant', 'content': [{'type': 'tool_use', 'id': 'c1', 'name': 'AskUserQuestion',
                                                    'input': {'questions': [q]}}]},
                 {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': 'c1',
                                               'content': f'"{q["question"]}"="Yes". You can now continue'}]}]
        out = modes.drivey_route({'messages': msgs, 'tools': tools, 'model': 'idli-9b'})
        use = [b for b in out['content'] if b.get('type') == 'tool_use'][0]
        self.assertEqual(use['input']['answer'], 'run')
        msgs += turn('binder_item', use['input'], {'gate': 2, 'id': '1763540000000', 'shown': 'REAL',
                                                   'sample': 'NAME_001 replied'}, 'u2')
        out = modes.drivey_route({'messages': msgs, 'tools': tools, 'model': 'idli-9b'})
        self.assertIn('NAME_001 replied', out['content'][0]['text'])
        q = [b for b in out['content'] if b.get('type') == 'tool_use'][0]['input']['questions'][0]
        self.assertEqual(q['question'], modes.SEND_ASK)


if __name__ == '__main__':
    unittest.main()
