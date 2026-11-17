"""Test accounts in Chrome profiles (narrative/BUILDER_JOURNEY.md): reading signed-in emails, the team's allowlist,
the consent hook's words, browser tools refusing non-test profiles, a CDP round trip on a local page, and a team
site tool driving a profile through its door in the wall."""
import glob
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import chromectl, chromeprofiles as cp, launchsettings, teamcaps  # noqa: E402


def fake_profile(home, slug, emails=(), last=None, meta=True, state_user=None):
    d = Path(home) / 'browsers' / slug
    (d / 'Default').mkdir(parents=True, exist_ok=True)
    prefs = {'account_info': [{'email': e, 'gaia': str(i), 'full_name': 'Test'} for i, e in enumerate(emails)]}
    if last:
        prefs['google'] = {'services': {'last_signed_in_username': last}}
    (d / 'Default' / 'Preferences').write_text(json.dumps(prefs))
    if state_user:
        (d / 'Local State').write_text(json.dumps({'profile': {'info_cache': {'Default': {'user_name': state_user}}}}))
    if meta:
        (d / cp.META).write_text(json.dumps({'label': slug.title(), 'kind': 'test'}))
    return d


class Base(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix='idli-chrome-'))
        self.team = self.home / 'teams' / 'leads'
        self.team.mkdir(parents=True)
        (self.team / 'team.json').write_text(json.dumps({'name': 'Leads'}))
        self.env = patch.dict(os.environ, {'IDLI_HOME': str(self.home), 'IDLI_DATA': str(self.team)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.home, ignore_errors=True)


class Profiles(Base):
    def test_emails_from_preferences_and_local_state(self):
        fake_profile(self.home, 'me-test', ['87Test@gmail.com'], last='87test@gmail.com', state_user='x@ngo.org')
        self.assertEqual(cp.emails('me-test'), ['87test@gmail.com', 'x@ngo.org'])

    def test_tolerant_of_missing_and_broken_files(self):
        d = fake_profile(self.home, 'empty')
        (d / 'Default' / 'Preferences').write_text('{not json')
        self.assertEqual(cp.emails('empty'), [])
        (d / 'Default' / 'Preferences').write_text(json.dumps({'account_info': {'a': {'email': 'a@b.co'}},
                                                               'google': 'odd'}))
        self.assertEqual(cp.emails('empty'), ['a@b.co'])

    def test_profile_made_by_hand_lists_with_its_folder_name(self):
        fake_profile(self.home, 'lead-test', ['88test@gmail.com'], meta=False)
        rows = cp.list_profiles()
        self.assertEqual([(r['profile'], r['label'], r['emails']) for r in rows],
                         [('lead-test', 'lead-test', ['88test@gmail.com'])])

    def test_slugs_are_new_and_safe(self):
        cp.create(cp.slug_for('Leads test: me'), 'Leads test: me')
        self.assertEqual(cp.slug_for('Leads test: me'), 'leads-test-me-2')
        with self.assertRaises(ValueError):
            cp.profile_dir('../x')

    def test_allowlist_only_for_signed_in_email(self):
        fake_profile(self.home, 'me-test', ['87test@gmail.com'])
        with self.assertRaisesRegex(ValueError, 'not the account signed in'):
            cp.set_test_account(self.team, 'me-test', 'other@gmail.com', 'me')
        with self.assertRaisesRegex(ValueError, 'role'):
            cp.set_test_account(self.team, 'me-test', '87test@gmail.com', 'Me!')
        cp.set_test_account(self.team, 'me-test', '87TEST@gmail.com', 'me')
        saved = json.loads((self.team / '.idli' / 'test-accounts.json').read_text())
        self.assertEqual(saved, {'accounts': [{'email': '87test@gmail.com', 'profile': 'me-test', 'role': 'me'}]})
        self.assertFalse(cp.accounts_file(self.team).is_relative_to(self.team / 'extensions'))

    def test_refuses_unless_every_email_is_a_confirmed_test_account(self):
        d = fake_profile(self.home, 'me-test', ['87test@gmail.com'])
        with self.assertRaisesRegex(ValueError, 'not a confirmed test account'):
            cp.check_test_profile(self.team, 'me-test')
        cp.set_test_account(self.team, 'me-test', '87test@gmail.com', 'me')
        self.assertEqual(cp.check_test_profile(self.team, 'me-test'), ['87test@gmail.com'])
        # the person signs in to a second (real) account in the same window: refused from the next call
        prefs = json.loads((d / 'Default' / 'Preferences').read_text())
        prefs['account_info'].append({'email': 'director@ngo.org'})
        (d / 'Default' / 'Preferences').write_text(json.dumps(prefs))
        with self.assertRaisesRegex(ValueError, 'not a confirmed test account'):
            cp.check_test_profile(self.team, 'me-test')
        # another team never confirmed it
        other = self.home / 'teams' / 'other'
        other.mkdir()
        with self.assertRaises(ValueError):
            cp.check_test_profile(other, 'me-test')

    def test_nobody_signed_in_and_real_profiles_are_refused(self):
        fake_profile(self.home, 'blank')
        with self.assertRaisesRegex(ValueError, 'No Google account'):
            cp.check_test_profile(self.team, 'blank')
        d = fake_profile(self.home, 'real-me', ['me@ngo.org'])
        (d / cp.META).write_text(json.dumps({'label': 'Real', 'kind': 'real'}))
        self.assertIn('real account', cp.check_new_account('real-me', 'me@ngo.org', 'me'))
        with self.assertRaisesRegex(ValueError, 'real account'):
            cp.check_test_profile(self.team, 'real-me')

    def test_real_profile_mapping_is_not_built_yet(self):
        with self.assertRaisesRegex(ValueError, 'not set up in Idli yet'):
            cp.real_profile_for_role(self.team, 'me')

    def test_chrome_paths_by_system(self):
        with patch.dict(os.environ, {'IDLI_CHROME': '/x/chrome'}):
            self.assertEqual(cp.chrome_path(), '/x/chrome')
        with patch.dict(os.environ, {'IDLI_CHROME': ''}), patch.object(cp.os.path, 'exists', return_value=False), \
                patch.object(cp.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(ValueError, 'not installed'):
                cp.chrome_path()


class Hook(Base):
    def run_hook(self, args):
        r = subprocess.run([sys.executable, '-I', str(ROOT / 'desktop/idli-test-account-consent.py'), str(self.team)],
                           input=json.dumps({'tool_name': 'mcp__idli__test_account_set', 'tool_input': args}),
                           capture_output=True, text=True, env={**os.environ}, check=True)
        return json.loads(r.stdout)['hookSpecificOutput']

    def test_asks_in_idlis_words(self):
        fake_profile(self.home, 'me-test', ['87test@gmail.com'])
        out = self.run_hook({'profile': 'me-test', 'email': '87test@gmail.com', 'role': 'me'})
        self.assertEqual(out['permissionDecision'], 'ask')
        self.assertTrue(out['permissionDecisionReason'].startswith(
            'Use 87test@gmail.com in Chrome profile Me-Test as a TEST account for this team?\n'
            'Only say yes if it is not a real account.'))

    def test_refuses_an_email_not_signed_in_without_asking(self):
        fake_profile(self.home, 'me-test', ['87test@gmail.com'])
        out = self.run_hook({'profile': 'me-test', 'email': 'boss@ngo.org', 'role': 'me'})
        self.assertEqual(out['permissionDecision'], 'deny')

    def test_settings_install_the_hook_and_never_allow_it(self):
        ext = teamcaps.ensure(self.team)
        launchsettings.merge_builder(ext, self.team, ROOT)
        path = launchsettings.builder_hooks(self.team, ROOT)
        hooks = json.loads(path.read_text())['hooks']['PreToolUse']
        self.assertEqual([h['matcher'] for h in hooks], ['mcp__idli__stack_install', 'mcp__idli__test_account_set'])
        self.assertIn('idli-test-account-consent.py', hooks[1]['hooks'][0]['command'])
        s = json.loads((ext / '.claude/settings.json').read_text())
        self.assertNotIn('mcp__idli__test_account_set', s['permissions']['allow'])
        self.assertIn('mcp__idli__browser_read', s['permissions']['allow'])
        denied = s['sandbox']['filesystem']['denyRead']
        self.assertIn(str((self.team / '.idli').resolve()), denied)
        self.assertIn(str((self.home / 'browsers').resolve()), [str(Path(p)) for p in denied] +
                      [str(Path(p).resolve()) for p in denied])


class BrowserTools(Base):
    def setUp(self):
        super().setUp()
        sys.path.insert(0, str(ROOT / 'lib'))
        import idli_mcp
        self.mcp = idli_mcp

    def test_every_browser_tool_refuses_a_profile_that_is_not_a_test_account(self):
        fake_profile(self.home, 'mine', ['director@ngo.org'])
        with patch.object(cp, 'open_for_work', side_effect=AssertionError('must not open')):
            for call in (lambda: self.mcp.browser_open('mine', 'https://mail.google.com/'),
                         lambda: self.mcp.browser_read('mine'),
                         lambda: self.mcp.browser_click('mine', text='Send'),
                         lambda: self.mcp.browser_type('mine', 'e1', 'hi'),
                         lambda: self.mcp.browser_shot('mine'),
                         lambda: self.mcp.browser_tabs('mine')):
                with self.assertRaisesRegex(ValueError, 'not a confirmed test account'):
                    call()

    def test_profiles_hide_emails_until_confirmed(self):
        fake_profile(self.home, 'me-test', ['87test@gmail.com'])
        fake_profile(self.home, 'lead-test', ['88test@gmail.com'])
        d = fake_profile(self.home, 'real-me', ['me@ngo.org'])
        (d / cp.META).write_text(json.dumps({'kind': 'real'}))
        cp.set_test_account(self.team, 'me-test', '87test@gmail.com', 'me')
        rows = {r['profile']: r for r in self.mcp.profiles()['profiles']}
        self.assertNotIn('real-me', rows)
        self.assertEqual(rows['me-test']['emails'], ['87test@gmail.com'])
        self.assertTrue(rows['me-test']['confirmed_test_account'])
        self.assertNotIn('emails', rows['lead-test'])
        self.assertNotIn('88test', json.dumps(rows))

    def test_profile_new_opens_for_sign_in_without_debugging(self):
        with patch.object(cp, '_launch') as launch:
            out = self.mcp.profile_new('Leads test me')
        self.assertEqual(out['profile'], 'leads-test-me')
        self.assertEqual(launch.call_args[0][1], [])  # no --remote-debugging-port
        self.assertIn('TEST Google account', out['tell_person'])


def _chromium():
    found = sorted(glob.glob(os.path.expanduser('~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome')))
    return found[-1] if found else None


PAGE = """<html><head><title>Inbox</title></head><body><h1>Inbox</h1>
<a href="/two.html">Open the reply</a><input aria-label="Search mail"><button onclick=
"document.getElementById('o').innerText='Found '+document.querySelector('input').value">Search</button>
<p id="o"></p><input type="password" aria-label="Secret" value="hunter2"></body></html>"""

TOOL = '''
import chromectl, json
def run(inputs, args, out):
    b = chromectl.Browser('me')
    b.open(args['url'])
    page = b.read()
    ref = next(c['ref'] for c in page['controls'] if c['label'] == 'Search mail')
    b.type(ref, args['q'])
    b.click(text='Search')
    return {'found': 'Found ' + args['q'] in b.read()['text']}
'''


@unittest.skipUnless(_chromium(), "Playwright's chromium is not on this computer")
class CdpRoundTrip(Base):
    def setUp(self):
        super().setUp()
        site = self.home / 'site'
        site.mkdir()
        (site / 'index.html').write_text(PAGE)
        (site / 'two.html').write_text('<html><head><title>Reply</title></head><body>Thanks</body></html>')
        handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=str(site), **k)  # noqa: E731
        http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
        self.srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f'http://127.0.0.1:{self.srv.server_address[1]}/index.html'
        self.chrome = patch.dict(os.environ, {'IDLI_CHROME': _chromium(),
                                              'IDLI_CHROME_ARGS': '--headless=new --no-sandbox'})
        self.chrome.start()
        fake_profile(self.home, 'me-test', ['87test@gmail.com'])
        cp.set_test_account(self.team, 'me-test', '87test@gmail.com', 'me')

    def tearDown(self):
        cp.close('me-test')
        self.chrome.stop()
        self.srv.shutdown()
        super().tearDown()

    def test_builder_tools_read_type_click_and_shoot(self):
        sys.path.insert(0, str(ROOT / 'lib'))
        import idli_mcp as mcp
        self.assertEqual(mcp.browser_open('me-test', self.url)['title'], 'Inbox')
        page = mcp.browser_read('me-test', save_as='Inbox page')
        self.assertEqual(page['saved_as'], 'samples/pages/inbox-page.json')
        labels = {c['label']: c for c in page['controls']}
        self.assertNotIn('value', labels['Secret'])  # passwords are never read
        self.assertNotIn('hunter2', json.dumps(page))
        mcp.browser_type('me-test', labels['Search mail']['ref'], 'rehearsal')
        mcp.browser_click('me-test', text='Search')
        self.assertIn('Found rehearsal', mcp.browser_read('me-test')['text'])
        shot = Path(mcp.browser_shot('me-test')['path'])
        self.assertEqual(shot.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
        self.assertEqual(mcp.browser_click('me-test', text='Open the reply')['title'], 'Reply')
        self.assertEqual(mcp.browser_tabs('me-test')['tabs'][0]['title'], 'Reply')
        port = cp.debug_port('me-test')
        self.assertTrue(port)
        self.assertEqual(cp.open_for_work('me-test'), port)  # reused, not restarted
        # a saved page answers a plugin test with no browser
        replay = chromectl.Replay({self.url: json.loads(
            (self.team / 'extensions/samples/pages/inbox-page.json').read_text())})
        replay.open(self.url)
        self.assertTrue(replay.find('search mail'))

    def test_site_tool_runs_through_its_door_on_the_test_profile(self):
        sys.path.insert(0, str(ROOT / 'lib'))
        import idli_mcp as mcp
        ext = teamcaps.ensure(self.team)
        (ext / 'sites/mail').mkdir(parents=True)
        (ext / 'sites/mail/search.py').write_text(TOOL)
        (ext / 'tests/test_search.py').write_text(
            'import chromectl\nr = chromectl.Replay([{"controls": [{"ref": "e1", "label": "Search"}]}])\n'
            'assert r.find("search") == "e1"\n')
        (ext / 'manifest.json').write_text(json.dumps({'capabilities': [
            {'id': 'mail-search', 'title': 'Search mail', 'kind': 'tool', 'takes': ['none'], 'profile': 'me',
             'entry': 'sites/mail/search.py', 'test': 'tests/test_search.py'}]}))
        caps, problems = teamcaps.manifest(self.team)
        self.assertEqual(problems, [])
        out = mcp.rehearse('mail-search', {'url': self.url, 'q': 'rehearsal'})
        self.assertEqual(out, {'ok': True, 'result': {'found': True}, 'files_in_.idli-out': []}, out)
        # the Analyst's team_run never reaches the test profile: the real-account step isn't built yet
        self.assertTrue(teamcaps.run_tests(self.team)['results']['mail-search']['ok'])
        with self.assertRaisesRegex(ValueError, 'not set up in Idli yet'):
            mcp.team_run('mail-search', [], {'url': self.url, 'q': 'x'})


class Manifest(Base):
    def test_profile_tools_name_roles_and_skip_the_stack(self):
        ext = teamcaps.ensure(self.team)
        (ext / 't.py').write_text('def run(i, a, o): return {}\n')
        (ext / 'tests/test_t.py').write_text('')
        caps = [{'id': 'a', 'title': 'A', 'kind': 'tool', 'takes': ['none'], 'entry': 't.py', 'test': 'tests/test_t.py',
                 'profile': ['me', 'lead']},
                {'id': 'b', 'title': 'B', 'kind': 'tool', 'takes': ['none'], 'entry': 't.py', 'test': 'tests/test_t.py',
                 'profile': 'Not A Role'}]
        (ext / 'manifest.json').write_text(json.dumps({'capabilities': caps}))
        good, problems = teamcaps.manifest(self.team)
        self.assertEqual([c['id'] for c in good], ['a'])
        self.assertIn('profile', problems[0])
        with self.assertRaisesRegex(ValueError, 'needs the browser'):
            teamcaps.run_tool(self.team, good[0], [], {}, browsers={'me': 1})


if __name__ == '__main__':
    unittest.main()
