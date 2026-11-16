"""A team's stack: tools from GitHub, conda-forge and PyPI, pinned, installed and run inside Idli's wall
(narrative/TEAM_STACKS.md).

The Builder writes the stack in <team>/extensions/stack/:
- pixi.toml: packages (conda-forge first, PyPI when needed) and tasks. pixi.lock pins every package.
- stack.json: GitHub repos (pinned to a commit), files to download (model weights), extra internet hosts, and
  whether the stack's tools may ask the private model.
- stack-lock.json, written by Idli at the first install: each repo's exact commit and each download's sha256.
  Teammates install exactly these.

Two walls, both bubblewrap (Linux; Windows through WSL2 and macOS through a small Linux VM run the same code):
- **Install**: no network of its own. One door, a bridge to Idli's egress proxy, which lets through only package
  and code hosts (and the extra hosts the person said yes to). Every host asked for is logged. Only the stack folder
  is writable. No home folder, no environment variables from the person's session.
- **Run**: no network at all. The stack folder read-only, the input files read-only, one output folder writable.
  If the stack declares it, one more door: a bridge to the private model's chat endpoint, nothing else.
"""
import asyncio
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLATFORM = Path(os.environ.get('IDLI_PLATFORM') or os.path.expanduser('~/idli-insights/platform'))
NINE_URL = os.environ.get('IDLI_9B_URL', 'http://127.0.0.1:8291')

# Hosts an install may reach: package indexes, code hosting and model weights. Matched on whole labels, so
# "github.com" allows "codeload.github.com" but not "evilgithub.com".
INSTALL_HOSTS = (
    'conda.anaconda.org', 'repo.prefix.dev', 'prefix.dev', 'conda-mapping.prefix.dev',
    'pypi.org', 'files.pythonhosted.org', 'download.pytorch.org',
    'github.com', 'githubusercontent.com',
    'huggingface.co', 'hf.co',
)
PROXY_PORT = 18080   # inside the wall only
MODEL_PORT = 18291   # inside the wall only
HOST_RE = re.compile(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$')


def pixi():
    for p in (PLATFORM / 'bin' / 'pixi', shutil.which('pixi')):
        if p and os.path.exists(p):
            return str(p)
    raise RuntimeError('The platform has no pixi yet (Idli installs it in ~/idli-insights/platform/bin).')


def stack_dir(data_dir):
    return Path(data_dir).resolve() / 'extensions' / 'stack'


# ---- what the Builder wrote ----

def spec(data_dir):
    """stack.json, checked. Returns (spec, problems)."""
    d = stack_dir(data_dir)
    problems = []
    try:
        s = json.loads((d / 'stack.json').read_text()) if (d / 'stack.json').exists() else {}
    except ValueError as exc:
        return {}, [f'stack.json is not valid JSON: {exc}']
    if not isinstance(s, dict):
        return {}, ['stack.json must be an object']
    repos = []
    for r in s.get('repos') or []:
        url = str((r or {}).get('url', ''))
        name = str((r or {}).get('name') or url.rstrip('/').split('/')[-1].removesuffix('.git'))
        if not re.fullmatch(r'https://github\.com/[\w.-]+/[\w.-]+?(\.git)?/?', url):
            problems.append(f'{url or "a repo"}: only https://github.com/<owner>/<repo> links')
            continue
        if not re.fullmatch(r'[\w.-]{1,60}', name) or name in ('.', '..'):
            problems.append(f'{name}: a repo name is letters, digits, . _ -')
            continue
        if not str(r.get('ref') or r.get('commit') or '').strip():
            problems.append(f'{name}: say which tag or commit to use ("ref")')
            continue
        repos.append({'name': name, 'url': url.rstrip('/'), 'ref': str(r.get('ref') or r.get('commit')),
                      'license': str(r.get('license', '')), 'why': str(r.get('why', ''))})
    downloads = []
    for f in s.get('downloads') or []:
        url, to = str((f or {}).get('url', '')), str((f or {}).get('to', ''))
        if not url.startswith('https://') or not to or to.startswith('/') or '..' in Path(to).parts:
            problems.append(f'{url or "a download"}: needs an https url and a "to" path inside the stack folder')
            continue
        downloads.append({'url': url, 'to': to, 'sha256': f.get('sha256'), 'why': str(f.get('why', ''))})
    hosts = []
    for h in s.get('hosts') or []:
        h = str(h).lower().strip()
        if not HOST_RE.match(h):
            problems.append(f'{h}: not a host name')
        else:
            hosts.append(h)
    setup = str(s.get('setup') or '')
    if setup and not re.fullmatch(r'[\w-]{1,40}', setup):
        problems.append('setup names a task in pixi.toml')
    return {'repos': repos, 'downloads': downloads, 'hosts': hosts, 'model': bool(s.get('model')),
            'why': str(s.get('why', '')), 'setup': setup}, problems


def _packages(d):
    try:
        t = tomllib.loads((d / 'pixi.toml').read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return [], []
    conda = list((t.get('dependencies') or {}).keys())
    pypi = list((t.get('pypi-dependencies') or {}).keys())
    for f in (t.get('feature') or {}).values():
        conda += list((f.get('dependencies') or {}).keys())
        pypi += list((f.get('pypi-dependencies') or {}).keys())
    return conda, pypi


def _size(p):
    total = 0
    for root, _, files in os.walk(p):
        for f in files:
            try:
                total += os.lstat(os.path.join(root, f)).st_size
            except OSError:
                pass
    return total


def _human(n):
    for unit in ('bytes', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return f'{n:.0f} {unit}' if unit in ('bytes', 'KB') else f'{n:.1f} {unit}'
        n /= 1024


def summary(data_dir, for_consent=False):
    """What the person says yes to before an install, written by code from the stack files (not by the Builder)."""
    d = stack_dir(data_dir)
    s, problems = spec(data_dir)
    conda, pypi = _packages(d)
    lines = []
    if s.get('why'):
        lines.append('For: ' + s['why'][:200])
    if s.get('setup'):
        lines.append(f"After installing, it runs its setup step ({s['setup']}) with the same internet limits.")
    if conda or pypi:
        lines.append('Packages: ' + ', '.join([p for p in conda if p != 'python'] + pypi)[:400])
    for r in s.get('repos', []):
        lines.append(f"From GitHub: {r['url'].removeprefix('https://github.com/')} at {r['ref']}"
                     + (f" ({r['license']})" if r['license'] else ''))
    for f in s.get('downloads', []):
        lines.append('Download: ' + f['url'].split('/')[2] + '/.../' + f['url'].rsplit('/', 1)[-1][:60])
    extra = [h for h in s.get('hosts', []) if not _allowed(h, INSTALL_HOSTS)]
    if extra:
        lines.append('Also allowed while installing: ' + ', '.join(extra))
    if (d / '.pixi').exists() and not for_consent:
        lines.append('Space used now: ' + _human(_size(d / '.pixi') + _size(d / 'repos') + _size(d / 'models')))
    lines.append('These install inside the team folder only. They run on this computer without internet and see '
                 'only the files you pick.' + (' They may ask the private model on this computer.' if s.get('model')
                                               else ''))
    if problems:
        lines.append('Problems: ' + '; '.join(problems))
    return '\n'.join(lines)


# ---- the egress proxy (host side) ----

def _allowed(host, allow):
    host = host.lower().rstrip('.')
    return any(host == a or host.endswith('.' + a) for a in allow)


async def _pipe(r, w):
    try:
        while data := await r.read(65536):
            w.write(data)
            await w.drain()
    except (ConnectionError, OSError):
        pass
    finally:
        try:
            w.close()
        except Exception:
            pass


class EgressProxy:
    """HTTP CONNECT proxy on a unix socket. Lets through port 443 to allowed hosts only, and logs every ask."""

    def __init__(self, sock_path, allow, log):
        self.sock_path, self.allow, self.log = str(sock_path), tuple(allow), log
        self.loop = asyncio.new_event_loop()
        self.ready = threading.Event()

    def _note(self, host, ok):
        self.log.append({'host': host, 'allowed': ok, 'at': int(time.time())})

    async def _handle(self, r, w):
        try:
            head = await asyncio.wait_for(r.readuntil(b'\r\n\r\n'), 30)
        except Exception:
            w.close()
            return
        first = head.split(b'\r\n', 1)[0].decode('latin-1').split()
        if len(first) < 2 or first[0] != 'CONNECT':
            self._note(first[1] if len(first) > 1 else '?', False)
            w.write(b'HTTP/1.1 403 Forbidden\r\n\r\nOnly HTTPS through CONNECT\r\n')
            await w.drain()
            w.close()
            return
        host, _, port = first[1].rpartition(':')
        ok = port == '443' and _allowed(host, self.allow)
        self._note(host, ok)
        if not ok:
            w.write(b'HTTP/1.1 403 Forbidden\r\n\r\n')
            await w.drain()
            w.close()
            return
        try:
            ur, uw = await asyncio.wait_for(asyncio.open_connection(host, 443, happy_eyeballs_delay=0.25), 30)
        except Exception:
            w.write(b'HTTP/1.1 502 Bad Gateway\r\n\r\n')
            await w.drain()
            w.close()
            return
        w.write(b'HTTP/1.1 200 Connection established\r\n\r\n')
        await w.drain()
        await asyncio.gather(_pipe(r, uw), _pipe(ur, w))

    def start(self):
        def run():
            asyncio.set_event_loop(self.loop)
            self.server = self.loop.run_until_complete(asyncio.start_unix_server(self._handle, self.sock_path))
            self.ready.set()
            self.loop.run_forever()
        threading.Thread(target=run, daemon=True).start()
        self.ready.wait(10)
        return self

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)


class ModelDoor:
    """The private model's chat endpoint on a unix socket: POST /v1/chat/completions and GET /v1/models only."""

    PATHS = {('POST', '/v1/chat/completions'), ('GET', '/v1/models')}

    def __init__(self, sock_path, url=NINE_URL, log=None):
        self.sock_path, self.log = str(sock_path), log if log is not None else []
        m = re.match(r'http://([^:/]+):(\d+)', url)
        self.host, self.port = m.group(1), int(m.group(2))
        self.loop = asyncio.new_event_loop()
        self.ready = threading.Event()

    async def _handle(self, r, w):
        try:
            head = await asyncio.wait_for(r.readuntil(b'\r\n\r\n'), 60)
            method, path = head.split(b'\r\n', 1)[0].decode('latin-1').split()[:2]
        except Exception:
            w.close()
            return
        ok = (method, path.split('?')[0]) in self.PATHS
        self.log.append({'model': path, 'allowed': ok, 'at': int(time.time())})
        if not ok:
            w.write(b'HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
            await w.drain()
            w.close()
            return
        # one request per connection: rewrite the head so the model server closes when done
        lines = [ln for ln in head.decode('latin-1').split('\r\n') if ln and not ln.lower().startswith(
            ('connection:', 'host:', 'keep-alive:'))]
        lines[1:1] = [f'Host: {self.host}:{self.port}', 'Connection: close']
        try:
            ur, uw = await asyncio.open_connection(self.host, self.port)
        except OSError:
            w.write(b'HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
            await w.drain()
            w.close()
            return
        uw.write(('\r\n'.join(lines) + '\r\n\r\n').encode('latin-1'))
        await uw.drain()
        await asyncio.gather(_pipe(r, uw), _pipe(ur, w))

    def start(self):
        def run():
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(asyncio.start_unix_server(self._handle, self.sock_path))
            self.ready.set()
            self.loop.run_forever()
        threading.Thread(target=run, daemon=True).start()
        self.ready.wait(10)
        return self

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)


# ---- inside the wall: a tiny launcher that opens the doors, then runs the command ----

LAUNCH = r"""
import os, socket, subprocess, sys, threading
os.makedirs(os.environ.get("HOME", "/tmp/home"), exist_ok=True)
doors = [d.split('=', 1) for d in os.environ.pop('IDLI_DOORS', '').split(',') if d]
def pipe(a, b):
    try:
        while True:
            data = a.recv(65536)
            if not data:
                break
            b.sendall(data)
    except OSError:
        pass
    finally:
        for s in (a, b):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
def serve(port, path):
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('127.0.0.1', int(port)))
    srv.listen(64)
    while True:
        c, _ = srv.accept()
        u = socket.socket(socket.AF_UNIX)
        try:
            u.connect(path)
        except OSError:
            c.close()
            continue
        threading.Thread(target=pipe, args=(c, u), daemon=True).start()
        threading.Thread(target=pipe, args=(u, c), daemon=True).start()
def serve_in(path, port):
    # a door in: the platform connects to a unix socket, which reaches the page the stack serves inside the wall
    srv = socket.socket(socket.AF_UNIX)
    srv.bind(path)
    srv.listen(64)
    while True:
        c, _ = srv.accept()
        try:
            t = socket.create_connection(('127.0.0.1', int(port)), 10)
            t.settimeout(None)  # the 10 s was for connecting; a page may take minutes to answer
        except OSError:
            c.close()
            continue
        threading.Thread(target=pipe, args=(c, t), daemon=True).start()
        threading.Thread(target=pipe, args=(t, c), daemon=True).start()
for port, path in doors:
    threading.Thread(target=serve, args=(port, path), daemon=True).start()
for d in [d.split('=', 1) for d in os.environ.pop('IDLI_INDOORS', '').split(',') if d]:
    threading.Thread(target=serve_in, args=(d[0], d[1]), daemon=True).start()
import time; time.sleep(0.2) if doors else None
sys.exit(subprocess.call(sys.argv[1:]))
"""


def _hidden_roots():
    return [p for p in ('/home', '/root', '/Users', '/mnt', '/media', '/srv', '/run/user', '/var/lib/docker')
            if os.path.isdir(p)]


def _wall(cmd, binds_rw=(), binds_ro=(), doors=None, env=None, cwd=None, scratch=()):
    """bubblewrap: whole filesystem read-only, people's folders hidden, no network, a clean environment."""
    bw = shutil.which('bwrap')
    if not bw:
        raise RuntimeError('This computer has no wall (bubblewrap). On Windows and macOS stacks run in Idli\'s '
                           'Linux environment.')
    sys_py = '/usr/bin/python3' if os.path.exists('/usr/bin/python3') else shutil.which('python3')
    args = [bw, '--ro-bind', '/', '/', '--dev', '/dev', '--proc', '/proc', '--tmpfs', '/tmp',
            '--unshare-all', '--die-with-parent', '--new-session', '--clearenv']
    for h in _hidden_roots():
        args += ['--tmpfs', h]
    for p in binds_ro:
        if os.path.exists(p):
            args += ['--ro-bind', str(p), str(p)]
    doors = doors or {}
    for port, sock in doors.items():
        args += ['--ro-bind', str(Path(sock).parent), str(Path(sock).parent)]
    for p in binds_rw:
        os.makedirs(p, exist_ok=True)
        args += ['--bind', str(p), str(p)]
    for p in scratch:  # writable but thrown away (caches under a read-only folder)
        args += ['--tmpfs', str(p)]
    base_env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/tmp/home', 'LANG': 'C.UTF-8', 'TMPDIR': '/tmp',
                'IDLI_DOORS': ','.join(f'{p}={s}' for p, s in doors.items())}
    for k, v in {**base_env, **(env or {})}.items():
        args += ['--setenv', k, str(v)]
    if cwd:
        args += ['--chdir', str(cwd)]
    return args + ['--', sys_py, '-I', '-c', LAUNCH] + list(cmd)


def _sockdir():
    # unix socket paths are short; one private folder per call
    return Path(tempfile.mkdtemp(prefix='idli-door-', dir='/tmp'))


# ---- install ----

def _cache(d):
    return d / '.cache'


def threads():
    """A sensible thread count for one job. Asking for every core oversubscribes some CPUs badly (on the DGX's mixed
    fast and slow cores, Whisper with 20 threads ran 25 times slower than with 4)."""
    n = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else (os.cpu_count() or 4)
    return max(2, min(8, n // 2))


def _env_vars(d, proxy):
    c = _cache(d)
    n = str(threads())
    env = {'IDLI_THREADS': n, 'OMP_NUM_THREADS': n, 'OPENBLAS_NUM_THREADS': n, 'MKL_NUM_THREADS': n,
           'CT2_INTER_THREADS': '1', 'NUMEXPR_MAX_THREADS': n,'PIXI_HOME': str(c / 'pixi-home'), 'RATTLER_CACHE_DIR': str(c / 'rattler'),
           'UV_CACHE_DIR': str(c / 'uv'), 'XDG_CACHE_HOME': str(c / 'xdg'), 'HF_HOME': str(d / 'models' / 'hf'),
           'PIXI_NO_UPDATE_CHECK': '1', 'GIT_TERMINAL_PROMPT': '0', 'PIP_NO_INPUT': '1',
           'HF_HUB_DISABLE_TELEMETRY': '1', 'DO_NOT_TRACK': '1'}
    if proxy:
        url = f'http://127.0.0.1:{PROXY_PORT}'
        env.update({'HTTPS_PROXY': url, 'https_proxy': url, 'HTTP_PROXY': url, 'http_proxy': url,
                    'ALL_PROXY': url, 'NO_PROXY': '127.0.0.1,localhost', 'no_proxy': '127.0.0.1,localhost'})
    return env


def _read_lock(d):
    try:
        return json.loads((d / 'stack-lock.json').read_text())
    except (OSError, ValueError):
        return {'repos': {}, 'downloads': {}}


def _sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _consent_file(data_dir):
    return Path(data_dir).resolve() / '.idli' / 'stack-consent.json'  # outside extensions/: the Builder can't touch it


def _items(data_dir):
    """Everything the person agrees to, one string each: packages by name, repos at their ref, downloads, hosts."""
    d = stack_dir(data_dir)
    s, _ = spec(data_dir)
    conda, pypi = _packages(d)
    return sorted({*('package ' + p for p in conda + pypi), *('repo ' + r['url'] + '@' + r['ref'] for r in s.get(
        'repos', [])), *('download ' + f['url'] for f in s.get('downloads', [])), *('host ' + h for h in s.get(
        'hosts', [])), *(['model'] if s.get('model') else []), *(['setup ' + s['setup']] if s.get('setup') else [])})


def _read_consent(data_dir):
    try:
        return set(json.loads(_consent_file(data_dir).read_text()).get('items', []))
    except (OSError, ValueError):
        return set()


def _note_consent(data_dir):
    """An install runs only after the person's yes (or with nothing new), so what it installs is agreed."""
    f = _consent_file(data_dir)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({'items': sorted(_read_consent(data_dir) | set(_items(data_dir))),
                             'at': int(time.time())}, indent=1))


def agreed(data_dir):
    """True when nothing here is new: every package, repo, download and host was in an install the person said yes
    to. Retrying with other versions, or dropping something, doesn't ask again; adding anything does."""
    return set(_items(data_dir)) <= _read_consent(data_dir)


def install(data_dir, timeout=3600, log_to=None):
    """Install the stack inside the install wall. Returns {'ok', 'steps', 'hosts', 'size'}.

    Order: repos (git, pinned), downloads (sha256 pinned on first install), then `pixi install` (pixi.lock pinned on
    first install). Anything not in the lock files gets pinned now; later installs (a teammate's) must match."""
    d = stack_dir(data_dir)
    if not (d / 'pixi.toml').exists():
        raise ValueError('stack/pixi.toml is missing. Write it first (see the build-team skill).')
    _note_consent(data_dir)
    s, problems = spec(data_dir)
    if problems:
        raise ValueError('; '.join(problems))
    lock = _read_lock(d)
    log, steps = [], []
    allow = INSTALL_HOSTS + tuple(s['hosts'])
    sd = _sockdir()
    proxy = EgressProxy(sd / 'egress.sock', allow, log).start()
    env = _env_vars(d, proxy=True)
    px = pixi()
    out_log = open(log_to or (d / '.install.log'), 'w')

    def step(name, cmd, t=timeout):
        args = _wall(cmd, binds_rw=[d], binds_ro=[str(Path(px).parent)], doors={PROXY_PORT: sd / 'egress.sock'},
                     env=env, cwd=d)
        t0 = time.time()
        out_log.write(f'\n== {name}\n')
        out_log.flush()
        try:
            r = subprocess.run(args, stdout=out_log, stderr=subprocess.STDOUT, timeout=t)
            ok = r.returncode == 0
        except subprocess.TimeoutExpired:
            ok = False
        steps.append({'step': name, 'ok': ok, 'seconds': round(time.time() - t0, 1)})
        return ok

    try:
        (d / 'repos').mkdir(exist_ok=True)
        for r in s['repos']:
            dest = d / 'repos' / r['name']
            want = lock['repos'].get(r['name'], {}).get('commit') if lock['repos'].get(r['name'], {}).get(
                'ref') == r['ref'] else None
            if not (dest / '.git').exists():
                shutil.rmtree(dest, ignore_errors=True)
                if not step(f"get {r['name']}", ['git', 'clone', '--filter=blob:none', '-q', r['url'], str(dest)]):
                    return _done(False, steps, log, d, out_log)
            ok = step(f"pin {r['name']}", ['git', '-C', str(dest), '-c', 'advice.detachedHead=false', 'checkout',
                                           '-q', want or r['ref']])
            if not ok:
                step(f"fetch {r['name']}", ['git', '-C', str(dest), 'fetch', '-q', 'origin', want or r['ref']])
                ok = step(f"pin {r['name']}", ['git', '-C', str(dest), 'checkout', '-q', want or 'FETCH_HEAD'])
            if not ok:
                return _done(False, steps, log, d, out_log)
            commit = subprocess.run(['git', '-C', str(dest), 'rev-parse', 'HEAD'], capture_output=True,
                                    text=True).stdout.strip()
            if want and commit != want:
                steps.append({'step': f"check {r['name']}", 'ok': False, 'error': 'commit does not match the lock'})
                return _done(False, steps, log, d, out_log)
            lock['repos'][r['name']] = {'url': r['url'], 'ref': r['ref'], 'commit': commit}
        for f in s['downloads']:
            dest = (d / f['to']).resolve()
            if not dest.is_relative_to(d):
                raise ValueError(f"{f['to']} is outside the stack folder")
            pinned = f.get('sha256') or lock['downloads'].get(f['url'])
            if not (dest.exists() and pinned and _sha(dest) == pinned):
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not step('download ' + dest.name, ['curl', '-fsSL', '--retry', '2', '-o', str(dest), f['url']]):
                    return _done(False, steps, log, d, out_log)
            got = _sha(dest)
            if pinned and got != pinned:
                dest.unlink(missing_ok=True)
                steps.append({'step': 'check ' + dest.name, 'ok': False, 'error': 'sha256 does not match the lock'})
                return _done(False, steps, log, d, out_log)
            lock['downloads'][f['url']] = got
        (d / 'stack-lock.json').write_text(json.dumps(lock, indent=2) + '\n')
        ok = step('packages', [px, 'install', '--manifest-path', str(d / 'pixi.toml')]
                  + (['--locked'] if (d / 'pixi.lock').exists() and os.environ.get('IDLI_STACK_LOCKED') else []))
        if ok and s['setup']:  # e.g. fetch model weights into models/, still inside the install wall
            ok = step('setup', [px, 'run', '--frozen', '--manifest-path', str(d / 'pixi.toml'), s['setup']])
        return _done(ok, steps, log, d, out_log)
    finally:
        proxy.stop()
        out_log.close()
        shutil.rmtree(sd, ignore_errors=True)


def _done(ok, steps, log, d, out_log):
    hosts = {}
    for e in log:
        k = e['host']
        hosts.setdefault(k, {'host': k, 'allowed': e['allowed'], 'times': 0})['times'] += 1
    out_log.flush()
    res = {'ok': ok, 'steps': steps, 'hosts': sorted(hosts.values(), key=lambda h: (h['allowed'], h['host'])),
           'size': _human(_size(d / '.pixi') + _size(d / 'repos') + _size(d / 'models'))}
    (d / '.installed.json').write_text(json.dumps({**res, 'at': int(time.time())}, indent=2))
    if not ok:
        try:
            res['log_tail'] = (d / '.install.log').read_text()[-2500:]
        except OSError:
            pass
    return res


def installed(data_dir):
    d = stack_dir(data_dir)
    try:
        return json.loads((d / '.installed.json').read_text()).get('ok') and (d / '.pixi').exists()
    except (OSError, ValueError):
        return False


# ---- run ----

def run(data_dir, cmd, inputs=(), out_dir=None, timeout=1800, cwd=None, extra_ro=()):
    """Run a command in the stack's environment inside the run wall: no network, the stack read-only, the input
    files read-only, out_dir writable, and the private model's door if the stack asks for it.

    `cmd` is a list run through `pixi run` (so it can name tasks from pixi.toml, or `python tools/x.py ...`)."""
    d = stack_dir(data_dir)
    if not installed(data_dir):
        raise ValueError('The stack is not installed yet.')
    s, _ = spec(data_dir)
    out_dir = Path(out_dir or tempfile.mkdtemp(prefix='idli-out-'))
    out_dir.mkdir(parents=True, exist_ok=True)
    doors, log, door = {}, [], None
    sd = None
    if s.get('model'):
        sd = _sockdir()
        door = ModelDoor(sd / 'model.sock', NINE_URL, log).start()
        doors[MODEL_PORT] = sd / 'model.sock'
    env = _env_vars(d, proxy=False)
    env.update({'IDLI_OUT': str(out_dir), 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
                'PIXI_FROZEN': 'true', 'IDLI_STACK': str(d)})
    if s.get('model'):
        env.update({'IDLI_MODEL_URL': f'http://127.0.0.1:{MODEL_PORT}/v1', 'IDLI_MODEL': 'qwen3.5-9b'})
    # The stack is read-only at run time; its caches get a scratch copy-on-nothing tmpfs.
    px = pixi()
    ro = [str(d), str(Path(px).parent), *[str(Path(p).resolve()) for p in inputs], *map(str, extra_ro)]
    args = _wall([px, 'run', '--frozen', '--manifest-path', str(d / 'pixi.toml'), *cmd],
                 binds_rw=[str(out_dir)], binds_ro=ro, doors=doors, env=env, cwd=cwd or d,
                 scratch=[p for p in (_cache(d) / 'xdg', _cache(d) / 'uv') if p.is_dir()])
    t0 = time.time()
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        ok, out = r.returncode == 0, (r.stdout + r.stderr)
    except subprocess.TimeoutExpired as exc:
        ok, out = False, f'took longer than {timeout} s\n' + str(exc.stdout or '')[-1000:]
    finally:
        if door:
            door.stop()
        if sd:
            shutil.rmtree(sd, ignore_errors=True)
    return {'ok': ok, 'output': out[-4000:], 'seconds': round(time.time() - t0, 1), 'out_dir': str(out_dir),
            'files': sorted(str(p.relative_to(out_dir)) for p in out_dir.rglob('*') if p.is_file())[:200],
            'model_calls': len(log)}


def remove(data_dir):
    """Delete the installed stack (packages, repos, downloads, caches). The stack's definition stays in git."""
    d = stack_dir(data_dir)
    for sub in ('.pixi', 'repos', 'models', '.cache', '.installed.json', '.install.log'):
        p = d / sub
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            p.unlink()


# ---- pages a stack serves (kind "app"): a door in from the person's browser, nothing out ----

APP_PORT = 7860  # inside the wall; the page must listen on 127.0.0.1:$PORT
_apps = {}


class _InDoor:
    """127.0.0.1:<free port> on this computer -> the unix socket the wall listens on."""

    def __init__(self, sock_path):
        self.sock_path = str(sock_path)
        self.srv = socket.socket()
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(('127.0.0.1', 0))
        self.port = self.srv.getsockname()[1]
        self.srv.listen(64)
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            try:
                c, _ = self.srv.accept()
            except OSError:
                return
            u = socket.socket(socket.AF_UNIX)
            try:
                u.connect(self.sock_path)
            except OSError:
                c.close()
                continue
            for a, b in ((c, u), (u, c)):
                threading.Thread(target=_spipe, args=(a, b), daemon=True).start()

    def close(self):
        try:
            self.srv.close()
        except OSError:
            pass


def _spipe(a, b):
    try:
        while data := a.recv(65536):
            b.sendall(data)
    except OSError:
        pass
    finally:
        for x in (a, b):
            try:
                x.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def serve(data_dir, task, state_dir, wait=120):
    """Start a page the stack serves, inside the run wall. Returns {'url', 'pid'}; the same page again if it runs.

    The page sees no internet, the stack read-only, `state_dir` writable (IDLI_OUT) and, if declared, the private
    model. The person's browser reaches it through one door on 127.0.0.1."""
    import urllib.request
    key = (str(Path(data_dir).resolve()), task)
    old = _apps.get(key)
    if old and old['proc'].poll() is None:
        return {'url': old['url'], 'pid': old['proc'].pid, 'again': True}
    if not installed(data_dir):
        raise ValueError('The stack is not installed yet.')
    d = stack_dir(data_dir)
    s, _ = spec(data_dir)
    sd = _sockdir()
    doors, door = {}, None
    if s.get('model'):
        door = ModelDoor(sd / 'model.sock', NINE_URL).start()
        doors[MODEL_PORT] = sd / 'model.sock'
    insock = sd / 'in' / 'page.sock'
    insock.parent.mkdir()
    env = _env_vars(d, proxy=False)
    env.update({'IDLI_OUT': str(state_dir), 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
                'IDLI_STACK': str(d), 'PORT': str(APP_PORT), 'GRADIO_SERVER_PORT': str(APP_PORT),
                'GRADIO_ANALYTICS_ENABLED': 'False', 'IDLI_INDOORS': f'{insock}={APP_PORT}'})
    if s.get('model'):
        env.update({'IDLI_MODEL_URL': f'http://127.0.0.1:{MODEL_PORT}/v1', 'IDLI_MODEL': 'qwen3.5-9b'})
    px = pixi()
    Path(state_dir).mkdir(parents=True, exist_ok=True)
    args = _wall([px, 'run', '--frozen', '--manifest-path', str(d / 'pixi.toml'), task],
                 binds_rw=[str(state_dir), str(insock.parent)], binds_ro=[str(d), str(Path(px).parent)],
                 doors=doors, env=env, cwd=d, scratch=[p for p in (_cache(d) / 'xdg', _cache(d) / 'uv') if p.is_dir()])
    # LAUNCH reads IDLI_INDOORS; the socket folder is bound writable above
    log = open(Path(state_dir) / '.page.log', 'w')
    proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)
    t0 = time.time()
    while not insock.exists() and time.time() - t0 < 10:
        time.sleep(0.1)
    indoor = _InDoor(insock)
    url = f'http://127.0.0.1:{indoor.port}/'
    while time.time() - t0 < wait:
        if proc.poll() is not None:
            indoor.close()
            raise ValueError('The page stopped while starting: ' + (Path(state_dir) / '.page.log').read_text()[-600:])
        try:
            urllib.request.urlopen(url, timeout=3)
            break
        except Exception as exc:
            if getattr(exc, 'code', None):  # an HTTP answer, even an error page, means it is up
                break
            time.sleep(1)
    else:
        stop(data_dir, task, proc=proc)
        raise ValueError(f'The page did not answer within {wait} s.')
    _apps[key] = {'proc': proc, 'url': url, 'door': indoor, 'model': door, 'sd': sd}
    return {'url': url, 'pid': proc.pid}


def stop(data_dir, task, proc=None):
    a = _apps.pop((str(Path(data_dir).resolve()), task), None) or {'proc': proc}
    p = a.get('proc')
    if p and p.poll() is None:
        p.terminate()
        try:
            p.wait(10)
        except subprocess.TimeoutExpired:
            p.kill()
    for k in ('door', 'model'):
        if a.get(k):
            (a[k].close if k == 'door' else a[k].stop)()
    if a.get('sd'):
        shutil.rmtree(a['sd'], ignore_errors=True)
