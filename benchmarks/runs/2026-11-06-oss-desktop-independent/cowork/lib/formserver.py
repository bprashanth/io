"""The file form: a small page on 127.0.0.1 that Idli opens in a Paseo browser tab.

One page per taught file: a tab per workbook tab, dropdowns built from the file skill and the data
(what to count, how to break it down, which rows), the answer computed by DuckDB, the checks' problems,
and the contract test's verdict. Nothing leaves the computer: the server listens on 127.0.0.1 only and
every request needs the token written to <data dir>/.idli/form-server.json (mode 600).

    python -I -m lib.formserver <data dir>     (started on demand by the files site's file_form tool)
"""
import json
import os
import secrets
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import duckdb

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from lib import filekit as fk  # noqa: E402
from lib import formkit as fm  # noqa: E402

PORT = int(os.environ.get("IDLI_FORM_PORT") or 8797)
PAGE = os.path.join(HERE, "lib", "form.html")


def state_file(data_dir):
    return os.path.join(data_dir, ".idli", "form-server.json")


class Files:
    """Opened files, rebuilt when the file or its skill changes."""

    def __init__(self, data_dir):
        self.data_dir = os.path.realpath(data_dir)
        self.cache = {}
        self.lock = threading.Lock()

    def resolve(self, rel):
        path = os.path.realpath(os.path.join(self.data_dir, rel))
        if not path.startswith(self.data_dir + os.sep) or not os.path.isfile(path):
            raise ValueError(f"No file '{rel}' in the workspace folder.")
        return path

    def open(self, rel):
        path = self.resolve(rel)
        with self.lock:
            sheets, _ = fk.raw_sheets(path)
            skill, score, tabmap = fm.match_file(sheets)
            key = (path, os.path.getmtime(path), skill and skill["id"], skill and skill.get("version"),
                   skill and os.path.getmtime(os.path.join(skill["_dir"], "skill.json")))
            hit = self.cache.get(rel)
            if hit and hit["key"] == key:
                return hit
            entry = {"key": key, "path": path, "skill": skill, "score": score, "sheets": sheets}
            if skill:
                con = duckdb.connect()
                built = fm.build(con, path, skill, fk.slug(skill["id"]))
                entry.update(con=con, built=built, contract=fm.contract(skill, sheets, con, built),
                             forms={t: fm.form(con, skill, t, built) for t in built})
                out_dir = os.path.join(self.data_dir, "checked")
                problems, checked = fm.check(path, skill, out_dir)
                entry.update(problems=problems, checked=os.path.relpath(checked, self.data_dir))
            hidden = path + ".hidden.json"
            if os.path.exists(hidden):
                with open(hidden) as f:
                    entry["hidden"] = json.load(f)
            self.cache[rel] = entry
            return entry

    def meta(self, rel):
        e = self.open(rel)
        title = os.path.splitext(os.path.basename(e["path"]))[0]
        if not e["skill"]:
            return {"file": rel, "title": title, "known": False, "overlap": e["score"],
                    "sheets": {n: {"rows": len(df), "columns": list(df.columns)} for n, df in e["sheets"].items()}}
        groups = {}
        for p in e["problems"]:
            g = groups.setdefault(p["tab"], {}).setdefault((p["column"], p["problem"]),
                                                           {"column": p["column"], "problem": p["problem"], "rows": []})
            g["rows"].append({"row": p["row"], "value": p["value"]})
        return {"file": rel, "title": e["skill"].get("title") or title, "known": True,
                "skill": {"id": e["skill"]["id"], "version": e["skill"].get("version", 1)},
                "contract": e["contract"], "checked_copy": e["checked"], "problem_count": len(e["problems"]),
                "problems": {t: list(v.values()) for t, v in groups.items()},
                "hidden_cells": e.get("hidden"),
                "tabs": [dict(fm.public(f), rows=len(e["built"][t]["df"])) for t, f in e["forms"].items()]}

    def run(self, rel, tab, spec):
        e = self.open(rel)
        if not e["skill"]:
            raise ValueError("Idli hasn't been taught this file yet.")
        if e["contract"]["status"] == "changed":
            raise ValueError("This file has changed since Idli was taught it: " + " ".join(e["contract"]["messages"])
                             + " Ask Idli in the chat to re-teach it.")
        tab = tab or next(iter(e["forms"]))
        if tab not in e["forms"]:
            raise ValueError(f"No tab '{tab}'. Tabs: {list(e['forms'])}")
        f = e["forms"][tab]
        with self.lock:
            res = fm.run(e["con"], f, e["built"][tab]["table"], spec)
        res["text"] = fm.answer_text(res, f, spec)
        res["tab"] = tab
        return res


def make_handler(files, token):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else (json.dumps(body, default=str) if ctype == "application/json"
                                                         else body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; "
                             "style-src 'unsafe-inline'; connect-src 'self'; img-src data:")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _ok(self, qs):
            return secrets.compare_digest((qs.get("t") or [""])[0], token)

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(u.query)
            if u.path == "/health":
                return self._send(200, {"ok": True})
            if not self._ok(qs):
                return self._send(403, "Forbidden: open the form from Idli's chat.", "text/plain")
            try:
                if u.path == "/":
                    with open(PAGE, encoding="utf-8") as f:
                        return self._send(200, f.read(), "text/html")
                if u.path == "/api/form":
                    return self._send(200, files.meta(qs["file"][0]))
            except (ValueError, KeyError) as e:
                return self._send(400, {"error": str(e)})
            except Exception as e:  # keep the page alive; the message helps the Teach workspace
                return self._send(500, {"error": f"{type(e).__name__}: {e}"})
            return self._send(404, {"error": "not found"})

        def do_POST(self):
            u = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(u.query)
            if not self._ok(qs):
                return self._send(403, {"error": "forbidden"})
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(min(n, 100000)) or b"{}")
                if u.path == "/api/run":
                    return self._send(200, files.run(body["file"], body.get("tab"), body.get("spec") or {}))
            except fm.SpecError as e:
                return self._send(400, {"error": str(e)})
            except (ValueError, KeyError) as e:
                return self._send(400, {"error": str(e)})
            except Exception as e:
                return self._send(500, {"error": f"{type(e).__name__}: {e}"})
            return self._send(404, {"error": "not found"})

    return H


def serve(data_dir, port=PORT):
    token = secrets.token_urlsafe(18)
    files = Files(data_dir)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(files, token))
    sf = state_file(data_dir)
    os.makedirs(os.path.dirname(sf), exist_ok=True)
    fd = os.open(sf, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"port": port, "token": token, "pid": os.getpid(), "data_dir": files.data_dir}, f)
    httpd.serve_forever()


if __name__ == "__main__":
    serve(sys.argv[1] if len(sys.argv) > 1 else os.getcwd(), int(sys.argv[2]) if len(sys.argv) > 2 else PORT)
