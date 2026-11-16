"""What a team knows how to do, and how the Builder extends it (narrative/MODEL_TYPES.md).

A team's base (today: Drivey's) reads spreadsheets. Its extensions live in <team>/extensions/: a manifest, readers,
Analyst skills, tests and fake samples, tracked by a local git repo so every change can be undone. A capability
counts only while its test passes on the files as they are now (a changed file needs a new passing run).

Readers run in Idli's bubblewrap wall (lib/chartkit.wall): no network, read-only filesystem, home folders hidden, only
the input file and the output folder visible. They turn a file into CSV tables, and the usual pipeline (privacy
review, masked copies, Analyst, Minis) takes it from there.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BASE = [
    {'id': 'spreadsheets', 'title': 'Read Excel, CSV and Google Sheets files', 'reads': ['spreadsheet']},
    {'id': 'privacy', 'title': 'Hide names, places and phone numbers as codes before Claude sees them'},
    {'id': 'analysis', 'title': 'Analyse tables with pandas, and draw charts and India maps'},
    {'id': 'minis', 'title': 'Save Minis and answer their questions on this computer'},
]

# kind -> (label, file suffixes, words people use for it)
KINDS = {
    'spreadsheet': ('spreadsheets', ('.xlsx', '.csv'), ()),
    'images': ('images', ('.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff', '.bmp', '.heic'),
               ('image', 'images', 'photo', 'photos', 'picture', 'pictures', 'scan', 'scans', 'scanned', 'jpg',
                'jpeg', 'png', 'handwritten', 'ocr')),
    'audio': ('voice notes and audio', ('.mp3', '.m4a', '.wav', '.ogg', '.opus', '.aac', '.amr'),
              ('audio', 'voice', 'recording', 'recordings', 'mp3', 'transcribe', 'transcript')),
    'video': ('videos', ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.3gp'), ('video', 'videos', 'clip', 'clips')),
    'pdf': ('PDFs', ('.pdf',), ('pdf', 'pdfs')),
    'documents': ('documents', ('.docx', '.doc', '.pptx', '.txt'),
                  ('document', 'documents', 'docx', 'word file', 'slides', 'presentation')),
}
MANIFEST = 'manifest.json'
TESTED = '.idli-tested.json'
ID = re.compile(r'[a-z0-9][a-z0-9-]{0,40}')


def ext_dir(data_dir):
    return Path(data_dir).resolve() / 'extensions'


def kind_of(name):
    suffix = Path(str(name)).suffix.lower()
    return next((k for k, (_, sufs, _) in KINDS.items() if suffix in sufs), None)


def label(kind):
    return KINDS.get(kind, (kind or 'these files',))[0]


def kinds_in_words(text):
    """Kinds of file a request talks about ("can you read these photos?"), by whole words."""
    words = set(re.findall(r"[a-z]+", str(text).lower()))
    low = str(text).lower()
    return [k for k, (_, _, ws) in KINDS.items() if any((w in words) if ' ' not in w else (w in low) for w in ws)]


# ---- the extensions folder, its manifest and git ----

README = """# This team's extensions

Made by the Builder (narrative/MODEL_TYPES.md). Read the `build-team` skill before changing anything here.
- `manifest.json` lists the capabilities. Each one has an entry file and a test.
- `samples/` holds fake files to build and test with. Never real files.
- Every change is saved as a checkpoint; the team card's Versions can go back to any of them.
"""


def _git(d, *args, check=True):
    env = {**os.environ, 'GIT_AUTHOR_NAME': 'Idli', 'GIT_AUTHOR_EMAIL': 'idli@localhost',
           'GIT_COMMITTER_NAME': 'Idli', 'GIT_COMMITTER_EMAIL': 'idli@localhost', 'GIT_TERMINAL_PROMPT': '0'}
    out = subprocess.run(['git', '-C', str(d), *args], capture_output=True, text=True, env=env, timeout=60)
    if check and out.returncode:
        raise RuntimeError((out.stderr or out.stdout).strip()[:300])
    return out.stdout


def ensure(data_dir):
    """The extensions folder with its manifest and history (safe to call every time)."""
    d = ext_dir(data_dir)
    for sub in ('samples', 'tests', 'skills'):
        (d / sub).mkdir(parents=True, exist_ok=True)
    if not (d / MANIFEST).exists():
        (d / MANIFEST).write_text(json.dumps({'capabilities': []}, indent=2) + '\n')
    if not (d / 'README.md').exists():
        (d / 'README.md').write_text(README)
    ignore = d / '.gitignore'
    if not ignore.exists():
        ignore.write_text('.claude/\n.idli-*\n__pycache__/\n*.pyc\n.mcp.json\nCLAUDE.local.md\n')
    if not (d / '.git').exists():
        _git(d, 'init', '-q', '-b', 'main')
        checkpoint(data_dir, 'Start')
    return d


def checkpoint(data_dir, message):
    """Save the extensions as they are now. Returns the version id, or None when nothing changed."""
    d = ext_dir(data_dir)
    _git(d, 'add', '-A')
    if not _git(d, 'status', '--porcelain').strip() and _git(d, 'rev-parse', '--verify', '-q', 'HEAD', check=False):
        return None
    _git(d, 'commit', '-q', '--allow-empty', '-m', ' '.join(str(message).split())[:120] or 'Checkpoint')
    return _git(d, 'rev-parse', '--short', 'HEAD').strip()


def versions(data_dir):
    d = ext_dir(data_dir)
    if not (d / '.git').exists():
        return []
    out = _git(d, 'log', '--format=%h%x09%ct%x09%s', '-n', '50', check=False)
    rows = []
    for line in out.splitlines():
        rev, at, msg = (line.split('\t', 2) + ['', ''])[:3]
        rows.append({'id': rev, 'at': int(at or 0), 'when': time.strftime('%d %b %H:%M', time.localtime(int(at or 0))),
                     'message': msg})
    return rows


def restore(data_dir, rev):
    """Go back to a version. The current state is saved first, and going back is itself a new version."""
    if not re.fullmatch(r'[0-9a-f]{4,40}', str(rev)):
        raise ValueError('Pick a version from the list.')
    d = ext_dir(data_dir)
    msg = _git(d, 'log', '-1', '--format=%s', rev, check=False).strip()
    if not msg:
        raise ValueError('That version is not in this team.')
    checkpoint(data_dir, 'Before going back')
    for f in _git(d, 'ls-files', '-z').split('\0'):
        if f:
            p = d / f
            if p.is_file() or p.is_symlink():
                p.unlink()
    _git(d, 'checkout', rev, '--', '.')
    (d / TESTED).unlink(missing_ok=True)  # tests run again on what came back
    run_tests(data_dir)
    return checkpoint(data_dir, 'Went back to: ' + msg) or rev


# ---- the manifest and what is tested ----

def _entry(d, rel):
    p = (d / str(rel)).resolve()
    if not p.is_relative_to(d) or not p.is_file():
        raise ValueError(f'{rel} is not a file in extensions/')
    return p


def manifest(data_dir):
    """The declared capabilities, checked. Problems are returned, not raised, so one bad entry can't hide the rest."""
    d = ext_dir(data_dir)
    try:
        caps = json.loads((d / MANIFEST).read_text()).get('capabilities', [])
    except (OSError, ValueError, AttributeError):
        return [], ['manifest.json is missing or not valid JSON']
    good, problems, seen = [], [], {c['id'] for c in BASE}
    for c in caps if isinstance(caps, list) else []:
        try:
            if not isinstance(c, dict) or not ID.fullmatch(str(c.get('id', ''))) or c['id'] in seen:
                raise ValueError('each capability needs its own id (lowercase letters, digits and -)')
            seen.add(c['id'])
            if not str(c.get('title', '')).strip():
                raise ValueError('a title is missing')
            kind = c.get('kind', 'reader')
            if kind not in ('reader', 'skill', 'tool', 'app'):
                raise ValueError('kind is reader, skill, tool or app')
            if (c.get('stack') or kind == 'app') and not (d / 'stack' / 'pixi.toml').is_file():
                raise ValueError('it uses the stack, but stack/pixi.toml is missing')
            if kind == 'tool':
                takes = c.get('takes') or []
                if not takes or any(t not in KINDS and t != 'none' for t in takes):
                    raise ValueError('takes lists file kinds (' + ', '.join(KINDS) + ') or none')
                _entry(d, c.get('entry', ''))
            if kind == 'app' and not re.fullmatch(r'[\w-]{1,40}', str(c.get('serve', ''))):
                raise ValueError('serve names a task in stack/pixi.toml that starts the page')
            if kind == 'reader':
                reads = c.get('reads') or []
                if not reads or any(r not in KINDS or r == 'spreadsheet' for r in reads):
                    raise ValueError('reads lists file kinds: ' + ', '.join(k for k in KINDS if k != 'spreadsheet'))
                _entry(d, c.get('entry', ''))
            if c.get('skill'):
                if not (d / 'skills' / str(c['skill']) / 'SKILL.md').is_file():
                    raise ValueError('skills/' + str(c['skill']) + '/SKILL.md is missing')
            _entry(d, c.get('test', ''))
            good.append({**c, 'kind': kind, 'stack': bool(c.get('stack') or kind == 'app')})
        except (ValueError, KeyError) as exc:
            problems.append(f"{c.get('id', '?') if isinstance(c, dict) else '?'}: {exc}")
    return good, problems


def _fingerprint(d, cap):
    h = hashlib.sha256()
    files = [cap.get('entry'), cap.get('test')]
    files += [str(p.relative_to(d)) for p in sorted((d / 'skills' / str(cap.get('skill', ''))).rglob('*'))
              if p.is_file()] if cap.get('skill') else []
    files += [str(p.relative_to(d)) for p in sorted((d / 'samples').rglob('*')) if p.is_file()]
    for rel in filter(None, files):
        p = d / rel
        h.update(rel.encode() + b'\0' + (p.read_bytes() if p.is_file() else b'') + b'\0')
    for p in sorted(d.glob('*.py')):  # helpers next to the entries
        h.update(p.name.encode() + p.read_bytes())
    if cap.get('stack'):  # the stack's definition and its code, not what got installed
        st = d / 'stack'
        for p in sorted(st.rglob('*')):
            rel = p.relative_to(st)
            if p.is_file() and rel.parts[0] not in STACK_INSTALLED and not rel.name.startswith('.'):
                h.update(str(rel).encode() + b'\0' + p.read_bytes())
    return h.hexdigest()[:16]


STACK_INSTALLED = ('.pixi', 'repos', 'models', '.cache')


def _tested(data_dir):
    try:
        return json.loads((ext_dir(data_dir) / TESTED).read_text())
    except (OSError, ValueError):
        return {}


def capabilities(data_dir):
    """The base plus every extension whose test passed on the files as they are now."""
    d = ext_dir(data_dir)
    caps, _ = manifest(data_dir) if d.exists() else ([], [])
    tested = _tested(data_dir)
    active = [c for c in caps if (tested.get(c['id']) or {}).get('ok') and
              tested[c['id']].get('fingerprint') == _fingerprint(d, c)]
    return BASE + active


def readable(data_dir):
    kinds = []
    for c in capabilities(data_dir):
        kinds += [k for k in c.get('reads', []) if k not in kinds]
    return kinds


def reader_for(data_dir, kind):
    return next((c for c in capabilities(data_dir) if c.get('kind') == 'reader' and kind in c.get('reads', [])), None)


def _python():
    py = ROOT / '.venv/bin/python'
    return str(py) if py.exists() else sys.executable


RUN_READER = r"""
import importlib.util, sys
root, entry, src, out = sys.argv[1:5]
sys.path.insert(0, root + '/lib')  # capmenu is importable as itself
spec = importlib.util.spec_from_file_location('reader', entry)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.read(src, out)
"""


def _wall(cmd, reads, writes):
    from lib import chartkit
    return chartkit.wall(cmd, reads=reads, writes=writes)


def _in_stack(data_dir, code, argv, inputs=(), out=None, timeout=1800, cwd=None):
    """Run platform glue code with the stack's Python, inside the stack's run wall (lib/stackwall.py)."""
    from lib import stackwall
    if not stackwall.installed(data_dir):
        raise ValueError('The stack is not installed. The Builder installs it with stack_install.')
    return stackwall.run(data_dir, ['python', '-I', '-c', code, *map(str, argv)], inputs=inputs, out_dir=out,
                         timeout=timeout, cwd=cwd, extra_ro=[ROOT / 'lib', ext_dir(data_dir)])


def run_reader(data_dir, cap, src, timeout=1800):
    """Turn one file into CSV tables with the team's reader, inside the wall. Returns the CSV paths (next to src)."""
    d = ext_dir(data_dir)
    src = Path(src).resolve()
    entry = _entry(d, cap['entry'])
    with tempfile.TemporaryDirectory(prefix='idli-read-') as out:
        if cap.get('stack'):
            r = _in_stack(data_dir, RUN_READER, [ROOT, entry, src, out], inputs=[src], out=out, timeout=timeout)
            failed = not r['ok']
        else:
            cmd = _wall([_python(), '-I', '-c', RUN_READER, str(ROOT), str(entry), str(src), out],
                        reads=[str(ROOT / 'lib'), str(ROOT / '.venv'), str(d), str(src)], writes=[out])
            failed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=out).returncode
        tables = sorted(Path(out).glob('*.csv'))
        if failed or not tables:
            raise ValueError(f"{cap['title']} could not read this file.")
        made = []
        for i, t in enumerate(tables[:20]):
            dest = src.with_name(src.name + ('' if len(tables) == 1 else f'.{t.stem}') + '.csv')
            shutil.copyfile(t, dest)
            made.append(dest)
        return made


RUN_TEST = r"""
import runpy, sys
root, test = sys.argv[1:3]
sys.path.insert(0, root + '/lib')
sys.argv = [test]
runpy.run_path(test, run_name='__main__')
"""


def run_tests(data_dir, timeout=300):
    """Run each capability's test in the wall, from extensions/. A test passes when it exits 0."""
    d = ensure(data_dir)
    caps, problems = manifest(data_dir)
    results = {}
    for c in caps:
        if c.get('stack'):
            try:
                r = _in_stack(data_dir, RUN_TEST, [ROOT, _entry(d, c['test'])], cwd=d, timeout=timeout)
                ok, out = r['ok'], r['output'][-1500:]
            except ValueError as exc:
                ok, out = False, str(exc)
            results[c['id']] = {'ok': ok, 'fingerprint': _fingerprint(d, c), 'at': int(time.time()), 'output': out}
            continue
        with tempfile.TemporaryDirectory(prefix='idli-test-') as tmp:
            cmd = _wall([_python(), '-I', '-c', RUN_TEST, str(ROOT), str(_entry(d, c['test']))],
                        reads=[str(ROOT / 'lib'), str(ROOT / '.venv'), str(d)], writes=[tmp])
            try:
                run = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(d),
                                     env={**os.environ, 'TMPDIR': tmp})
                ok, out = run.returncode == 0, (run.stdout + run.stderr)[-1500:]
            except subprocess.TimeoutExpired:
                ok, out = False, f'took longer than {timeout} s'
        results[c['id']] = {'ok': ok, 'fingerprint': _fingerprint(d, c), 'at': int(time.time()), 'output': out}
    (d / TESTED).write_text(json.dumps(results, indent=2))
    return {'results': {k: {'ok': v['ok'], 'output': v['output']} for k, v in results.items()}, 'problems': problems}


RUN_TOOL = r"""
import importlib.util, json, sys
root, entry, out, args = sys.argv[1:5]
inputs = sys.argv[5:]
sys.path.insert(0, root + '/lib')
spec = importlib.util.spec_from_file_location('tool', entry)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
res = mod.run(inputs, json.loads(args), out)
print('IDLI_RESULT ' + json.dumps(res if isinstance(res, dict) else {}, default=str)[:4000])
"""


def tools(data_dir):
    return [c for c in capabilities(data_dir) if c.get('kind') == 'tool']


def run_tool(data_dir, cap, inputs, args, timeout=3600):
    """Run a tool on the original files with the Analyst's instructions (JSON). Its files go to the team's
    outputs/ folder, which the person opens; the Analyst gets back only file names and the tool's short result."""
    d = ext_dir(data_dir)
    inputs = [Path(p).resolve() for p in inputs]
    takes = cap.get('takes') or []
    for p in inputs:
        if kind_of(p) not in takes and kind_of(p) != 'spreadsheet':
            raise ValueError(f"{cap['title']} takes {', '.join(label(k) for k in takes if k in KINDS)}.")
    out = Path(data_dir).resolve() / 'outputs' / (time.strftime('%Y-%m-%d %H%M%S ') + cap['id'])
    out.mkdir(parents=True, exist_ok=True)
    entry = _entry(d, cap['entry'])
    argv = [ROOT, entry, out, json.dumps(args or {}), *inputs]
    if cap.get('stack'):
        r = _in_stack(data_dir, RUN_TOOL, argv, inputs=inputs, out=out, timeout=timeout)
        ok, text = r['ok'], r['output']
    else:
        cmd = _wall([_python(), '-I', '-c', RUN_TOOL, *map(str, argv)],
                    reads=[str(ROOT / 'lib'), str(ROOT / '.venv'), str(d), *map(str, inputs)], writes=[str(out)])
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(out))
        ok, text = p.returncode == 0, p.stdout + p.stderr
    result = {}
    for line in text.splitlines():
        if line.startswith('IDLI_RESULT '):
            try:
                result = json.loads(line[12:])
            except ValueError:
                pass
    if not ok:
        raise ValueError(f"{cap['title']} did not finish on this file.")
    return {'folder': str(out), 'files': sorted(str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()),
            'result': result}


# ---- what each model is told ----

def describe(data_dir, team):
    """The Analyst's list of what this team knows how to do (appended to its CLAUDE.md at launch)."""
    lines = [f'# What {team} knows how to do', '',
             f'These are the tested capabilities of the {team} team. Work only within them:']
    for c in capabilities(data_dir):
        how = {'tool': f" (tool `{c['id']}`: call team_run)", 'app': f" (a page: call app_open with `{c['id']}`)"}
        lines.append(f"- {c['title']}" + (f" ({c.get('analyst', '')})" if c.get('analyst') else '')
                     + how.get(c.get('kind'), ''))
    missing = [label(k) for k in KINDS if k not in readable(data_dir)]
    if missing:
        lines += ['', f"{team} can't read these yet: " + ', '.join(missing) + '.']
    lines += ['',
              "If the person asks for something outside this list (a new kind of file, a new tool, a site the team "
              "hasn't learned), don't improvise a one-off. Say plainly that the team can't do it yet, and ask with "
              "AskUserQuestion whether to open the Builder, which adds it to the team. On yes, call `builder_open` "
              "with their request in one or two sentences. Within the list, you can extend Minis as usual."]
    return '\n'.join(lines) + '\n'


def team_name(data_dir):
    try:
        return json.loads((Path(data_dir) / 'team.json').read_text())['name']
    except (OSError, ValueError, KeyError):
        return 'Drivey'


def platform_request(data_dir, text):
    """The Builder asks for something only the platform can add (a package, a model). Kept for us to read."""
    d = ext_dir(data_dir)
    with open(d / 'platform-requests.md', 'a') as f:
        f.write(f"- {time.strftime('%Y-%m-%d %H:%M')}: {' '.join(str(text).split())[:600]}\n")
    return {'saved': True}
