#!/usr/bin/env python3
"""Keep Claude Code's preamble cacheable on Muse.

Claude Code sends its environment note (folder, date, skills list) as a `system` message *after* the
first user message. Muse's chat template then prints every tool definition a second time after that
note, so the prompt grows from ~10.7k to ~18.6k tokens and any new folder re-reads ~9.7k of them.
This proxy turns such mid-conversation `system` messages into user text blocks (merging adjacent
same-role turns) on POST /v1/messages and /v1/messages/count_tokens. Everything else passes through
unchanged, streamed. Measured 2026-11-07: "hi" in a new folder re-reads 2.2k tokens (~3.8 s total)
instead of 18.6k (~28 s).

Usage: muse_prefix_proxy.py [LISTEN_PORT=8185] [UPSTREAM=127.0.0.1:8181]   (binds 127.0.0.1 only)
"""
import http.client
import http.server
import json
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8185
UP_HOST, UP_PORT = (sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1:8181").rsplit(":", 1)
DUMP = os.environ.get("MUSE_PROXY_DUMP")  # debug only: write the last /v1/messages body here (contains user data)
HOP = {"host", "content-length", "connection", "transfer-encoding", "keep-alive"}


def rewrite(body):
    try:
        j = json.loads(body)
    except ValueError:
        return body
    msgs = j.get("messages")
    if not isinstance(msgs, list) or not any(m.get("role") == "system" for m in msgs if isinstance(m, dict)):
        return body
    out = []
    for m in msgs:
        role = "user" if m.get("role") == "system" else m.get("role")
        c = m.get("content")
        c = list(c) if isinstance(c, list) else [{"type": "text", "text": c or ""}]
        if out and out[-1]["role"] == role:
            out[-1]["content"] += c
        else:
            out.append({**m, "role": role, "content": c})
    j["messages"] = out
    return json.dumps(j).encode()


class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def handle_one(self):
        n = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(n) if n else None
        if body is not None and self.command == "POST" and self.path.split("?")[0] in ("/v1/messages", "/v1/messages/count_tokens"):
            body = rewrite(body)
            if DUMP:
                fd = os.open(DUMP, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                os.write(fd, body); os.close(fd)
        up = http.client.HTTPConnection(UP_HOST, int(UP_PORT), timeout=900)
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
