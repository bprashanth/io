"""Assistant -> Builder hand-offs, the team's capabilities (extensions, readers in the wall, tests, versions) and the
outside service's three answers. narrative/MODEL_TYPES.md. No Paseo, Drive or model needed."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from lib import builder, home, modes, teamcaps, teams  # noqa: E402
from test_journey import Transcript as Base  # noqa: E402

READER = '''
import csv, os, capmenu
def read(src, out):
    with open(os.path.join(out, 'lines.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['line', 'text'])
        for i, line in enumerate(l for l in capmenu.ocr_text(src).splitlines() if l.strip()):
            w.writerow([i + 1, line.strip()])
'''
TEST = '''
import csv, importlib.util, os, tempfile
spec = importlib.util.spec_from_file_location('r', 'read_images.py'); m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
out = tempfile.mkdtemp(); m.read('samples/register.png', out)
rows = list(csv.DictReader(open(os.path.join(out, 'lines.csv'))))
assert any('Asha' in r['text'] for r in rows), rows
'''


def register_png(path):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 28)
    im = Image.new('RGB', (640, 200), 'white')
    d = ImageDraw.Draw(im)
    for i, row in enumerate(['Name Village Present', 'Asha Kuli 12', 'Ravi Pune 9']):
        d.text((20, 20 + i * 60), row, fill='black', font=font)
    im.save(path)


def add_reader(dd, title='Read photos and scans (text, line by line)'):
    d = teamcaps.ensure(dd)
    register_png(d / 'samples' / 'register.png')
    (d / 'read_images.py').write_text(READER)
    (d / 'tests' / 'test_read_images.py').write_text(TEST)
    (d / 'manifest.json').write_text(json.dumps({'capabilities': [{
        'id': 'read-images', 'title': title, 'kind': 'reader', 'reads': ['images'],
        'entry': 'read_images.py', 'test': 'tests/test_read_images.py'}]}))
    return d


class Transcript(Base):
    def __init__(self, model='idli-9b'):
        super().__init__(model)
        self.j['tools'].append({'name': 'mcp__cowork__builder_open'})


class RouterTests(unittest.TestCase):
    def test_image_the_team_cant_read_offers_the_builder(self):
        t = Transcript(); t.said('What do these registers say? @Drive/register.jpg')
        t.result({'files': [], 'unsupported': ['register.jpg'], 'missing': ['images'], 'team': 'Insights',
                  'labels': ['images']})
        card = t.tool()['input']['questions'][0]
        self.assertEqual(card['header'], 'Builder')
        self.assertEqual(card['question'], "Insights can't read images yet. The Builder can add that to Insights. "
                                           'Build it with the Builder?')
        self.assertEqual([o['label'] for o in card['options']], ['Build it', 'Not now'])
        t.choose('Build it')
        self.assertTrue(t.tool()['name'].endswith('builder_open'))
        self.assertEqual(t.tool()['input'], {'request': 'What do these registers say?', 'kinds': ['images'],
                                             'files': ['register.jpg']})
        t.result({'reply': 'The Builder has your request on the right.'})
        self.assertIn('Builder has your request', t.text())

    def test_not_now_changes_nothing(self):
        t = Transcript(); t.said('@Drive/clip.mp4')
        t.result({'files': [], 'unsupported': ['clip.mp4'], 'missing': ['video'], 'team': 'Insights', 'labels': ['videos']})
        t.choose('Not now')
        self.assertEqual(t.text(), 'OK. Nothing changes.')

    def test_without_the_builder_tool_the_old_advice_stays(self):
        t = Base(); t.said('@Drive/report.pdf'); t.result({'files': [], 'unsupported': ['report.pdf']})
        self.assertIn('spreadsheet copies', t.text())

    def test_some_files_read_others_need_the_builder(self):
        t = Transcript(); t.said('Compare @Drive/visits.xlsx @Drive/photo.png')
        t.result({'files': [{'local': 'drive/visits.xlsx', 'title': 'Visits'}], 'unsupported': ['photo.png'],
                  'missing': ['images'], 'team': 'Insights', 'labels': ['images'], 'masked_question': 'Compare'})
        self.assertEqual(t.tool()['input']['questions'][0]['header'], 'Privacy')
        self.assertIn('Type "build it"', t.text())
        t.result('dismissed')
        t.said('build it')
        self.assertTrue(t.tool()['name'].endswith('builder_open'))
        self.assertEqual(t.tool()['input']['kinds'], ['images'])

    def test_asking_about_photos_with_no_file(self):
        t = Transcript(); t.said('Can you read photos of our attendance registers?')
        self.assertEqual(t.tool()['input'], {'request': 'Can you read photos of our attendance registers?',
                                             'preview': True})
        t.result({'team': 'Insights', 'missing': ['images'], 'labels': ['images']})
        self.assertEqual(t.tool()['input']['questions'][0]['header'], 'Builder')
        t.choose('Build it')
        self.assertEqual(t.tool()['input']['request'], 'Can you read photos of our attendance registers?')
        # a team that already reads images: no card, pick files as usual
        t = Transcript(); t.said('Can you read photos?'); t.result({'team': 'Insights', 'missing': [], 'labels': []})
        self.assertEqual(t.text(), modes.PICK_FILES)

    def mini(self, **more):
        t = Transcript(); t.said('Open Mini: Visits [visits]')
        t.result({'id': 'visits', 'files': [{'local': 'drive/visits.xlsx'}], 'can_query': True,
                  'questions': [{'id': 'total', 'question': 'How many visits in each ward?', 'params': {}}],
                  'reply': 'Visits', **more})
        return t

    def test_inside_a_mini_photos_go_the_usual_way_not_to_the_builder(self):
        t = self.mini()
        with patch.object(modes._lib('minimap'), 'map_questions', return_value={}):
            t.said('read the photos of the registers')
        self.assertTrue(t.tool()['name'].endswith('mini_ask'))
        self.assertTrue(t.tool()['input']['preview'])

    def test_yes_at_setup_skips_the_card(self):
        t = self.mini(query_auto=True)
        with patch.object(modes._lib('minimap'), 'map_questions', return_value={}):
            t.said('which ward had the fewest visits in March?')
        self.assertIn('Only masked data is sent', t.text())
        self.assertEqual(t.tool()['input'], {'id': 'visits', 'question': 'which ward had the fewest visits in March?'})


class CapabilityTests(unittest.TestCase):
    def setUp(self):
        self.dd = tempfile.mkdtemp()
        (Path(self.dd) / 'team.json').write_text('{"name": "Insights"}')

    def tearDown(self):
        shutil.rmtree(self.dd, ignore_errors=True)

    def test_untested_reader_does_not_count(self):
        add_reader(self.dd)
        self.assertEqual(teamcaps.readable(self.dd), ['spreadsheet'])
        out = teamcaps.run_tests(self.dd)
        self.assertTrue(out['results']['read-images']['ok'], out)
        self.assertEqual(teamcaps.readable(self.dd), ['spreadsheet', 'images'])
        # a change after the test switches it off until it passes again
        with open(Path(self.dd) / 'extensions' / 'read_images.py', 'a') as f:
            f.write('\n# changed\n')
        self.assertEqual(teamcaps.readable(self.dd), ['spreadsheet'])

    def test_a_failing_test_keeps_it_off(self):
        d = add_reader(self.dd)
        (d / 'tests' / 'test_read_images.py').write_text('raise SystemExit(1)\n')
        self.assertFalse(teamcaps.run_tests(self.dd)['results']['read-images']['ok'])
        self.assertNotIn('images', teamcaps.readable(self.dd))

    def test_bad_manifest_entries_are_reported(self):
        d = teamcaps.ensure(self.dd)
        (d / 'manifest.json').write_text(json.dumps({'capabilities': [
            {'id': 'x', 'title': 'X', 'reads': ['spreadsheet'], 'entry': 'nope.py', 'test': 't.py'},
            {'id': '../evil', 'title': 'E'}]}))
        caps, problems = teamcaps.manifest(self.dd)
        self.assertEqual(caps, [])
        self.assertEqual(len(problems), 2)

    def test_reader_runs_in_the_wall_without_network_or_home(self):
        d = add_reader(self.dd)
        (d / 'read_images.py').write_text(READER + '''
import socket, pathlib
def read(src, out, _r=read):
    try:
        socket.create_connection(('1.1.1.1', 53), timeout=2); raise SystemExit('network reached')
    except OSError:
        pass
    assert not any(pathlib.Path.home().glob('.ssh/*')), 'home is visible'
    _r(src, out)
''')
        teamcaps.run_tests(self.dd)
        self.assertIn('images', teamcaps.readable(self.dd))
        src = Path(self.dd) / 'drive' / 'register.jpg'
        src.parent.mkdir()
        register_png(src)
        tables = teamcaps.run_reader(self.dd, teamcaps.reader_for(self.dd, 'images'), src)
        self.assertEqual([t.name for t in tables], ['register.jpg.csv'])
        self.assertIn('Asha Kuli 12', tables[0].read_text())

    def test_versions_and_going_back(self):
        add_reader(self.dd)
        teamcaps.run_tests(self.dd)
        teamcaps.checkpoint(self.dd, 'Read images')
        self.assertIn('images', teamcaps.readable(self.dd))
        first = teamcaps.versions(self.dd)[-1]
        self.assertEqual(first['message'], 'Start')
        teamcaps.restore(self.dd, first['id'])
        self.assertEqual(teamcaps.readable(self.dd), ['spreadsheet'])
        msgs = [v['message'] for v in teamcaps.versions(self.dd)]
        self.assertEqual(msgs[0], 'Went back to: Start')
        self.assertIn('Read images', msgs)  # going back can itself be undone
        with self.assertRaises(ValueError):
            teamcaps.restore(self.dd, 'zzz')

    def test_git_tracks_definitions_only(self):
        d = add_reader(self.dd)
        (d / '.claude').mkdir()
        (d / '.claude' / 'settings.json').write_text('{}')
        teamcaps.checkpoint(self.dd, 'x')
        tracked = teamcaps._git(d, 'ls-files').split()
        self.assertNotIn('.claude/settings.json', tracked)
        self.assertIn('manifest.json', tracked)

    def test_analyst_is_told_the_capabilities_and_the_way_out(self):
        text = teamcaps.describe(self.dd, 'Insights')
        self.assertIn("Insights can't read these yet: images", text)
        self.assertIn('builder_open', text)
        add_reader(self.dd); teamcaps.run_tests(self.dd)
        self.assertIn('Read photos and scans', teamcaps.describe(self.dd, 'Insights'))
        self.assertNotIn('yet: images', teamcaps.describe(self.dd, 'Insights'))

    def test_builder_check_and_prompt_are_masked(self):
        self.assertEqual(builder.check(self.dd, 'can you read these photos?')['missing'], ['images'])
        with patch('lib.privacy.mask_free_text', return_value='read photos of NAME_001 forms'):
            p = builder.prompt_for(self.dd, 'read photos of Meera Singh forms', ['images'], ['a.jpg'])
        self.assertEqual(p, 'Request from the Insights team: "read photos of NAME_001 forms" Insights can\'t read '
                            'images yet (.jpg files). Read the build-team skill first.')

    def test_drive_fetch_uses_the_reader(self):
        from lib import drivestubs
        add_reader(self.dd); teamcaps.run_tests(self.dd)
        fake = Path(tempfile.mkdtemp())
        register_png(fake / 'f1.png')
        (fake / 'f1.xlsx').write_bytes((fake / 'f1.png').read_bytes())  # the fake Drive serves <id>.xlsx bytes
        entries = {'register.jpg': {'id': 'f1', 'url': 'x', 'kind': 'image/jpeg', 'title': 'register.jpg'},
                   'clip.mp4': {'id': 'f2', 'url': 'x', 'kind': 'video/mp4', 'title': 'clip.mp4'}}
        with patch.dict(os.environ, {'IDLI_DRIVE_FAKE': str(fake)}), \
                patch.object(drivestubs, 'refresh', return_value=entries):
            out = drivestubs.fetch(self.dd, ['Drive/register.jpg', 'Drive/clip.mp4'], spreadsheets_only=True)
        self.assertEqual([f['local'] for f in out['files']], ['drive/register.jpg.csv'])
        self.assertEqual(out['unsupported'], ['clip.mp4'])
        self.assertEqual(out['missing'], ['video'])
        shutil.rmtree(fake)


class OutsideServiceTests(unittest.TestCase):
    def test_three_answers(self):
        self.assertEqual(teams.outside_choice('always'), 'always')
        self.assertEqual(teams.outside_choice('ask'), 'ask')
        self.assertEqual(teams.outside_choice(True), 'ask')  # teams made before 2026-11-16
        self.assertIs(teams.outside_choice(False), False)
        d = tempfile.mkdtemp()
        teams.set_outside(d, 'always')
        self.assertEqual(sorted(os.listdir(d)), ['query-service-always'])
        teams.set_outside(d, False)
        self.assertEqual(sorted(os.listdir(d)), ['no-query-service'])
        teams.set_outside(d, 'ask')
        self.assertEqual(os.listdir(d), [])
        shutil.rmtree(d)


if __name__ == '__main__':
    unittest.main()


class OpenBuilderTests(unittest.TestCase):
    def test_opens_a_builder_terminal_once_then_types_into_it(self):
        dd = tempfile.mkdtemp()
        (Path(dd) / 'team.json').write_text('{"name": "Insights"}')
        calls, terms = [], []

        def cli(*args):
            calls.append(args)
            if args[:2] == ('workspace', 'ls'):
                return json.dumps([{'workspaceId': 'w1', 'cwd': dd}])
            if args[:2] == ('terminal', 'ls'):
                return json.dumps(terms)
            if args[:2] == ('terminal', 'create'):
                terms.append({'id': 't9', 'workspaceId': 'w1', 'name': 'Builder'})
                return json.dumps({'id': 't9'})
            return ''
        from lib import uiswitch
        with patch.object(home, 'cli', side_effect=cli), \
                patch.object(uiswitch, 'show_terminal', return_value={'ok': True}) as shown, \
                patch('lib.privacy.mask_free_text', side_effect=lambda d, t: t):
            out = builder.open_builder(dd, 'read photos', 'w1', ['images'])
            self.assertEqual(out['terminal'], 't9')
            launch = [c for c in calls if c[:2] == ('terminal', 'send-keys') and 'claude-builder.sh' in c[-1]]
            self.assertEqual(len(launch), 1)
            self.assertIn('IDLI_DATA=', launch[0][-1])
            shown.assert_called_with('w1', 't9', 'right')
            builder.open_builder(dd, 'and PDFs', 'w1', ['pdf'])
        self.assertEqual(len([c for c in calls if c[:2] == ('terminal', 'create')]), 1)
        self.assertTrue(any('and PDFs' in c[-1] for c in calls if c[:2] == ('terminal', 'send-keys')))
        self.assertTrue((Path(dd) / 'extensions' / '.git').exists())
        with patch.object(home, 'cli', side_effect=FileNotFoundError('paseo')), \
                patch('lib.privacy.mask_free_text', side_effect=lambda d, t: t):
            with self.assertRaisesRegex(ValueError, 'could not open the Builder'):
                builder.open_builder(dd, 'x', 'w1')
        shutil.rmtree(dd)


class TypedBuilderTests(unittest.TestCase):
    def test_open_the_builder_by_typing(self):
        t = Transcript(); t.said('Open the Builder')
        self.assertTrue(t.tool()['name'].endswith('builder_open'))
        self.assertIn('Ask what the team should be able to do', t.tool()['input']['request'])
        t = Transcript(); t.said('please open the builder: we need to read PDFs of funder reports')
        self.assertEqual(t.tool()['input']['request'], 'we need to read PDFs of funder reports')
