"""One ephemeral container/session. No shell-execution API; PTY runs pinned Codex only."""
import base64
import errno
import fcntl
import hmac
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
# Serialize lifecycle operations, so concurrent requests cannot create two Codex processes.
operation = threading.RLock()
actions = threading.RLock()


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
    return dict(instance=INSTANCE, loggedIn=logged, running=process is not None and process.poll() is None,
                hasConversation=any(pathlib.Path('/state/codex/sessions').rglob('*.jsonl')), mode=mode, version=VERSION, policy='offline', ended=ended, sandbox=CONFORMANCE['ok'])


def dimensions(body):
    cols, rows = int(body.get('cols', 100)), int(body.get('rows', 30))
    if not 20 <= cols <= 500 or not 5 <= rows <= 300:
        raise ValueError('Invalid terminal size')
    return struct.pack('HHHH', rows, cols, 0, 0)


def start(args, kind, body):
    global process, master, mode
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
        def pump():
            global process, master, mode
            import codecs
            decoder = codecs.getincrementaldecoder('utf8')('replace')
            try:
                while True:
                    data = os.read(fd, 8192)
                    if not data:
                        break
                    emit(kind, decoder.decode(data))
            except OSError as e:
                if e.errno != errno.EIO:
                    emit('state', 'Terminal stream ended unexpectedly')
            finally:
                tail = decoder.decode(b'', final=True)
                if tail:
                    emit(kind, tail)
                code = child.wait()
                with operation:
                    os.close(fd)
                    if process is child:
                        process = master = mode = None
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
        global ended, event_bytes
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
                    start(['login', '--device-auth'], 'login', body)
                elif path.path == '/start':
                    if not status()['loggedIn']:
                        raise ValueError('Sign in with ChatGPT first')
                    args = ['resume', '--last', '-p', 'io'] if body.get('resume') else ['-p', 'io']
                    start(args + ['-a', 'never', '--no-alt-screen'], 'data', body)
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
                    stop()
                elif path.path == '/logout':
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
    # Ephemeral experiment expires even if client disappears. Operator cannot extend it remotely.
    expiry = max(60, min(int(os.environ.get('IO_REMOTE_TTL', '14400')), 86400))
    def expire():
        global ended
        time.sleep(expiry)
        stop()
        ended = True
        server.shutdown()
    threading.Thread(target=expire, daemon=True).start()
    print(json.dumps(dict(ready=True, version=VERSION, expiresIn=expiry)), flush=True)
    server.serve_forever()
    stop()
    server.server_close()
