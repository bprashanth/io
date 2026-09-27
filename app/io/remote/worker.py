"""One container/workspace (ephemeral or explicitly persistent). No shell-execution API; PTY runs pinned Codex only."""
import base64
import datetime
import errno
import fcntl
import hmac
import re
import http.server
import json
import os
import pathlib
import pty
import signal
import shutil
import socket
import stat
import struct
import subprocess
import termios
import threading
import time
import urllib.parse
import uuid

LIMIT = 10 * 1024 * 1024
CODEX = '/opt/codex/bin/codex'
ROOT = '/workspace'
INSTANCE = os.urandom(16).hex()
TOKEN = os.environ.pop('IO_REMOTE_TOKEN', '')
if len(TOKEN) < 40:
    raise RuntimeError('A fresh session capability is required')
os.umask(0o077)
ENV = dict(PATH='/opt/codex/bin:/usr/local/bin:/usr/bin:/bin', HOME='/state',
           CODEX_HOME='/state/codex', LANG='C.UTF-8', TERM='xterm-256color', COLORTERM='truecolor')
subprocess.run(['node', '/opt/remote/config.js'], env=ENV, check=True)
from oauth_callback import deliver
from conformance import check
CONFORMANCE = check()
VERSION = subprocess.check_output([CODEX, '--version'], env=ENV, text=True).strip()
if VERSION != 'codex-cli ' + json.loads(pathlib.Path('/opt/io/codex-pins.json').read_text())['version']:
    raise RuntimeError('Bundled Codex version does not match io pin')
condition = threading.Condition(threading.RLock())
events = []
event_bytes = 0
sequence = 0
process = None
master = None
mode = None
ended = False
browser_auth = None
browser_consumed = False
active_conversation_id = None
PERSISTENT = os.environ.get('IO_REMOTE_PERSISTENT') == '1'
SESSION_ROOT = pathlib.Path('/state/codex/sessions')
# Serialize lifecycle operations, so concurrent requests cannot create two Codex processes.
operation = threading.RLock()
actions = threading.RLock()


def _uuid_text(value):
    if not isinstance(value, str):
        return None
    try:
        return str(uuid.UUID(value))
    except (TypeError, ValueError, AttributeError):
        return None


def _clean_text(value, fallback):
    if not isinstance(value, str):
        return fallback
    text = re.sub(r'[\x00-\x1f\x7f]+', ' ', value)
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return fallback
    return text[:120]


def _timestamp_text(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        dt = datetime.datetime.fromtimestamp(value, datetime.timezone.utc)
        return dt.strftime('%Y-%m-%d %H:%M UTC')
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if re.fullmatch(r'\d+(?:\.\d+)?', text):
            return _timestamp_text(float(text))
        try:
            dt = datetime.datetime.fromisoformat(text.replace('Z', '+00:00'))
        except ValueError:
            return _clean_text(text, None)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    return None


def _conversation_date(meta, fallback_mtime=None):
    for key in ('created_at', 'createdAt', 'created', 'started_at', 'startedAt', 'timestamp', 'time', 'updated_at', 'updatedAt'):
        text = _timestamp_text(meta.get(key))
        if text:
            return text
    if fallback_mtime is not None:
        return datetime.datetime.fromtimestamp(fallback_mtime, datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    return 'Unknown date'


def _session_root(root=None):
    return pathlib.Path('/state/codex/sessions') if root is None else pathlib.Path(root)


def _resolve_session_relative(root, relative):
    root = _session_root(root)
    parts = pathlib.PurePosixPath(str(relative)).parts
    if not parts or any(p in ('', '.', '..') or '\\' in p or '\x00' in p for p in parts):
        raise ValueError('Invalid conversation path')
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        result = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    finally:
        os.close(fd)
    st = os.fstat(result)
    if not stat.S_ISREG(st.st_mode):
        os.close(result)
        raise ValueError('Only regular conversation files can be used')
    return result


def _iter_session_relpaths(root=None, limit=500):
    root = _session_root(root)
    seen = 0
    visited = 0
    for current, dirs, files in os.walk(root, followlinks=False):
        visited += 1
        if visited > 2000:
            return
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and not os.path.islink(os.path.join(current, d)))
        for name in sorted(files):
            if seen >= limit:
                return
            if name.startswith('.') or not name.endswith('.jsonl'):
                continue
            path = pathlib.Path(current) / name
            if path.is_symlink():
                continue
            relative = os.path.relpath(path, root)
            if relative.startswith('..'):
                continue
            seen += 1
            yield relative


def _read_session_meta(root, relative, limit=256 * 1024):
    fd = _resolve_session_relative(root, relative)
    with os.fdopen(fd, 'rb') as f:
        stat_result = os.fstat(f.fileno())
        raw = f.readline(limit + 1)
    if not raw or len(raw) > limit:
        return None
    try:
        meta = json.loads(raw.decode('utf-8'))
    except Exception:
        return None
    if not isinstance(meta, dict) or meta.get('type') != 'session_meta':
        return None
    payload = meta.get('payload', meta)
    if not isinstance(payload, dict):
        return None
    return payload, stat_result


def conversation_records(root=None, limit=500):
    root = _session_root(root)
    records = []
    for relative in _iter_session_relpaths(root, limit=limit):
        try:
            result = _read_session_meta(root, relative)
        except (OSError, ValueError, OverflowError):
            continue
        if not result:
            continue
        meta, stat_result = result
        conversation_id = None
        for key in ('id', 'conversationId', 'conversation_id', 'session_id', 'thread_id'):
            conversation_id = _uuid_text(meta.get(key))
            if conversation_id:
                break
        if not conversation_id:
            conversation_id = _uuid_text(pathlib.PurePosixPath(relative).stem)
        if not conversation_id:
            continue
        records.append(dict(
            id=conversation_id,
            title=_clean_text(
                meta.get('title')
                or meta.get('subject')
                or meta.get('summary')
                or meta.get('conversationName')
                or meta.get('name'),
                'Untitled conversation',
            ),
            date=_conversation_date(meta, stat_result.st_mtime),
            _path=relative,
            _mtime=stat_result.st_mtime,
        ))
    records.sort(key=lambda r: (r['_mtime'], r['id']), reverse=True)
    return records


def list_conversations(root=None, limit=500):
    return [dict(id=r['id'], title=r['title'], date=r['date']) for r in conversation_records(root, limit=limit)]


def find_conversation_path(root, conversation_id, limit=500):
    conversation_id = _uuid_text(conversation_id)
    if not conversation_id:
        raise ValueError('Invalid conversationId')
    match = None
    for record in conversation_records(root, limit=limit):
        if record['id'] != conversation_id:
            continue
        if match is not None:
            raise ValueError('Conversation id is ambiguous')
        match = record['_path']
    return match


def delete_conversation(root, conversation_id, limit=500):
    relative = find_conversation_path(root, conversation_id, limit=limit)
    if relative is None:
        raise ValueError('Conversation not found')
    root = _session_root(root)
    parts = pathlib.PurePosixPath(str(relative)).parts
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        os.unlink(parts[-1], dir_fd=fd)
    finally:
        os.close(fd)


def status_snapshot(*, logged_in, running, mode, ended, sandbox, persistent, instance, version, active_conversation_id=None, root=None):
    conversations = list_conversations(root)
    active = active_conversation_id if running else None
    if active is None and running and conversations:
        active = None  # Do not attribute a new process to a previous conversation.
    return dict(instance=instance, loggedIn=logged_in, running=running,
                hasConversation=bool(conversations), mode=mode, version=version,
                policy='offline', ended=ended, sandbox=sandbox, persistent=persistent,
                conversationId=active)


def emit(kind, data='', **extra):
    global sequence, event_bytes
    with condition:
        sequence += 1
        entry = dict(kind=kind, data=data, **extra)
        size = len(json.dumps(entry))
        events.append((sequence, entry, size))
        event_bytes += size
        while events and event_bytes > 2 * 1024 * 1024:
            event_bytes -= events.pop(0)[2]
        condition.notify_all()


def status():
    result = subprocess.run([CODEX, 'login', 'status'], env=ENV, capture_output=True,
                            text=True, timeout=15)
    # No auth file contents ever leave the worker.
    logged = result.returncode == 0 and 'chatgpt' in (result.stdout + result.stderr).lower()
    return status_snapshot(logged_in=logged,
                           running=process is not None and process.poll() is None,
                           mode=mode,
                           ended=ended,
                           sandbox=CONFORMANCE['ok'],
                           persistent=PERSISTENT,
                           instance=INSTANCE,
                           version=VERSION,
                           active_conversation_id=active_conversation_id,
                           root=SESSION_ROOT)


def dimensions(body):
    cols, rows = int(body.get('cols', 100)), int(body.get('rows', 30))
    if not 20 <= cols <= 500 or not 5 <= rows <= 300:
        raise ValueError('Invalid terminal size')
    return struct.pack('HHHH', rows, cols, 0, 0)


def browser_output(text):
    global browser_auth
    # Collect only the authorization URL; never replay OAuth parameters into terminal logs.
    match = re.search(r'https://auth\.openai\.com/oauth/authorize\?[^\s]+(?=\s)', text)
    if match:
        candidate = match.group(0)
        parsed = urllib.parse.urlsplit(candidate)
        query = urllib.parse.parse_qs(parsed.query)
        if (query.get('redirect_uri') == ['http://localhost:1455/auth/callback'] and
                query.get('response_type') == ['code'] and query.get('code_challenge_method') == ['S256'] and
                len(query.get('state', [''])[0]) >= 16):
            with condition:
                browser_auth = candidate
                condition.notify_all()


def start(args, kind, body, conversation_id=None):
    global process, master, mode, active_conversation_id
    with operation:
        if ended:
            raise ValueError('Session has ended')
        if process is not None:
            raise ValueError('A process is already running; stop it first')
        size = dimensions(body)
        fd, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, size)
        try:
            child = subprocess.Popen(['python3', '-c',
                'import fcntl,termios,os,sys; fcntl.ioctl(0,termios.TIOCSCTTY,0); os.execve(sys.argv[1],sys.argv[1:],os.environ)',
                CODEX] + args, stdin=slave, stdout=slave, stderr=slave,
                                     cwd=ROOT, env=ENV, start_new_session=True)
        except Exception:
            os.close(fd)
            raise
        finally:
            os.close(slave)
        process, master, mode = child, fd, kind
        active_conversation_id = conversation_id
        def pump():
            global process, master, mode, active_conversation_id
            import codecs
            decoder = codecs.getincrementaldecoder('utf8')('replace')
            login_buffer = ''
            browser = kind == 'login' and '--device-auth' not in args
            try:
                while True:
                    data = os.read(fd, 8192)
                    if not data:
                        break
                    text = decoder.decode(data)
                    if browser:
                        login_buffer = (login_buffer + text)[-32768:]
                        browser_output(login_buffer)
                    else:
                        emit(kind, text)
            except OSError as e:
                if e.errno != errno.EIO:
                    emit('state', 'Terminal stream ended unexpectedly')
            finally:
                tail = decoder.decode(b'', final=True)
                if tail and not browser:
                    emit(kind, tail)
                code = child.wait()
                with operation:
                    os.close(fd)
                    if process is child:
                        process = master = mode = None
                        active_conversation_id = None
                emit('exit', kind, code=code)
        threading.Thread(target=pump, daemon=True).start()


def stop():
    # Do not hold operation while joining the pump, which also acquires it.
    with operation:
        child = process
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
    if child:
        child.wait(timeout=10)
        for _ in range(100):
            if process is None:
                break
            time.sleep(.02)


def open_file(name):
    # openat + O_NOFOLLOW on *every* component, avoiding symlink replacement races.
    parts = name.split('/')
    if not parts or any(p in ('', '.', '..') or '\\' in p or '\x00' in p for p in parts):
        raise ValueError('Invalid result path')
    fd = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for p in parts[:-1]:
            nxt = os.open(p, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        result = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    finally:
        os.close(fd)
    s = os.fstat(result)
    if not stat.S_ISREG(s.st_mode) or s.st_size > LIMIT:
        os.close(result)
        raise ValueError('Only regular files up to 10 MiB can be downloaded')
    return result


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *args):
        pass  # Never log capabilities, device codes, user text, or filenames.

    def reply(self, code, data, raw=False):
        payload = data if raw else json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/octet-stream' if raw else 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(payload)

    def authorized(self):
        # Not a browser API: no CORS, cookies, or origins, even with a valid capability.
        if self.headers.get('Origin') or not hmac.compare_digest(
                self.headers.get('Authorization', ''), 'Bearer ' + TOKEN):
            self.close_connection = True
            self.reply(401, dict(error='Unauthorized'))
            return False
        return True

    def do_GET(self):
        if not self.authorized():
            return
        try:
            path = urllib.parse.urlsplit(self.path)
            query = urllib.parse.parse_qs(path.query)
            if path.path == '/status':
                return self.reply(200, status())
            if path.path == '/conversations':
                conversations = list_conversations(SESSION_ROOT, limit=501)
                return self.reply(200, dict(conversations=conversations[:500], truncated=len(conversations) > 500))
            if path.path == '/events':
                after = int(query.get('after', ['0'])[0])
                if after < 0 or after > sequence:
                    after = 0
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                while not ended:
                    with condition:
                        if events and after < events[0][0] - 1:
                            self.wfile.write(b'data: {"kind":"gap","data":"Earlier terminal output is no longer available."}\n\n')
                            after = events[0][0] - 1
                        pending = [(i,e) for i,e,_ in events if i > after]
                        if not pending:
                            condition.wait(10)
                    for i, e in pending:
                        self.wfile.write(('id: %s\ndata: %s\n\n' % (i,json.dumps(e))).encode())
                        after = i
                    self.wfile.write(b': keepalive\n\n')
                    self.wfile.flush()
                self.close_connection = True
                return
            if path.path == '/files':
                files = []
                for root, dirs, names in os.walk(ROOT, followlinks=False):
                    dirs[:] = [d for d in dirs if not d.startswith('.') and not os.path.islink(os.path.join(root,d))]
                    for name in names:
                        relative = os.path.relpath(os.path.join(root,name), ROOT)
                        try:
                            fd = open_file(relative)
                            files.append(dict(name=relative, size=os.fstat(fd).st_size))
                            os.close(fd)
                        except (ValueError, OSError):
                            continue
                        if len(files) >= 500:
                            return self.reply(200, dict(files=files, truncated=True))
                return self.reply(200, dict(files=files))
            if path.path == '/file':
                fd = open_file(query.get('name', [''])[0])
                with os.fdopen(fd, 'rb') as f:
                    data = f.read(LIMIT + 1)
                if len(data) > LIMIT:
                    raise ValueError('Result exceeds 10 MiB')
                return self.reply(200, data, raw=True)
            self.reply(404, dict(error='Unknown endpoint'))
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            self.reply(400, dict(error=type(e).__name__ + ': request failed'))

    def do_POST(self):
        global ended, event_bytes, browser_auth, browser_consumed
        if not self.authorized():
            return
        try:
            if self.headers.get('Transfer-Encoding'):
                raise ValueError('Chunked uploads are not accepted')
            length = int(self.headers.get('Content-Length', '0'))
            path = urllib.parse.urlsplit(self.path)
            if not 0 <= length <= (LIMIT if path.path == '/files' else 65536):
                raise ValueError('Request too large')
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError('Incomplete upload')
            if path.path == '/files':
                name = urllib.parse.parse_qs(path.query).get('name', [''])[0]
                if not name or name.startswith('.') or '/' in name or '\\' in name or '\x00' in name or len(name) > 240:
                    raise ValueError('Choose a simple filename')
                with operation:
                    try:
                        fd = os.open(os.path.join(ROOT, name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                    except FileExistsError:
                        # Identical retries are safe; never overwrite an existing file or follow a link.
                        try:
                            existing = open_file(name)
                            with os.fdopen(existing, 'rb') as f:
                                same = f.read(LIMIT + 1) == raw
                        except (ValueError, OSError):
                            same = False
                        if same:
                            return self.reply(200, dict(name=name, size=length, reused=True))
                        raise ValueError('A different file already uses this name. Rename your copy and attach it again; the existing file was not changed.')
                    with os.fdopen(fd, 'wb') as f:
                        f.write(raw)
                return self.reply(201, dict(name=name, size=length))
            body = json.loads(raw or b'{}')
            if not isinstance(body, dict):
                raise ValueError('Expected object')
            with actions:
                if path.path == '/login':
                    method = body.get('method', 'browser')
                    if method not in ('browser', 'device'):
                        raise ValueError('Unknown sign-in method')
                    if process is not None:
                        raise ValueError('A process is already running; stop it first')
                    browser_auth = None
                    browser_consumed = False
                    start(['login'] + (['--device-auth'] if method == 'device' else []), 'login', body)
                    if method == 'browser':
                        emit('login', 'Finish sign-in in your browser. No device-code setting is required.')
                        deadline = time.monotonic() + 15
                        with condition:
                            while browser_auth is None and process is not None and time.monotonic() < deadline:
                                condition.wait(.1)
                        if browser_auth is None:
                            stop()
                            raise ValueError('Browser sign-in did not start. Please retry.')
                        return self.reply(200, dict(ok=True, authUrl=browser_auth))
                elif path.path == '/login/callback':
                    callback = body.get('callback', '')
                    if not isinstance(callback, str) or len(callback) > 16384:
                        raise ValueError('Invalid callback')
                    parsed = urllib.parse.urlsplit(callback)
                    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
                    expected = urllib.parse.parse_qs(urllib.parse.urlsplit(browser_auth or '').query).get('state', [''])[0]
                    if (not expected or browser_consumed or mode != 'login' or process is None or
                            parsed.scheme or parsed.netloc or parsed.fragment or parsed.path != '/auth/callback' or
                            any(len(v) != 1 for v in query.values()) or
                            set(query) - {'code','state','error','error_description','scope','session_state','iss'} or
                            ('iss' in query and query['iss'] != ['https://auth.openai.com']) or
                            ('code' in query and 'error' in query) or
                            not hmac.compare_digest(query.get('state', [''])[0], expected) or
                            not (query.get('code', [''])[0] or query.get('error', [''])[0])):
                        raise ValueError('Callback does not match the active sign-in')
                    browser_consumed = True
                    try:
                        deliver(callback)
                        if not status()['loggedIn']:
                            raise ValueError('Authentication was not saved')
                    except Exception:
                        stop()
                        raise ValueError('Browser sign-in did not complete. Please retry.') from None
                    browser_auth = None
                elif path.path == '/start':
                    if not status()['loggedIn']:
                        raise ValueError('Sign in with ChatGPT first')
                    conversation_id = body.get('conversationId')
                    if conversation_id is not None:
                        conversation_id = _uuid_text(conversation_id)
                        if not conversation_id:
                            raise ValueError('Invalid conversationId')
                        if find_conversation_path(SESSION_ROOT, conversation_id) is None:
                            raise ValueError('Conversation not found')
                        args = ['resume', conversation_id, '-p', 'io']
                    elif body.get('resume'):
                        saved = list_conversations(SESSION_ROOT)
                        if not saved:
                            raise ValueError('No saved conversation to resume')
                        conversation_id = saved[0]['id']
                        args = ['resume', conversation_id, '-p', 'io']
                    else:
                        args = ['-p', 'io']
                    start(args + ['-a', 'never', '--no-alt-screen'], 'data', body, conversation_id=conversation_id)
                elif path.path == '/conversations/delete':
                    conversation_id = _uuid_text(body.get('conversationId'))
                    if not conversation_id:
                        raise ValueError('Invalid conversationId')
                    with operation:
                        if process is not None and process.poll() is None:
                            raise ValueError('Stop Codex before deleting a conversation')
                        delete_conversation(SESSION_ROOT, conversation_id)
                    return self.reply(200, dict(ok=True))
                elif path.path in ('/input', '/resize', '/interrupt'):
                    with operation:
                        if master is None:
                            raise ValueError('No running Codex process')
                        if path.path == '/resize':
                            fcntl.ioctl(master, termios.TIOCSWINSZ, dimensions(body))
                            os.killpg(process.pid, signal.SIGWINCH)
                        else:
                            data = '\x03' if path.path == '/interrupt' else body.get('data', '')
                            if not isinstance(data, str) or len(data) > 32768:
                                raise ValueError('Invalid terminal input')
                            os.write(master, data.encode())
                elif path.path == '/stop':
                    browser_auth = None
                    stop()
                elif path.path == '/logout':
                    browser_auth = None
                    stop()
                    result = subprocess.run([CODEX, 'logout'], env=ENV, capture_output=True, timeout=20)
                    if result.returncode or status()['loggedIn']:
                        raise ValueError('Sign-out failed. Delete the workspace to remove its login.')
                    # A different account must start a new chat, not resume cached account state.
                    shutil.rmtree('/state/codex')
                    subprocess.run(['node', '/opt/remote/config.js'], env=ENV, check=True, timeout=20)
                    with condition:
                        events.clear()
                        event_bytes = 0
                    emit('reset', 'Signed out. Saved chat cleared; uploaded files remain in this workspace.')
                elif path.path == '/end':
                    stop()
                    self.reply(200, dict(ok=True))
                    ended = True
                    with condition:
                        condition.notify_all()
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return
                else:
                    return self.reply(404, dict(error='Unknown endpoint'))
                self.reply(200, dict(ok=True))
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            self.close_connection = True
            # Useful but never reflect request contents or filesystem paths in diagnostics.
            message = str(e) if isinstance(e, ValueError) else type(e).__name__ + ': request failed'
            self.reply(400, dict(error=message))

    def setup(self):
        super().setup()
        self.connection.settimeout(30)


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    # Cap long-lived streams/slow clients instead of allocating unbounded threads.
    slots = threading.BoundedSemaphore(24)
    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        super().process_request(request, address)
    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()


if __name__ == '__main__':
    server = Server(('0.0.0.0', 8787), Handler)
    expiry = None if PERSISTENT else max(60, min(int(os.environ.get('IO_REMOTE_TTL', '14400')), 86400))
    if expiry is not None:
        # Ephemeral experiment expires even if client disappears. Operator cannot extend it remotely.
        def expire():
            global ended
            time.sleep(expiry)
            stop()
            ended = True
            server.shutdown()
        threading.Thread(target=expire, daemon=True).start()
    print(json.dumps(dict(ready=True, version=VERSION, persistent=PERSISTENT, expiresIn=expiry)), flush=True)
    server.serve_forever()
    stop()
    server.server_close()
