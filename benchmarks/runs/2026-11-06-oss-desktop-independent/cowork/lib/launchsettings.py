"""Merge the masked project's Claude settings without replacing other settings.

Claude works on masked copies in its own folder. Its shell runs in Claude Code's sandbox, which cannot read Idli's
private folder (the real files, the vault, privacy choices), Idli's caches or the browser's sign-ins. The Read, Edit
and search tools get the same limits as permission rules. Idli's own tools (MCP) run outside the sandbox.
"""
import json
from pathlib import Path
import os
import tempfile

ASK = ['mcp__idli__unmask']


def private_paths(data_dir, work):
    home = Path.home()
    work = Path(work).resolve()
    paths = [Path(data_dir).resolve(), home / '.cache/idli', home / '.paseo', home / '.config/Paseo',
             home / '.config/paseo', home / '.config/idlisseus']
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
