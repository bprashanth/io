#!/usr/bin/env python3
"""Loopback Claude Code masking proxy. Run with python -I lib/ccproxy.py --data-dir DIR."""
import argparse
from collections import OrderedDict

import copy
import datetime as dt
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

# Direct execution under -I deliberately adds only this checkout's package root.
HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from lib import privacy  # noqa: E402
from lib.privacy_engine.pseudonymize import PseudonymMap, TOKEN_RE, normalise  # noqa: E402

CONTENT_PATHS = {'/v1/messages', '/v1/messages/count_tokens'}
SIGNED = {'thinking', 'redacted_thinking'}
REMINDER = re.compile(r'<system-reminder\b[^>]*>.*?(?:</system-reminder\s*>|$)', re.I | re.S)
HOP = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
       'te', 'trailer', 'transfer-encoding', 'upgrade'}


def walk(node, fn, keys=False):
    """Transform JSON string values, preserving signed blocks in their entirety."""
    if isinstance(node, str):
        return fn(node)
    if isinstance(node, list):
        return [walk(x, fn, keys) for x in node]
    if isinstance(node, dict):
        if node.get('type') in SIGNED:
            return copy.deepcopy(node)
        return {fn(k) if keys else k: walk(v, fn, keys) for k, v in node.items()}
    return node


def eligible(value):
    # Whole numeric cells from selected columns only; short counts are too ambiguous.
    return not re.fullmatch(r'[+-]?\d+(?:\.\d+)?', value) or len(re.sub(r'\D', '', value)) >= 4


CONTENT_FIELDS = ("system", "messages")


class Transformer:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir).resolve()
        self.cache = OrderedDict()
        self.signature = None
        self.full = None
        self.vault = PseudonymMap()
        self.revision = 0
        self.refresh()

    def refresh(self):
        settings = self.data_dir / 'privacy.json'
        raw = settings.read_bytes() if settings.exists() else b'{}'
        options = json.loads(raw)
        files = []
        for name, config in sorted(options.items()):
            if config.get('mode') == 'mask':
                key = privacy._key(self.data_dir, name)
                stat = (self.data_dir / key).stat()
                files.append((key, stat.st_mtime_ns, stat.st_size))
        vp = self.data_dir / 'vault' / 'session.json'
        signature = (raw, tuple(files), vp.stat().st_mtime_ns if vp.exists() else None)
        if signature == self.signature:
            return
        self.full = privacy.session_vault(self.data_dir)
        self.vault = privacy.active_vault(self.data_dir, self.full)
        self.vault.display = {c: v for c, v in self.vault.display.items() if eligible(v)}
        self.vault.forward = {normalise(v): c for c, v in self.vault.display.items()}
        self.vault.refresh()
        self.cache.clear()
        self.revision += 1
        self.signature = (raw, tuple(files), vp.stat().st_mtime_ns)

    def string(self, text, scan, scanner, stats):
        digest = hashlib.sha256(text.encode()).digest()
        key = (self.revision, scan, digest)
        if key in self.cache:
            out, n, status = self.cache[key]
            self.cache.move_to_end(key)
            stats['masked'] += n
            if scan and stats['scanner'] == 'not used':
                stats['scanner'] = 'cached (' + status + ')'
            return out

        def detect(remaining):
            if not scan:
                return []
            remaining = REMINDER.sub(lambda m: ' ' * len(m.group()), remaining)
            if not remaining.strip():
                return []
            spans = scanner(remaining)
            stats['scanner'] = scanner.status
            return [(a, b, label, score) for a, b, label, score in spans
                    if not re.fullmatch(r'[+-]?\d+(?:\.\d+)?', remaining[a:b])]

        before = len(self.vault.display)
        out, found = privacy._redact(text, self.vault, detect)
        if len(self.vault.display) != before:
            self.revision += 1
            self.cache.clear()  # old history may now contain a newly discovered private value
        stats['masked'] += len(found)
        self.cache[(self.revision, scan, digest)] = (out, len(found), scanner.status)
        if len(self.cache) > 4000:
            self.cache.popitem(last=False)
        return out

    def outbound(self, body):
        self.refresh()
        stats = {'masked': 0, 'scanner': 'not used'}
        scanner = privacy.Scanner()
        out = copy.deepcopy(body)
        clean = lambda text: self.string(text, False, scanner, stats)
        if 'system' in out:
            out['system'] = walk(out['system'], clean)
        messages = out.get('messages', [])
        last_user = max((i for i, m in enumerate(messages) if m.get('role') == 'user'), default=-1)
        for i, message in enumerate(messages):
            if 'content' not in message:
                continue
            content = message['content']
            typed = lambda text: self.string(text, True, scanner, stats)
            if i == last_user and isinstance(content, str):
                message['content'] = typed(content)
            elif i == last_user and isinstance(content, list):
                message['content'] = [
                    {k: typed(v) if k == 'text' else walk(v, clean) for k, v in block.items()}
                    if isinstance(block, dict) and block.get('type') == 'text' and isinstance(block.get('text'), str)
                    else walk(block, clean) for block in content]
            else:
                message['content'] = walk(content, clean)
        # A later string may have introduced a value that occurred earlier in the body.
        if 'system' in out:
            out['system'] = walk(out['system'], clean)
        for message in messages:
            if 'content' in message:
                message['content'] = walk(message['content'], clean)
        self.full.forward.update(self.vault.forward)
        self.full.display.update(self.vault.display)
        self.full.counters.update(self.vault.counters)
        if self.full.display != PseudonymMap(self.full.path).display:
            privacy._save(self.full)
            self.signature = (*self.signature[:2], self.full.path.stat().st_mtime_ns)
        return out, stats

    def leaks(self, body):
        # Inspect decoded JSON values AND keys: quotes/backslashes must not hide leaks.
        def strings(node):
            if isinstance(node, str):
                yield node
            elif isinstance(node, (int, float)) and not isinstance(node, bool):
                yield str(int(node)) if isinstance(node, float) and node.is_integer() else str(node)
            elif isinstance(node, list):
                for v in node:
                    yield from strings(v)
            elif isinstance(node, dict):
                for k, v in node.items():
                    yield k
                    yield from strings(v)
        # Only what can carry the person's data: the system prompt and the conversation. Claude Code's own tool
        # definitions and settings fields (tools, safeguards, metadata...) are its fixed text, and ordinary words in
        # them ("pip", "mine") matched short values of masked columns and blocked every request (2026-11-14).
        if isinstance(body, dict) and any(k in body for k in CONTENT_FIELDS):  # a whole request
            body = {k: body[k] for k in CONTENT_FIELDS if k in body}
        return any(privacy.known_leaks(text, self.vault) for text in strings(body))

    def where(self, body):
        """For the log when a request is refused: which codes leaked and under which top-level field (never the
        values themselves), e.g. [["tools", "PLACE_004"]]."""
        out = []
        for field, node in ((k, body[k]) for k in CONTENT_FIELDS if isinstance(body, dict) and k in body):
            text = json.dumps(node, ensure_ascii=False)
            for v in privacy.known_leaks(text, self.vault):
                code = self.vault.forward.get(privacy.normalise(v)) if hasattr(self.vault, 'forward') else None
                out.append([field, code or '?'])
        return out[:20]

    def restore(self, body):
        return walk(body, self.full.rehydrate, keys=True)


class StreamRestorer:
    """Hold a possible code tail, including a complete code that could gain digits."""
    tail = re.compile(r'[A-Z][A-Z_]{0,24}(?:\\_)?\d*$')

    def __init__(self, vault, escaped=False):
        self.vault, self.escaped = vault, escaped
        self.held = ''
        self.previous = ''

    def restore(self, text):
        def sub(m):
            real = self.vault.display.get(m.group().replace('\\_', '_'))
            if real is None:
                return m.group()
            return json.dumps(real, ensure_ascii=False)[1:-1] if self.escaped else real
        return TOKEN_RE.sub(sub, text)

    def feed(self, chunk):
        text = self.held + chunk
        match = self.tail.search(text)
        cut = len(text)
        if match:
            pos = match.start()
            preceding = text[:pos] if pos else self.previous
            boundary = not preceding or not re.match(r'\w', preceding[-1]) or preceding.endswith(('\\n', '\\t', '\\r'))
            tail = match.group().replace('\\_', '_')
            if boundary and any(code.startswith(tail) for code in self.vault.display):
                cut = pos
        out, self.held = text[:cut], text[cut:]
        # Keep the original boundary when a new chunk starts inside an ordinary word.
        prefix = self.previous[-2:] if self.previous else ''
        result = self.restore(prefix + out)[len(prefix):] if prefix else self.restore(out)
        if out:
            self.previous = (self.previous + out)[-2:]
        return result

    def flush(self):
        out, self.held = self.held, ''
        return self.restore(out)


class SSE:
    def __init__(self, vault):
        self.vault = vault
        self.blocks = {}

    @staticmethod
    def event(obj):
        return ('event: ' + obj['type'] + '\ndata: ' + json.dumps(obj, ensure_ascii=False) + '\n\n').encode()

    def process(self, raw):
        lines = raw.decode('utf-8').splitlines()
        data = '\n'.join(line[5:].lstrip(' ') for line in lines if line.startswith('data:'))
        try:
            obj = json.loads(data)
        except (ValueError, TypeError):
            return raw
        if not isinstance(obj, dict):
            return raw
        kind = obj.get('type')
        index = obj.get('index')
        if kind == 'content_block_delta':
            delta = obj.get('delta', {})
            if not isinstance(delta, dict):
                return raw
            field = {'text_delta': 'text', 'input_json_delta': 'partial_json'}.get(delta.get('type'))
            if field and isinstance(delta.get(field), str):
                key = (index, delta['type'])
                restorer = self.blocks.setdefault(key, StreamRestorer(self.vault, field == 'partial_json'))
                delta[field] = restorer.feed(delta[field])
                return self.event(obj)
        if kind == 'content_block_stop':
            flushed = b''
            for key in list(self.blocks):
                if key[0] == index:
                    text = self.blocks.pop(key).flush()
                    if text:
                        field = 'partial_json' if key[1] == 'input_json_delta' else 'text'
                        flushed += self.event({'type': 'content_block_delta', 'index': index,
                                               'delta': {'type': key[1], field: text}})
            return flushed + raw
        return raw

    def stream(self, response):
        lines = []
        for line in response:
            lines.append(line)
            if line in (b'\n', b'\r\n'):
                yield self.process(b''.join(lines))
                lines = []
        if lines:
            yield self.process(b''.join(lines))


def state_file(data_dir):
    return Path(data_dir) / '.idli' / 'ccproxy.json'


class Proxy:
    def __init__(self, data_dir, upstream='https://api.anthropic.com', wire_log=False):
        self.data_dir = Path(data_dir).resolve()
        self.upstream = urlsplit(upstream)
        if self.upstream.scheme not in ('http', 'https') or not self.upstream.hostname or self.upstream.username or self.upstream.query or self.upstream.fragment:
            raise ValueError('Upstream must be an HTTP(S) base URL without credentials')
        self.transformer = Transformer(self.data_dir)
        self.wire_log = wire_log
        self.lock = threading.RLock()
        self.log_lock = threading.Lock()
        self.instance = secrets.token_hex(16)

    def handler(self):
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *args):
                pass

            def handle_one_request(self):
                # BaseHTTPRequestHandler otherwise prints exceptions containing request data.
                try:
                    super().handle_one_request()
                except (OSError, ValueError, http.client.HTTPException):
                    self.close_connection = True

            def go(self):
                proxy.handle(self)

            do_POST = do_GET = do_HEAD = do_OPTIONS = do_PUT = do_PATCH = do_DELETE = go

        return Handler

    def log(self, entry):
        with self.log_lock:
            path = self.data_dir / 'ccproxy.log'
            fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            with os.fdopen(fd, 'a') as f:
                f.write(json.dumps(entry) + '\n')

    @staticmethod
    def error(h, status, message):
        data = json.dumps({'type': 'error', 'error': {
            'type': 'permission_error' if status == 403 else 'invalid_request_error' if status < 500 else 'api_error',
            'message': message}}).encode()
        h.send_response(status)
        h.send_header('Content-Type', 'application/json')
        h.send_header('Content-Length', str(len(data)))
        h.send_header('Connection', 'close')
        h.end_headers()
        h.close_connection = True
        if h.command != 'HEAD':
            h.wfile.write(data)

    def handle(self, h):
        path = urlsplit(h.path).path
        entry = {'time': dt.datetime.now(dt.timezone.utc).isoformat(), 'path': path,
                 'status': 502, 'masked': 0, 'scanner': 'not used', 'refused': False}
        connection = None
        started = False
        try:
            if path == '/_ccproxy/health' and h.command == 'GET':
                data = json.dumps({'instance': self.instance}).encode()
                h.send_response(200)
                h.send_header('Content-Length', str(len(data)))
                h.end_headers()
                h.wfile.write(data)
                entry['status'] = 200
                return
            protected = h.command == 'POST' and path.rstrip('/') in CONTENT_PATHS
            if h.headers.get('Transfer-Encoding'):
                entry.update(status=400, refused=True)
                return self.error(h, 400, 'Transfer-Encoding is unsupported')
            if protected and h.headers.get('Content-Encoding', 'identity') != 'identity':
                entry.update(status=415, refused=True)
                return self.error(h, 415, 'Encoded request bodies are unsupported')
            try:
                length = int(h.headers.get('Content-Length', '0'))
                if length < 0:
                    raise ValueError('Invalid length')
            except ValueError:
                entry.update(status=400, refused=True)
                return self.error(h, 400, 'Invalid Content-Length')
            body = h.rfile.read(length) if length else None
            if protected:
                try:
                    obj = json.loads(body or b'')
                    if not isinstance(obj, dict):
                        raise ValueError('Expected an object')
                    with self.lock, privacy.session_lock(self.data_dir):
                        obj, stats = self.transformer.outbound(obj)
                        entry.update(stats)
                        if self.transformer.leaks(obj):
                            entry.update(status=403, refused=True, leaks=self.transformer.where(obj))
                            return self.error(h, 403, 'Refused: private values remain in the outgoing body')
                        body = json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode()
                        # Each response retains the vault for its own request, including during concurrent requests.
                        vault = copy.deepcopy(self.transformer.full)
                    if self.wire_log:
                        folder = self.data_dir / 'ccproxy-wire'
                        folder.mkdir(mode=0o700, exist_ok=True)
                        with open(folder / (secrets.token_hex(12) + '.json'), 'xb') as f:
                            os.chmod(f.name, 0o600)
                            f.write(body)
                except (ValueError, KeyError, TypeError, AttributeError, OSError):
                    entry.update(status=400, refused=True)
                    return self.error(h, 400, 'Could not prepare the masked request')
            blocked = HOP | {'host', 'content-length', 'accept-encoding'}
            blocked |= {v.strip().lower() for v in h.headers.get('Connection', '').split(',')}
            headers = {k: v for k, v in h.headers.items() if k.lower() not in blocked}
            headers['Accept-Encoding'] = 'identity'
            cls = http.client.HTTPSConnection if self.upstream.scheme == 'https' else http.client.HTTPConnection
            connection = cls(self.upstream.hostname, self.upstream.port, timeout=300)
            route = self.upstream.path.rstrip('/') + h.path
            connection.request(h.command, route, body=body, headers=headers)
            response = connection.getresponse()
            entry['status'] = response.status
            content_type = response.getheader('Content-Type', '')
            if protected and response.getheader('Content-Encoding', 'identity') != 'identity':
                entry['status'] = 502
                return self.error(h, 502, 'Encoded upstream responses are unsupported')
            # Read/restore JSON before sending response headers so malformed JSON is a clean 502.
            payload = None
            if protected and 'application/json' in content_type:
                payload = json.dumps(walk(json.loads(response.read()), vault.rehydrate, keys=True), ensure_ascii=False).encode()
            h.send_response(response.status)
            blocked = HOP | {'content-length'}
            blocked |= {v.strip().lower() for v in response.getheader('Connection', '').split(',')}
            for k, v in response.getheaders():
                if k.lower() not in blocked:
                    h.send_header(k, v)
            h.send_header('Connection', 'close')
            h.end_headers()
            h.close_connection = True
            started = True
            if h.command == 'HEAD' or response.status in (204, 304):
                return
            if payload is not None:
                chunks = [payload]
            elif protected and 'text/event-stream' in content_type:
                chunks = SSE(vault).stream(response)
            else:
                chunks = iter(lambda: response.read1(65536), b'')
            for chunk in chunks:
                h.wfile.write(chunk)
                h.wfile.flush()
        except (OSError, ValueError, TypeError, http.client.HTTPException):
            entry['status'] = 502
            if not started:
                self.error(h, 502, 'Proxy could not complete the upstream request')
        finally:
            if connection:
                connection.close()
            self.log(entry)


def _alive(state):
    try:
        with urlopen(f"http://127.0.0.1:{int(state['port'])}/_ccproxy/health", timeout=2) as r:
            return json.load(r).get('instance') == state['instance']
    except (OSError, ValueError, KeyError, TypeError):
        return False


def ensure(data_dir):
    """Return the port of this directory's detached proxy, starting one if needed."""
    import fcntl
    data_dir = Path(data_dir).resolve()
    sf = state_file(data_dir)
    sf.parent.mkdir(parents=True, exist_ok=True)
    with open(sf.parent / 'ccproxy-start.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            state = json.loads(sf.read_text())
            if state.get('data_dir') == str(data_dir) and _alive(state):
                return state['port']
        except (OSError, ValueError, KeyError, TypeError):
            pass
        process = subprocess.Popen([sys.executable, '-I', str(Path(__file__).resolve()),
                                    '--data-dir', str(data_dir), '--port', '0'],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
        for _ in range(80):
            if process.poll() is not None:
                break
            time.sleep(.1)
            try:
                state = json.loads(sf.read_text())
                if state.get('pid') == process.pid and _alive(state):
                    return state['port']
            except (OSError, ValueError, KeyError, TypeError):
                pass
        process.terminate()
        process.wait(timeout=5)
        raise RuntimeError('The Claude Code proxy did not start')


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'ensure':  # ccproxy.py ensure --data-dir DIR: start if needed, print port
        ep = argparse.ArgumentParser()
        ep.add_argument('--data-dir', required=True)
        print(ensure(ep.parse_args(sys.argv[2:]).data_dir))
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--port', type=int, default=8870)
    parser.add_argument('--upstream', default='https://api.anthropic.com')
    parser.add_argument('--wire-log', action='store_true')
    args = parser.parse_args()
    # Reuse Scanner's configurable endpoint; proxy default is the hosted scanner.
    os.environ.setdefault('IDLI_SCANNER', 'https://privacy.idli.cc/scan')
    proxy = Proxy(args.data_dir, args.upstream, args.wire_log)
    with ThreadingHTTPServer(('127.0.0.1', args.port), proxy.handler()) as server:
        sf = state_file(proxy.data_dir)
        privacy._write(sf, {'port': server.server_port, 'pid': os.getpid(),
                            'data_dir': str(proxy.data_dir), 'instance': proxy.instance})
        try:
            server.serve_forever()
        finally:
            try:
                if json.loads(sf.read_text()).get('instance') == proxy.instance:
                    sf.unlink()
            except (OSError, ValueError):
                pass


if __name__ == '__main__':
    main()
