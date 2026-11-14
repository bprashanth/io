"""Synthetic-only regressions: .venv/bin/python -m pytest lib/test_ccproxy.py."""
import copy
from contextlib import contextmanager
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading

import pandas as pd
import pytest

from lib import ccproxy as cc, privacy as p
from lib.privacy_engine.pseudonymize import PseudonymMap, normalise

FIXTURE = Path(__file__).resolve().parents[3] / '2026-11-13-grounded-9b/fixtures/drive/households.xlsx'


@pytest.fixture
def book(tmp_path, monkeypatch):
    monkeypatch.setenv('IDLI_SCANNER', 'http://127.0.0.1:1/scan')
    shutil.copyfile(FIXTURE, tmp_path / 'households.xlsx')
    p.set(tmp_path, 'households.xlsx', mode='mask', columns={'household_head': True, 'ward': True})
    frame = next(iter(p.fk.raw_sheets(str(tmp_path / 'households.xlsx'))[0].values()))
    name = frame.household_head.iloc[0]
    ward = next(w for w in frame.ward if 'Yerawada' in w)
    return tmp_path, name, ward


def code(vault, text):
    return vault.forward[normalise(text)]


def request(text):
    return {'model': 'test-model', 'messages': [{'role': 'user', 'content': text}], 'max_tokens': 100}


@contextmanager
def running(handler):
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def call(port, body=None, path='/v1/messages', method='POST', headers=None):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
    try:
        connection.request(method, path, json.dumps(body).encode() if body is not None else None,
                           headers=headers or {'Content-Type': 'application/json'})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def test_transform_nested_and_signed(book):
    root, name, ward = book
    transform = cc.Transformer(root)
    name_code, ward_code = code(transform.vault, name), code(transform.vault, ward)
    signed = {'type': 'thinking', 'thinking': name + '\n' + ward, 'signature': 'unaltered-signature'}
    redacted = {'type': 'redacted_thinking', 'data': ward}
    body = {'model': 'model', 'metadata': {'user_id': ward},
            'tools': [{'name': 'lookup', 'description': ward, 'input_schema': {'type': 'object'}}],
            'system': [{'type': 'text', 'text': ward}],
            'messages': [{'role': 'assistant', 'content': [signed, redacted,
                          {'type': 'tool_use', 'id': 't1', 'name': 'Bash',
                           'input': {'command': 'cat /tmp/' + ward + '/' + name,
                                     'nested': [{'path': ward, 'count': 2}]}}]},
                         {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': 't1',
                                                       'content': [{'type': 'text', 'text': name}]},
                                                      {'type': 'text', 'text': ward}]}]}
    before = copy.deepcopy(body)
    out, stats = transform.outbound(body)
    assert body == before
    assert out['system'][0]['text'] == ward_code
    content = out['messages'][0]['content']
    assert content[:2] == [signed, redacted]
    assert content[2]['input']['command'] == 'cat /tmp/' + ward_code + '/' + name_code
    assert content[2]['input']['nested'] == [{'path': ward_code, 'count': 2}]
    assert out['messages'][1]['content'][0]['content'][0]['text'] == name_code
    assert out['tools'] == body['tools'] and out['metadata'] == body['metadata'] and out['model'] == 'model'
    assert stats['masked'] > 0
    assert transform.leaks(out)  # excluded fields still trigger the final fail-closed check
    restored = transform.restore({'content': [signed, redacted, {'type': 'text', 'text': name_code + '/' + ward_code}]})
    assert restored['content'] == [signed, redacted, {'type': 'text', 'text': name + '/' + ward}]
    assert transform.restore({name_code: ward_code}) == {name: ward}


def test_scanner_scope_reminders_and_cache(book, monkeypatch):
    root, name, ward = book
    seen = []

    class Scanner:
        status = 'ok'
        def __call__(self, text):
            seen.append(text)
            start = text.find('Novel Person')
            return [(start, start + 12, 'person_name', .99)] if start >= 0 else []

    monkeypatch.setattr(p, 'Scanner', Scanner)
    transform = cc.Transformer(root)
    text = f'Ask Novel Person about {name} in {ward}. <system-reminder>Reminder Person {ward}</system-reminder>'
    body = {'system': 'System Person', 'messages': [
        {'role': 'user', 'content': [{'type': 'text', 'text': 'Old Person'}]},
        {'role': 'assistant', 'content': [{'type': 'tool_use', 'input': {'arg': 'Tool Person'}}]},
        {'role': 'user', 'content': [{'type': 'text', 'text': text},
                                     {'type': 'tool_result', 'content': 'Result Person'}]}]}
    out, stats = transform.outbound(body)
    assert len(seen) == 1 and 'Novel Person' in seen[0]
    assert all(w not in seen[0] for w in [name, ward, 'Reminder Person', 'System Person', 'Old Person', 'Result Person'])
    assert 'Novel Person' not in out['messages'][-1]['content'][0]['text']
    assert 'Reminder Person' in out['messages'][-1]['content'][0]['text']
    assert ward not in out['messages'][-1]['content'][0]['text']
    assert stats['scanner'] == 'ok'
    again, stats = transform.outbound(body)
    assert again == out and len(seen) == 1 and 'cached' in stats['scanner']
    # A tool-only last user message must never cause an older typed question to be scanned.
    body['messages'].append({'role': 'user', 'content': [{'type': 'tool_result', 'content': 'Unseen Person'}]})
    transform.outbound(body)
    assert len(seen) == 1
    # Unclosed reminders are excluded too.
    transform.outbound(request('A question <system-reminder>Hidden Person'))
    assert 'Hidden Person' not in seen[-1]


def test_cache_invalidation_and_late_discoveries(book, monkeypatch):
    root, _, _ = book
    transform = cc.Transformer(root)
    body = {'system': 'Novel Person', 'messages': [{'role': 'user', 'content': 'Novel Person'}]}
    transform.outbound(body)  # scanner down, this string initially stays clear
    class Scanner:
        status = 'ok'
        def __call__(self, text):
            start = text.find('Novel Person')
            return [(start, start + 12, 'person_name', .99)] if start >= 0 else []
    monkeypatch.setattr(p, 'Scanner', Scanner)
    # A new typed string discovers a value also in cached system/history strings.
    body['messages'][0]['content'] = 'Hello Novel Person'
    out, _ = transform.outbound(body)
    assert 'Novel Person' not in json.dumps(out)
    assert not transform.leaks(out)
    pd.DataFrame({'Ward': ['Additional Ward']}).to_excel(root / 'second.xlsx', index=False)
    p.set(root, 'second.xlsx', mode='mask', columns={'Ward': True})
    before, _ = transform.outbound(request('Additional Ward'))
    assert 'Additional Ward' not in json.dumps(before)
    persisted = cc.Transformer(root)
    assert persisted.vault.forward == transform.vault.forward


def test_regex_on_system_tool_arguments_results_and_history(book, monkeypatch):
    root, _, _ = book
    class Scanner:
        status = 'ok'
        def __call__(self, text):
            pytest.fail('Tool-only last user message must not reach the scanner')
    monkeypatch.setattr(p, 'Scanner', Scanner)
    transform = cc.Transformer(root)
    body = {'system': 'Contact system@example.org', 'messages': [
        {'role': 'user', 'content': 'Contact old@example.org'},
        {'role': 'assistant', 'content': [{'type': 'tool_use', 'input': {'arg': 'tool@example.org'}}]},
        {'role': 'user', 'content': [{'type': 'tool_result', 'content': 'result@example.org'}]}]}
    out, stats = transform.outbound(body)
    assert '@example.org' not in json.dumps(out)
    assert stats['masked'] == 4 and stats['scanner'] == 'not used'
    assert transform.restore(out) == body


def test_numbers_and_whole_tokens(book):
    root, _, _ = book
    pd.DataFrame({'NUMBER': ['7', '42', '123', '9876', '12345.5']}).to_excel(root / 'numbers.xlsx', index=False)
    p.set(root, 'numbers.xlsx', mode='mask', columns={'NUMBER': True})
    transform = cc.Transformer(root)
    out, _ = transform.outbound(request('7 42 123 9876 12345.5 19876 x9876 9876x 4444 9876.1 .9876'))
    text = out['messages'][0]['content']
    assert text.startswith(' '.join(code(transform.vault, v) for v in ['7', '42', '123', '9876']))
    assert code(transform.vault, '12345.5') in text
    assert '19876 x9876 9876x 4444 9876.1 .9876' in text
    assert not transform.leaks(out)
    assert transform.leaks(request('7 42 123'))  # Unknown masked columns fail closed, including short identifiers.
    assert transform.leaks({'input': {'number': 9876}})
    assert transform.leaks({'input': {'number': 9876.0}})
    assert transform.restore(code(transform.full, '42')) == '42'


def test_shared_namespace_and_legacy_migration(book):
    root, name, _ = book
    first = p._seed(root, 'households.xlsx', root / 'households.xlsx')
    name_code = code(first, name)
    pd.DataFrame({'Name': ['Other Person'], 'Ward': ['Other Ward']}).to_excel(root / 'other.xlsx', index=False)
    p.set(root, 'other.xlsx', mode='mask', columns={'Name': True, 'Ward': True})
    vault = p.session_vault(root)
    assert code(vault, name) == name_code
    assert code(vault, 'Other Ward') != code(vault, book[2])
    assert p.unmask(root, 'other.xlsx', code(vault, 'Other Person')) == 'Other Person'
    # Preserve an unambiguous legacy code; reject collisions instead of guessing.
    legacy_root = root / 'legacy'
    (legacy_root / 'vault').mkdir(parents=True)
    old = PseudonymMap(legacy_root / 'vault/a.json')
    old.token('Old Ward', 'village')
    p._save(old)
    assert p.session_vault(legacy_root).display == old.display
    (legacy_root / 'vault/session.json').unlink()
    old = PseudonymMap(legacy_root / 'vault/b.json')
    old.token('Different Ward', 'village')
    p._save(old)
    with pytest.raises(ValueError, match='Conflicting legacy'):
        p.session_vault(legacy_root)


def test_concurrent_vault_writers(book):
    root, _, _ = book
    # The form server and proxy run in different processes and must reserve codes together.
    source = ('import sys; from lib import privacy as p; '
              'p.mask_text(sys.argv[1], "households.xlsx", '
              'sys.argv[1] + "/households.xlsx", sys.argv[2])')
    processes = [subprocess.Popen([sys.executable, '-c', source, str(root), email], cwd=cc.HERE,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                 for email in ['first@example.org', 'second@example.org']]
    for process in processes:
        _, error = process.communicate(timeout=10)
        assert process.returncode == 0, error.decode()
    vault = p.session_vault(root)
    assert code(vault, 'first@example.org') != code(vault, 'second@example.org')
    assert len(set(vault.forward.values())) == len(vault.forward)


def event(kind, **fields):
    return cc.SSE.event({'type': kind, **fields})


def parse_events(data):
    return [json.loads(line[6:]) for line in data.decode().splitlines() if line.startswith('data: ')]


@pytest.mark.parametrize('escaped', [False, True])
def test_sse_every_code_split_and_json_escaping(escaped):
    vault = PseudonymMap()
    real = 'A "quoted" name\\path\nमराठी'
    token = vault.token(real, 'person_name')
    field, kind = ('partial_json', 'input_json_delta') if escaped else ('text', 'text_delta')
    for cut in range(1, len(token) + 1):
        stream = cc.SSE(vault)
        raw = [event('content_block_delta', index=0, delta={'type': kind, field: token[:cut]}),
               event('content_block_delta', index=0, delta={'type': kind, field: token[cut:]}),
               event('content_block_stop', index=0)]
        restored = parse_events(b''.join(stream.stream(io.BytesIO(b''.join(raw)))))
        text = ''.join(o['delta'][field] for o in restored if o['type'] == 'content_block_delta')
        assert text == (json.dumps(real, ensure_ascii=False)[1:-1] if escaped else real)
        assert restored[-1]['type'] == 'content_block_stop'
        assert restored[-2]['delta'][field]  # held full code flushed before stop


def test_sse_interleaved_blocks_and_passthrough():
    vault = PseudonymMap()
    token = vault.token('Yerawada', 'village')
    stream = cc.SSE(vault)
    for i in (0, 1):
        stream.process(event('content_block_delta', index=i, delta={'type': 'text_delta', 'text': 'PLACE_0'}))
    for i in (1, 0):
        data = stream.process(event('content_block_delta', index=i, delta={'type': 'text_delta', 'text': '01!'}))
        assert parse_events(data)[0]['delta']['text'] == 'Yerawada!'
    for kind in ('thinking_delta', 'signature_delta'):
        raw = event('content_block_delta', index=0, delta={'type': kind, 'thinking': token})
        assert stream.process(raw) == raw
    for raw in (b': ping\r\n\r\n', event('message_start', message={'content': []}), b'data: [DONE]\n\n', b'data: null\n\n'):
        assert stream.process(raw) == raw
    # Do not restore a code embedded in an ordinary identifier, even across chunk boundaries.
    restore = cc.StreamRestorer(vault)
    assert restore.feed('x') + restore.feed(token) + restore.flush() == 'x' + token
    restore = cc.StreamRestorer(vault)
    assert restore.feed('\\n') + restore.feed(token) + restore.flush() == '\\nYerawada'
    restore = cc.StreamRestorer(vault)
    assert restore.feed('PLACE_0') + restore.flush() == 'PLACE_0'


def test_leak_decodes_json_values(book):
    root, _, ward = book
    transform = cc.Transformer(root)
    assert transform.leaks({'tools': [{'description': ward}]})
    real = 'A "quoted" Person'
    transform.vault.token(real, 'person_name')
    assert transform.leaks({'metadata': real})
    assert transform.leaks({ward: 'key'})


def test_fake_upstream_roundtrip_and_refusal(book):
    root, name, ward = book
    seen = []
    auth_ok = []
    proxy = None

    class Upstream(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            raw = self.rfile.read(int(self.headers['Content-Length']))
            body = json.loads(raw)
            seen.append(body)
            # Compare credentials in memory only. Never retain or log their values.
            auth_ok.append(self.headers.get('Authorization') == 'Bearer synthetic-local-fixture')
            assert name not in raw.decode() and ward not in raw.decode()
            assert self.headers.get('anthropic-version') == '2023-06-01'
            name_code = code(proxy.transformer.vault, name)
            ward_code = code(proxy.transformer.vault, ward)
            if 'count_tokens' in self.path:
                answer = json.dumps({'input_tokens': 42}).encode()
                mime = 'application/json'
            elif body.get('stream'):
                tool_json = json.dumps({'command': 'echo ' + name_code + ' ' + ward_code})
                answer = event('message_start', message={'content': []})
                for i, kind, field, text in [(0, 'text_delta', 'text', name_code + ' in ' + ward_code),
                                              (1, 'input_json_delta', 'partial_json', tool_json)]:
                    answer += event('content_block_start', index=i, content_block={'type': 'text', 'text': ''})
                    # Split at every character, including UTF-8 and JSON token boundaries.
                    for char in text:
                        answer += event('content_block_delta', index=i, delta={'type': kind, field: char})
                    answer += event('content_block_stop', index=i)
                answer += event('message_stop')
                mime = 'text/event-stream'
            else:
                answer = json.dumps({'type': 'message', 'content': [
                    {'type': 'thinking', 'thinking': ward_code, 'signature': 'unchanged'},
                    {'type': 'text', 'text': name_code + ' in ' + ward_code},
                    {'type': 'tool_use', 'input': {'path': '/tmp/' + ward_code, 'name': name_code}}]}).encode()
                mime = 'application/json'
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(answer)))
            self.end_headers()
            # Arbitrary network chunks, not aligned with SSE frames.
            for offset in range(0, len(answer), 17):
                self.wfile.write(answer[offset:offset + 17])
                self.wfile.flush()
        def do_GET(self):
            self.send_response(201)
            self.end_headers()
            self.wfile.write(b'passthrough')
        def do_HEAD(self):
            self.send_response(204)
            self.end_headers()

    with running(Upstream) as upstream:
        proxy = cc.Proxy(root, f'http://127.0.0.1:{upstream.server_port}', wire_log=True)
        with running(proxy.handler()) as server:
            headers = {'Authorization': 'Bearer synthetic-local-fixture', 'Content-Type': 'application/json',
                       'anthropic-version': '2023-06-01'}
            body = request(name + ' in ' + ward)
            status, _, data = call(server.server_port, body, path='/v1/messages?beta=true', headers=headers)
            assert status == 200
            result = json.loads(data)
            assert result['content'][1]['text'] == name + ' in ' + ward
            assert result['content'][2]['input'] == {'path': '/tmp/' + ward, 'name': name}
            assert result['content'][0]['thinking'] == code(proxy.transformer.vault, ward)
            status, _, data = call(server.server_port, {**body, 'stream': True}, headers=headers)
            assert status == 200
            events = parse_events(data)
            text = ''.join(o['delta']['text'] for o in events if o.get('delta', {}).get('type') == 'text_delta')
            args = ''.join(o['delta']['partial_json'] for o in events if o.get('delta', {}).get('type') == 'input_json_delta')
            assert text == name + ' in ' + ward
            assert json.loads(args) == {'command': 'echo ' + name + ' ' + ward}
            status, _, data = call(server.server_port, body, '/v1/messages/count_tokens', headers=headers)
            assert status == 200 and json.loads(data)['input_tokens'] == 42
            assert auth_ok == [True] * 3
            # Claude Code's own fields (tools, metadata) aren't checked: ordinary words in its tool text matched short
            # masked values and blocked every request; a real value left in the conversation is still refused
            assert not proxy.transformer.leaks({'messages': [], 'tools': [{'description': ward}], 'metadata': {'user_id': ward}})
            status, _, data = call(server.server_port, {**body, 'messages': [
                {'role': 'assistant', 'content': [{'type': 'thinking', 'thinking': ward}]}]})
            assert status == 403 and json.loads(data)['error']['type'] == 'permission_error'
            assert len(seen) == 3  # refused requests never reach upstream
            assert call(server.server_port, path='/api/hello', method='GET')[::2] == (201, b'passthrough')
            assert call(server.server_port, path='/api/hello', method='HEAD')[0] == 204
    logs = [json.loads(line) for line in (root / 'ccproxy.log').read_text().splitlines()]
    assert len(logs) == 6 and sum(e['refused'] for e in logs) == 1
    assert all(set(e) - {'leaks'} == {'time', 'path', 'status', 'masked', 'scanner', 'refused'} for e in logs)
    assert all(isinstance(c, str) and c.isupper() or c == '?' for e in logs for _, c in e.get('leaks', []))  # codes only, never values
    wires = list((root / 'ccproxy-wire').glob('*.json'))
    assert len(wires) == 3
    for path in [root / 'ccproxy.log', *wires]:
        text = path.read_text()
        assert name not in text and ward not in text and 'Authorization' not in text and 'synthetic-local-fixture' not in text
        assert path.stat().st_mode & 0o777 == 0o600


def test_bad_json_encoding_and_upstream_failure(book):
    root, _, _ = book
    proxy = cc.Proxy(root, 'http://127.0.0.1:1')
    with running(proxy.handler()) as server:
        status, _, data = call(server.server_port, request('hello'), headers={'Content-Encoding': 'gzip'})
        assert status == 415 and json.loads(data)['type'] == 'error'
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port)
        connection.request('POST', '/v1/messages', body=b'{broken')
        response = connection.getresponse()
        assert response.status == 400
        response.read()
        connection.close()
        assert call(server.server_port, request('hello'))[0] == 502


def test_ensure_detached_reuses_and_restarts(book):
    root, _, _ = book
    state = None
    try:
        port = cc.ensure(root)
        state = json.loads(cc.state_file(root).read_text())
        assert state['port'] == port and cc._alive(state)
        assert state['data_dir'] == str(root)
        assert cc.ensure(root) == port
        os.kill(state['pid'], signal.SIGTERM)
        # Identity validation rejects a stale state even if another service reuses its port.
        state['instance'] = 'stale-instance'
        assert not cc._alive(state)
        port = cc.ensure(root)
        state = json.loads(cc.state_file(root).read_text())
        assert port == state['port'] and cc._alive(state)
    finally:
        if state:
            try:
                os.kill(state['pid'], signal.SIGTERM)
            except ProcessLookupError:
                pass


def test_cli_fake_upstream(book):
    root, name, ward = book
    received = []
    class Upstream(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            received.append(body)
            data = json.dumps({'content': body['messages'][0]['content']}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
    with running(Upstream) as upstream:
        process = subprocess.Popen([sys.executable, '-I', str(cc.HERE / 'lib/ccproxy.py'), '--data-dir', str(root),
                                    '--port', '0', '--wire-log', '--upstream', f'http://127.0.0.1:{upstream.server_port}'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            import time
            for _ in range(60):
                if cc.state_file(root).exists():
                    break
                assert process.poll() is None
                time.sleep(.05)
            state = json.loads(cc.state_file(root).read_text())
            status, _, data = call(state['port'], request(name + ' in ' + ward))
            assert status == 200 and json.loads(data)['content'] == name + ' in ' + ward
            assert name not in json.dumps(received) and ward not in json.dumps(received)
        finally:
            process.terminate()
            process.wait(timeout=5)
