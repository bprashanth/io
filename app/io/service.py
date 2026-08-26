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
# When the scanner is already cached, load it offline. The hub's startup HTTPS check has no
# timeout, and a dropped connection leaves the warm-up thread blocked forever on a dead
# socket - the "stuck at loading the on-device scanner" wedge (seen live: CLOSE-WAIT to the
# HF CDN, 0% CPU, 6.5 hours).
if any((HERE / "hf-cache" / "hub").glob("models--knowledgator--*")) if (HERE / "hf-cache" / "hub").is_dir() else False:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
sys.path.insert(0, str(HERE / "engine"))                    # the shield's tested modules, vendored unchanged

from columns import classify_columns  # noqa: E402
from detect import build_engine, regex_engine  # noqa: E402
from detect import make_text_v2  # noqa: E402
from pseudonymize import PseudonymMap, pseudonymise_frame, redact_question  # noqa: E402

UI = Path(__file__).resolve().parent / "ui"
CONF = Path(os.environ.get("IO_HOME") or (Path.home() / ".config" / "io"))
CONF.mkdir(parents=True, exist_ok=True)
DECISIONS_PATH = CONF / "decisions.json"
FOLDERS_PATH = CONF / "folders.json"

REASON = {
    "hidden": "hidden",
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
        self.docs: list[dict] = []
        saved = json.loads(DECISIONS_PATH.read_text()) if DECISIONS_PATH.exists() else {}
        self.kept: dict = saved.pop("_kept", {}) if isinstance(saved, dict) else {}
        self.decisions: dict = saved
        self.detector = None
        self.det_lock = threading.Lock()
        self.lock = threading.Lock()
        self.progress: list[str] = []

    def step(self, text: str) -> None:
        self.progress.append(text)
        del self.progress[:-6]

    # ---------------------------------------------------------------- engine
    def get_text_detector(self):
        if getattr(self, "text_detector", None) is None:
            self.get_detector()
            try:
                self.text_detector = make_text_v2(f"gliner:{GLINER_MODEL}")
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                self.text_detector = regex_engine
        return self.text_detector

    def get_detector(self):
        with self.det_lock:
            if self.detector is None:
                self.step("loading the on-device scanner")
                try:
                    gl = build_engine(f"gliner:{GLINER_MODEL}")
                    self.detector = lambda t: regex_engine(t) + gl(t)
                    self.step("scanner ready")   # never leave "loading..." as the last visible word
                except Exception:  # noqa: BLE001
                    traceback.print_exc()
                    self.detector = regex_engine
        return self.detector

    @staticmethod
    def header_key(columns: list[str]) -> str:
        return hashlib.sha256("|".join(sorted(str(c).strip().lower() for c in columns)).encode()).hexdigest()[:16]

    def load_folder(self, folder: Path) -> None:
        saved = json.loads(DECISIONS_PATH.read_text()) if DECISIONS_PATH.exists() else {}
        self.kept = saved.pop("_kept", {}) if isinstance(saved, dict) else {}
        self.decisions = saved
        self.folder = folder
        self.tables, self.redacted, self.turns = [], {}, []
        self.docs = []
        self.pmap = PseudonymMap(CONF / f"vault-{hashlib.sha256(str(folder).encode()).hexdigest()[:12]}-local-only.json")
        det = self.get_detector()
        self.skipped = []
        for f in sorted(folder.iterdir()):
            if f.name.startswith("~$") or f.name.startswith("."):
                continue
            if not f.is_file():
                continue
            if f.suffix.lower() in (".txt", ".md", ".log", ".pdf"):
                try:
                    self.load_doc(f)
                except Exception:  # noqa: BLE001
                    traceback.print_exc()
                    self.skipped.append(f.name)
                continue
            if f.suffix.lower() not in (".csv", ".xlsx", ".xls"):
                self.skipped.append(f.name)
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
        n_files = len(self.tables) + len(self.docs)
        folders = json.loads(FOLDERS_PATH.read_text()) if FOLDERS_PATH.exists() else []
        folders = [x for x in folders if x["path"] != str(folder)]
        folders.insert(0, {"path": str(folder), "name": folder.name, "files": n_files})
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

    def cell_spans(self, frame: pd.DataFrame, classes: dict, decided: dict, det) -> dict[str, dict[int, dict]]:
        """Free-text columns: per cell (first 200 rows), what exactly the scanner found."""
        spans: dict[str, dict[int, dict]] = {}
        for col, info in classes.items():
            cls = decided.get(col, info["class"] if isinstance(info, dict) else info)
            if cls != "free_text_with_pii":
                continue
            hits: dict[int, dict] = {}
            for i, v in enumerate(frame[col].head(200)):
                if not (isinstance(v, str) and v.strip()):
                    continue
                found = det(v)
                if found:
                    parts, vals = [], []
                    for st, en, label, _c in found[:3]:
                        word = REASON.get(label, label).rstrip("s")
                        parts.append(f"{word}: {v[st:en][:24]}")
                        vals.append(v[st:en])
                    hits[i] = {"why": ", ".join(parts), "values": vals}
            spans[col] = hits
        return spans

    def load_doc(self, f: Path) -> None:
        name = f.stem + (" (pdf)" if f.suffix.lower() == ".pdf" else "")
        self.step(f"scanning {name}")
        if f.suffix.lower() == ".pdf":
            from pypdf import PdfReader
            text = "\n\n".join((page.extract_text() or "") for page in PdfReader(str(f)).pages)
        else:
            text = f.read_text(errors="replace")
        text = text[:400_000]
        key = "doc:" + hashlib.sha256(("|".join([f.name, str(len(text))])).encode()).hexdigest()[:16]
        det = self.get_text_detector()
        spans = self.doc_spans(text, det(text))
        d = {"name": name, "file": f.name, "key": key, "text": text, "spans": spans, "labels": []}
        self.apply_doc_terms(d)
        self.docs.append(d)

    @staticmethod
    def doc_spans(text: str, raw) -> list[dict]:
        """Overlap-resolved, deduped spans: [{s, e, label, text}] sorted by position."""
        raw = sorted(raw, key=lambda x: (x[0], -(x[1] - x[0])))
        out, last = [], -1
        for st, en, label, _c in raw:
            if st >= last and en > st and en - st < 120:
                out.append({"s": st, "e": en, "label": label, "text": text[st:en]})
                last = en
        return out

    def doc_decisions(self, key: str) -> dict:
        d = self.decisions.get(key) or {}
        return {"terms": d.get("terms", []), "labels": d.get("labels", [])}

    def apply_doc_terms(self, d: dict) -> None:
        """User search-terms become spans (class 'hidden') at every occurrence."""
        dd = self.doc_decisions(d["key"])
        d["labels"] = dd["labels"]
        existing = {(sp["s"], sp["e"]) for sp in d["spans"]}
        for term in dd["terms"]:
            for m in re.finditer(re.escape(term), d["text"], flags=re.I):
                if not any(s < m.end() and m.start() < e for s, e in existing):
                    d["spans"].append({"s": m.start(), "e": m.end(), "label": "hidden", "text": m.group(0)})
                    existing.add((m.start(), m.end()))
        d["spans"].sort(key=lambda x: x["s"])

    def rescan_doc(self, d: dict, labels: list[str]) -> None:
        """'names, addresses, bank account ids' -> extra GLiNER labels, zero-shot."""
        if getattr(self, "gliner_model", None) is None:
            from gliner import GLiNER  # noqa: PLC0415
            self.gliner_model = GLiNER.from_pretrained(GLINER_MODEL, map_location="cpu")
        model = self.gliner_model
        found = []
        text = d["text"]
        for start in range(0, len(text), 1400):
            chunk = text[start:start + 1500]
            for ent in model.predict_entities(chunk, labels, threshold=0.35):
                found.append((start + ent["start"], start + ent["end"], "hidden", ent["score"]))
        existing = {(sp["s"], sp["e"]) for sp in d["spans"]}
        for st, en, lab, _c in found:
            if not any(s < en and st < e for s, e in existing):
                d["spans"].append({"s": st, "e": en, "label": lab, "text": text[st:en]})
                existing.add((st, en))
        d["spans"].sort(key=lambda x: x["s"])
        dec = self.decisions.setdefault(d["key"], {})
        dec["labels"] = sorted(set(dec.get("labels", [])) | set(labels))
        self.save_decisions()

    def redact_doc(self, d: dict) -> str:
        kept = self.kept_for(d["key"])
        out, cur = [], 0
        for sp in d["spans"]:
            if sp["text"].casefold() in kept:
                continue
            out.append(d["text"][cur:sp["s"]])
            out.append(self.pmap.token(sp["text"], sp["label"] if sp["label"] != "hidden" else "hidden"))
            cur = sp["e"]
        out.append(d["text"][cur:])
        return "".join(out)

    def kept_for(self, key: str) -> set:
        return {v.casefold() for v in self.kept.get(key, [])}

    def kept_all(self) -> set:
        return {v.casefold() for vals in self.kept.values() for v in vals}

    def save_decisions(self) -> None:
        DECISIONS_PATH.write_text(json.dumps({**self.decisions, "_kept": self.kept}, indent=1))

    def build_vault(self) -> None:
        det = self.get_detector()
        for t in self.tables:
            self.step(f"coding {t['name']}")
            kept = self.kept_for(t["key"])
            def filt(text, _d=det, _k=kept):
                return [sp for sp in _d(text) if text[sp[0]:sp[1]].casefold() not in _k]
            kv = (lambda text, _k=kept: [sp for sp in regex_engine(text) if text[sp[0]:sp[1]].casefold() not in _k]) if kept else regex_engine
            classes = {c: v for c, v in self.effective(t).items()}
            full = {c: classes.get(c, "none") for c in t["frame"].columns}
            self.redacted[t["name"]] = pseudonymise_frame(t["frame"], full, self.pmap, detector=filt, kept_validator=kv)
        for d in self.docs:
            self.step(f"coding {d['name']}")
            self.redacted[d["name"]] = self.redact_doc(d)
        self.pmap.save()

    def sub_known(self, text: str) -> str:
        known = self.pmap.known_regex() if self.pmap else None
        if not known:
            return text
        kept = self.kept_all()
        def sub(m):
            if m.group(0).casefold() in kept:
                return m.group(0)
            return self.pmap.forward.get(re.sub(r"\s+", " ", m.group(0).strip()).casefold(), m.group(0))
        return known.sub(sub, text)

    def leak_check(self, text: str) -> list[str]:
        known = self.pmap.known_regex() if self.pmap else None
        if not known:
            return []
        kept = self.kept_all()
        return sorted({m.group(0) for m in known.finditer(text) if m.group(0).casefold() not in kept})[:8]


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


SHARED: dict = {}
SHARE_IDS: dict = {}
SHARE_SRV: list = []

def lan_ip() -> str:
    import socket
    try:
        sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sk.connect(("8.8.8.8", 80))
        ip = sk.getsockname()[0]
        sk.close()
        return ip
    except OSError:
        return "127.0.0.1"


class ShareH(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):  # noqa: N802
        m = re.match(r"^/p/(\d+)$", self.path.split("?")[0])
        page = SHARED.get(int(m.group(1))) if m else None
        body = page.encode() if page else b"nothing shared here"
        self.send_response(200 if page else 404)
        self.send_header("Content-Type", "text/html; charset=utf-8" if page else "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def ensure_share_server() -> int:
    if SHARE_SRV:
        return SHARE_SRV[0]
    port = 8820
    for port in range(8820, 8840):
        try:
            srv = ThreadingHTTPServer(("0.0.0.0", port), ShareH)
            break
        except OSError:
            continue
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    SHARE_SRV.append(port)
    return port


def chat(question: str) -> dict:
    if not S.redacted:
        S.step("hiding what you marked")
        S.build_vault()
    det = S.get_detector()
    # @ mentions restrict the question to named files
    all_names = [t["name"] for t in S.tables] + [d["name"] for d in S.docs]
    mentioned = []
    q_clean = question
    for m in re.finditer(r"@([\w][\w .()\-]{0,60}?)(?=\s*(?:@|$|[,;:?]|\s{2}))|@(\S+)", question):
        frag = (m.group(1) or m.group(2) or "").strip()
        hit = next((n for n in all_names if n.casefold() == frag.casefold()), None) or next((n for n in all_names if frag and frag.casefold() in n.casefold()), None)
        if hit and hit not in mentioned:
            mentioned.append(hit)
            q_clean = q_clean.replace("@" + frag, hit)
    use = mentioned if mentioned else all_names
    if not mentioned and len(all_names) > 12:
        return {"error": f"this folder has {len(all_names)} files. Use @ to pick the ones your question needs, sending everything is a heavy call."}
    blocks, sent_rows, sent_lines, total = [], 0, 0, 0
    for t in S.tables:
        if t["name"] not in use:
            continue
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
    for d in S.docs:
        if d["name"] not in use:
            continue
        red = S.redacted.get(d["name"])
        if red is None:
            continue
        if total + len(red) > 150_000:
            red = red[:8000]
            blocks.append(f"--- {d['name']} (first part only) ---\n{red}")
        else:
            blocks.append(f"--- {d['name']} ---\n{red}")
        total += len(red)
        sent_lines += red.count("\n") + 1
    q = S.sub_known(redact_question(q_clean, S.pmap, det)["redacted"])
    history = ""
    prior = [x for x in S.turns if x.get("answer")][-3:]
    if prior:
        history = "EARLIER:\n" + "\n".join(f"Q: {x['q_sent']}\nA: {x['answer_sent'][:400]}" for x in prior) + "\n\n"
    keys = ", ".join(json.dumps(t["name"]) for t in S.tables)
    payload = S.sub_known(PROMPT.replace("{keys}", keys).format(files="\n\n".join(blocks), history=history, question=q))
    leaks = S.leak_check(payload)
    if leaks:
        return {"error": f"stopped: {len(leaks)} private value(s) were about to leave, {', '.join(leaks[:3])}"}
    S.step(f"asking: {sent_rows} rows, {sent_lines} lines go as codes")
    raw, meta = call_model(payload)
    S.step("translating codes back")
    turn = {"q": question, "q_sent": q, "answer_sent": raw if "<html" not in raw.lower() else "(page)",
            "sent_rows": sent_rows, "sent_lines": sent_lines, "bytes": len(payload), "files_used": use if mentioned else [], **meta}
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
            dirs, count, chats, pdfs = [], 0, 0, 0
            try:
                for e in sorted(cur.iterdir()):
                    if e.name.startswith("."):
                        continue
                    if e.is_dir():
                        dirs.append(e.name)
                    elif e.suffix.lower() in (".csv", ".xlsx", ".xls"):
                        count += 1
                    elif e.suffix.lower() in (".txt", ".md", ".log"):
                        chats += 1
                    elif e.suffix.lower() == ".pdf":
                        pdfs += 1
            except PermissionError:
                pass
            return self._json({"path": str(cur), "parent": str(cur.parent) if cur != cur.parent else None, "dirs": dirs[:200], "data_files": count, "chat_files": chats, "pdf_files": pdfs})
        if p.startswith("/api/vault/find"):
            from urllib.parse import parse_qs, urlparse
            qq = parse_qs(urlparse(self.path).query).get("q", [""])[0].strip()
            out = []
            if qq and len(qq) >= 2 and S.pmap:
                cf = qq.casefold()
                for tok, val in S.pmap.display.items():
                    if cf in val.casefold():
                        out.append({"value": val, "token": tok, "cls": tok.rsplit("_", 1)[0].replace("_", " ").lower()})
                out.sort(key=lambda x: (len(x["value"]), x["value"].casefold()))
            return self._json({"matches": out[:8]})
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
                for d in S.docs:
                    red = S.redacted.get(d["name"])
                    if red is None:
                        continue
                    out.append({"name": d["name"], "kind": "doc", "text": red[:200_000]})
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
                        t["decided"][col] = auto if auto not in (None, "none", "record_id_non_pii", "age") else "hidden"
                    S.decisions[t["key"]] = t["decided"]
                    S.save_decisions()
                    S.redacted = {}  # rebuild vault on next question
                return self._json(self.review())
            if self.path == "/api/dockeep":
                with S.lock:
                    d = next(x for x in S.docs if x["name"] == body["name"])
                    val = body["value"]
                    kept = set(S.kept.get(d["key"], []))
                    if val.casefold() in {k.casefold() for k in kept}:
                        kept = {k for k in kept if k.casefold() != val.casefold()}
                    else:
                        kept.add(val)
                    S.kept[d["key"]] = sorted(kept)
                    S.save_decisions()
                    S.redacted = {}
                return self._json(self.review())
            if self.path == "/api/docterm":
                with S.lock:
                    d = next(x for x in S.docs if x["name"] == body["name"])
                    dec = S.decisions.setdefault(d["key"], {})
                    terms = set(dec.get("terms", []))
                    if body.get("remove"):
                        terms = {t for t in terms if t.casefold() != body["term"].casefold()}
                    else:
                        terms.add(body["term"])
                    dec["terms"] = sorted(terms)
                    S.save_decisions()
                    d["spans"] = [sp for sp in d["spans"] if sp["label"] != "hidden" or sp["text"].casefold() in {t.casefold() for t in terms}]
                    S.apply_doc_terms(d)
                    S.redacted = {}
                return self._json(self.review())
            if self.path == "/api/rescan":
                with S.lock:
                    d = next(x for x in S.docs if x["name"] == body["name"])
                    labels = [x.strip() for x in re.split(r"[,;]", body.get("labels", "")) if x.strip()][:8]
                    if labels:
                        S.step("scanning for: " + ", ".join(labels))
                        S.rescan_doc(d, labels)
                        S.redacted = {}
                return self._json(self.review())
            if self.path == "/api/cellkeep":
                with S.lock:
                    t = next(x for x in S.tables if x["name"] == body["name"])
                    hit = t["spans"].get(body["column"], {}).get(int(body["row"]))
                    if hit:
                        kept = set(S.kept.get(t["key"], []))
                        vals = set(hit["values"])
                        if vals <= {v for v in kept if v in vals} or all(v.casefold() in {k.casefold() for k in kept} for v in vals):
                            kept -= vals
                        else:
                            kept |= vals
                        S.kept[t["key"]] = sorted(kept)
                        S.save_decisions()
                        S.redacted = {}
                return self._json(self.review())
            if self.path == "/api/folders/remove":
                folders = json.loads(FOLDERS_PATH.read_text()) if FOLDERS_PATH.exists() else []
                folders = [x for x in folders if x["path"] != body.get("path")]
                FOLDERS_PATH.write_text(json.dumps(folders, indent=1))
                return self._json({"folders": folders})
            if self.path == "/api/share":
                t = next((x for x in S.turns if x.get("id") == int(body["id"]) and x.get("page")), None)
                if not t:
                    return self._json({"error": "no page"}, 404)
                port = ensure_share_server()
                # turn ids restart on every folder load, so the share id must not be
                # the turn id (measured: three folders in one session all shared /p/3,
                # each overwriting the last). One monotonic id per shared page; sharing
                # the same page again keeps its link.
                key = (str(S.folder), t["id"])
                sid = SHARE_IDS.get(key)
                if sid is None:
                    sid = len(SHARE_IDS) + 1
                    SHARE_IDS[key] = sid
                SHARED[sid] = t["page"]
                return self._json({"url": f"http://{lan_ip()}:{port}/p/{sid}"})
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
                    why[c] = ""
                elif cls == "free_text_with_pii":
                    why[c] = f"found in {len(t['spans'].get(c, {}))} of the first 200 cells"
                else:
                    why[c] = RULE.get(rule, rule or "") + (f", {int(conf * 100)}% of sampled cells" if conf and rule == "validator" else "")
            kept = S.kept_for(t["key"])
            cols = {c: REASON.get(cls, cls) for c, cls in eff.items() if cls != "free_text_with_pii"}
            cells = {}
            cellcols = {}
            for c, cls in eff.items():
                if cls != "free_text_with_pii":
                    continue
                cellcols[c] = REASON.get(cls, cls)
                cells[c] = {str(r): {"why": h["why"], "kept": all(v.casefold() in kept for v in h["values"])}
                            for r, h in t["spans"].get(c, {}).items()}
            out.append({"kind": "table", "name": t["name"], "rows": len(t["frame"]), "columns": list(t["frame"].columns),
                        "grid": grid.values.tolist(),
                        "hidden": cols, "cellcols": cellcols, "cells": cells, "why": why})
        for d in S.docs:
            kept = S.kept_for(d["key"])
            out.append({"kind": "doc", "name": d["name"], "chars": len(d["text"]), "text": d["text"][:200_000],
                        "labels": d.get("labels", []),
                        "spans": [{**sp, "kept": sp["text"].casefold() in kept} for sp in d["spans"]]})
        return {"files": out, "skipped": getattr(S, "skipped", [])}


def main():
    threading.Thread(target=S.get_detector, daemon=True).start()  # warm the scanner
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8801
    print(f"io on http://127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()


if __name__ == "__main__":
    main()
