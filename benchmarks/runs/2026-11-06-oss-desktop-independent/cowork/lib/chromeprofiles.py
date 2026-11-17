"""Test accounts in real Google Chrome profiles (narrative/BUILDER_JOURNEY.md).

Google refuses sign-in inside Paseo's embedded browser ("This browser or app may not be secure"), so the accounts the
Builder works on live in real Chrome, one profile (a Chrome --user-data-dir) per account, under
~/idli-insights/browsers/<slug>/. The person creates a profile and signs in to it. Idli opens it without remote
debugging for that (Google may refuse sign-in when debugging is on). When the Builder works, Idli relaunches the
profile with DevTools on 127.0.0.1 (a free port Chrome picks and writes to DevToolsActivePort in the profile folder).

A team trusts a profile only through <team>/.idli/test-accounts.json, which sits outside extensions/ so the Builder
can't edit it. Entries are added only by the Builder's test_account_set tool, after the person said yes to a prompt
Idli words (desktop/idli-test-account-consent.py), and only for an email that is signed in to that profile. Every
browser tool refuses a profile unless every Google email signed in to it is a confirmed test account of the team.

This module reads only the profile's preference files to list signed-in emails. It never reads cookies, saved
passwords or login databases.
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

SLUG = re.compile(r'[a-z0-9][a-z0-9-]{0,39}')
ROLE = re.compile(r'[a-z][a-z0-9-]{0,19}')
EMAIL = re.compile(r'[^@\s]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,}')
META = 'idli-profile.json'
SIGN_IN_URL = 'https://accounts.google.com/'
# DevTools is on 127.0.0.1: never through a proxy from the environment
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def root():
    return Path(os.environ.get('IDLI_HOME') or '~/idli-insights').expanduser() / 'browsers'


def profile_dir(slug):
    if not SLUG.fullmatch(str(slug or '')):
        raise ValueError('That is not one of the Chrome profiles. Call profiles for the list.')
    return root() / slug


def _meta(slug):
    try:
        return json.loads((profile_dir(slug) / META).read_text())
    except (OSError, ValueError):
        return {}


def _write_meta(slug, meta):
    d = profile_dir(slug)
    fd, tmp = tempfile.mkstemp(dir=d)
    with os.fdopen(fd, 'w') as f:
        json.dump(meta, f, indent=2)
    os.replace(tmp, d / META)


def slug_for(label):
    """A new, unused folder name for a profile label ("Leads test 1" -> leads-test-1)."""
    base = re.sub(r'[^a-z0-9]+', '-', str(label or '').lower()).strip('-')[:32] or 'profile'
    slug, n = base, 2
    while (root() / slug).exists():
        slug, n = f'{base}-{n}', n + 1
    return slug


def create(slug, label):
    """Make the profile folder (Chrome fills it at the first start). Safe to call again; the label is updated."""
    d = profile_dir(slug)
    d.mkdir(parents=True, exist_ok=True)
    os.chmod(d, 0o700)
    meta = _meta(slug)
    meta.update({'label': ' '.join(str(label or slug).split())[:60] or slug, 'kind': meta.get('kind', 'test')})
    meta.setdefault('created', int(time.time()))
    _write_meta(slug, meta)
    return d


def label(slug):
    return _meta(slug).get('label') or slug


def exists(slug):
    """A profile folder: made by Idli (with idli-profile.json) or by hand with google-chrome --user-data-dir."""
    try:
        d = profile_dir(slug)
    except ValueError:
        return False
    return d.is_dir() and any((d / f).exists() for f in (META, 'Local State', 'Default'))


# ---- who is signed in (preference files only) ----

def _json(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError, UnicodeDecodeError):
        return {}


def _emails_in(obj):
    out = set()
    if isinstance(obj, dict):
        obj = obj.values()
    for item in obj if isinstance(obj, (list, tuple, type({}.values()))) else []:
        if isinstance(item, dict):
            e = item.get('email')
            if isinstance(e, str) and EMAIL.fullmatch(e.strip()):
                out.add(e.strip().lower())
    return out


def emails(slug):
    """The Google accounts signed in to this profile, read from Chrome's own files: each profile's Preferences
    ("account_info", the accounts Chrome knows) and "Local State" (the profile's signed-in user). Tolerant of missing
    or partial files: a profile Chrome hasn't written yet has none."""
    d = profile_dir(slug)
    found = set()
    state = _json(d / 'Local State')
    cache = ((state.get('profile') or {}).get('info_cache') or {}) if isinstance(state, dict) else {}
    subdirs = {'Default'} | (set(cache) if isinstance(cache, dict) else set())
    for info in (cache.values() if isinstance(cache, dict) else []):
        user = info.get('user_name') if isinstance(info, dict) else None
        if isinstance(user, str) and EMAIL.fullmatch(user.strip()):
            found.add(user.strip().lower())
    for sub in subdirs:
        if not re.fullmatch(r'[\w .-]{1,40}', str(sub)):
            continue
        prefs = _json(d / sub / 'Preferences')
        if isinstance(prefs, dict):
            found |= _emails_in(prefs.get('account_info') or [])
            # the last account signed in to Chrome itself (verified on the laptop, 2026-11-17). It can outlive a
            # sign-out; counting it only makes the check stricter.
            last = ((prefs.get('google') or {}).get('services') or {}).get('last_signed_in_username') \
                if isinstance(prefs.get('google'), dict) else None
            if isinstance(last, str) and EMAIL.fullmatch(last.strip()):
                found.add(last.strip().lower())
    return sorted(found)


def list_profiles():
    """Every profile with its label and signed-in emails (Idli's own view; the Builder gets a filtered one)."""
    out = []
    base = root()
    for d in sorted(base.iterdir()) if base.is_dir() else []:
        if not SLUG.fullmatch(d.name) or not exists(d.name):
            continue
        meta = _meta(d.name)
        out.append({'profile': d.name, 'label': meta.get('label') or d.name, 'kind': meta.get('kind', 'test'),
                    'emails': emails(d.name), 'running': bool(running_pids(d.name)),
                    'debugging': bool(debug_port(d.name))})
    return out


# ---- the team's test accounts (<team>/.idli/test-accounts.json; outside extensions/) ----

def accounts_file(data_dir):
    return Path(data_dir).resolve() / '.idli' / 'test-accounts.json'


def test_accounts(data_dir):
    raw = _json(accounts_file(data_dir))
    rows = raw.get('accounts') if isinstance(raw, dict) else None
    good = []
    for r in rows if isinstance(rows, list) else []:
        if isinstance(r, dict) and isinstance(r.get('email'), str) and SLUG.fullmatch(str(r.get('profile', ''))):
            good.append({'email': r['email'].strip().lower(), 'profile': r['profile'], 'role': str(r.get('role') or '')})
    return good


def check_new_account(slug, email, role):
    """Plain reasons why (profile, email, role) can't become a test account, or None when it can."""
    if not exists(slug):
        return 'That is not one of the Chrome profiles. Call profiles for the list.'
    if _meta(slug).get('kind') == 'real':
        return 'That profile is for a real account. Only Idli uses it.'
    if not ROLE.fullmatch(str(role or '')):
        return 'Give the account a short role in lowercase, such as me or lead.'
    email = str(email or '').strip().lower()
    if not EMAIL.fullmatch(email):
        return 'Give the email address that is signed in to the profile.'
    have = emails(slug)
    if email not in have:
        return (f'{email} is not signed in to the Chrome profile {label(slug)} yet. Ask the person to sign in there '
                '(Chrome can take a few seconds to save it), then try again.' if not have else
                f'{email} is not the account signed in to the Chrome profile {label(slug)}. Ask the person which '
                'email they signed in with.')
    return None


def set_test_account(data_dir, slug, email, role):
    """Record a confirmed test account. Only called from the Builder's test_account_set, behind the person's yes."""
    why = check_new_account(slug, email, role)
    if why:
        raise ValueError(why)
    email = email.strip().lower()
    rows = [r for r in test_accounts(data_dir) if r['email'] != email and r['role'] != role]
    rows.append({'email': email, 'profile': slug, 'role': role})
    path = accounts_file(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    with os.fdopen(fd, 'w') as f:
        json.dump({'accounts': rows}, f, indent=2)
    os.replace(tmp, path)
    return rows


def is_confirmed(data_dir, slug, email, role=None):
    return any(r['email'] == str(email).strip().lower() and r['profile'] == slug and (role is None or r['role'] == role)
               for r in test_accounts(data_dir))


def check_test_profile(data_dir, slug):
    """Raise ValueError (plain words) unless every Google email signed in to this profile is a confirmed test account
    of this team. Called before every browser action, so an account signed in later is caught."""
    if not exists(slug):
        raise ValueError('That is not one of the Chrome profiles. Call profiles for the list.')
    if _meta(slug).get('kind') == 'real':
        raise ValueError('That profile is for a real account. Only Idli uses it, never the Builder.')
    have = emails(slug)
    if not have:
        raise ValueError(f'No Google account is signed in to {label(slug)} yet, so it is not a confirmed test '
                         'account. Ask the person to sign in, then confirm it with test_account_set.')
    confirmed = {r['email'] for r in test_accounts(data_dir)}
    if any(e not in confirmed for e in have):
        raise ValueError(f'{label(slug)} has an account signed in that is not a confirmed test account for this team. '
                         'Ask the person which email it is. If it is a test account, confirm it with test_account_set. '
                         'Never use a real account.')
    return have


def profile_for_role(data_dir, role):
    """The test profile for a role ("me", "lead"), checked."""
    row = next((r for r in test_accounts(data_dir) if r['role'] == role), None)
    if not row:
        raise ValueError(f'No test account has the role {role} yet. Confirm one with test_account_set.')
    check_test_profile(data_dir, row['profile'])
    return row['profile']


def real_profile_for_role(data_dir, role):
    """The REAL account's profile for a role, used only by Idli's team_run (never by the Builder).

    TODO(real accounts): nothing writes <team>/.idli/real-accounts.json yet. The next step is a page where the person
    signs in to a separate profile (kind "real") that only Idli opens, and maps it to the role; the first real runs
    are "draft and show me", and the private 9B reads real content."""
    raw = _json(Path(data_dir).resolve() / '.idli' / 'real-accounts.json')
    rows = raw.get('accounts') if isinstance(raw, dict) else None
    row = next((r for r in rows if isinstance(r, dict) and r.get('role') == role), None) if isinstance(rows, list) else None
    if not row or not SLUG.fullmatch(str(row.get('profile', ''))) or _meta(row['profile']).get('kind') != 'real':
        raise ValueError('This tool works on your real account in Chrome, and that step is not set up in Idli yet.')
    return row['profile']


# ---- Chrome itself ----

def chrome_path():
    """Google Chrome on this computer (IDLI_CHROME overrides, for tests)."""
    if os.environ.get('IDLI_CHROME'):
        return os.environ['IDLI_CHROME']
    if sys.platform == 'darwin':
        cands = ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                 os.path.expanduser('~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')]
    elif os.name == 'nt':
        cands = [os.path.join(os.environ.get(v, ''), 'Google', 'Chrome', 'Application', 'chrome.exe')
                 for v in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA') if os.environ.get(v)]
    else:
        cands = [shutil.which(n) or '' for n in ('google-chrome', 'google-chrome-stable', 'chromium',
                                                 'chromium-browser')] + ['/opt/google/chrome/chrome']
    found = next((c for c in cands if c and os.path.exists(c)), None)
    if not found:
        raise ValueError('Google Chrome is not installed on this computer. Install it from google.com/chrome, then '
                         'try again.')
    return found


def _alive(pid):
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if os.name == 'nt':
        r = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], capture_output=True, text=True)
        return str(pid) in r.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _same_dir(arg, want):
    if not arg.startswith('--user-data-dir='):
        return False
    v = arg.split('=', 1)[1].strip('"\'')
    try:
        return os.path.realpath(os.path.expanduser(v)) == want
    except (OSError, ValueError):
        return False


def running_pids(slug):
    """Chrome's main process for this profile (not its helpers), found by its --user-data-dir (however it was typed:
    the person may have started it by hand with a trailing slash or ~)."""
    want = os.path.realpath(profile_dir(slug))
    pids = []
    if sys.platform.startswith('linux') and os.path.isdir('/proc'):
        for p in os.listdir('/proc'):
            if not p.isdigit():
                continue
            try:
                with open(f'/proc/{p}/cmdline', 'rb') as f:
                    args = [a for a in f.read().decode(errors='replace').split('\0') if a]
            except OSError:
                continue
            if len(args) == 1:  # Chrome rewrites its process title: the arguments joined with spaces
                args = args[0].split(' ')
            if any(_same_dir(a, want) for a in args) and not any(a.startswith('--type=') for a in args):
                pids.append(int(p))
    elif os.name != 'nt':
        r = subprocess.run(['ps', '-axo', 'pid=,command='], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            pid, _, cmd = line.strip().partition(' ')
            if '--type=' not in cmd and pid.isdigit() and any(_same_dir(a, want) for a in cmd.split()):
                pids.append(int(pid))
    else:
        pid = _meta(slug).get('pid')
        if pid and _alive(pid):
            pids.append(int(pid))
    return pids


def debug_port(slug):
    """The DevTools port of this profile's running Chrome, or None (not running, or opened without debugging)."""
    f = profile_dir(slug) / 'DevToolsActivePort'
    try:
        port = int(f.read_text().splitlines()[0])
    except (OSError, ValueError, IndexError):
        return None
    try:
        with _LOCAL.open(f'http://127.0.0.1:{port}/json/version', timeout=2) as r:
            json.load(r)
    except (OSError, ValueError):
        return None
    return port if running_pids(slug) else None


def _launch(slug, args, url):
    exe = chrome_path()
    d = profile_dir(slug)
    cmd = [exe, f'--user-data-dir={d}', '--no-first-run', '--no-default-browser-check', *args]
    if os.environ.get('IDLI_CHROME_ARGS'):  # tests: --headless=new and friends
        cmd += os.environ['IDLI_CHROME_ARGS'].split()
    if url:
        cmd.append(url)
    kw = {'stdin': subprocess.DEVNULL, 'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}
    if os.name == 'nt':
        kw['creationflags'] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kw['start_new_session'] = True
    p = subprocess.Popen(cmd, **kw)
    meta = _meta(slug)
    meta['pid'] = p.pid
    _write_meta(slug, meta)
    return p


def open_for_sign_in(slug, url=SIGN_IN_URL):
    """Open the profile for the person to sign in: no remote debugging (Google may refuse sign-in with it on). A
    debugging instance of the same profile is closed first."""
    if not exists(slug):
        raise ValueError('That is not one of the Chrome profiles. Call profiles for the list.')
    if url and not re.match(r'https?://', url):
        raise ValueError('Open a web address (https://...).')
    if debug_port(slug):
        close(slug)
    _launch(slug, [], url)  # if it is already open without debugging, Chrome opens the page in that window
    return {'opened': True}


def open_for_work(slug, wait=30):
    """The profile with DevTools on 127.0.0.1, for Idli's browser tools. Reuses a running debugging instance;
    otherwise closes any running instance of the profile and starts it again. Returns the port."""
    port = debug_port(slug)
    if port:
        return port
    if running_pids(slug):
        close(slug)
    d = profile_dir(slug)
    (d / 'DevToolsActivePort').unlink(missing_ok=True)
    _launch(slug, ['--remote-debugging-port=0', '--remote-debugging-address=127.0.0.1'], None)
    end = time.time() + wait
    while time.time() < end:
        port = debug_port(slug)
        if port:
            meta = _meta(slug)
            meta['port'] = port
            _write_meta(slug, meta)
            return port
        time.sleep(0.3)
    raise ValueError(f'Chrome did not open the profile {label(slug)}. Ask the person to close its window and try '
                     'again.')


def close(slug, wait=15):
    """Close this profile's Chrome (gracefully, so it saves its files)."""
    pids = running_pids(slug)
    port = debug_port(slug) if pids else None
    if port:
        try:
            from lib.uiswitch import Cdp
        except ImportError:
            from uiswitch import Cdp
        try:
            with _LOCAL.open(f'http://127.0.0.1:{port}/json/version', timeout=2) as r:
                ws = json.load(r)['webSocketDebuggerUrl']
            c = Cdp(ws, 5)
            try:
                c.call('Browser.close')
            except (OSError, ConnectionError, TimeoutError):
                pass
            c.close()
        except (OSError, ValueError, KeyError, ConnectionError, TimeoutError):
            pass
    else:
        for pid in pids:
            try:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(pid)], capture_output=True)
                else:
                    os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
    end = time.time() + wait
    while time.time() < end and running_pids(slug):
        time.sleep(0.2)
    for pid in running_pids(slug):  # still there: stop it
        try:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True)
            else:
                os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    (profile_dir(slug) / 'DevToolsActivePort').unlink(missing_ok=True)
    return {'closed': True}
