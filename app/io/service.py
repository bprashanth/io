#!/usr/bin/env python3
"""io — minimal service. Point at a folder, see what will be hidden, talk about the files.

Engine: the tested privacy-shield modules (benchmarks/pii: columns.py + detect.py + pseudonymize.py),
unchanged. Provider credentials live in memory only. Redaction decisions are remembered by header
signature (as the shield plugin does); the vault is per folder, local only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import threading
import time
import traceback
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
os.environ.setdefault("HF_HOME", str(HERE / "hf-cache"))   # model weights live with the app
sys.path.insert(0, str(HERE / "engine"))                    # the shield's tested modules, vendored unchanged

from columns import classify_columns  # noqa: E402
from detect import build_engine, regex_engine  # noqa: E402
from pseudonymize import PseudonymMap, pseudonymise_frame, redact_question  # noqa: E402

UI = Path(__file__).resolve().parent / "ui"
CONF = Path(os.environ.get("IO_HOME") or (Path.home() / ".config" / "io"))
CONF.mkdir(parents=True, exist_ok=True)
DECISIONS_PATH = CONF / "decisions.json"
FOLDERS_PATH = CONF / "folders.json"

REASON = {
    "person_name": "names", "phone": "phone numbers", "aadhaar": "Aadhaar numbers", "email": "emails",
    "bank_account": "account numbers", "ifsc": "IFSC codes", "village": "villages", "address": "addresses",
    "dob": "birth dates", "gps": "locations", "caste_category": "categories", "upi": "UPI ids",
    "pan": "PAN numbers", "voter_id": "voter ids", "vehicle": "vehicle numbers",
    "free_text_with_pii": "names or numbers inside text",
}

GLINER_MODEL = "knowledgator/gliner-pii-edge-v1.0"

RULE = {
    "validator": "the format checks out",
    "long-unique-number": "long unique numbers",
    "code-like-id": "record codes",
    "precise-coordinate": "precise coordinates",
    "sensitive-vocabulary": "sensitive words",
    "categorical-names": "the values are people's names",
    "span-coverage": "the scanner recognised the values",
    "free-text": "found inside the text",
    "categorical": "categories",
    "numeric": "numbers",
}


class State:
    def __init__(self) -> None:
        self.provider: dict = {}          # memory only: api_key | server, model
        self.folder: Path | None = None
        self.tables: list[dict] = []      # {file, sheet, name, frame, classes, decided, spans}
        self.pmap: PseudonymMap | None = None
        self.redacted: dict[str, pd.DataFrame] = {}
        self.turns: list[dict] = []
        self.decisions: dict = json.loads(DECISIONS_PATH.read_text()) if DECISIONS_PATH.exists() else {}
        self.detector = None
        self.det_lock = threading.Lock()
        self.lock = threading.Lock()
        self.progress: list[str] = []

    def step(self, text: str) -> None:
        self.progress.append(text)
        del self.progress[:-6]

    # ---------------------------------------------------------------- engine
    def get_detector(self):
        with self.det_lock:
            if self.detector is None:
                self.step("loading the on-device scanner")
                try:
                    gl = build_engine(f"gliner:{GLINER_MODEL}")
                    self.detector = lambda t: regex_engine(t) + gl(t)
                except Exception:  # noqa: BLE001
                    traceback.print_exc()
                    self.detector = regex_engine
        return self.detector

    @staticmethod
    def header_key(columns: list[str]) -> str:
        return hashlib.sha256("|".join(sorted(str(c).strip().lower() for c in columns)).encode()).hexdigest()[:16]

    def load_folder(self, folder: Path) -> None:
        self.decisions = json.loads(DECISIONS_PATH.read_text()) if DECISIONS_PATH.exists() else {}
        self.folder = folder
        self.tables, self.redacted, self.turns = [], {}, []
        self.pmap = PseudonymMap(CONF / f"vault-{hashlib.sha256(str(folder).encode()).hexdigest()[:12]}-local-only.json")
        det = self.get_detector()
        self.skipped = []
        for f in sorted(folder.iterdir()):
            if f.name.startswith("~$") or f.name.startswith("."):
                continue
            if f.is_file() and f.suffix.lower() not in (".csv", ".xlsx", ".xls"):
                self.skipped.append(f.name)
                continue
            if not f.is_file():
                continue
            try:
                frames = {None: pd.read_csv(f, dtype=str)} if f.suffix.lower() == ".csv" else {
                    s: d.astype(str) for s, d in pd.read_excel(f, sheet_name=None, dtype=str).items()}
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                continue
            for sheet, frame in frames.items():
                if frame.empty:
                    continue
                frame = frame.fillna("")
                frame.columns = [str(c) for c in frame.columns]
                name = f.stem + (f" - {sheet}" if sheet and len(frames) > 1 else "")
                if any(t["name"] == name for t in self.tables):
                    name = f"{f.stem} ({f.suffix.lstrip('.')})" + (f" - {sheet}" if sheet and len(frames) > 1 else "")
                self.step(f"scanning {name}")
                classes = classify_columns(frame, det)
                key = self.header_key(list(frame.columns))
                decided = dict(self.decisions.get(key, {}))
                spans = self.cell_spans(frame, classes, decided, det)
                self.tables.append({"file": f.name, "sheet": sheet, "name": name, "key": key,
                                    "frame": frame, "classes": classes, "decided": decided, "spans": spans})
        self.step("done")
        folders = json.loads(FOLDERS_PATH.read_text()) if FOLDERS_PATH.exists() else []
        folders = [x for x in folders if x["path"] != str(folder)]
        folders.insert(0, {"path": str(folder), "name": folder.name, "files": len(self.tables)})
        FOLDERS_PATH.write_text(json.dumps(folders[:24], indent=1))

    @staticmethod
    def effective(t: dict) -> dict[str, str]:
        """column -> class, after user decisions. '' or 'none' means kept."""
        out = {}
        for col, info in t["classes"].items():
            cls = t["decided"].get(col, info["class"] if isinstance(info, dict) else info)
            if cls and cls not in ("none", "record_id_non_pii", "age"):
                out[col] = cls if isinstance(cls, str) else cls[0]
        return out

    def cell_spans(self, frame: pd.DataFrame, classes: dict, decided: dict, det) -> dict[str, dict[int, str]]:
        """Free-text columns: per cell (first 200 rows), what exactly the scanner found."""
        spans: dict[str, dict[int, str]] = {}
        for col, info in classes.items():
            cls = decided.get(col, info["class"] if isinstance(info, dict) else info)
            if cls != "free_text_with_pii":
                continue
            hits: dict[int, str] = {}
            for i, v in enumerate(frame[col].head(200)):
                if not (isinstance(v, str) and v.strip()):
                    continue
                found = det(v)
                if found:
                    parts = []
                    for st, en, label, _c in found[:3]:
                        word = REASON.get(label, label).rstrip("s")
                        parts.append(f"{word}: {v[st:en][:24]}")
                    hits[i] = ", ".join(parts)
            spans[col] = hits
        return spans

    def build_vault(self) -> None:
        det = self.get_detector()
        for t in self.tables:
            self.step(f"coding {t['name']}")
            classes = {c: v for c, v in self.effective(t).items()}
            full = {c: classes.get(c, "none") for c in t["frame"].columns}
            self.redacted[t["name"]] = pseudonymise_frame(t["frame"], full, self.pmap, detector=det, kept_validator=regex_engine)
        self.pmap.save()

    def sub_known(self, text: str) -> str:
        known = self.pmap.known_regex() if self.pmap else None
        if not known:
            return text
        return known.sub(lambda m: self.pmap.forward.get(re.sub(r"\s+", " ", m.group(0).strip()).casefold(), m.group(0)), text)

    def leak_check(self, text: str) -> list[str]:
        known = self.pmap.known_regex() if self.pmap else None
        return sorted({m.group(0) for m in known.finditer(text)})[:8] if known else []


S = State()

PROMPT = """You are helping someone understand their files. The files are below as CSV. Values like NAME_001,
PHONE_002, PLACE_003 are stand-ins; treat them as ordinary labels and never mention that they are stand-ins.

Answer questions directly and briefly, computing from the data. If a page or dashboard is the better answer,
return one complete self-contained HTML document (inline CSS/JS, no external URLs) and nothing else — and in
that case DO NOT embed the rows: at runtime the full data is available as window.data, an object with one array
of row objects per file ({keys}); compute every figure in JavaScript from window.data.

{files}

{history}QUESTION:
{question}
"""


def call_model(prompt: str) -> tuple[str, dict]:
    p = S.provider
    if p.get("server"):
        url, key, model = p["server"].rstrip("/") + "/chat/completions", p.get("api_key", ""), p.get("model") or "local"
    else:
        url, key, model = "https://openrouter.ai/api/v1/chat/completions", p.get("api_key", ""), p.get("model") or "google/gemini-3.7-flash"
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 16000}
    if re.match(r"google/gemini|openai/gpt-oss|openai/o", model):
        body["reasoning"] = {"effort": "low"}
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    t0 = time.monotonic()
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=600) as r:
        raw = json.load(r)
    text = raw["choices"][0]["message"].get("content") or ""
    return text, {"model": raw.get("model", model), "seconds": round(time.monotonic() - t0, 1)}


def chat(question: str) -> dict:
    if not S.redacted:
        S.step("hiding what you marked")
        S.build_vault()
    det = S.get_detector()
    blocks, sent_rows, total = [], 0, 0
    for t in S.tables:
        red = S.redacted.get(t["name"])
        if red is None:
            continue
        csv = S.sub_known(red.to_csv(index=False))
        if total + len(csv) > 150_000:
            csv = "\n".join(csv.splitlines()[:80])
            blocks.append(f"--- {t['name']} (first 80 of {len(red)} rows) ---\n{csv}")
            sent_rows += 79
        else:
            blocks.append(f"--- {t['name']} ({len(red)} rows) ---\n{csv}")
            sent_rows += len(red)
        total += len(csv)
    q = S.sub_known(redact_question(question, S.pmap, det)["redacted"])
    history = ""
    prior = [x for x in S.turns if x.get("answer")][-3:]
    if prior:
        history = "EARLIER:\n" + "\n".join(f"Q: {x['q_sent']}\nA: {x['answer_sent'][:400]}" for x in prior) + "\n\n"
    keys = ", ".join(json.dumps(t["name"]) for t in S.tables)
    payload = S.sub_known(PROMPT.replace("{keys}", keys).format(files="\n\n".join(blocks), history=history, question=q))
    leaks = S.leak_check(payload)
    if leaks:
        return {"error": f"stopped: {len(leaks)} private value(s) were about to leave, {', '.join(leaks[:3])}"}
    S.step(f"asking: {sent_rows} rows go as codes")
    raw, meta = call_model(payload)
    S.step("translating codes back")
    turn = {"q": question, "q_sent": q, "answer_sent": raw if "<html" not in raw.lower() else "(page)",
            "sent_rows": sent_rows, "bytes": len(payload), **meta}
    if "<html" in raw.lower() or "<!doctype" in raw.lower():
        i = raw.lower().find("<!doctype")
        i = i if i >= 0 else raw.lower().find("<html")
        j = raw.lower().rfind("</html>")
        page = S.pmap.rehydrate(raw[i:(j + 7) if j > 0 else None])
        data = {t["name"]: json.loads(t["frame"].to_json(orient="records")) for t in S.tables}
        inject = "<script>window.data = " + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + ";</script>"
        k = page.lower().find("<head>")
        turn["page"] = (page[:k + 6] + inject + page[k + 6:]) if k >= 0 else inject + page
    else:
        turn["answer"] = S.pmap.rehydrate(raw)
    S.turns.append(turn)
    turn["id"] = len(S.turns)
    S.step("done")
    return turn


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, default=str).encode())

    def do_GET(self):  # noqa: N802
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            return self._send(200, (UI / "index.html").read_bytes(), "text/html; charset=utf-8")
        if p == "/api/state":
            return self._json({"provider": {"set": bool(S.provider), "model": S.provider.get("model"), "server": bool(S.provider.get("server"))},
                               "folder": str(S.folder) if S.folder else None,
                               "files": [{"name": t["name"], "rows": len(t["frame"]), "columns": list(t["frame"].columns)} for t in S.tables],
                               "vault": len(S.pmap.display) if S.pmap else 0, "progress": S.progress[-4:]})
        m = re.match(r"^/api/page/(\d+)$", p)
        if m:
            t = next((x for x in S.turns if x.get("id") == int(m.group(1)) and x.get("page")), None)
            return self._send(200, t["page"].encode(), "text/html; charset=utf-8") if t else self._send(404, b"")
        if p.startswith("/api/browse"):
            from urllib.parse import parse_qs, urlparse
            q = parse_qs(urlparse(self.path).query)
            cur = Path(q.get("path", [str(Path.home())])[0]).expanduser().resolve()
            if not cur.is_dir():
                cur = Path.home()
            dirs, count = [], 0
            try:
                for e in sorted(cur.iterdir()):
                    if e.name.startswith("."):
                        continue
                    if e.is_dir():
                        dirs.append(e.name)
                    elif e.suffix.lower() in (".csv", ".xlsx", ".xls"):
                        count += 1
            except PermissionError:
                pass
            return self._json({"path": str(cur), "parent": str(cur.parent) if cur != cur.parent else None, "dirs": dirs[:200], "data_files": count})
        if p == "/api/folders":
            folders = json.loads(FOLDERS_PATH.read_text()) if FOLDERS_PATH.exists() else []
            return self._json({"folders": folders})
        if p == "/api/preview":
            with S.lock:
                if not S.redacted:
                    S.step("coding the files")
                    S.build_vault()
                out = []
                for t in S.tables:
                    red = S.redacted.get(t["name"])
                    if red is None:
                        continue
                    grid = red.head(120)
                    changed = {}
                    for ci, c in enumerate(grid.columns):
                        rows = [ri for ri, (a, b) in enumerate(zip(t["frame"][c].head(120), grid[c])) if str(a) != str(b)]
                        if rows:
                            changed[c] = rows
                    out.append({"name": t["name"], "columns": list(grid.columns), "grid": grid.values.tolist(), "changed": changed})
            return self._json({"files": out, "vault": len(S.pmap.display) if S.pmap else 0})
        if p == "/api/review":
            return self._json(self.review())
        if p == "/api/terms":
            terms = sorted(S.pmap.display.values(), key=len, reverse=True)[:4000] if S.pmap else []
            return self._json({"terms": terms})
        return self._send(404, b"")

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        try:
            if self.path == "/api/provider":
                for k in ("api_key", "server", "model"):
                    if k in body:
                        S.provider[k] = body[k].strip()
                S.provider = {k: v for k, v in S.provider.items() if v}
                return self._json({"ok": bool(S.provider)})
            if self.path == "/api/folder":
                folder = Path(body["path"]).expanduser()
                if not folder.is_dir():
                    return self._json({"error": "not a folder"}, 400)
                with S.lock:
                    S.load_folder(folder)
                return self._json(self.review())
            if self.path == "/api/toggle":
                with S.lock:
                    t = next(x for x in S.tables if x["name"] == body["name"])
                    col = body["column"]
                    now = self.effective_class(t, col)
                    if now:
                        t["decided"][col] = "none"
                    else:
                        info = t["classes"].get(col, {})
                        auto = info.get("class") if isinstance(info, dict) else info
                        t["decided"][col] = auto if auto not in (None, "none", "record_id_non_pii", "age") else "person_name"
                    S.decisions[t["key"]] = t["decided"]
                    DECISIONS_PATH.write_text(json.dumps(S.decisions, indent=1))
                    S.redacted = {}  # rebuild vault on next question
                return self._json(self.review())
            if self.path == "/api/folders/remove":
                folders = json.loads(FOLDERS_PATH.read_text()) if FOLDERS_PATH.exists() else []
                folders = [x for x in folders if x["path"] != body.get("path")]
                FOLDERS_PATH.write_text(json.dumps(folders, indent=1))
                return self._json({"folders": folders})
            if self.path == "/api/accept":
                with S.lock:
                    if not S.redacted:
                        S.step("hiding what you marked")
                        S.build_vault()
                return self._json({"vault": len(S.pmap.display)})
            if self.path == "/api/chat":
                with S.lock:
                    r = chat(body["text"])
                return self._json({k: v for k, v in r.items() if k != "page"} | ({"has_page": True} if r.get("page") else {}))
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            return self._json({"error": str(exc)[:300]}, 500)
        return self._json({"error": "?"}, 404)

    @staticmethod
    def effective_class(t, col):
        cls = t["decided"].get(col)
        if cls is None:
            info = t["classes"].get(col, {})
            cls = info.get("class") if isinstance(info, dict) else info
        return cls if cls and cls not in ("none", "record_id_non_pii", "age") else None

    def review(self):
        out = []
        for t in S.tables:
            eff = S.effective(t)
            grid = t["frame"].head(120)
            why = {}
            for c, cls in eff.items():
                info = t["classes"].get(c, {})
                rule = info.get("rule") if isinstance(info, dict) else None
                conf = info.get("confidence") if isinstance(info, dict) else None
                if c in t["decided"]:
                    why[c] = "you marked this"
                elif cls == "free_text_with_pii":
                    why[c] = f"found in {len(t['spans'].get(c, {}))} of the first 200 cells"
                else:
                    why[c] = RULE.get(rule, rule or "") + (f", {int(conf * 100)}% of sampled cells" if conf and rule == "validator" else "")
            out.append({"name": t["name"], "rows": len(t["frame"]), "columns": list(t["frame"].columns),
                        "grid": grid.values.tolist(),
                        "hidden": {c: REASON.get(cls, cls) for c, cls in eff.items()},
                        "why": why,
                        "spans": {c: r for c, r in t["spans"].items() if c in eff}})
        return {"files": out, "skipped": getattr(S, "skipped", [])}


def main():
    threading.Thread(target=S.get_detector, daemon=True).start()  # warm the scanner
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8801
    print(f"io on http://127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()


if __name__ == "__main__":
    main()
