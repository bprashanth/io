"""For the grader: POST /ask {"q": "SELECT ..."} runs read-only SQL on a copy of the store."""
import json, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import duckdb
DB, PORT = sys.argv[1], int(sys.argv[2])
con = duckdb.connect(DB, read_only=True)
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        q = json.loads(self.rfile.read(int(self.headers['Content-Length'])))['q'].strip().rstrip(';')
        try:
            if not q.lower().startswith(('select', 'with', 'describe', 'show')):
                raise ValueError('read-only: SELECT, WITH, DESCRIBE or SHOW only')
            cur = con.cursor().execute(q)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchmany(200)
            out = ' | '.join(cols) + '\n' + '\n'.join(' | '.join(str(v)[:160] for v in r) for r in rows)
        except Exception as e:
            out = f'error: {e}'
        b = out.encode(); self.send_response(200); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
print('serving', flush=True)
ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
