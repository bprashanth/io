"""Idli's catalog of vetted tools (narrative/PAGES_AND_TOOLS.md, "Decision 2026-11-17: a catalog of trusted tools").

A team's Builder installs only tools from this list. The catalog lives on silo (the DGX router):
- GET  /idli/catalog/catalog.json        the list
- GET  /idli/catalog/files/<path>        mirrored model files and example scripts
- POST /idli/catalog/requests            a request for a tool we don't have yet

Where it is reached, first match wins:
1. IDLI_CATALOG_URL (a server root such as http://127.0.0.1:8185, or the full .../idli/catalog prefix);
2. the router on this computer (127.0.0.1:8185), on the DGX;
3. silo through Cloudflare Access, with the same service token as the private model (lib/muse.py). The token is
   only ever put in request headers here; it is never logged or returned.

Pure standard library: this runs on Linux, macOS and Windows.
"""
import ctypes
import json
import os
import platform as _platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREFIX = '/idli/catalog'
LOCAL = 'http://127.0.0.1:8185'
CACHE_SECONDS = 600
DISK_MARGIN_GB = 2.0  # keep this much free after an install
PLATFORM_WORDS = {'linux-64': 'Linux', 'linux-aarch64': 'Linux (ARM)', 'osx-arm64': 'Mac (Apple Silicon)',
                  'osx-64': 'Mac (Intel)', 'win-64': 'Windows'}
GB = 1024 ** 3


def _idli():
    return Path(os.environ.get('IDLI_HOME') or os.path.expanduser('~/idli-insights'))


# ---- where tools go on this computer ----

def _config():
    try:
        c = json.loads((_idli() / 'config' / 'tools.json').read_text())
        return c if isinstance(c, dict) else {}
    except (OSError, ValueError):
        return {}


def tools_home():
    """IDLI_TOOLS_HOME, else ~/idli-insights/config/tools.json {"home": ...}, else ~/idli-insights/tools."""
    if os.environ.get('IDLI_TOOLS_HOME'):
        return Path(os.environ['IDLI_TOOLS_HOME']).expanduser()
    home = _config().get('home')
    if isinstance(home, str) and home.strip():
        return Path(home).expanduser()
    return _idli() / 'tools'


def _links_ok(folder):
    """Can this folder hold symlinks? Conda environments need them; exFAT and FAT disks can't."""
    p = _existing(folder)
    try:
        import tempfile
        with tempfile.TemporaryDirectory(dir=p) as t:
            os.symlink('x', os.path.join(t, 'l'))
        return True
    except (OSError, NotImplementedError):
        return sys.platform.startswith('win')  # Windows without developer mode: pixi copies instead


def envs_home():
    """Where teams' environments go: tools.json {"envs": ...}, else <tools home>/envs when that disk can hold symlinks,
    else ~/idli-insights/tools/envs (on the DGX the big disk is exFAT; models stay there, environments can't)."""
    if os.environ.get('IDLI_TOOLS_ENVS'):
        return Path(os.environ['IDLI_TOOLS_ENVS']).expanduser()
    envs = _config().get('envs')
    if isinstance(envs, str) and envs.strip() and not os.environ.get('IDLI_TOOLS_HOME'):
        return Path(envs).expanduser()
    home = tools_home()
    return home / 'envs' if _links_ok(home) else _idli() / 'tools' / 'envs'


# ---- this computer ----

def platform(system=None, machine=None):
    """This computer as a conda platform: linux-64, linux-aarch64, osx-arm64, osx-64 or win-64."""
    system = (system or sys.platform).lower()
    machine = (machine or _platform.machine() or '').lower()
    arm = machine in ('arm64', 'aarch64', 'armv8', 'armv8l')
    if system.startswith('win'):
        return 'win-64'
    if system == 'darwin':
        return 'osx-arm64' if arm else 'osx-64'
    return 'linux-aarch64' if arm else 'linux-64'


def _ram_bytes():
    try:
        if sys.platform.startswith('linux'):
            with open('/proc/meminfo') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        return int(line.split()[1]) * 1024
        if sys.platform == 'darwin':
            out = subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True, timeout=5)
            return int(out.stdout.strip())
        if sys.platform.startswith('win'):
            class MemoryStatus(ctypes.Structure):
                _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                            ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                            ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                            ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                            ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
            st = MemoryStatus()
            st.dwLength = ctypes.sizeof(MemoryStatus)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
                return int(st.ullTotalPhys)
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        pass
    try:
        return os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
    except (ValueError, OSError, AttributeError):
        return 0


def _gpu(plat):
    if shutil.which('nvidia-smi'):
        return 'nvidia'
    if plat == 'osx-arm64':
        return 'apple'
    return None


def _existing(p):
    p = Path(p)
    while not p.exists() and p.parent != p:
        p = p.parent
    return p


def resources(home=None):
    """Free disk where tools go, total memory, cores and GPU. Sizes in bytes."""
    plat = platform()
    home = Path(home or tools_home())
    try:
        free = shutil.disk_usage(_existing(home)).free
        if home == tools_home():  # environments may live on another disk: the smaller of the two is what's free
            free = min(free, shutil.disk_usage(_existing(envs_home())).free)
    except OSError:
        free = 0
    return {'platform': plat, 'home': str(home), 'disk_free': free, 'ram': _ram_bytes(),
            'cores': os.cpu_count() or 1, 'gpu': _gpu(plat)}


def gb(n):
    return f'{n / GB:.1f} GB' if n >= GB else f'{max(n, 0) / 1024 ** 2:.0f} MB'


def describe_computer(res=None):
    """A few lines for the Builder's instructions: what this computer is and has."""
    r = res or resources()
    gpu = {'nvidia': 'an NVIDIA GPU', 'apple': 'Apple Silicon (its GPU)'}.get(r['gpu'], 'no GPU')
    return (f"- System: {PLATFORM_WORDS.get(r['platform'], r['platform'])} ({r['platform']}). Install only tools the "
            f"catalog lists for {r['platform']}.\n"
            f"- Free disk where tools go: {gb(r['disk_free'])}. Memory: {gb(r['ram'])}. Cores: {r['cores']}. "
            f"GPU: {gpu}.\n")


# ---- reaching the catalog ----

def _local_router():
    try:
        with socket.create_connection(('127.0.0.1', 8185), timeout=0.5):
            return True
    except OSError:
        return False


def source():
    """(base url ending in /idli/catalog, headers). Raises ValueError when there is no way to reach it."""
    url = os.environ.get('IDLI_CATALOG_URL', '').strip().rstrip('/')
    if url:
        return (url if url.endswith(PREFIX) else url + PREFIX), {'User-Agent': 'idli'}
    if _local_router():
        return LOCAL + PREFIX, {'User-Agent': 'idli'}
    try:
        sys.path.insert(0, str(ROOT))
        from lib import muse
        if muse.access():
            return muse.base_url() + PREFIX, muse.headers()
    except Exception:
        pass
    raise ValueError("Idli can't reach its catalog of tools from this computer. Sign in to Idli's server first "
                     "(the Logins check in Start here).")


def _get(path, timeout=30):
    base, headers = source()
    req = urllib.request.Request(base + path, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def file_url(path):
    """The catalog's copy of a file (models, examples) as (url, headers)."""
    base, headers = source()
    return base + '/files/' + urllib.parse.quote(str(path).lstrip('/')), headers


def _cache_file():
    return tools_home() / 'catalog-cache.json'


def _valid(cat):
    return isinstance(cat, dict) and isinstance(cat.get('tools'), list)


def load(refresh=False):
    """The catalog. Fetched at most every 10 minutes; an older copy is used when the server can't be reached."""
    cache = _cache_file()
    old = None
    try:
        old = json.loads(cache.read_text())
    except (OSError, ValueError):
        pass
    if old and _valid(old.get('catalog')) and not refresh and time.time() - old.get('fetched', 0) < CACHE_SECONDS:
        return old['catalog']
    try:
        cat = json.loads(_get('/catalog.json'))
        if not _valid(cat):
            raise ValueError('not a catalog')
    except (OSError, ValueError, urllib.error.URLError) as exc:
        if old and _valid(old.get('catalog')):
            return {**old['catalog'], 'stale': True}
        if isinstance(exc, ValueError) and "can't reach" in str(exc):
            raise
        raise ValueError("Idli's catalog of tools didn't answer. Try again in a minute.") from None
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix('.tmp')
        tmp.write_text(json.dumps({'fetched': time.time(), 'catalog': cat}))
        os.replace(tmp, cache)
    except OSError:
        pass
    return cat


def tools_by_id(cat=None):
    cat = cat if cat is not None else load()
    return {str(t.get('id')): t for t in cat.get('tools', []) if isinstance(t, dict) and t.get('id')}


def example(tool_id, cat=None):
    """The example script for a tool, as text."""
    t = tools_by_id(cat).get(str(tool_id))
    if not t:
        raise ValueError(f'{tool_id} is not in the catalog.')
    if not t.get('example'):
        return ''
    url, headers = file_url(t['example'])
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return r.read(200_000).decode('utf-8', errors='replace')


# ---- will it run here? ----

def _needs_gpu(value):
    """None, 'any' or 'nvidia' from a catalog's gpu field (false, true, 'optional', 'cuda', 'nvidia', 'required')."""
    if not value:
        return None
    v = str(value).lower()
    if v in ('optional', 'preferred', 'faster', 'no', 'false', 'none'):
        return None
    if 'cuda' in v or 'nvidia' in v:
        return 'nvidia'
    return 'any'


def tool_bytes(t, have_models=()):
    """Disk a tool needs, less any of its models already on this computer (models are shared between teams)."""
    total = float((t.get('needs') or {}).get('disk_gb') or 0) * GB
    model_bytes = sum(int(m.get('bytes') or 0) for m in t.get('models') or [])
    shared = sum(int(m.get('bytes') or 0) for m in t.get('models') or [] if m.get('sha256') in set(have_models))
    total = max(total, model_bytes)
    return int(max(total - shared, 0))


def check(tool_ids, team=None, cat=None, res=None, registry=None):
    """Will these tools run on this computer? Returns {'ok', 'platform', 'resources', 'need_bytes', 'tools': {id:
    {'ok', 'name', 'reasons', 'notes', 'need_bytes'}}, 'reasons'}. Reasons are plain sentences for the person."""
    cat = cat if cat is not None else load()
    res = res or resources()
    if registry is None:
        from lib import toolhome
        registry = toolhome.installs()
    have_models = {s for e in registry for s in e.get('models') or []}
    team_has = {e['tool'] for e in registry if team and e.get('team') == team}
    by_id = tools_by_id(cat)
    plat = res['platform']
    out, need_total, reasons = {}, 0, []
    for tid in dict.fromkeys(str(t) for t in tool_ids or []):
        t = by_id.get(tid)
        if not t:
            out[tid] = {'ok': False, 'name': tid, 'reasons': [f'{tid} is not on Idli\'s vetted list.'], 'notes': [],
                        'need_bytes': 0}
            continue
        name, needs = t.get('name') or tid, t.get('needs') or {}
        why, notes = [], []
        plats = t.get('platforms') or []
        if plat not in plats:
            where = ', '.join(dict.fromkeys(PLATFORM_WORDS.get(p, p) for p in plats)) or 'no system yet'
            why.append(f"{name} doesn't run on this computer ({PLATFORM_WORDS.get(plat, plat)}). It runs on {where}.")
        ram = float(needs.get('ram_gb') or 0)
        if ram and res['ram'] and ram * GB > res['ram'] * 1.02:
            why.append(f"{name} needs {ram:g} GB of memory. This computer has {gb(res['ram'])}.")
        want_gpu = _needs_gpu(needs.get('gpu'))
        if want_gpu == 'nvidia' and res['gpu'] != 'nvidia':
            why.append(f'{name} needs an NVIDIA graphics card. This computer has none.')
        elif want_gpu == 'any' and not res['gpu']:
            why.append(f'{name} needs a graphics card (GPU). This computer has none.')
        elif needs.get('gpu') and not want_gpu and not res['gpu']:
            notes.append(f'{name} runs faster with a GPU. It will be slower here.')
        cores = int(needs.get('cores') or 0)
        if cores and res['cores'] < cores:
            notes.append(f'{name} wants {cores} cores. This computer has {res["cores"]}, so it will be slow.')
        need = 0 if tid in team_has else tool_bytes(t, have_models)
        have_models |= {m.get('sha256') for m in t.get('models') or []}  # two tools sharing a model count it once
        need_total += need
        out[tid] = {'ok': not why, 'name': name, 'reasons': why, 'notes': notes, 'need_bytes': need}
    free = res['disk_free'] - DISK_MARGIN_GB * GB
    if need_total and need_total > free:
        reasons.append(f"Not enough free disk: these need about {gb(need_total)}, and {gb(max(res['disk_free'], 0))} "
                       f"is free where tools go (Idli keeps {DISK_MARGIN_GB:g} GB spare). Removing tools on the "
                       "Installed tools page (in Teams) frees space.")
    ok = bool(out) and all(v['ok'] for v in out.values()) and not reasons
    return {'ok': ok, 'platform': plat, 'resources': res, 'need_bytes': need_total, 'tools': out,
            'reasons': reasons + [r for v in out.values() for r in v['reasons']]}


def fitting(cat=None, res=None, registry=None):
    """The catalog's tools for this computer's system, each with its verdict here."""
    cat = cat if cat is not None else load()
    res = res or resources()
    rows, other = [], 0
    for t in cat.get('tools', []):
        if not isinstance(t, dict) or not t.get('id'):
            continue
        if res['platform'] not in (t.get('platforms') or []):
            other += 1
            continue
        v = check([t['id']], cat=cat, res=res, registry=registry or [])
        rows.append({'id': t['id'], 'name': t.get('name'), 'for': t.get('for'), 'licence': t.get('licence'),
                     'cautions': t.get('cautions') or [], 'needs': t.get('needs') or {}, 'tags': t.get('tags') or [],
                     'size': gb(tool_bytes(t)), 'fits': v['ok'], 'why_not': v['reasons'],
                     'notes': v['tools'][t['id']]['notes'], 'has_example': bool(t.get('example'))})
    return rows, other


# ---- asking for a new tool ----

def request(need, why, tools_considered=(), team=None):
    """Ask our team to vet a tool for a need the catalog doesn't cover. General words only, no team data."""
    need, why = ' '.join(str(need or '').split())[:300], ' '.join(str(why or '').split())[:600]
    if not need:
        raise ValueError('Say what is needed, in general words.')
    body = json.dumps({'need': need, 'why': why, 'tools_considered': [str(t)[:80] for t in tools_considered or []][:20],
                       'team': str(team or '')[:60], 'platform': platform(), 'at': time.strftime('%Y-%m-%dT%H:%M:%S'),
                       'version': 1}).encode()
    base, headers = source()
    req = urllib.request.Request(base + '/requests', data=body, method='POST',
                                 headers={**headers, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            got = r.read(4000)
        try:
            ans = json.loads(got)
        except ValueError:
            ans = {}
        return {'sent': True, 'id': ans.get('id') if isinstance(ans, dict) else None}
    except (OSError, urllib.error.URLError):
        return {'sent': False, 'error': "Idli's server didn't take the request. It is noted on this computer."}
