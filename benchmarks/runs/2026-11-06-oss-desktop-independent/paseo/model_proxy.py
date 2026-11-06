"""Narrow model proxy: listens only on the internal network gateway, forwards to Muse on
host loopback, logs one line per request (source container, path, model, user agent).
Usage: python3 model_proxy.py LISTEN_IP PORT LOGFILE [UPSTREAM]"""
import http.server, json, sys, time, urllib.request, urllib.error
LISTEN, PORT, LOG = sys.argv[1], int(sys.argv[2]), sys.argv[3]
UP = sys.argv[4] if len(sys.argv) > 4 else 'http://127.0.0.1:8181'
class P(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def _go(self, method):
        n = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(n) if n else None
        model = None
        try: model = json.loads(body).get('model') if body else None
        except Exception: pass
        rec = dict(t=round(time.time(), 3), src=self.client_address[0], method=method, path=self.path,
                   model=model, ua=(self.headers.get('User-Agent') or '')[:60])
        status = None
        try:
            req = urllib.request.Request(UP + self.path, data=body, method=method,
                                         headers={'Content-Type': self.headers.get('Content-Type', 'application/json')})
            with urllib.request.urlopen(req, timeout=300) as r:
                status = r.status
                self.send_response(r.status)
                self.send_header('Content-Type', r.headers.get('Content-Type', 'application/json'))
                self.send_header('Transfer-Encoding', 'chunked'); self.end_headers()
                while chunk := r.read1(8192):
                    self.wfile.write(b'%x\r\n%s\r\n' % (len(chunk), chunk)); self.wfile.flush()
                self.wfile.write(b'0\r\n\r\n')
        except urllib.error.HTTPError as e:
            status = e.code; data = e.read()
            self.send_response(e.code); self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
        except Exception as e:
            status = 'error:' + type(e).__name__
            self.send_response(502); self.send_header('Content-Length', '0'); self.end_headers()
        rec['status'] = status; rec['secs'] = round(time.time() - rec['t'], 2)
        with open(LOG, 'a') as f: f.write(json.dumps(rec) + '\n')
    def do_POST(self): self._go('POST')
    def do_GET(self): self._go('GET')
    def log_message(self, *a): pass
http.server.ThreadingHTTPServer((LISTEN, PORT), P).serve_forever()
