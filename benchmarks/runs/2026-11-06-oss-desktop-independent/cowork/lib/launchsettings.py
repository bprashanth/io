"""Merge the masked project's Claude settings without replacing other settings.

Claude works on masked copies in its own folder. Its shell runs in Claude Code's sandbox, which cannot read Idli's
private folder (the real files, the vault, privacy choices), Idli's caches or the browser's sign-ins. The Read, Edit
and search tools get the same limits as permission rules. Idli's own tools (MCP) run outside the sandbox.
"""
import json
from pathlib import Path
import os
import tempfile

ASK = ['mcp__idli__unmask', 'mcp__idli__lookup']


def private_paths(data_dir, work):
    home = Path.home()
    work = Path(work).resolve()
    paths = [Path(data_dir).resolve(), home / '.cache/idli', home / '.paseo', home / '.config/Paseo',
             home / '.config/paseo', home / '.config/idlisseus']
    # Everything else Idli keeps beside Claude's folder (other workspaces, downloads, settings).
    parent = work.parent
    if parent != home and parent.name == 'idli-insights':
        paths += [p for p in parent.iterdir() if p.resolve() != work] if parent.exists() else []
    return sorted({str(p.resolve()) for p in paths if p.resolve() != work and not work.is_relative_to(p.resolve())})


def merge(work, data_dir=None):
    path = Path(work) / '.claude/settings.json'
    settings = json.loads(path.read_text()) if path.exists() else {}
    permissions = settings.setdefault('permissions', {})
    permissions['ask'] = list(dict.fromkeys(permissions.get('ask', []) + ASK))
    if data_dir:
        private = private_paths(data_dir, work)
        rules = [f'{tool}(/{p}/**)' for p in private for tool in ('Read', 'Edit')]
        permissions['deny'] = list(dict.fromkeys(permissions.get('deny', []) + rules))
        sandbox = settings.setdefault('sandbox', {})
        sandbox.update({'enabled': True, 'autoAllowBashIfSandboxed': True, 'allowUnsandboxedCommands': False})
        fs = sandbox.setdefault('filesystem', {})
        # Claude Code's own transcripts hold the person's real values (Claude's replies with codes put back). Claude
        # Code reads them itself; its shell must not.
        transcripts = str((Path.home() / '.claude/projects').resolve())
        fs['denyRead'] = sorted(set(fs.get('denyRead', [])) | set(private) | {transcripts})
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(settings, out, indent=2)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
