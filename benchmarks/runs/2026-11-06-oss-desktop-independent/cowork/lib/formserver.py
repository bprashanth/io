"""The file form: a small page on 127.0.0.1 that Idli opens in a Paseo browser tab.

One page per taught file: a tab per workbook tab, dropdowns built from the file skill and the data
(what to count, how to break it down, which rows), the answer computed by DuckDB, the checks' problems,
and the contract test's verdict. Nothing leaves the computer: the server listens on 127.0.0.1 only and
every request needs the token written to <data dir>/.idli/form-server.json (mode 600).

    python -I -m lib.formserver <data dir>     (started on demand by the files site's file_form tool)
"""
import datetime as dt
import json
import re
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

    # ---- suggested fixes: the person accepts or rejects each one; nothing touches the original file
    def _decisions_path(self, rel):
        name = os.path.splitext(os.path.basename(self.resolve(rel)))[0]
        return os.path.join(self.data_dir, "checked", f"{name}.decisions.json")

    def decisions(self, rel):
        try:
            with open(self._decisions_path(rel)) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def decide(self, rel, keys, decision):
        d = self.decisions(rel)
        for k in keys:
            if decision in ("accept", "reject"):
                d[k] = decision
            else:
                d.pop(k, None)
        os.makedirs(os.path.dirname(self._decisions_path(rel)), exist_ok=True)
        with open(self._decisions_path(rel), "w") as f:
            json.dump(d, f, indent=1)
        return {"ok": True, "accepted": sum(v == "accept" for v in d.values()), "rejected": sum(v == "reject" for v in d.values())}

    @staticmethod
    def pkey(p):
        return f"{p['tab']}|{p.get('cell')}|{p.get('rule')}"

    def source(self, rel):
        try:
            with open(self.resolve(rel) + ".source.json") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def fixlist(self, rel):
        """Write '<name> - fixes.xlsx' (the accepted fixes, cell by cell) and, for Excel files, '<name> - fixed.xlsx':
        the original with accepted fixes applied at the same cells (formatting kept), each changed cell commented
        with its old value, and accepted skipped rows removed. The original is never touched."""
        from openpyxl import Workbook, load_workbook
        from openpyxl.comments import Comment
        from openpyxl.utils.cell import coordinate_from_string
        e = self.open(rel)
        d = self.decisions(rel)
        acc = [p for p in e["problems"] if d.get(self.pkey(p)) == "accept" and p.get("suggestion")]
        name = os.path.splitext(os.path.basename(e["path"]))[0]
        out_dir = os.path.join(self.data_dir, "checked")
        os.makedirs(out_dir, exist_ok=True)
        src = self.source(rel) or {}
        wb = Workbook()
        ws = wb.active
        ws.title = "Fix list"
        ws.append(["Tab", "Cell", "Was", "Change to", "Why", "Open"])
        for p in acc:
            sg = p["suggestion"]
            to = "(delete the row)" if sg.get("action") == "skip_row" else ("(blank)" if sg.get("to") == "" else sg.get("to"))
            ws.append([p["tab"], p.get("cell"), p["value"], to, sg.get("why"), src.get("url") or ""])
        fixes = os.path.join(out_dir, f"{name} - fixes.xlsx")
        wb.save(fixes)
        fixed = None
        if e["path"].lower().endswith(".xlsx"):
            book = load_workbook(e["path"])
            drop = {}
            for p in acc:
                if p["tab"] not in book.sheetnames or not p.get("cell"):
                    continue
                sh = book[p["tab"]]
                sg = p["suggestion"]
                col, row = coordinate_from_string(p["cell"])
                if sg.get("action") == "skip_row":
                    drop.setdefault(p["tab"], set()).add(row)
                elif sg.get("to") is not None:
                    c = sh[p["cell"]]
                    new = sg["to"]
                    num = fk.as_number(new) if new else None
                    c.value = num if num is not None and re.fullmatch(r"-?\d+(\.\d+)?", new) else (new or None)
                    c.comment = Comment(f"Idli: was '{p['value']}'. {sg.get('why', '')}", "Idli")
            for tab, rows in drop.items():
                for r in sorted(rows, reverse=True):
                    book[tab].delete_rows(r)
            fixed = os.path.join(out_dir, f"{name} - fixed.xlsx")
            book.save(fixed)
        rel_ = lambda x: os.path.relpath(x, self.data_dir) if x else None
        return {"fixes": len(acc), "fix_list": rel_(fixes), "fixed_copy": rel_(fixed)}

    def meta(self, rel):
        e = self.open(rel)
        title = os.path.splitext(os.path.basename(e["path"]))[0]
        if not e["skill"]:
            return {"file": rel, "title": title, "known": False, "overlap": e["score"],
                    "sheets": {n: {"rows": len(df), "columns": list(df.columns)} for n, df in e["sheets"].items()}}
        groups, skipped = {}, {}
        dec = self.decisions(rel)
        for p in e["problems"]:
            if p.get("skipped"):
                k = skipped.setdefault(p["tab"], {}).setdefault(p["problem"], [])
                k.append(p["row"])
                continue
            g = groups.setdefault(p["tab"], {}).setdefault((p["column"], p["problem"]),
                                                           {"column": p["column"], "problem": p["problem"], "rows": []})
            g["rows"].append({"row": p["row"], "value": p["value"], "cell": p.get("cell"), "key": self.pkey(p),
                              "suggestion": p.get("suggestion"), "decision": dec.get(self.pkey(p))})
        real = [p for p in e["problems"] if not p.get("skipped")]
        src = self.source(rel) or {}
        return {"file": rel, "title": e["skill"].get("title") or title, "known": True,
                "working_copy": src.get("working_copy"), "is_copy": bool(src.get("copy_of")),
                "problem_kinds": len({(p["tab"], p["column"], p["rule"]) for p in real}),
                "charts": self.charts(rel),
                "skill": {"id": e["skill"]["id"], "version": e["skill"].get("version", 1)},
                "contract": e["contract"], "checked_copy": e["checked"], "problem_count": len(real),
                "source": self.source(rel),
                "skipped": {t: [{"why": w, "rows": r} for w, r in v.items()] for t, v in skipped.items()},
                "problems": {t: list(v.values()) for t, v in groups.items()},
                "hidden_cells": e.get("hidden"),
                "tabs": [dict(fm.public(f), rows=len(e["built"][t]["df"])) for t, f in e["forms"].items()]}

    def charts_dir(self, rel):
        stem = re.sub(r"[^\w.-]+", "_", os.path.splitext(os.path.basename(rel))[0])
        return os.path.join(self.data_dir, "charts", stem)

    def charts(self, rel):
        """Charts drawn for this file (Claude's and quick ones from the chat), newest first."""
        d = self.charts_dir(rel)
        if not os.path.isdir(d):
            return []
        out = []
        for f in os.listdir(d):
            if not f.endswith(".svg"):
                continue
            meta = {}
            try:
                with open(os.path.join(d, f[:-4] + ".json")) as fh:
                    meta = json.load(fh)
            except (OSError, ValueError):
                pass
            out.append({"name": f[:-4], "title": meta.get("title") or f[:-4], "kind": meta.get("kind", "quick"),
                        "mtime": os.path.getmtime(os.path.join(d, f))})
        return sorted(out, key=lambda x: -x["mtime"])

    def chart(self, rel, name):
        import base64
        if not re.fullmatch(r"[\w.-]+", name or ""):
            raise ValueError("bad chart name")
        with open(os.path.join(self.charts_dir(rel), name + ".svg"), "rb") as f:
            return {"data": "data:image/svg+xml;base64," + base64.b64encode(f.read()).decode()}

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


def skills_list():
    """What Idli has learned: one skill per file (from the Claude workspace), with its charts."""
    from lib import chartkit
    out = []
    for sk in fk.load_skills():
        tabs = fm.tabs_of(sk)
        hist = sk.get("history") or []
        out.append({"id": sk["id"], "title": sk.get("title") or sk["id"], "version": sk.get("version", 1),
                    "tabs": list(tabs), "checks": sum(len(t.get("validations") or []) for t in tabs.values()),
                    "measures": sum(len(t.get("measures") or []) for t in tabs.values()),
                    "charts": [c["title"] or c["id"] for c in chartkit.charts_of(sk)],
                    "taught": (hist[-1].get("taught") if hist else "") or "",
                    "changed": dt.datetime.fromtimestamp(os.path.getmtime(os.path.join(sk["_dir"], "skill.json")))
                    .strftime("%d %b %Y %H:%M")})
    return out


def skills_delete(sid):
    """Remove one file's skill (moved to ~/idli-insights/archive/skills, so a mistake can be undone by hand)."""
    import shutil
    if not re.fullmatch(r"[\w.-]+", sid or ""):
        raise ValueError("bad skill id")
    sk = next((s for s in fk.load_skills() if s["id"] == sid), None)
    if not sk:
        raise ValueError(f"No skill '{sid}'.")
    dest = os.path.join(os.path.expanduser("~/idli-insights/archive/skills"),
                        f"{sid}-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(sk["_dir"], dest)
    return {"deleted": sid, "kept_at": dest}


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
                if u.path == "/index":
                    with open(os.path.join(HERE, "lib", "index.html"), encoding="utf-8") as f:
                        return self._send(200, f.read(), "text/html")
                if u.path == "/api/index":
                    from lib import driveindex as di
                    st = di.status()
                    return self._send(200, {"status": st, "line": di.progress_line(st)})
                if u.path == "/api/form":
                    return self._send(200, files.meta(qs["file"][0]))
                if u.path == "/api/chart":
                    return self._send(200, files.chart(qs["file"][0], qs["name"][0]))
                if u.path == "/skills":
                    with open(os.path.join(HERE, "lib", "skills.html"), encoding="utf-8") as f:
                        return self._send(200, f.read(), "text/html")
                if u.path == "/api/skills":
                    return self._send(200, skills_list())
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
                if u.path == "/api/decide":
                    return self._send(200, files.decide(body["file"], list(body["keys"]), body.get("decision")))
                if u.path == "/api/fixlist":
                    return self._send(200, files.fixlist(body["file"]))
                if u.path == "/api/skills/delete":
                    out = skills_delete(body["id"])
                    files.cache.clear()
                    return self._send(200, out)
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
