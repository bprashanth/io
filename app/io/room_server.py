#!/usr/bin/env python3
"""The room board: every io laptop pushes its blind-compare votes here; the projector
shows the live tally. Stdlib only. Run: python3 room_server.py [port]  (default 8890).
Point each laptop at it in io settings: room server = http://<this-machine>:8890
"""
import json, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOG = Path("room-votes.jsonl")
ALIASES = ("9b", "27b", "frontier", "tie", "none")

def tally():
    t = {a: 0 for a in ALIASES}
    rows = []
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            try:
                r = json.loads(line)
                t[r.get("outcome", "none")] = t.get(r.get("outcome", "none"), 0) + 1
                rows.append(r)
            except Exception:
                pass
    return t, rows

PAGE = """<!doctype html><html><head><meta charset=utf-8><meta http-equiv=refresh content=3>
<title>the room's choices</title><style>
body{background:#1a1d21;color:#e8e6e3;font-family:system-ui;margin:0;padding:40px 60px}
h1{font-weight:600;font-size:28px;margin:0 0 6px} .dim{color:#8b8f96}
.row{display:flex;gap:24px;margin:34px 0}
.big{flex:1;background:#22262b;border:1px solid #2f343a;border-radius:16px;padding:26px;text-align:center}
.big .n{font-size:64px;font-weight:700} .big .l{color:#8b8f96;margin-top:6px;font-size:15px}
.hi{color:#e8b26a} table{border-collapse:collapse;width:100%%;font-size:14px}
td,th{padding:6px 12px;border-bottom:1px solid #2f343a;text-align:left} th{color:#8b8f96;font-weight:500}
</style></head><body>
<h1>Which answer did the room prefer?</h1>
<div class=dim>Every vote was blind: three unnamed answers, same question, same coded data. %(total)s votes so far.</div>
<div class=row>
<div class=big><div class="n hi">%(9b)s</div><div class=l>the laptop model (9B)</div></div>
<div class=big><div class="n hi">%(27b)s</div><div class=l>the mid model (27B)</div></div>
<div class=big><div class="n hi">%(frontier)s</div><div class=l>the frontier model</div></div>
<div class=big><div class=n>%(tie)s</div><div class=l>no difference</div></div>
<div class=big><div class=n>%(none)s</div><div class=l>all bad</div></div>
</div>
<table><tr><th>when</th><th>question (coded)</th><th>choice</th></tr>%(rows)s</table>
</body></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        if self.path != "/vote":
            return self._send(404, b"")
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        try:
            json.loads(body)
        except Exception:
            return self._send(400, b"bad json")
        with open(LOG, "a") as f:
            f.write(body.decode("utf8", "replace").strip() + "\n")
        return self._send(200, b'{"ok": true}', "application/json")
    def do_GET(self):
        t, rows = tally()
        total = sum(t.get(a, 0) for a in ALIASES)
        last = "".join(f"<tr><td>{time.strftime('%H:%M', time.localtime(r.get('t', 0)))}</td>"
                       f"<td>{(r.get('q_sent') or '')[:90]}</td><td class=hi>{r.get('outcome')}</td></tr>"
                       for r in rows[-12:][::-1])
        html = PAGE % {**{a: t.get(a, 0) for a in ALIASES}, "total": total, "rows": last}
        return self._send(200, html.encode())

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8890
    print(f"room board on http://0.0.0.0:{port}  (votes POST to /vote)")
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
