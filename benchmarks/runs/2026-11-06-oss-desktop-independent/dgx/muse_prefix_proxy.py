#!/usr/bin/env python3
"""Idli's model router (silo.idli.cc → here → Muse, the 9B, or Steam), by the model id Claude Code sends.

The model menu on Idli's Paseo provider picks one (cowork/lib/modes.py has the details):
  muse-glimmer-30b (default)  → Muse, as before: Claude Code's mid-conversation `system` messages become user text
                                 blocks (Muse's template otherwise prints every tool twice: ~18.6k instead of ~10.7k
                                 tokens, measured 2026-11-07), and file_ask shows today's spec-only schema.
  idli-9b                      → the local 9B (IDLI_9B_URL, default 127.0.0.1:8291) on a lean prompt, with guards.
  idli-steam                   → code runs the chat (no model), except one 9B call per question for the form's dials.
POST /v1/chat/completions with model idli-9b (file_ask's split, from the MCP server) goes to the 9B as is.
Everything else passes through to Muse unchanged, streamed.

Usage: muse_prefix_proxy.py [LISTEN_PORT=8185] [UPSTREAM=127.0.0.1:8181]   (binds 127.0.0.1 only)
"""
import http.client
import http.server
import importlib.util
import json
import os
import sys
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


def rewrite(body):
    """Muse's request: today's tools, and no mid-conversation system messages."""
    try:
        j = json.loads(body)
    except ValueError:
        return body
    return json.dumps(modes.muse_body(j)).encode()


class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def reply(self, status, ctype, data):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

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

    def handle_one(self):
        n = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(n) if n else None
        path = self.path.split("?")[0]
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

    do_GET = do_POST = do_PUT = do_DELETE = do_OPTIONS = handle_one

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
