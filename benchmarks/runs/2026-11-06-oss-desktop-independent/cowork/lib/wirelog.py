"""What Idli's privacy proxy sent to Claude, kept on this computer so the person can check it.

One line per request in ~/idli-insights/wire/<day>.jsonl: the time, the app that sent it (Drivey, ...), whether it
went out or was refused, how many values were masked, and only what was new in that request (each request repeats
the whole conversation, so logging it all would store the same text again and again). The text is exactly what
left: codes stay codes. A refused request keeps only the codes that stopped it, never its text. Days older than
KEEP_DAYS are removed. The folder sits beside Claude's work folder, where Claude's sandbox cannot read.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import threading

KEEP_DAYS = 7
MAX_TEXT = 20000  # per request; a pasted file can be long
_lock = threading.Lock()
_seen = {}  # app -> hashes of system prompts and messages already logged by this proxy process


def folder():
    return Path(os.environ.get('IDLI_WIRE_DIR') or Path.home() / 'idli-insights' / 'wire')


def _text(node):
    """Readable text of one message: words, tool calls and tool results. Claude's signed reasoning came from Anthropic
    and is sent back unchanged, so it is left out."""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return '\n'.join(t for t in (_text(x) for x in node) if t)
    if isinstance(node, dict):
        kind = node.get('type')
        if kind in ('thinking', 'redacted_thinking'):
            return ''
        if kind in ('tool_use', 'server_tool_use'):
            return f"[{node.get('name', 'tool')}] " + json.dumps(node.get('input', {}), ensure_ascii=False)
        if kind == 'tool_result':
            return '[result] ' + _text(node.get('content', ''))
        if 'text' in node:
            return str(node['text'])
        if 'content' in node:
            return _text(node['content'])
    return ''


def _digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]


def record(app, body, status, masked=0, refused=False, codes=(), data_dir=None):
    """Append one request. `body` is the request as sent (already masked); for a refused one pass body=None."""
    app = re.sub(r'[^\w .-]', '', str(app or 'Claude'))[:40] or 'Claude'
    now = dt.datetime.now().astimezone()
    entry = {'time': now.isoformat(timespec='seconds'), 'app': app, 'status': status, 'masked': masked,
             'refused': bool(refused)}
    if data_dir:
        entry['data'] = str(data_dir)  # whose codes these are (for searching by a real name); stays on this computer
    if refused:
        entry['codes'] = sorted(set(codes))
    elif isinstance(body, dict):
        with _lock:
            seen = _seen.setdefault(app, set())
            parts = []
            system = body.get('system')
            if system:
                h = _digest(system)
                if h not in seen:
                    seen.add(h)
                    parts.append('[instructions] ' + _text(system))
            for message in body.get('messages', []):
                h = _digest(message)
                if h in seen:
                    continue
                seen.add(h)
                text = _text(message.get('content'))
                if text:
                    parts.append(('[you] ' if message.get('role') == 'user' else '[claude] ') + text)
            if len(seen) > 50000:
                seen.clear()
        entry['model'] = str(body.get('model', ''))[:60]
        text = '\n'.join(parts)
        entry['text'] = text[:MAX_TEXT] + ('\n[cut here: longer than this view keeps]' if len(text) > MAX_TEXT else '')
    try:
        d = folder()
        d.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = d / (now.date().isoformat() + '.jsonl')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        _prune(d, now.date())
    except OSError:
        pass  # the log must never stop a request


def _prune(d, today):
    for p in d.glob('*.jsonl'):
        try:
            if (today - dt.date.fromisoformat(p.stem)).days > KEEP_DAYS:
                p.unlink()
        except (ValueError, OSError):
            pass


def search(query='', app='', limit=200, vault_for=None):
    """Newest first. `query` matches the text as sent. If it is a private value Idli knows (`vault_for(data_dir)` gives
    that folder's codes), its code matches too, so searching a person's name shows where it went out as a code."""
    query = (query or '').strip()
    q = query.casefold()
    codes, cache = set(), {}

    def code_in(data_dir):
        if not query or vault_for is None or not data_dir:
            return None
        if data_dir not in cache:
            from lib.privacy_engine.pseudonymize import normalise
            try:
                cache[data_dir] = vault_for(data_dir).forward.get(normalise(query))
            except Exception:
                cache[data_dir] = None
        return cache[data_dir]
    out, apps = [], set()
    files = sorted(folder().glob('*.jsonl'), reverse=True) if folder().exists() else []
    for p in files:
        try:
            lines = p.read_text(encoding='utf-8').splitlines()
        except OSError:
            continue
        for line in reversed(lines):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            apps.add(e.get('app', 'Claude'))
            if app and e.get('app') != app:
                continue
            hay = (e.get('text', '') + ' ' + ' '.join(e.get('codes', []))).casefold()
            if query:
                c = code_in(e.get('data'))
                if q not in hay and not (c and c.casefold() in hay):
                    continue
                if c:
                    codes.add(c)
            if len(out) < limit:
                out.append({k: v for k, v in e.items() if k != 'data'})
    return {'entries': out, 'apps': sorted(apps), 'codes': sorted(codes)}
