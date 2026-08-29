#!/usr/bin/env python3
"""The privacy server: runs the on-device scanner for machines that cannot run it themselves.

    python3 privacy_server.py [port]          # default 8899

Some machines cannot install the scanner at all. An Intel Mac is the clear case - PyTorch
stopped shipping macOS x86_64 wheels after 2.2.2 - but a laptop with no disk space left or
a locked-down install hits the same wall. Rather than leave those people with no shield,
io can be pointed at one of these.

Read this before running one:

  The text sent here is NOT redacted. It cannot be. The whole job of this server is to find
  the names and numbers in it, so it has to see them first. Anyone who runs this server, and
  anyone who can watch the network between it and the laptop, can see what the laptop is
  scanning.

That is the opposite of what io normally promises, which is why io asks the person before
it sends anything here, and why the honest place to run this is a machine the same people
already trust - the organizer's laptop on the room's own wifi - rather than something on the
public internet.

Nothing is stored. Text is scanned and dropped; only counts are kept, so the operator can
see it is alive without keeping what went through it.
"""

import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "engine"))

from detect import build_engine, regex_engine  # noqa: E402

MODEL = os.environ.get("IO_SCANNER_MODEL", "knowledgator/gliner-pii-edge-v1.0")
STATS = {"started": time.time(), "requests": 0, "chars": 0, "spans": 0}
ENGINE = None


def engine():
    global ENGINE
    if ENGINE is None:
        try:
            gl = build_engine(f"gliner:{MODEL}")
            ENGINE = lambda t: regex_engine(t) + gl(t)   # noqa: E731
            print("scanner ready", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"could not load the scanner, serving regex only: {exc}", flush=True)
            ENGINE = regex_engine
    return ENGINE


PAGE = """<!doctype html><meta charset=utf-8><title>io privacy server</title>
<body style="background:#1a1d21;color:#e8e6e3;font:15px/1.6 system-ui;padding:40px 60px">
<h1 style="font-weight:600">io privacy server</h1>
<p style="color:#8b8f96">Scanning for laptops that cannot run the model themselves.</p>
<p>up %(up)s &nbsp;|&nbsp; %(requests)s requests &nbsp;|&nbsp; %(chars)s characters scanned
&nbsp;|&nbsp; %(spans)s values found</p>
<p style="color:#8b8f96">Nothing sent here is written to disk.</p>
</body>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path.rstrip("/") in ("", "/health"):
            up = int(time.time() - STATS["started"])
            body = PAGE % {"up": f"{up // 60}m", **{k: f"{v:,}" for k, v in STATS.items() if k != "started"}}
            return self._send(200, body.encode(), "text/html; charset=utf-8")
        return self._send(404, b'{"error":"not found"}')

    def do_POST(self):  # noqa: N802
        if self.path.rstrip("/") != "/scan":
            return self._send(404, b'{"error":"post to /scan"}')
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 4_000_000:
                return self._send(413, b'{"error":"too much text in one request"}')
            body = json.loads(self.rfile.read(n) or b"{}")
            text = body.get("text") or ""
        except Exception:  # noqa: BLE001
            return self._send(400, b'{"error":"bad json"}')

        spans = engine()(text)
        STATS["requests"] += 1
        STATS["chars"] += len(text)
        STATS["spans"] += len(spans)
        out = json.dumps({"spans": [[int(a), int(b), str(c), float(d)] for a, b, c, d in spans]})
        return self._send(200, out.encode())


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
    print(f"io privacy server on http://0.0.0.0:{port}   (scan: POST /scan)", flush=True)
    print("warming the scanner...", flush=True)
    engine()
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()


if __name__ == "__main__":
    main()
