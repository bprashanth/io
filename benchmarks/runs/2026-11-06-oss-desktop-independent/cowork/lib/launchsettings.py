"""Merge the masked project's Claude settings without replacing other settings.

Claude works on masked copies in its own folder. Its shell runs in Claude Code's sandbox, which cannot read Idli's
private folder (the real files, the vault, privacy choices), Idli's caches or the browser's sign-ins. The Read, Edit
and search tools get the same limits as permission rules. Idli's own tools (MCP) run outside the sandbox.
"""
import json
import sys
import shlex
from pathlib import Path
import os
import tempfile

ASK = ['mcp__idli__unmask', 'mcp__idli__script_try']


def private_paths(data_dir, work):
    home = Path.home()
    work = Path(work).resolve()
    from lib import wirelog  # the "Sent to Claude" log, even before it exists
    paths = [Path(data_dir).resolve(), home / '.cache/idli', home / '.paseo', home / '.config/Paseo',
             home / '.config/paseo', home / '.config/idlisseus', wirelog.folder()]
    # Everything else Idli keeps beside Claude's folder (other workspaces, downloads, settings).
    parent = work.parent
    if parent != home and parent.name == 'idli-insights':
        paths += [p for p in parent.iterdir() if p.resolve() != work] if parent.exists() else []
    # Claude Code matches these rules without regard to case: a sibling "Claude-masked" would also hide
    # "claude-masked" and Claude's own CLAUDE.md (laptop, 2026-11-15). Leave out anything that matches work that way.
    def covers_work(p):
        folded = Path(str(p.resolve()).casefold())
        return folded == Path(str(work).casefold()) or Path(str(work).casefold()).is_relative_to(folded)
    return sorted({str(p.resolve()) for p in paths if not covers_work(p)})


def merge(work, data_dir=None):
    path = Path(work) / '.claude/settings.json'
    settings = json.loads(path.read_text()) if path.exists() else {}
    permissions = settings.setdefault('permissions', {})
    permissions['ask'] = list(dict.fromkeys(permissions.get('ask', []) + ASK))
    if data_dir:
        private = private_paths(data_dir, work)
        rules = [f'{tool}(/{p}/**)' for p in private for tool in ('Read', 'Edit')]
        own = str(Path(work).resolve()).casefold()
        def blocks_work(path):  # an older rule that covers Claude's own folder (see private_paths)
            folded = path.casefold().rstrip('/')
            return own == folded or own.startswith(folded + '/')
        old = [r for r in permissions.get('deny', [])
               if not (r.startswith(('Read(//', 'Edit(//')) and r.endswith('/**)') and blocks_work(r.split('(/', 1)[1][:-4]))]
        permissions['deny'] = list(dict.fromkeys(old + rules))
        sandbox = settings.setdefault('sandbox', {})
        sandbox.update({'enabled': True, 'autoAllowBashIfSandboxed': True, 'allowUnsandboxedCommands': False})
        fs = sandbox.setdefault('filesystem', {})
        # Claude Code's own transcripts hold the person's real values (Claude's replies with codes put back). Claude
        # Code reads them itself; its shell must not.
        transcripts = str((Path.home() / '.claude/projects').resolve())
        fs['denyRead'] = sorted({p for p in fs.get('denyRead', []) if not blocks_work(p)} | set(private) | {transcripts})
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(settings, out, indent=2)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def builder_private(data_dir, ext):
    """What the Builder must not read: everything of the team except extensions/, every other team and Idli folder,
    Idli's caches and settings, Paseo's data and Claude Code's transcripts (narrative/MODEL_TYPES.md)."""
    home = Path.home()
    data, ext = Path(data_dir).resolve(), Path(ext).resolve()
    paths = [p for p in data.iterdir() if p.resolve() != ext] if data.exists() else []
    # Always, even before they exist: the team's own settings (test accounts, consent) and the Chrome profiles
    # (their cookies are the test and real accounts' sign-ins). The Builder reaches profiles only through Idli's tools.
    from lib import chromeprofiles
    paths += [data / '.idli', home / 'idli-insights' / 'browsers', chromeprofiles.root()]
    idli = (home / 'idli-insights').resolve()
    if idli.exists():
        for p in idli.iterdir():
            r = p.resolve()
            if r == data:
                continue
            if data.is_relative_to(r):  # teams/: every other team
                paths += [q for q in r.iterdir() if q.resolve() != data]
                continue
            paths.append(p)
    from lib import wirelog
    paths += [home / '.cache/idli', home / '.paseo', home / '.config/Paseo', home / '.config/paseo',
              home / '.config/idlisseus', wirelog.folder(), home / '.claude/projects']
    return sorted({str(Path(p).resolve()) for p in paths})


def merge_builder(ext, data_dir, platform):
    """The Builder's settings: Claude Code's sandbox on, reads denied as above, edits only inside extensions/ (the
    platform source is reference, read only)."""
    path = Path(ext) / '.claude/settings.json'
    settings = json.loads(path.read_text()) if path.exists() else {}
    private = builder_private(data_dir, ext)
    permissions = settings.setdefault('permissions', {})
    deny = [f'{tool}(/{p}/**)' for p in private for tool in ('Read', 'Edit')]
    deny += [f'Edit(/{Path(platform).resolve()}/**)']
    permissions['deny'] = sorted(set(deny))
    # Claude Code's own scratch folder (it crops and previews sample images there): a working folder, so no prompt
    scratch = str(Path(tempfile.gettempdir()) / f'claude-{os.getuid()}')
    permissions['additionalDirectories'] = sorted(set(permissions.get('additionalDirectories', []) + [scratch]))
    permissions['allow'] = sorted(set(permissions.get('allow', []) + [
        f'Read(/{Path(platform).resolve()}/**)', 'mcp__idli__team_check', 'mcp__idli__team_save',
        'mcp__idli__platform_request', 'mcp__idli__stack_run', 'mcp__idli__capability_menu',
        'mcp__idli__catalog', 'mcp__idli__catalog_request', 'mcp__idli__profiles', 'mcp__idli__profile_new',
        'mcp__idli__browser_open', 'mcp__idli__browser_read', 'mcp__idli__browser_click', 'mcp__idli__browser_type',
        'mcp__idli__browser_shot', 'mcp__idli__browser_tabs', 'mcp__idli__rehearse', 'mcp__idli__routine_check', 'mcp__idli__routine_config_set', 'mcp__idli__google_connect',
        'mcp__idli__routine_rehearse']))
    # test_account_set is never allowed here: Idli's hook asks the person every time (builder_hooks)
    permissions['allow'] = [a for a in permissions['allow'] if a != 'mcp__idli__test_account_set']
    # Its own settings and the installed stack are Idli's, not the Builder's to change
    permissions['deny'] = sorted(set(permissions['deny'] + [
        f'Edit(/{Path(ext).resolve()}/.claude/**)', f'Edit(/{Path(ext).resolve()}/stack/.pixi/**)',
        f'Edit(/{Path(ext).resolve()}/stack/stack-lock.json)', f'Edit(/{Path(ext).resolve()}/stack/catalog.json)']))
    sandbox = settings.setdefault('sandbox', {})
    sandbox.update({'enabled': True, 'autoAllowBashIfSandboxed': True, 'allowUnsandboxedCommands': False})
    sandbox.setdefault('filesystem', {})['denyRead'] = private
    # The team folder's CLAUDE.md is the left chat's (and is denied): skip it rather than warn at every start
    settings['claudeMdExcludes'] = [str((Path(data_dir).resolve() / 'CLAUDE.md'))]
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent)
    with os.fdopen(fd, 'w') as out:
        json.dump(settings, out, indent=2)
    os.replace(temp, path)


def builder_hooks(data_dir, platform):
    """The Builder's hooks, in a settings file outside extensions/ (passed with --settings): installs ask the person,
    with a summary Idli writes."""
    path = Path(data_dir).resolve() / '.idli' / 'builder-settings.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    def hook(matcher, script):
        cmd = ' '.join(shlex.quote(x) for x in (sys.executable, '-I', str(Path(platform).resolve() / 'desktop' / script),
                                                 str(Path(data_dir).resolve())))
        return {'matcher': matcher, 'hooks': [{'type': 'command', 'timeout': 30, 'command': cmd}]}
    # installs, and test accounts (narrative/BUILDER_JOURNEY.md): the person says yes to words Idli writes
    settings = {'hooks': {'PreToolUse': [hook('mcp__idli__stack_install', 'idli-stack-consent.py'),
                                         hook('mcp__idli__test_account_set', 'idli-test-account-consent.py')]}}
    path.write_text(json.dumps(settings, indent=2))
    return path
