"""Streaming logging reverse proxy for Antigravity's CloudCode endpoint.
Handles chunked request bodies and streams SSE responses chunk by chunk.
Logs request bodies (auth stripped) and response chunks to traffic.log."""
import http.client
import http.server
import json
import ssl

UPHOST = "daily-cloudcode-pa.googleapis.com"
LOG = open("traffic.log", "a")


def log(**kw):
    LOG.write(json.dumps(kw, ensure_ascii=False) + "\n")
    LOG.flush()


class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def read_body(self):
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            out = b""
            while True:
                size = int(self.rfile.readline().strip().split(b";")[0], 16)
                if size == 0:
                    self.rfile.readline()
                    return out
                out += self.rfile.read(size)
                self.rfile.readline()
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def _fwd(self):
        body = self.read_body()
        hdr = {k: v for k, v in self.headers.items()
               if k.lower() not in ("host", "content-length", "transfer-encoding", "accept-encoding")}
        hdr["Host"] = UPHOST
        hdr["Content-Length"] = str(len(body))
        log(dir="req", p=self.path, len=len(body), body=body.decode("utf8", "replace")[:30000])
        conn = http.client.HTTPSConnection(UPHOST, timeout=600, context=ssl.create_default_context())
        conn.request(self.command, self.path, body=body, headers=hdr)
        r = conn.getresponse()
        self.send_response(r.status)
        for k, v in r.getheaders():
            if k.lower() not in ("transfer-encoding", "content-length", "connection", "content-encoding"):
                self.send_header(k, v)
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        total = 0
        while True:
            chunk = r.read1(65536)
            if not chunk:
                break
            total += len(chunk)
            self.wfile.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n")
            self.wfile.flush()
            if "streamGenerateContent" in self.path:
                log(dir="resp-chunk", p=self.path, chunk=chunk.decode("utf8", "replace")[:4000])
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()
        log(dir="resp-end", p=self.path, status=r.status, len=total)
        conn.close()

    do_POST = do_GET = _fwd

    def log_message(self, *a):
        pass


http.server.ThreadingHTTPServer(("127.0.0.1", 8765), H).serve_forever()
