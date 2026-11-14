"""Merge the masked project's Claude permissions without replacing other settings."""
import json
from pathlib import Path
import os
import tempfile

ASK = ['mcp__idli__unmask', 'mcp__idli__lookup']


def merge(work):
    path = Path(work) / '.claude/settings.json'
    settings = json.loads(path.read_text()) if path.exists() else {}
    permissions = settings.setdefault('permissions', {})
    permissions['ask'] = list(dict.fromkeys(permissions.get('ask', []) + ASK))
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(settings, out, indent=2)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
