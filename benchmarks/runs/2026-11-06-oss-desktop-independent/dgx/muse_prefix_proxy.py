#!/usr/bin/env python3
"""Idli's model router (silo.idli.cc → here → Muse, the 9B, or Steam), by the model id Claude Code sends.

The model menu on Idli's Paseo provider picks one (cowork/lib/modes.py has the details):
  muse-glimmer-30b (default)  → Muse, as before: Claude Code's mid-conversation `system` messages become user text
                                 blocks (Muse's template otherwise prints every tool twice: ~18.6k instead of ~10.7k
                                 tokens, measured 2026-11-07), and file_ask shows today's spec-only schema.
  idli-9b                      → the local 9B (IDLI_9B_URL, default 127.0.0.1:8291) on a lean prompt, with guards.
  idli-steam                   → code runs the chat (no model), except one 9B call per question for the form's dials.
POST /v1/chat/completions with model idli-9b (file_ask's split, from the MCP server) goes to the 9B as is.
GET /idli/catalog/catalog.json, GET|HEAD /idli/catalog/files/<path>: the trusted tools catalog (IDLI_CATALOG_DIR, default
  /mnt/seagate/silo/idli-catalog). POST /idli/catalog/requests asks for a new tool; GET lists the requests.
POST /idli/share (an Idli skill bundle, a zip) -> {"code": "IDLI-XXXX-XXXX"}; GET /idli/share/<code> -> the bundle.
  Sharing what Idli learned by a short code (cowork/lib/share.py); bundles hold no rows of anyone's data.
Everything else passes through to Muse unchanged, streamed.

Usage: muse_prefix_proxy.py [LISTEN_PORT=8185] [UPSTREAM=127.0.0.1:8181]   (binds 127.0.0.1 only)
"""
import http.client
import http.server
import importlib.util
import json
import os
import re
import secrets
import sys
import threading
import time
import traceback
import urllib.parse

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8185
UP_HOST, UP_PORT = (sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1:8181").rsplit(":", 1)
DUMP = os.environ.get("MUSE_PROXY_DUMP")  # debug only: write the last /v1/messages body here (contains user data)
HOP = {"host", "content-length", "connection", "transfer-encoding", "keep-alive"}

_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cowork", "lib", "modes.py")
_s = importlib.util.spec_from_file_location("idli_modes", _p)
modes = importlib.util.module_from_spec(_s)
_s.loader.exec_module(modes)
NINE = urllib.parse.urlparse(modes.NINE_URL)


SHARE_DIR = os.environ.get("IDLI_SHARE_DIR") or os.path.expanduser("~/idli-shares")
CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"  # no 0/O, 1/I/L, U


def _new_code():
    import secrets
    while True:
        c = "IDLI-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(4)) + "-" + \
            "".join(secrets.choice(CODE_ALPHABET) for _ in range(4))
        if not os.path.exists(os.path.join(SHARE_DIR, c + ".idli")):
            return c


CATALOG_DIR = os.environ.get("IDLI_CATALOG_DIR") or "/mnt/seagate/silo/idli-catalog"
CATALOG_REQ_MAX = 16 * 1024
CATALOG_REQ_FIELDS = {"need": 2000, "why": 4000, "platform": 40, "team": 40, "tools_considered": 2000}
_catalog_lock = threading.Lock()


def catalog_file(rel):
    """The real path of a file under the catalog root for a URL path, or None. No '..', no absolute paths, no
    directories, and no symlink that leads outside the root."""
    rel = urllib.parse.unquote(rel)
    if not rel or "\\" in rel or "\0" in rel or rel.startswith("/") or re.match(r"^[A-Za-z]:", rel):
        return None
    parts = rel.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return None
    root = os.path.realpath(CATALOG_DIR)
    p = os.path.realpath(os.path.join(root, *parts))
    if not p.startswith(root + os.sep) or not os.path.isfile(p):
        return None
    return p


def catalog_request(body):
    """Check a tool request. Returns (record, None) or (None, error)."""
    try:
        j = json.loads(body)
    except ValueError:
        return None, "not JSON"
    if not isinstance(j, dict):
        return None, "expected a JSON object"
    extra = set(j) - set(CATALOG_REQ_FIELDS)
    if extra:
        return None, "unknown fields: " + ", ".join(sorted(extra))[:200]
    rec = {}
    for k, limit in CATALOG_REQ_FIELDS.items():
        v = j.get(k)
        if k == "tools_considered" and isinstance(v, list):
            if not all(isinstance(x, str) for x in v):
                return None, "tools_considered must be a list of names"
            v = [x.strip()[:200] for x in v if x.strip()][:30]
        elif v is not None and not isinstance(v, str):
            return None, f"{k} must be text"
        elif isinstance(v, str):
            v = v.strip()
            if len(v) > limit:
                return None, f"{k} is too long (at most {limit} characters)"
        rec[k] = v if v not in (None, "") else ([] if k == "tools_considered" else "")
    if not rec["need"]:
        return None, "need is required"
    if rec["team"] and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]{0,39}", rec["team"]):
        return None, "team must be a short name (letters, digits, space, . _ -)"
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rec = {"id": "req-" + time.strftime("%Y%m%d-%H%M%S", time.gmtime()) + "-" + secrets.token_hex(3),
           "received": ts, **rec}
    return rec, None


def rewrite(body):
    """Muse's request: today's tools, and no mid-conversation system messages."""
    try:
        j = json.loads(body)
    except ValueError:
        return body
    return json.dumps(modes.muse_body(j)).encode()


class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def local(self, path, j):
        """The 9B and Steam modes, answered here."""
        if path.endswith("/count_tokens"):
            return self.reply(200, "application/json",
                              json.dumps({"input_tokens": len(json.dumps(j)) // 4}).encode())
        try:
            msg = modes.respond(j)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            err = {"type": "error", "error": {"type": "api_error", "message": f"Idli {modes.mode_of(j.get('model'))}: "
                                                                              f"{type(e).__name__}: {e}"[:500]}}
            return self.reply(500, "application/json", json.dumps(err).encode())
        if j.get("stream"):
            return self.reply(200, "text/event-stream", modes.sse(msg))
        return self.reply(200, "application/json", json.dumps(msg, ensure_ascii=False).encode())

    def share(self, path, body):
        if self.command == "POST" and path == "/idli/share":
            if not body or len(body) > 20_000_000 or not body.startswith(b"PK"):
                return self.reply(400, "application/json", b'{"error": "not an Idli bundle"}')
            os.makedirs(SHARE_DIR, exist_ok=True)
            code = _new_code()
            with open(os.path.join(SHARE_DIR, code + ".idli"), "wb") as f:
                f.write(body)
            return self.reply(200, "application/json", json.dumps({"code": code}).encode())
        code = path.rsplit("/", 1)[-1].upper()
        p = os.path.join(SHARE_DIR, code + ".idli")
        if self.command != "GET" or not re.fullmatch(r"IDLI-[2-9A-Z]{4}-[2-9A-Z]{4}", code) or not os.path.exists(p):
            return self.reply(404, "application/json", b'{"error": "no such code"}')
        with open(p, "rb") as f:
            return self.reply(200, "application/zip", f.read())

    def send_file(self, p, ctype):
        size = os.path.getsize(p)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if self.command == "HEAD":
            return
        try:
            with open(p, "rb") as f:
                while True:
                    chunk = f.read(1 << 20)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True

    def catalog(self, path):
        """The trusted tools catalog: read-only files, plus requests for new tools."""
        if self.headers.get("content-length") and not (self.command == "POST" and path == "/idli/catalog/requests"):
            self.close_connection = True  # a body we will not read must not be parsed as the next request
        if path == "/idli/catalog/requests":
            if self.command == "POST":
                n = int(self.headers.get("content-length") or 0)
                if n > CATALOG_REQ_MAX:
                    self.close_connection = True
                    return self.reply(413, "application/json", b'{"error": "request too large (16 KB at most)"}')
                rec, err = catalog_request(self.rfile.read(n) if n else b"")
                if err:
                    return self.reply(400, "application/json", json.dumps({"error": err}).encode())
                line = (json.dumps(rec, ensure_ascii=False) + "\n").encode()
                with _catalog_lock:
                    fd = os.open(os.path.join(CATALOG_DIR, "requests.jsonl"), os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                                 0o644)
                    try:
                        os.write(fd, line)
                    finally:
                        os.close(fd)
                return self.reply(200, "application/json", json.dumps({"ok": True, "id": rec["id"]}).encode())
            if self.command in ("GET", "HEAD"):
                out = []
                try:
                    with open(os.path.join(CATALOG_DIR, "requests.jsonl"), encoding="utf-8") as f:
                        for ln in f:
                            try:
                                out.append(json.loads(ln))
                            except ValueError:
                                pass
                except FileNotFoundError:
                    pass
                return self.reply(200, "application/json", json.dumps({"requests": out}, ensure_ascii=False).encode())
            return self.reply(405, "application/json", b'{"error": "use GET or POST"}')
        if self.command not in ("GET", "HEAD"):
            return self.reply(405, "application/json", b'{"error": "the catalog is read-only"}')
        if path == "/idli/catalog/catalog.json":
            p = catalog_file("catalog.json")
            ctype = "application/json"
        elif path.startswith("/idli/catalog/files/"):
            p = catalog_file("files/" + path[len("/idli/catalog/files/"):])
            ctype = "application/octet-stream"
            if p and p.endswith((".py", ".txt", ".md", ".json")):
                ctype = "text/plain; charset=utf-8" if not p.endswith(".json") else "application/json"
        else:
            p = None
        if not p:
            return self.reply(404, "application/json", b'{"error": "not in the catalog"}')
        return self.send_file(p, ctype)

    def reply(self, status, ctype, data):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def handle_one(self):
        path = self.path.split("?")[0]
        if path.startswith("/idli/catalog/"):
            return self.catalog(path)
        if self.command == "HEAD":
            return self.reply(405, "application/json", b'{"error": "HEAD is only for the catalog"}')
        n = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(n) if n else None
        if path == "/idli/share" or path.startswith("/idli/share/"):
            return self.share(path, body)
        if path == "/idli/9b/props" and self.command == "GET":  # what the 9B can do (vision?), for team stacks
            try:
                c = http.client.HTTPConnection(NINE.hostname, NINE.port or 80, timeout=10)
                c.request("GET", "/props")
                props = json.loads(c.getresponse().read())
                return self.reply(200, "application/json", json.dumps(
                    {"modalities": props.get("modalities") or {}}).encode())
            except (OSError, ValueError):
                return self.reply(502, "application/json", b'{"error": "the 9B did not answer"}')
        host, port = UP_HOST, int(UP_PORT)
        if body is not None and self.command == "POST" and path in ("/v1/messages", "/v1/messages/count_tokens",
                                                                    "/v1/chat/completions"):
            try:
                j = json.loads(body)
            except ValueError:
                j = None
            mode = modes.mode_of(j.get("model")) if isinstance(j, dict) else "muse"
            if mode != "muse" and path != "/v1/chat/completions":
                return self.local(path, j)
            if mode == "muse" and path == "/v1/messages":  # the per-file privacy choice and masked questions
                try:
                    pre = modes.privacy_route(j)
                except Exception:  # noqa: BLE001
                    traceback.print_exc()
                    pre = None
                if pre:
                    return self.reply(200, "text/event-stream", modes.sse(pre)) if j.get("stream") else \
                        self.reply(200, "application/json", json.dumps(pre, ensure_ascii=False).encode())
                try:
                    j = modes.privacy_nudge(j)
                except Exception:  # noqa: BLE001
                    traceback.print_exc()
            if mode != "muse":  # the split's spec call: straight to the 9B
                j["model"] = modes.NINE_MODEL
                body = json.dumps(j).encode()
                host, port = NINE.hostname, NINE.port or 80
            elif path != "/v1/chat/completions":
                body = json.dumps(modes.muse_body(j)).encode() if isinstance(j, dict) else body
            if DUMP and path == "/v1/messages":
                fd = os.open(DUMP, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                os.write(fd, body); os.close(fd)
        up = http.client.HTTPConnection(host, int(port), timeout=900)
        hdrs = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
        if body is not None:
            hdrs["Content-Length"] = str(len(body))
        try:
            up.request(self.command, self.path, body=body, headers=hdrs)
            r = up.getresponse()
        except OSError as e:
            self.send_error(502, f"upstream: {e}")
            return
        self.send_response(r.status, r.reason)
        for k, v in r.getheaders():
            if k.lower() not in HOP:
                self.send_header(k, v)
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        try:
            while True:
                chunk = r.read1(65536)
                if not chunk:
                    break
                self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk))
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
        except (BrokenPipeError, ConnectionResetError):
            pass  # client went away (e.g. Stop); closing upstream lets llama.cpp cancel the task
        finally:
            up.close()

    do_GET = do_POST = do_PUT = do_DELETE = do_OPTIONS = do_HEAD = handle_one

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
