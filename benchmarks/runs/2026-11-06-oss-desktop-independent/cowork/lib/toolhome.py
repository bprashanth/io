"""Where catalog tools are installed on this computer, and who installed what (narrative/PAGES_AND_TOOLS.md).

    <home>/envs/<team-id>/       the team's pixi environment: pixi.toml (made from the chosen catalog tools),
                                 pixi.lock and .pixi/. The team's git keeps only a copy of the definition
                                 (extensions/stack/catalog.json, pixi.toml, pixi.lock).
    <home>/models/<sha>/<name>   each model once, shared by every team that uses it
    <home>/installs.json         [{team, team_name, tool, bytes, models: [sha256], platform, installed_at}]
    <home>/.cache/               pixi's package cache, shared

<home> is lib/catalog.tools_home(): IDLI_TOOLS_HOME, ~/idli-insights/config/tools.json, or ~/idli-insights/tools.
A model is deleted only when no install refers to it; a team's environment when it has no tools left.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import catalog  # noqa: E402

MADE_BY = '# Made by Idli from its catalog of vetted tools.'
TEAM_ID = re.compile(r'[a-z0-9][a-z0-9-]{0,40}')


def home():
    return catalog.tools_home()


def registry_file():
    return home() / 'installs.json'


def envs_home():
    return catalog.envs_home()


def cache_dir():
    """pixi's package cache, beside the environments (it links into them, so it needs the same kind of disk)."""
    return envs_home().parent / '.cache'


def env_dir(team):
    if not TEAM_ID.fullmatch(str(team)):
        raise ValueError('Not a team.')
    return envs_home() / team


def models_dir():
    return home() / 'models'


def model_path(m):
    """Where a catalog model lives: <home>/models/<sha256 prefix>/<name>."""
    sha = str(m.get('sha256') or '').lower()
    name = Path(str(m.get('name') or m.get('file') or 'model')).name
    if not re.fullmatch(r'[0-9a-f]{64}', sha) or name in ('', '.', '..'):
        raise ValueError(f"The catalog's entry for {name} has no valid sha256.")
    return models_dir() / sha[:16] / name


def team_id(data_dir):
    """A team's id is its folder's name; Drivey's folder (cowork-real) is 'drivey'."""
    name = Path(data_dir).resolve().name
    return 'drivey' if name == 'cowork-real' else name


def team_name(data_dir):
    try:
        return json.loads((Path(data_dir) / 'team.json').read_text())['name']
    except (OSError, ValueError, KeyError):
        return 'Drivey' if team_id(data_dir) == 'drivey' else team_id(data_dir)


# ---- installs.json ----

class _Lock:
    """A lock file next to installs.json (works on every system). A lock older than 10 minutes is stale."""

    def __init__(self):
        self.path = home() / '.installs.lock'

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        while True:
            try:
                os.close(os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                return self
            except FileExistsError:
                try:
                    if time.time() - self.path.stat().st_mtime > 600:
                        self.path.unlink()
                        continue
                except OSError:
                    continue
                if time.time() - t0 > 30:
                    raise RuntimeError('Another install is updating the list of tools. Try again.')
                time.sleep(0.1)

    def __exit__(self, *a):
        self.path.unlink(missing_ok=True)


def installs():
    try:
        rows = json.loads(registry_file().read_text())
        return [r for r in rows if isinstance(r, dict) and r.get('team') and r.get('tool')]
    except (OSError, ValueError, TypeError):
        return []


def _write(rows):
    f = registry_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix('.tmp')
    tmp.write_text(json.dumps(rows, indent=1) + '\n')
    os.replace(tmp, f)


def record(team, name, tool, models, nbytes, plat=None):
    """Add or refresh one install."""
    with _Lock():
        rows = [r for r in installs() if not (r['team'] == team and r['tool'] == tool)]
        rows.append({'team': team, 'team_name': name, 'tool': tool, 'bytes': int(nbytes), 'models': list(models),
                     'platform': plat or catalog.platform(), 'installed_at': time.strftime('%Y-%m-%dT%H:%M:%S')})
        _write(rows)


def team_tools(team):
    return [r['tool'] for r in installs() if r['team'] == team]


def _rm(p):
    p = Path(p)
    if p.is_dir() and not p.is_symlink():
        shutil.rmtree(p, ignore_errors=True)
    elif p.exists() or p.is_symlink():
        p.unlink()


def _purge_models(rows):
    """Delete each model folder no install refers to. Returns bytes freed."""
    keep = {s[:16] for r in rows for s in r.get('models') or []}
    freed = 0
    for d in models_dir().iterdir() if models_dir().is_dir() else []:
        if d.name not in keep:
            freed += size(d)
            _rm(d)
    return freed


def remove(team, tool=None, data_dir=None):
    """Remove one tool from a team, or every tool of the team (tool=None). The team's environment goes when it has no
    tools left, and a model only when no other install uses it. Returns {'removed', 'freed'}."""
    with _Lock():
        rows = installs()
        gone = [r for r in rows if r['team'] == team and (tool is None or r['tool'] == tool)]
        if not gone:
            return {'removed': [], 'freed': 0}
        rows = [r for r in rows if r not in gone]
        _write(rows)
        freed = 0
        left = [r['tool'] for r in rows if r['team'] == team]
        env = env_dir(team)
        if not left:
            freed += size(env)
            _rm(env)
        freed += _purge_models(rows)
        if not rows:  # no tool left on this computer: pixi's package cache goes too (it can be gigabytes)
            freed += size(cache_dir())
            _rm(cache_dir())
    if left and env.exists():  # the environment keeps only the tools that are left (best effort; next install too)
        try:
            write_manifest(team, left, catalog.load(), team_tasks(data_dir) if data_dir else None)
        except (ValueError, OSError):
            pass
    if data_dir:
        _write_definition(data_dir, left)
    return {'removed': [r['tool'] for r in gone], 'freed': freed}


def purge_team(team, data_dir=None):
    return remove(team, None, data_dir)


def purge_orphans(teams_root=None):
    """Remove the tools of teams whose folder is gone (deleted or archived outside Idli). Drivey is never an orphan."""
    root = Path(teams_root) if teams_root else catalog._idli() / 'teams'
    freed = 0
    for team in sorted({r['team'] for r in installs()}):
        if team != 'drivey' and not (root / team).exists():
            freed += remove(team)['freed']
    return freed


def usage():
    """What tools use on this computer and what is free, for the one line on the Teams page."""
    used = size(envs_home()) + size(models_dir()) + size(cache_dir())
    free = catalog.resources(home())['disk_free']
    return {'used': used, 'free': free, 'text': f'Tools use {catalog.gb(used)}. {catalog.gb(free)} free.'}


def size(p):
    total = 0
    for root, _, files in os.walk(p):
        for f in files:
            try:
                total += os.lstat(os.path.join(root, f)).st_size
            except OSError:
                pass
    return total


# ---- the team's pixi.toml, from the chosen tools ----

def _toml_value(v):
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, dict):
        return '{ ' + ', '.join(f'{_toml_key(k)} = {_toml_value(x)}' for k, x in v.items()) + ' }'
    if isinstance(v, (list, tuple)):
        return '[' + ', '.join(_toml_value(x) for x in v) + ']'
    return json.dumps(str(v), ensure_ascii=False)


def _toml_key(k):
    return k if re.fullmatch(r'[A-Za-z0-9_-]+', str(k)) else json.dumps(str(k))


def _loose(spec):
    return spec in ('*', '', None) or spec == {'version': '*'}


def union(tools):
    """Merge the chosen tools' pixi sections. Returns (dependencies, pypi-dependencies, platforms, conflicts).
    The same package with two different pins is a conflict; '*' gives way to a pin."""
    deps, pypi, conflicts, owner = {}, {}, [], {}
    plats = None
    for t in tools:
        px = t.get('pixi') or {}
        for table, key in ((deps, 'dependencies'), (pypi, 'pypi-dependencies')):
            for pkg, spec in (px.get(key) or {}).items():
                k = (key, pkg.lower())
                if pkg not in table or _loose(table[pkg]):
                    table[pkg] = spec
                    owner[k] = t.get('name') or t.get('id')
                elif not _loose(spec) and spec != table[pkg]:
                    conflicts.append(f"{owner[k]} needs {pkg} {_plain(table[pkg])}, but {t.get('name') or t.get('id')}"
                                     f" needs {pkg} {_plain(spec)}.")
        p = set(t.get('platforms') or [])
        plats = p if plats is None else plats & p
    return deps, pypi, sorted(plats or []), conflicts


def _plain(spec):
    return spec if isinstance(spec, str) else json.dumps(spec)


def _version(v):
    return tuple(int(x) for x in re.findall(r'\d+', str(v))[:3])


def system_requirements(tools):
    """The chosen tools' pixi `system-requirements` (for example {"macos": "14.0"}: PyAV's Apple Silicon wheels need
    macOS 14, and pixi assumes an older macOS, so without it faster-whisper tries to build av from source and fails).
    The highest version of each wins."""
    out = {}
    for t in tools:
        for k, v in ((t.get('pixi') or {}).get('system-requirements') or {}).items():
            if re.fullmatch(r'[a-z-]{1,20}', str(k)) and re.fullmatch(r'\d+(\.\d+){0,2}', str(v)) and (
                    k not in out or _version(v) > _version(out[k])):
                out[k] = str(v)
    return out


def team_tasks(data_dir):
    """Tasks the Builder declares in stack/stack.json ("tasks": {"serve": "python tools/page.py"}), for pages.
    The environment's pixi.toml lives in the tools home, and pixi runs a task from the folder of its manifest, so
    each task names the team's stack folder as its cwd (where `tools/page.py` is)."""
    stack = Path(data_dir).resolve() / 'extensions' / 'stack'
    try:
        s = json.loads((stack / 'stack.json').read_text())
        tasks = s.get('tasks') or {}
    except (OSError, ValueError, AttributeError):
        return {}
    return {k: {'cmd': v, 'cwd': str(stack)} for k, v in tasks.items() if re.fullmatch(r'[\w-]{1,40}', str(k))
            and isinstance(v, str) and v.strip() and '\n' not in v} if isinstance(tasks, dict) else {}


def manifest_text(team, tools, tasks=None):
    deps, pypi, plats, conflicts = union(tools)
    if conflicts:
        raise ValueError('These tools ask for different versions of the same package: ' + ' '.join(conflicts))
    if pypi and 'python' not in deps:
        deps = {'python': '3.11.*', **deps}
    lines = [MADE_BY + ' Do not edit: install with stack_install.',
             f'# Tools: {", ".join(t["id"] for t in tools)}', '[workspace]', f'name = "idli-{team}"',
             'channels = ["conda-forge"]', f'platforms = {_toml_value(plats)}', '', '[dependencies]']
    lines += [f'{_toml_key(k)} = {_toml_value(v)}' for k, v in deps.items()]
    if pypi:
        lines += ['', '[pypi-dependencies]'] + [f'{_toml_key(k)} = {_toml_value(v)}' for k, v in pypi.items()]
    sysreq = system_requirements(tools)
    if sysreq:
        lines += ['', '[system-requirements]'] + [f'{_toml_key(k)} = {_toml_value(v)}' for k, v in sysreq.items()]
    if tasks:
        lines += ['', '[tasks]'] + [f'{_toml_key(k)} = {_toml_value(v)}' for k, v in tasks.items()]
    text = '\n'.join(lines) + '\n'
    tomllib.loads(text)  # never write a manifest pixi can't read
    return text


def write_manifest(team, tool_ids, cat, tasks=None):
    by_id = catalog.tools_by_id(cat)
    tools = [by_id[t] for t in tool_ids if t in by_id]
    text = manifest_text(team, tools, tasks)
    d = env_dir(team)
    d.mkdir(parents=True, exist_ok=True)
    f = d / 'pixi.toml'
    if not f.exists() or f.read_text() != text:
        f.write_text(text)
    return f


def _write_definition(data_dir, tool_ids):
    """The team's copy of what it uses (in its git, so teammates get the same): catalog.json, pixi.toml, pixi.lock."""
    st = Path(data_dir).resolve() / 'extensions' / 'stack'
    team = team_id(data_dir)
    if not tool_ids:
        (st / 'catalog.json').unlink(missing_ok=True)
        for name in ('pixi.toml', 'pixi.lock'):  # only Idli's own copies, never a hand-made stack's
            f = st / name
            if name == 'pixi.toml' and f.exists() and not f.read_text().startswith(MADE_BY):
                return
            f.unlink(missing_ok=True)
        return
    st.mkdir(parents=True, exist_ok=True)
    (st / 'catalog.json').write_text(json.dumps({'tools': list(tool_ids)}, indent=1) + '\n')
    for name in ('pixi.toml', 'pixi.lock'):
        src = env_dir(team) / name
        if src.exists():
            shutil.copyfile(src, st / name)


def catalog_tools(data_dir):
    """The catalog tools this team's definition lists, or None for a team without catalog tools."""
    try:
        got = json.loads((Path(data_dir).resolve() / 'extensions' / 'stack' / 'catalog.json').read_text())
        return [str(t) for t in got.get('tools') or []]
    except (OSError, ValueError, AttributeError):
        return None


def is_catalog_team(data_dir):
    return catalog_tools(data_dir) is not None


# ---- models ----

def _sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _download(url, headers, dest, sha, timeout=120):
    """Fetch url to dest, checking sha256. Returns True, or False when the server has no such file (404)."""
    tmp = dest.with_name(dest.name + '.part')
    h = hashlib.sha256()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r, \
                open(tmp, 'wb') as out:
            while chunk := r.read(1 << 20):
                h.update(chunk)
                out.write(chunk)
    except urllib.error.HTTPError as e:
        tmp.unlink(missing_ok=True)
        if e.code == 404:
            return False
        raise ValueError(f'The download of {dest.name} failed ({e.code}).') from None
    except OSError:
        tmp.unlink(missing_ok=True)
        raise ValueError(f'The download of {dest.name} stopped. Check the internet and try again.') from None
    if h.hexdigest() != sha:
        tmp.unlink(missing_ok=True)
        raise ValueError(f"{dest.name} did not match the catalog's sha256, so Idli threw it away.")
    os.replace(tmp, dest)
    return True


def _unpack(archive, kind, into):
    into.mkdir(parents=True, exist_ok=True)
    root = into.resolve()
    if kind == 'zip':
        with zipfile.ZipFile(archive) as z:
            for n in z.namelist():
                if not (root / n).resolve().is_relative_to(root):
                    raise ValueError(f'{archive.name} has a file outside its folder.')
            z.extractall(into)
    elif kind == 'tar':
        with tarfile.open(archive) as t:
            for m in t.getmembers():
                if not (root / m.name).resolve().is_relative_to(root) or m.issym() or m.islnk() or m.isdev():
                    raise ValueError(f'{archive.name} has a file Idli does not unpack.')
            t.extractall(into)


def fetch_model(m, log=None):
    """One model into <home>/models/<sha>/<name>: the catalog's copy first, the public source only when the catalog
    has no copy. sha256 checked either way. Returns the path."""
    dest = model_path(m)
    log = log if log is not None else []
    sha = m['sha256'].lower()
    done = dest.parent / '.ok'
    if done.exists() and done.read_text().strip() == sha and dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    kind = str(m.get('unpack') or 'none').lower()
    target = dest if kind == 'none' else dest.parent / ('.archive-' + Path(str(m.get('file') or dest.name)).name)
    got = False
    if m.get('file'):
        url, headers = catalog.file_url(m['file'])
        got = _download(url, headers, target, sha)
        log.append({'model': dest.name, 'from': 'catalog' if got else 'catalog: missing'})
    if not got:
        src = str(m.get('source') or '')
        if not src.startswith('https://'):
            raise ValueError(f'{dest.name} is not on the catalog server and has no public source.')
        if not _download(src, {'User-Agent': 'idli'}, target, sha):
            raise ValueError(f'{dest.name} is missing from both the catalog and its source.')
        log.append({'model': dest.name, 'from': src.split('/')[2]})
    if kind != 'none':
        _rm(dest)
        _unpack(target, kind, dest)
        target.unlink(missing_ok=True)
    done.write_text(sha)
    return dest


def model_env(tool_ids, cat):
    """Environment variables that point a tool at its models: IDLI_MODELS, IDLI_MODEL_<NAME> per model and
    IDLI_MODEL_PATHS (JSON {name: path})."""
    by_id = catalog.tools_by_id(cat)
    paths = {}
    for tid in tool_ids:
        for m in (by_id.get(tid) or {}).get('models') or []:
            try:
                paths[str(m.get('name'))] = str(model_path(m))
            except ValueError:
                continue
    env = {'IDLI_MODELS': str(models_dir()), 'IDLI_MODEL_PATHS': json.dumps(paths)}
    for name, p in paths.items():
        env['IDLI_MODEL_' + re.sub(r'[^A-Z0-9]+', '_', name.upper()).strip('_')] = p
    return env


# ---- install ----

def plan(data_dir, tool_ids, cat=None):
    """What an install would do: the full set of tools for the team, the check, and any version conflicts."""
    cat = cat if cat is not None else catalog.load()
    team = team_id(data_dir)
    have = catalog_tools(data_dir) or []
    want = list(dict.fromkeys([*have, *[str(t) for t in tool_ids]]))
    verdict = catalog.check([t for t in tool_ids], team=team, cat=cat)
    by_id = catalog.tools_by_id(cat)
    _, _, plats, conflicts = union([by_id[t] for t in want if t in by_id])
    plat = catalog.platform()
    if want and all(t in by_id for t in want) and plat not in plats:
        conflicts.append(f'Together these tools have no system in common with this computer ({plat}).')
    return {'team': team, 'all': want, 'new': [t for t in tool_ids if t not in have], 'check': verdict,
            'conflicts': conflicts, 'ok': verdict['ok'] and not conflicts}


def consent_summary(data_dir, tool_ids, cat=None):
    """The text the person says yes to, written from the catalog (never by the Builder)."""
    cat = cat if cat is not None else catalog.load()
    by_id = catalog.tools_by_id(cat)
    lines = ["From Idli's vetted list of tools."]
    cautions, licences = [], []
    for tid in tool_ids:
        t = by_id.get(tid)
        if not t:
            lines.append(f'{tid}: not on the list')
            continue
        lines.append(f"Adds: {t.get('name') or tid}, about {catalog.gb(catalog.tool_bytes(t))}. For: "
                     f"{' '.join(str(t.get('for') or '').split())[:160]}")
        if t.get('licence'):
            licences.append(f"{t.get('name') or tid}: {t['licence']}")
        cautions += [f"{t.get('name') or tid}: {c}" for c in t.get('cautions') or []]
    if cautions:
        lines.append('Cautions: ' + '. '.join(cautions)[:400])
    if licences:
        lines.append('Licences: ' + '. '.join(licences)[:300])
    lines.append('They run on this computer without internet and see only the files you pick.')
    lines.append(f'Installed in {home()}. Remove them any time on the Installed tools page, in Teams.')
    return '\n'.join(lines)


def _consent_file(data_dir):
    return Path(data_dir).resolve() / '.idli' / 'stack-consent.json'


def agreed(data_dir, tool_ids):
    try:
        have = set(json.loads(_consent_file(data_dir).read_text()).get('items', []))
    except (OSError, ValueError):
        have = set()
    return {f'catalog {t}' for t in tool_ids} <= have


def note_consent(data_dir, tool_ids):
    f = _consent_file(data_dir)
    try:
        old = json.loads(f.read_text())
    except (OSError, ValueError):
        old = {}
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({**old, 'items': sorted(set(old.get('items', [])) | {f'catalog {t}' for t in tool_ids}),
                             'at': int(time.time())}, indent=1))


def _pixi_env(cache):
    n = '4'
    return {'PIXI_HOME': str(cache / 'pixi-home'), 'RATTLER_CACHE_DIR': str(cache / 'rattler'),
            'UV_CACHE_DIR': str(cache / 'uv'), 'XDG_CACHE_HOME': str(cache / 'xdg'), 'PIXI_NO_UPDATE_CHECK': '1',
            'PIP_NO_INPUT': '1', 'HF_HUB_DISABLE_TELEMETRY': '1', 'DO_NOT_TRACK': '1', 'OMP_NUM_THREADS': n}


def _plain_env(extra=None):
    """For running pixi without a wall (macOS and Windows, the POC): only what a program needs, no keys or tokens."""
    keep = ('PATH', 'SYSTEMROOT', 'SystemRoot', 'WINDIR', 'TEMP', 'TMP', 'TMPDIR', 'USERPROFILE', 'HOME', 'LANG',
            'APPDATA', 'LOCALAPPDATA', 'PROGRAMDATA', 'COMSPEC', 'PATHEXT', 'NUMBER_OF_PROCESSORS',
            'PROCESSOR_ARCHITECTURE', 'SSL_CERT_FILE')
    env = {k: v for k, v in os.environ.items() if k in keep}
    env['PYTHONUTF8'] = '1'  # Windows: a tool printing Hindi to a pipe would otherwise crash in cp1252
    env.update(extra or {})
    return env


def walled():
    """Linux keeps Idli's walls (bubblewrap). On macOS and Windows tools run with plain pixi for the POC."""
    return sys.platform.startswith('linux')


def _catalog_host():
    try:
        base, _ = catalog.source()
        return base.split('/')[2].split(':')[0]
    except ValueError:
        return None


def pixi_install(team, timeout=3600):
    """`pixi install` for the team's environment. On Linux inside the install wall (only Idli's egress proxy, to
    package hosts and the catalog), elsewhere directly. Returns (ok, log tail, hosts)."""
    from lib import stackwall
    d = env_dir(team)
    cache = cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    px = stackwall.pixi()
    cmd = [px, 'install', '--manifest-path', str(d / 'pixi.toml')]
    logf = d / '.install.log'
    if not walled():
        with open(logf, 'w') as out:
            try:
                r = subprocess.run(cmd, stdout=out, stderr=subprocess.STDOUT, timeout=timeout, cwd=d,
                                   env=_plain_env(_pixi_env(cache)))
                ok = r.returncode == 0
            except subprocess.TimeoutExpired:
                ok = False
        return ok, logf.read_text(errors='replace')[-2500:], []
    log = []
    host = _catalog_host()
    allow = stackwall.INSTALL_HOSTS + ((host,) if host and host not in ('127.0.0.1', 'localhost') else ())
    sd = stackwall._sockdir()
    proxy = stackwall.EgressProxy(sd / 'egress.sock', allow, log).start()
    try:
        env = {**_pixi_env(cache), **{k: v for k, v in stackwall._env_vars(d, proxy=True).items()
                                      if 'PROXY' in k.upper()}}
        args = stackwall._wall(cmd, binds_rw=[d, cache], binds_ro=[str(Path(px).parent)],
                               doors={stackwall.PROXY_PORT: sd / 'egress.sock'}, env=env, cwd=d)
        with open(logf, 'w') as out:
            try:
                ok = subprocess.run(args, stdout=out, stderr=subprocess.STDOUT, timeout=timeout).returncode == 0
            except subprocess.TimeoutExpired:
                ok = False
    finally:
        proxy.stop()
        shutil.rmtree(sd, ignore_errors=True)
    return ok, logf.read_text(errors='replace')[-2500:], sorted({e['host'] for e in log if not e['allowed']})


def install(data_dir, tool_ids, cat=None, consented=True):
    """Install catalog tools for a team: check, pixi.toml from the union of its tools, pixi install, models from the
    catalog (sha256 checked), then installs.json. Returns {'ok', 'tools', 'steps', ...} or raises ValueError with the
    reasons in plain words."""
    cat = cat if cat is not None else catalog.load()
    tool_ids = [str(t) for t in dict.fromkeys(tool_ids or [])]
    if not tool_ids:
        raise ValueError('Name one or more tools from the catalog.')
    p = plan(data_dir, tool_ids, cat)
    if not p['ok']:
        raise ValueError(' '.join(p['check']['reasons'] + p['conflicts']) or 'These tools cannot be installed here.')
    team = p['team']
    if consented:
        note_consent(data_dir, tool_ids)
    steps, t0 = [], time.time()
    f = write_manifest(team, p['all'], cat, team_tasks(data_dir))
    mine = Path(data_dir).resolve() / 'extensions' / 'stack'
    if not (f.parent / 'pixi.lock').exists() and (mine / 'pixi.lock').exists() and (
            mine / 'pixi.toml').exists() and (mine / 'pixi.toml').read_text() == f.read_text():
        shutil.copyfile(mine / 'pixi.lock', f.parent / 'pixi.lock')  # a teammate gets the author's exact lock
    ok, tail, blocked = pixi_install(team)
    steps.append({'step': 'packages', 'ok': ok, 'seconds': round(time.time() - t0, 1)})
    if not ok:
        return {'ok': False, 'steps': steps, 'log_tail': tail, 'blocked_hosts': blocked}
    by_id = catalog.tools_by_id(cat)
    fetched = []
    for tid in p['all']:
        for m in by_id[tid].get('models') or []:
            t1 = time.time()
            fetch_model(m, fetched)
            steps.append({'step': 'model ' + str(m.get('name')), 'ok': True, 'seconds': round(time.time() - t1, 1)})
    env_bytes = size(env_dir(team))
    share = env_bytes // max(len(p['all']), 1)
    name = team_name(data_dir)
    for tid in p['all']:
        models = [m['sha256'].lower() for m in by_id[tid].get('models') or []]
        mb = sum(size(model_path(m).parent) for m in by_id[tid].get('models') or [])
        record(team, name, tid, models, share + mb)
    _write_definition(data_dir, p['all'])
    return {'ok': True, 'tools': p['all'], 'steps': steps, 'models': fetched,
            'env': str(env_dir(team)), 'size': catalog.gb(env_bytes)}


def installed(data_dir):
    team = team_id(data_dir)
    return bool(team_tools(team)) and (env_dir(team) / '.pixi').exists()


# ---- Mission control: Installed tools ----

def overview(cat=None):
    """Every install, by tool and by team, with the disk they use and what is free."""
    rows = installs()
    names = {}
    try:
        cat = cat if cat is not None else catalog.load()
        names = {k: v.get('name') or k for k, v in catalog.tools_by_id(cat).items()}
    except ValueError:
        pass
    by_tool, by_team = {}, {}
    for r in sorted(rows, key=lambda r: r.get('installed_at', '')):
        item = {**r, 'tool_name': names.get(r['tool'], r['tool']), 'size': catalog.gb(r.get('bytes', 0)),
                'date': str(r.get('installed_at', ''))[:10]}
        by_tool.setdefault(r['tool'], {'tool': r['tool'], 'tool_name': item['tool_name'], 'installs': []})[
            'installs'].append(item)
        by_team.setdefault(r['team'], {'team': r['team'], 'team_name': r.get('team_name') or r['team'],
                                       'installs': []})['installs'].append(item)
    used = size(envs_home()) + size(models_dir()) + size(cache_dir())
    res = catalog.resources(home())
    return {'home': str(home()), 'envs': str(envs_home()), 'platform': res['platform'], 'used': used, 'used_text': catalog.gb(used),
            'free': res['disk_free'], 'free_text': catalog.gb(res['disk_free']),
            'by_tool': sorted(by_tool.values(), key=lambda x: x['tool_name'].lower()),
            'by_team': sorted(by_team.values(), key=lambda x: x['team_name'].lower())}
