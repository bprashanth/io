"""The blind tester's ./ask: one conversation through idli ask on the real store. Logs every turn.
    serve.py --port N --mapper remote|nine --log turns.jsonl
"""
import argparse, json, os, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
COWORK = Path(__file__).resolve().parents[2] / '2026-11-06-oss-desktop-independent' / 'cowork'
sys.path.insert(0, str(COWORK)); os.chdir(COWORK)
from lib import recstore as rs, idlicli  # noqa: E402
ap = argparse.ArgumentParser(); ap.add_argument('--port', type=int); ap.add_argument('--mapper', default='remote')
ap.add_argument('--log'); a = ap.parse_args()
SB = os.environ['IDLI_SANDBOX']; con = rs.connect(SB); hist = []; lock = threading.Lock()
class H(BaseHTTPRequestHandler):
    def log_message(self, *x): pass
    def do_POST(self):
        q = json.loads(self.rfile.read(int(self.headers['Content-Length'])))['q']
        with lock:
            rec = idlicli.ask(con, q, hist, a.mapper, data_dir=SB)
            hist.append({k: rec.get(k) for k in ('q', 'commands', 'shown', 'reply')})
            open(a.log, 'a').write(json.dumps(rec, default=str) + '\n')
        b = rec['reply'].encode(); self.send_response(200); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
print('serving', flush=True)
ThreadingHTTPServer(('127.0.0.1', a.port), H).serve_forever()
