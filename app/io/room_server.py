#!/usr/bin/env python3
"""The room board: every io laptop pushes its blind-compare votes here; the projector
shows the live tally. Stdlib only. Run: python3 room_server.py [port]  (default 8890).
Point each laptop at it in io settings: room server = http://<this-machine>:8890

Votes land in room-votes.jsonl next to wherever this was started, and GET /votes.jsonl
hands the whole file back for taking away afterwards.

Each vote carries the organisation the participant typed, if they typed one. Since
2026-09-02 (organizer's call) the board shows it: an org column in the recent-votes
table, and filter chips to view one org's votes or only the votes where a given model
was chosen (?org=...&choice=9b|27b|frontier|tie|none). Caveat that stood before: in a
small room "which org preferred what" can be the same as naming a person.
"""
import html
import json, sys, time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOG = Path("room-votes.jsonl")
ALIASES = ("9b", "27b", "frontier", "tie", "none")
CHOICE_LABEL = {"9b": "9B chosen", "27b": "27B chosen", "frontier": "frontier chosen",
                "tie": "no difference", "none": "all bad"}

def load_rows():
    rows = []
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows

def tally(rows):
    t = {a: 0 for a in ALIASES}
    for r in rows:
        t[r.get("outcome", "none")] = t.get(r.get("outcome", "none"), 0) + 1
    return t

def chip(label, org, choice, active):
    query = urllib.parse.urlencode([(k, v) for k, v in (("org", org), ("choice", choice)) if v])
    href = "/" + ("?" + query if query else "")
    return f'<a class="chip{" on" if active else ""}" href="{html.escape(href, quote=True)}">{html.escape(label)}</a>' 

PAGE = """<!doctype html><html><head><meta charset=utf-8><meta http-equiv=refresh content=3>
<title>the room's choices</title><style>
body{background:#1a1d21;color:#e8e6e3;font-family:system-ui;margin:0;padding:40px 60px}
h1{font-weight:600;font-size:28px;margin:0 0 6px} .dim{color:#8b8f96}
.row{display:flex;gap:24px;margin:34px 0}
.big{flex:1;background:#22262b;border:1px solid #2f343a;border-radius:16px;padding:26px;text-align:center}
.big .n{font-size:64px;font-weight:700} .big .l{color:#8b8f96;margin-top:6px;font-size:15px}
.hi{color:#e8b26a} table{border-collapse:collapse;width:100%%;font-size:14px}
td,th{padding:6px 12px;border-bottom:1px solid #2f343a;text-align:left} th{color:#8b8f96;font-weight:500}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 0}
.chip{color:#8b8f96;border:1px solid #2f343a;border-radius:999px;padding:4px 12px;text-decoration:none;font-size:13px}
.chip.on{color:#e8b26a;border-color:#e8b26a}
</style></head><body>
<h1>Which answer did the room prefer?</h1>
<div class=dim>total: %(total)s</div>
<div class=chips>%(orgchips)s</div>
<div class=chips>%(choicechips)s</div>
<div class=row>
<div class=big><div class="n hi">%(9b)s</div><div class=l>the laptop model (9B)</div><div class=l>%(sub_9b)s</div></div>
<div class=big><div class="n hi">%(27b)s</div><div class=l>the mid model (27B)</div><div class=l>%(sub_27b)s</div></div>
<div class=big><div class="n hi">%(frontier)s</div><div class=l>the frontier model</div><div class=l>%(sub_frontier)s</div></div>
<div class=big><div class=n>%(tie)s</div><div class=l>no difference</div></div>
<div class=big><div class=n>%(none)s</div><div class=l>all bad</div></div>
</div>
<table><tr><th>when</th><th>org</th><th>question (coded)</th><th>choice</th><th>why</th></tr>%(rows)s</table>
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
        url = urllib.parse.urlparse(self.path)
        # The raw log, for the organizer to take away after the event. Every vote is in
        # here, including which organisation sent it.
        if url.path == "/votes.jsonl":
            body = LOG.read_bytes() if LOG.exists() else b""
            return self._send(200, body, "application/x-ndjson")
        qs = urllib.parse.parse_qs(url.query)
        f_org = (qs.get("org") or [""])[0][:80]
        f_choice = (qs.get("choice") or [""])[0]
        if f_choice not in ALIASES:
            f_choice = ""
        allrows = load_rows()
        rows = [r for r in allrows
                if (not f_org or (r.get("org") or "").strip() == f_org)
                and (not f_choice or r.get("outcome") == f_choice)]
        t = tally(rows)
        total = sum(t.get(a, 0) for a in ALIASES)
        orgs = sorted({(r.get("org") or "").strip() for r in allrows} - {""})
        orgchips = chip("everyone", "", f_choice, f_org == "") + "".join(
            chip(o, o, f_choice, o == f_org) for o in orgs)
        choicechips = chip("all choices", f_org, "", f_choice == "") + "".join(
            chip(CHOICE_LABEL[a], f_org, a, a == f_choice) for a in ALIASES)
        WHY = {"style": "formatting and style", "correctness": "others were wrong",
               "more-correct": "more correct", "written-better": "written better",
               "cost-less": "time / tokens less", "not-sure": "not sure",
               "wrong-answers": "wrong answers", "bad-writing": "bad writing",
               "cost-high": "time / tokens high", "citations": "citations"}
        last = "".join(f"<tr><td>{time.strftime('%H:%M', time.localtime(r.get('t', 0)))}</td>"
                       f"<td>{html.escape((r.get('org') or '').strip()[:30]) or '&mdash;'}</td>"
                       f"<td>{html.escape((r.get('q_sent') or '')[:90])}</td><td class=hi>{r.get('outcome')}</td>"
                       f"<td>{html.escape(WHY.get(r.get('why'), (r.get('why') or '')[:40]))}</td></tr>"
                       for r in rows[-12:][::-1])
        subs = {}
        for a in ("9b", "27b", "frontier"):
            secs, toks, n = 0.0, 0, 0
            for r in rows:
                for c in r.get("cands", []):
                    if c.get("alias") == a and c.get("seconds") is not None:
                        secs += c["seconds"]; toks += c.get("tokens_out") or 0; n += 1
            subs["sub_" + a] = f"avg {secs/n:.1f}s, {toks//n} tokens" if n else ""
        page = PAGE % {**{a: t.get(a, 0) for a in ALIASES}, **subs, "total": total, "rows": last,
                       "orgchips": orgchips, "choicechips": choicechips}
        return self._send(200, page.encode())

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8890
    print(f"room board on http://0.0.0.0:{port}  (votes POST to /vote)")
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
