"""Transform blocks: readers and transforms the Builder writes for a sandbox (narrative/SANDBOXES.md, "Three levels").

Three levels of what a sandbox can do:
- actions (Gmail drafts, Calendar bookings, any account write): our team builds them (lib/blocks.py);
- transforms (read PDFs, Word files, tables; summarise; ask the 9B): the Builder writes them, here;
- pages and servers: not decided yet (local or on silo).

A transform block is a folder: manifest.json, block.py (`def run(kit, **args)`), test_block.py
(`def test(kit, run)`, fake data only). The Builder (outside every sandbox) writes it in its own folder, never sees
the sandbox's data, and adds it with block_add. Adding runs `check` once: a quick scan of the code (only trusted
imports, no files, network, processes or eval) and the block's fake-data test. The checked folder's digest is
kept; a run checks only that the digest still matches, so a run costs nothing extra.

The same scan applies to the scripts Sandbox Claude writes for Minis (`check_script`), so the Claude inside a
sandbox can't reach past its blocks either.

There is no wall around a run (owner, 2026-11-18): every platform runs the same way for now. The scan and the
trusted list are the guard; walls come with todos/idli-insights/p1/sandboxing_later.md.
"""
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Trusted imports, baked into the build. Silo's catalog may add more ("trusted_imports" in catalog.json, read from
# the local catalog cache only; nothing is fetched here).
STDLIB = {'json', 're', 'math', 'statistics', 'datetime', 'collections', 'itertools', 'functools', 'operator',
          'string', 'textwrap', 'unicodedata', 'decimal', 'fractions', 'typing', 'dataclasses', 'enum', 'io', 'csv',
          'hashlib', 'html', 'difflib', 'heapq', 'bisect', 'copy', 'calendar', 'zoneinfo', 'uuid', 'base64', 'time',
          'random', 'pprint', 'numbers', 'argparse'}
PACKAGES = {'pandas': 'pandas', 'numpy': 'numpy', 'openpyxl': 'openpyxl', 'pypdf': 'pypdf', 'docx': 'python-docx'}
# Mini scripts start with `import os, sys; sys.path.insert(0, os.environ["IDLI_COWORK"]); from lib import blocks`
MINI_ONLY = {'os': {'environ', 'getenv', 'path'}, 'sys': {'path', 'argv', 'stdout', 'stderr', 'exit'}}
MINI_PLATFORM = {'lib': {'blocks'}}
NEVER_CALL = {'eval', 'exec', 'compile', '__import__', 'open', 'input', 'breakpoint', 'globals', 'locals', 'vars',
              'getattr', 'setattr', 'delattr', 'memoryview'}
# os, shutil, pathlib, subprocess and socket can't be imported at all; these catch the same reached another way
NEVER_ATTR = {'system', 'popen', 'Popen', 'unlink', 'rmtree', 'urlopen', 'urlretrieve', 'create_connection',
              'getaddrinfo', 'execv', 'execve', 'read_html', 'read_xml', 'to_pickle', 'read_pickle', 'load_extension',
              'install_extension'}
OS_PATH_OK = {'join', 'basename', 'dirname', 'splitext', 'abspath'}
KINDS = {'pdf': 'PDFs', 'documents': 'Word files', 'spreadsheet': 'spreadsheets', 'images': 'images'}


def trusted():
    """{import name: package} for transform blocks: the build's list plus the catalog's additions."""
    out = {m: 'Python' for m in STDLIB}
    out.update(PACKAGES)
    try:
        from lib import catalog
        cache = catalog.tools_home() / 'catalog-cache.json'
        extra = json.loads(cache.read_text()).get('trusted_imports') if cache.exists() else None
        for name, pkg in (extra or {}).items():
            if isinstance(name, str) and name.isidentifier() and name not in MINI_ONLY:
                out.setdefault(name, str(pkg))
    except Exception:  # noqa: BLE001  the build's list is enough
        pass
    return out


# ---- the scan ----

def _plain(node, why):
    return f'line {getattr(node, "lineno", "?")}: {why}'


def scan(source, kind='block'):
    """Problems in one file of code, in plain words ([] when it passes). kind: 'block' or 'mini'."""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [f'line {e.lineno}: the code does not parse ({e.msg})']
    ok = trusted()
    problems, platform = [], {}
    limited = MINI_ONLY if kind == 'mini' else {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                top = a.name.split('.')[0]
                if top in limited and a.name == top:
                    continue
                if top not in ok:
                    problems.append(_plain(node, f'imports {a.name}, which is not on the trusted list'))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ''
            top = mod.split('.')[0]
            if node.level:
                problems.append(_plain(node, 'imports from a relative path'))
            elif kind == 'mini' and mod in MINI_PLATFORM:
                for a in node.names:
                    if a.name not in MINI_PLATFORM[mod]:
                        problems.append(_plain(node, f'imports lib.{a.name}; a Mini may use lib.blocks only'))
                    platform[a.asname or a.name] = a.name
            elif top in limited:
                problems.append(_plain(node, f'imports from {mod}; use {top}.{"/".join(sorted(limited[top]))} only'))
            elif top not in ok:
                problems.append(_plain(node, f'imports from {mod}, which is not on the trusted list'))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in NEVER_CALL:
            problems.append(_plain(node, f'calls {node.func.id}(), which is not allowed'))
        elif isinstance(node, ast.Name) and node.id.startswith('__') and node.id not in ('__name__',):
            problems.append(_plain(node, f'uses {node.id}'))
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith('_'):
                problems.append(_plain(node, f'reaches into .{node.attr}, a private part'))
            elif node.attr in NEVER_ATTR:
                problems.append(_plain(node, f'calls .{node.attr}, which is not allowed'))
            elif isinstance(node.value, ast.Name) and node.value.id in limited and \
                    node.attr not in limited[node.value.id]:
                problems.append(_plain(node, f'uses {node.value.id}.{node.attr}; only '
                                       f'{", ".join(sorted(limited[node.value.id]))} are allowed'))
            elif isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name) and \
                    node.value.value.id == 'os' and node.value.attr == 'path' and node.attr not in OS_PATH_OK:
                problems.append(_plain(node, f'uses os.path.{node.attr}; only {", ".join(sorted(OS_PATH_OK))}'))
            elif isinstance(node.value, ast.Name) and node.value.id in platform:
                from lib import blocks
                fn = getattr(blocks, node.attr, None)
                if not callable(fn) or getattr(fn, '__module__', '') != 'lib.blocks' or isinstance(fn, type):
                    problems.append(_plain(node, f'uses blocks.{node.attr}; only the block functions are allowed'))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            v = node.value.strip()
            if '://' in v:
                problems.append(_plain(node, 'has a web address; transforms send nothing anywhere'))
            elif v.startswith(('/', '~', '\\')) or (len(v) > 2 and v[1] == ':' and v[2] in '\\/') or \
                    '../' in v or '..\\' in v:
                problems.append(_plain(node, 'names a file path outside the sandbox'))
    return problems[:12]


def check_script(path):
    """A Mini script Sandbox Claude wrote: [] or the plain problems. Quiet and fast (one parse)."""
    try:
        return scan(Path(path).read_text(), 'mini')
    except OSError:
        return ['the script could not be read']


# ---- a block's folder ----

def _files(folder):
    folder = Path(folder)
    return sorted(p for p in folder.rglob('*') if p.is_file() and '.idli' not in p.parts and
                  '__pycache__' not in p.parts and not p.name.startswith('.'))


def digest(folder):
    h = hashlib.sha256()
    for p in _files(folder):
        if p.suffix in ('.py', '.json'):
            h.update(p.relative_to(folder).as_posix().encode() + b'\0' + p.read_bytes() + b'\0')
    return h.hexdigest()


def manifest(folder):
    try:
        m = json.loads((Path(folder) / 'manifest.json').read_text())
    except (OSError, ValueError):
        return None
    return m if isinstance(m, dict) else None


NAME_OK = 'abcdefghijklmnopqrstuvwxyz0123456789_'


def _manifest_problems(m, folder):
    if not m:
        return ['manifest.json is missing or not JSON']
    out = []
    name = str(m.get('name') or '')
    if not name or any(c not in NAME_OK for c in name) or len(name) > 30:
        out.append('manifest name: lower-case letters, digits and _ only')
    elif name != Path(folder).name:
        out.append(f'the folder must be named {name}, like the manifest')
    if not str(m.get('title') or '').strip():
        out.append('manifest title is missing (a few words, e.g. "Read PDFs")')
    if m.get('level', 'transform') != 'transform':
        out.append('only transform blocks can be added; actions are built by our team')
    for k in m.get('reads') or []:
        if k not in KINDS:
            out.append(f'manifest reads "{k}"; use one of: {", ".join(KINDS)}')
    for name in m.get('uses') or []:
        if str(name) not in trusted() and str(name) not in trusted().values():
            out.append(f'manifest uses {name}, which is not on the trusted list')
    for f in ('block.py', 'test_block.py'):
        if not (Path(folder) / f).is_file():
            out.append(f'{f} is missing')
    return out


def card(folder):
    """The one approval card's words: what the block is and what it can't do."""
    m = manifest(folder) or {}
    used = [str(u) for u in m.get('uses') or []] or ['Python only']
    reads = ' and '.join(KINDS[k] for k in m.get('reads') or [] if k in KINDS) or 'files'
    return (f'Add block: {str(m.get("title") or m.get("name")).strip().rstrip(".")}. Uses {", ".join(used)}. '
            f'Reads {reads} you give it. Sends nothing.')


RUNNER = ROOT / 'lib' / 'transformrun.py'


def _python():
    py = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    return str(py) if py.exists() else sys.executable


def _spawn(mode, folder, sandbox, args, timeout, env_extra=None):
    with tempfile.TemporaryDirectory(prefix='idli-block-') as tmp:
        a, out = Path(tmp) / 'args.json', Path(tmp) / 'out.json'
        a.write_text(json.dumps(args or {}))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('PASEO_', 'CF_', 'IDLI_SILO'))}
        env.update(env_extra or {})
        env['PYTHONUTF8'] = '1'
        try:
            r = subprocess.run([_python(), '-I', str(RUNNER), mode, str(folder), str(sandbox or ''), str(a),
                                str(out)], capture_output=True, text=True, timeout=timeout, env=env,
                               stdin=subprocess.DEVNULL, cwd=str(folder))
        except subprocess.TimeoutExpired:
            return {'ok': False, 'error': f'it took longer than {timeout} s'}
        try:
            res = json.loads(out.read_text())
        except (OSError, ValueError):
            res = {'ok': False, 'error': (r.stderr or 'it stopped without an answer').strip().splitlines()[-1][:300]
                   if (r.stderr or '').strip() else 'it stopped without an answer'}
        res['progress'] = [l[9:] for l in (r.stderr or '').splitlines() if l.startswith('PROGRESS ')][-20:]
        return res


def check(folder, run_tests=True):
    """Check a block once: manifest, the scan of every .py, then its fake-data test (about a second).
    Returns {'ok', 'problems', 'card', 'digest', 'seconds'}; on success writes .idli/checked.json in the folder."""
    t0 = time.time()
    folder = Path(folder).resolve()
    m = manifest(folder)
    problems = _manifest_problems(m, folder)
    for p in _files(folder):
        if p.suffix == '.py':
            problems += [f'{p.name} {x}' for x in scan(p.read_text(errors='replace'), 'block')]
        elif p.suffix not in ('.json', '.md', '.txt', '.csv'):
            problems.append(f'{p.name}: only code, the manifest and notes belong in a block (use fake data in the test)')
    if not problems and run_tests:
        res = _spawn('test', folder, None, {}, 90)
        if not res.get('ok'):
            problems.append('its test failed: ' + str(res.get('error') or 'no reason given')[:300])
    out = {'ok': not problems, 'problems': problems[:12], 'card': card(folder) if m else '',
           'seconds': round(time.time() - t0, 1)}
    if out['ok']:
        out['digest'] = digest(folder)
        (folder / '.idli').mkdir(exist_ok=True)
        (folder / '.idli' / 'checked.json').write_text(json.dumps({'digest': out['digest'], 'when': time.time()}))
    return out


# ---- a sandbox's transform blocks ----

def sandbox_blocks_dir(sandbox):
    return Path(sandbox).resolve() / 'blocks'


def installed(sandbox):
    """{name: manifest} for the transform blocks added to this sandbox (listed in team.json)."""
    try:
        meta = json.loads((Path(sandbox) / 'team.json').read_text())
    except (OSError, ValueError):
        return {}
    out = {}
    for name in meta.get('transforms') or []:
        m = manifest(sandbox_blocks_dir(sandbox) / str(name))
        if m:
            out[str(name)] = m
    return out


def for_kinds(sandbox, kinds):
    """The first added block that reads one of these kinds of file (e.g. ['pdf'])."""
    for name, m in installed(sandbox).items():
        if set(m.get('reads') or []) & set(kinds or []):
            return name, m
    return None, None


def add(sandbox, folder):
    """Copy a checked block into a sandbox and list it in team.json. The Builder's block_add calls this after the
    person's yes (desktop/idli-block-consent.py asks)."""
    folder, sandbox = Path(folder).resolve(), Path(sandbox).resolve()
    res = check(folder)
    if not res['ok']:
        return {'ok': False, 'problems': res['problems']}
    name = manifest(folder)['name']
    dest = sandbox_blocks_dir(sandbox) / name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for p in _files(folder):
        (dest / p.relative_to(folder)).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, dest / p.relative_to(folder))
    (dest / '.idli').mkdir()
    (dest / '.idli' / 'checked.json').write_text(json.dumps({'digest': digest(dest), 'when': time.time()}))
    meta_path = sandbox / 'team.json'
    meta = json.loads(meta_path.read_text())
    meta['transforms'] = sorted(set(meta.get('transforms') or []) | {name})
    meta_path.write_text(json.dumps(meta, indent=2))
    return {'ok': True, 'name': name, 'title': manifest(dest).get('title'), 'seconds': res['seconds']}


def run(sandbox, name, args=None, timeout=900):
    """Run an added block on the sandbox's real files. The 9B is reached through a door on 127.0.0.1 (the silo key
    stays in this process). Returns the block's dict ({'reply': ...}) or {'error': ...}."""
    sandbox = Path(sandbox).resolve()
    if str(name) not in installed(sandbox):
        return {'error': f'This sandbox has no block called {name}. The Builder can add one.'}
    folder = sandbox_blocks_dir(sandbox) / str(name)
    try:
        want = json.loads((folder / '.idli' / 'checked.json').read_text())['digest']
    except (OSError, ValueError, KeyError):
        want = None
    if want != digest(folder):
        return {'error': 'This block changed after it was checked. Ask the Builder to add it again.'}
    m = manifest(folder)
    args = dict(args or {})
    files, missed = [], []
    if m.get('reads'):
        got = fetch_drive(sandbox, args.pop('paths', None) or [], m['reads'])
        if got.get('error'):
            return got
        files, missed = got['files'], got.get('missed') or []
    from lib import stackwall
    door = stackwall.ModelDoor(None).start()
    try:
        res = _spawn('run', folder, sandbox, {'args': args, 'files': files}, timeout,
                     {'IDLI_MODEL_URL': f'http://127.0.0.1:{door.port}'})
    finally:
        door.stop()
    if not res.get('ok'):
        return {'error': f'{m.get("title") or name} could not finish: {res.get("error") or "no reason given"}'}
    out = res['result'] if isinstance(res.get('result'), dict) else {'reply': str(res.get('result'))}
    return {**out, **({'missed': missed} if missed else {})}


def fetch_drive(sandbox, paths, kinds):
    """The person's @ Drive paths, as local files of the kinds a block reads (downloaded once, then reused)."""
    from concurrent.futures import ThreadPoolExecutor
    from lib import drivefetch, drivestubs, teamcaps
    if not paths:
        return {'error': 'Pick the files or a folder with @ first.'}
    entries = drivestubs.refresh(sandbox)
    chosen = {}
    for name in paths:
        rel = drivestubs._relative(str(name)[6:].rstrip('/')) if str(name).startswith('Drive/') else None
        if rel is None:
            continue
        hits = {p: e for p, e in entries.items() if p == rel or p.startswith(rel + '/')}
        chosen.update(hits)
    chosen = {p: e for p, e in chosen.items() if teamcaps.kind_of(p) in kinds}
    if not chosen:
        return {'error': 'There are no ' + ' or '.join(KINDS.get(k, k) for k in kinds) + ' there.'}

    def one(item):
        rel, e = item
        dest = sandbox / 'drive' / rel
        src = Path(str(dest) + '.source.json')
        try:
            if not (dest.is_file() and src.is_file() and json.loads(src.read_text()).get('id') == e['id']):
                data = drivefetch.fetch(e['id'], sheet=False)
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_name(dest.name + '.part')
                tmp.write_bytes(data)
                os.replace(tmp, dest)
                src.write_text(json.dumps({**e, 'sheet': False}))
            return {'title': e.get('title') or Path(rel).name, 'kind': teamcaps.kind_of(rel), 'path': str(dest),
                    'id': e['id']}
        except (drivefetch.NoAccess, drivefetch.NoGoogle, OSError):
            return {'title': e.get('title') or Path(rel).name, 'error': True}

    with ThreadPoolExecutor(4) as pool:
        got = list(pool.map(one, sorted(chosen.items())))
    files = [g for g in got if not g.get('error')]
    if not files:
        return {'error': 'Could not download those files. Check you can open them in Drive.'}
    return {'files': files, 'missed': [g['title'] for g in got if g.get('error')]}
