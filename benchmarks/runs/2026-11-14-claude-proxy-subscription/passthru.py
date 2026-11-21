"""Pass-through proxy for the Claude Code subscription test. Logs method, path, status and the login *type* only."""
import http.client, http.server, sys, json, time
UP = "api.anthropic.com"
LOG = open(sys.argv[2], "a")
class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def _go(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else None
        hdrs = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "content-length", "accept-encoding", "connection")}
        auth = self.headers.get("Authorization") or ""
        key = self.headers.get("x-api-key") or ""
        kind = ("bearer:oauth" if auth.startswith("Bearer sk-ant-oat") else "bearer:other" if auth else
                "x-api-key" if key else "none")
        c = http.client.HTTPSConnection(UP, timeout=300)
        c.request(self.command, self.path, body=body, headers={**hdrs, "Host": UP})
        r = c.getresponse()
        self.send_response(r.status)
        for k, v in r.getheaders():
            if k.lower() not in ("transfer-encoding", "connection", "content-length", "content-encoding"):
                self.send_header(k, v)
        self.send_header("Transfer-Encoding", "chunked"); self.end_headers()
        nbytes = 0
        while True:
            chunk = r.read1(65536) if hasattr(r, "read1") else r.read(65536)
            if not chunk: break
            nbytes += len(chunk)
            self.wfile.write(b"%x\r\n" % len(chunk) + chunk + b"\r\n"); self.wfile.flush()
        self.wfile.write(b"0\r\n\r\n")
        beta = self.headers.get("anthropic-beta") or ""
        LOG.write(json.dumps({"t": time.strftime("%H:%M:%S"), "m": self.command, "path": self.path.split("?")[0],
                              "status": r.status, "auth": kind, "oauth_beta": "oauth" in beta, "bytes": nbytes}) + "\n"); LOG.flush()
    do_GET = do_POST = do_HEAD = _go
http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
