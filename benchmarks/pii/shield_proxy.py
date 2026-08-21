#!/usr/bin/env python3
"""Privacy shield: a local redacting reverse proxy for Antigravity.

    CLOUD_CODE_URL=http://127.0.0.1:8765 agy ...      (CLI)
    CLOUD_CODE_URL=http://127.0.0.1:8765 antigravity  (IDE launched from a shell)

Outbound (request.contents):
  * Every string part is classified: TABLE (CSV-like, with or without line-number
    prefixes), DATA (prose that came from a user file), CODE/SHELL (program text,
    directory listings, command output). TABLE goes through the validated column
    classifier and column-wise tokenisation. DATA goes through validators + GLiNER
    with a case-insensitive name pass. CODE/SHELL gets vault substitution and
    validators only, so junk never grows the vault.
  * --numbers N also hides every run of N+ digits inside DATA/TABLE parts.
  * --always-hide FILE seeds the vault with names/values that must always be hidden.
  * Results are cached by hash; conversation history costs nothing on later calls.
  * In-chat review (--review chat): the first time a TABLE is seen, the proxy
    answers the IDE itself with the proposed column list and waits for the user
    to reply "ok" / "also hide X, Y" / "don't hide Z" before anything leaves.

Inbound: SSE stream rehydrated with a hold-back buffer; --annotate appends a
timing footer to each answer; peek mode (/shield/peek?on=1) disables
rehydration so the user can see what the model really saw.

Status pages: /shield/status, /shield/vault, /shield/last-request (wire view).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import http.client
import http.server
import io
import json
import os
import re
import ssl
import sys
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from columns import classify_columns  # noqa: E402
from detect import build_engine, regex_engine  # noqa: E402
from pseudonymize import PseudonymMap, TOKEN_RE, pseudonymise_frame, redact_text  # noqa: E402

UPHOST = "daily-cloudcode-pa.googleapis.com"
SKIP_KEYS = {"thoughtSignature", "id", "name", "role", "model", "project", "requestId", "sessionId", "userAgent",
             "requestType", "AbsolutePath", "Cwd", "SearchDirectory", "TargetFile", "FilePath", "Pattern",
             "PathToDelete", "mimeType"}
DIRECT = {"person_name", "phone", "email", "aadhaar", "pan", "bank_account", "ifsc", "upi_id",
          "ration_card", "voter_id", "vehicle_number", "address", "village", "gps"}
NAME_SHAPE = re.compile(r"^[A-Za-z][a-z]+(?:\s[A-Za-z]\.?)*(?:\s[A-Za-z][a-z]+){1,3}$")
LINE_NO = re.compile(r"^(\d+): ", re.M)
FOOTER = re.compile(r"\n*_shield: [^\n]*_\s*$")
CODE_HINT = re.compile(r"^\s*(def |class |import |from \S+ import|#include|function |const |let |var |\{|\}|</?\w+>|<\?xml)|;\s*$|=>|\(\)\s*\{", re.M)
SHELL_HINT = re.compile(r"^(total \d+|[d-][rwx-]{9}\s|\$ |PID\s|USER\s+PID)|\S+/\S+/\S+", re.M)
USER_REQ = re.compile(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", re.S)

STATS: dict[str, Any] = {"calls": 0, "redact_ms_total": 0.0, "redact_ms_last": 0.0, "spans_total": 0,
                         "cache_hits": 0, "cache_misses": 0, "bytes_out": 0, "upstream_ms_total": 0.0,
                         "blocked": 0, "reviews": 0, "started": time.time(), "last": None}
LOCK = threading.Lock()
LAST_REQUEST: dict[str, Any] = {"body": "", "path": "", "when": None}
PEEK = {"on": False}


def kind_of(text: str) -> str:
    lines = [LINE_NO.sub("", l) for l in text.splitlines() if l.strip()]
    if len(lines) >= 3:
        for sep in (",", "\t"):
            try:
                widths = [len(r) for r in csv.reader(lines[:40], delimiter=sep)]
            except csv.Error:
                continue
            if widths and widths[0] >= 3 and sum(w == widths[0] for w in widths) >= 0.8 * len(widths):
                return "table"
    if len(CODE_HINT.findall(text)) >= 3 or len(SHELL_HINT.findall(text)) >= 3:
        return "code"
    return "data"


class Shield:
    def __init__(self, engine_spec: str, vault_path: Path, numbers: int | None, always_hide: Path | None,
                 review: str) -> None:
        self.span_engine = build_engine(engine_spec)
        self.vault = PseudonymMap(vault_path)
        self.cache: dict[str, str] = {}
        self.headers: set[str] = set()   # column names seen in any table: never identifiers
        self.kept: set[str] = set()      # values of columns the user chose to keep: allowed anywhere
        self.kept_long: set[str] = set()
        self.hidden_headers: dict[str, str] = {}   # header (lower) -> class, from reviewed tables
        self.numbers = numbers
        self.review = review
        self.pending: dict[str, Any] | None = None   # in-chat review waiting for the user
        self.decisions_path = vault_path.with_name("shield-decisions-local-only.json")
        self.decisions: dict[str, dict[str, str]] = (
            json.loads(self.decisions_path.read_text()) if self.decisions_path.exists() else {})
        if always_hide and always_hide.exists():
            for line in always_hide.read_text().splitlines():
                value = line.strip()
                if value:
                    self.vault.token(value, "person_name")
            self.vault.save()

    # ---------------------------------------------------------------- engines
    def header_value_spans(self, text: str):
        """`Naam: Lalita` / `Mob = 98...` lines and `Name: X,` fragments where the key is a
        column the user chose to hide: the value gets that column's class whatever its shape."""
        spans = []
        if not self.hidden_headers:
            return spans
        keys = "|".join(re.escape(h) for h in sorted(self.hidden_headers, key=len, reverse=True))
        for m in re.finditer(rf"(?i)(?:^|[\s,;|(])({keys})\s*[:=]\s*([^\r\n,;|]{{2,80}}?)\s*(?=$|[\r\n,;|)])", text, re.M):
            value = m.group(2).strip().strip("'\"")
            if value and value.casefold() not in self.kept and not TOKEN_RE.search(value):
                start = m.start(2) + (len(m.group(2)) - len(m.group(2).lstrip()))
                spans.append((start, start + len(value), self.hidden_headers[m.group(1).casefold()], 1.0))
        return spans

    def data_engine(self, text: str):
        spans = [sp for sp in regex_engine(text) if sp[1] - sp[0] >= 4] + self.header_value_spans(text)
        seen = set()
        for variant in (text, text.title()):
            for start, end, label, score in self.span_engine(variant):
                value = text[start:end]
                if label not in DIRECT or score < 0.45 or (start, end) in seen or end - start < 4:
                    continue
                if "\n" in value or "\r" in value:
                    continue
                if "/" in value or re.search(r"[0-9a-f]{8}-[0-9a-f]{4}", value):
                    continue  # paths and uuids are not identifiers
                low = value.casefold().strip()
                if low in self.headers or low in self.kept:
                    continue  # column headers / values from kept columns are not identifiers
                if any(len(k) >= 4 and (k in low or low in k) for k in self.kept_long):
                    continue  # overlaps a kept value ("Pune district", scheme names)
                if label == "person_name" and not NAME_SHAPE.match(value):
                    continue
                seen.add((start, end))
                spans.append((start, end, label, score))
        if self.numbers:
            spans += [(m.start(), m.end(), "long_number", 1.0)
                      for m in re.finditer(rf"(?<!\d)\d{{{self.numbers},}}(?!\d)", text)]
        return spans

    def code_engine(self, text: str):
        return list(regex_engine(text))

    # ----------------------------------------------------------------- tables
    def parse_table(self, text: str) -> tuple[pd.DataFrame, list[str], str]:
        prefixes = LINE_NO.findall(text)
        raw = LINE_NO.sub("", text)
        sep = "\t" if raw.count("\t") > raw.count(",") else ","
        frame = pd.read_csv(io.StringIO(raw), dtype=str, keep_default_na=False, sep=sep, skip_blank_lines=False)
        return frame, prefixes, sep

    def propose(self, text: str) -> dict[str, dict[str, Any]]:
        frame, _, _ = self.parse_table(text)
        self.headers.update(str(c).casefold().strip() for c in frame.columns)
        return classify_columns(frame, self.span_engine)

    def redact_table(self, text: str, classes: dict[str, str]) -> tuple[str, int]:
        frame, prefixes, sep = self.parse_table(text)
        self.headers.update(str(c).casefold().strip() for c in frame.columns)
        for c, cls in classes.items():
            if cls not in ("none", "record_id_non_pii", "age", "dob", "gps", "free_text_with_pii"):
                self.hidden_headers[str(c).casefold().strip()] = cls
            if cls in ("none", "record_id_non_pii", "age") and c in frame.columns:
                vals = {str(v).casefold().strip() for v in frame[c].unique() if str(v).strip()}
                self.kept.update(vals)
                self.kept_long.update(v for v in vals if len(v) >= 4 and not v.replace(".", "").isdigit())
        before = len(self.vault.display)
        shadow = pseudonymise_frame(frame, classes, self.vault, self.data_engine)
        if self.numbers:
            shadow = shadow.map(lambda v: re.sub(rf"(?<!\d)\d{{{self.numbers},}}(?!\d)",
                                                 lambda m: self.vault.token(m.group(0), "long_number"), v)
                                if isinstance(v, str) else v)
        out = shadow.to_csv(index=False, sep=sep, lineterminator="\n")
        out = redact_text(out, self.vault, None)[0]   # hidden anywhere => hidden everywhere
        if prefixes:
            lines = out.splitlines()
            out = "\n".join(f"{n}: {l}" for n, l in zip(prefixes, lines)) + ("\n" if text.endswith("\n") else "")
        return out, len(self.vault.display) - before

    # ---------------------------------------------------------------- strings
    def split_table(self, text: str) -> tuple[str, str, str] | None:
        """Find a CSV/TSV block inside a tool result: returns (preamble, table, rest)."""
        lines = text.split("\n")
        stripped = [LINE_NO.sub("", l) for l in lines]
        for sep in (",", "\t"):
            for start in range(min(len(lines), 15)):
                try:
                    widths = [len(r) for r in csv.reader(stripped[start:start + 40], delimiter=sep)]
                except csv.Error:
                    continue
                if not widths or widths[0] < 3:
                    continue
                ok = [i for i, w in enumerate(widths) if w == widths[0]]
                header_known = stripped[start].casefold().strip().split(sep)[0].strip('"') in self.headers
                if (len(ok) < 3 and not header_known) or len(ok) < 0.8 * len(widths):
                    continue
                end = start
                for i, l in enumerate(stripped[start:], start):
                    if not l.strip():
                        break
                    end = i + 1
                return "\n".join(lines[:start]) + ("\n" if start else ""), "\n".join(lines[start:end]), \
                    ("\n" if end < len(lines) else "") + "\n".join(lines[end:])
        return None

    def redact_string(self, text: str) -> tuple[str, int, bool]:
        if len(text) < 3:
            return text, 0, True
        text = FOOTER.sub("", text)
        key = hashlib.sha256(text.encode()).hexdigest()
        if key in self.cache:
            # vault may have grown since this part was cached: re-apply known values only
            return redact_text(self.cache[key], self.vault, None)[0], 0, True
        split = self.split_table(text)
        if split:
            pre, table, rest = split
            try:
                classes = self.decisions.get(key) or {c: v["class"] for c, v in self.propose(table).items()}
                redacted, spans = self.redact_table(table, classes)
                pre_r, e1 = redact_text(pre, self.vault, self.data_engine, classes=DIRECT | {"long_number"})
                rest_r, e2 = redact_text(rest, self.vault, self.data_engine, classes=DIRECT | {"long_number"})
                out = pre_r + redacted + rest_r
                self.cache[key] = out
                return out, spans + len(e1) + len(e2), False
            except Exception:
                pass
        kind = kind_of(text)
        engine = self.data_engine if kind == "data" else self.code_engine
        redacted, events = redact_text(text, self.vault, engine, classes=DIRECT | {"long_number"})
        self.cache[key] = redacted
        return redacted, len(events), False

    def walk(self, node: Any, counters: dict[str, int], mint: bool = True, walked: list[str] | None = None) -> Any:
        if isinstance(node, dict):
            out = {}
            if node.get("role") == "model":
                mint = False                        # model-authored content: vault only ...
            for k, v in node.items():
                if k in SKIP_KEYS:
                    out[k] = v
                elif k == "functionResponse":      # ... except tool results, which carry user data
                    out[k] = self.walk(v, counters, True, walked)
                elif k in ("functionCall", "thought"):
                    out[k] = self.walk(v, counters, False, walked)
                else:
                    out[k] = self.walk(v, counters, mint, walked)
            return out
        if isinstance(node, list):
            return [self.walk(v, counters, mint, walked) for v in node]
        if isinstance(node, str):
            if mint:
                before = len(self.vault.display)
                out, spans, hit = self.redact_string(node)
                if not hit and len(self.vault.display) > before:
                    new = list(self.vault.display.items())[before:before + 6]
                    with open("shield.log", "a") as log:
                        log.write(json.dumps({"minted_from": node[:160], "kind": kind_of(FOOTER.sub("", node)),
                                              "new": new, "count": len(self.vault.display) - before}, ensure_ascii=False) + "\n")
            else:
                out, spans, hit = redact_text(FOOTER.sub("", node), self.vault, None)[0], 0, True
            counters["spans"] += spans
            counters["hits" if hit else "misses"] += 1
            if walked is not None:
                walked.append(out)
            return out
        return node

    # --------------------------------------------------------- in-chat review
    def find_unreviewed_tables(self, node: Any, found: list[tuple[str, str]]) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k not in SKIP_KEYS and k != "functionCall" and not (node.get("role") == "model" and k == "text"):
                    self.find_unreviewed_tables(v, found)
        elif isinstance(node, list):
            for v in node:
                self.find_unreviewed_tables(v, found)
        elif isinstance(node, str) and len(node) >= 3:
            text = FOOTER.sub("", node)
            key = hashlib.sha256(text.encode()).hexdigest()
            if key not in self.cache and key not in self.decisions:
                split = self.split_table(text)
                if split:
                    found.append((key, split[1]))

    def latest_user_request(self, contents: Any) -> str | None:
        last = None
        for item in contents if isinstance(contents, list) else []:
            if item.get("role") == "user":
                for part in item.get("parts", []):
                    m = USER_REQ.search(part.get("text", "") or "")
                    if m:
                        last = m.group(1)
        return last

    def apply_review_reply(self, reply: str) -> str | None:
        """Returns a message to show the user, or None if reply was not a review answer."""
        assert self.pending
        low = reply.strip().casefold()
        classes = dict(self.pending["classes"])
        columns = {c.casefold(): c for c in classes}
        if low in {"ok", "okay", "yes", "fine", "go", "go ahead", "proceed", "ok go"}:
            pass
        elif low.startswith(("also hide", "hide", "don't hide", "dont hide", "do not hide", "unhide")):
            adding = not low.startswith(("don't", "dont", "do not", "unhide"))
            names = re.split(r"[,;]|\band\b", re.sub(r"^(also hide|hide|don't hide|dont hide|do not hide|unhide)", "", low))
            for n in names:
                n = n.strip().strip("`'\"")
                if n in columns:
                    classes[columns[n]] = "person_name" if adding else "none"
        else:
            return None
        self.decisions[self.pending["key"]] = classes
        self.decisions_path.write_text(json.dumps(self.decisions, indent=1))
        self.pending = None
        hidden = [c for c, k in classes.items() if k not in ("none", "record_id_non_pii", "age")]
        return f"Understood. Hiding {len(hidden)} columns: {', '.join(hidden)}. Continuing."

    def review_message(self, key: str, text: str) -> str:
        proposal = self.propose(text)
        classes = {c: v["class"] for c, v in proposal.items()}
        self.pending = {"key": key, "classes": classes}
        hidden = [f"{c} ({v['class']}, {v['rule']})" for c, v in proposal.items()
                  if v["class"] not in ("none", "record_id_non_pii", "age")]
        kept = [c for c, v in proposal.items() if v["class"] in ("none", "record_id_non_pii", "age")]
        return (
            "🛡️ Privacy shield: a table is about to leave your laptop. I will replace these columns with tokens "
            f"before sending:\n- " + "\n- ".join(hidden) +
            f"\n\nKept as-is: {', '.join(kept) or 'none'}.\n\nReply **ok** to continue, **also hide X, Y** to hide more "
            "columns, or **don't hide Z** to keep one."
        )

    def redact_request(self, body: bytes) -> tuple[bytes | None, dict[str, int], str | None]:
        """Returns (redacted body, counters, synthetic reply). If synthetic reply is
        set, the body is None and the proxy must answer the IDE itself."""
        counters = {"spans": 0, "hits": 0, "misses": 0}
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return body, counters, None
        req = payload.get("request")
        if not (isinstance(req, dict) and "contents" in req):
            return body, counters, None
        if payload.get("requestType") == "checkpoint":  # title generator: redact, never review
            walked: list[str] = []
            req["contents"] = self.walk(req["contents"], counters, True, walked)
            self.last_walked = "\n".join(walked)
            return json.dumps(payload, ensure_ascii=False).encode(), counters, None
        if self.review == "chat":
            if self.pending:
                reply = self.latest_user_request(req["contents"])
                verdict = self.apply_review_reply(reply or "")
                if verdict is None:
                    return None, counters, self.pending_prompt  # re-ask
                self.pending_prompt = None
                with LOCK:
                    STATS["reviews"] += 1
                # fall through: forward this same request so the model continues the task
            found: list[tuple[str, str]] = []
            self.find_unreviewed_tables(req["contents"], found)
            if found:
                key, text = found[0]
                self.pending_prompt = self.review_message(key, text)
                return None, counters, self.pending_prompt
        walked: list[str] = []
        before = len(self.vault.display)
        req["contents"] = self.walk(req["contents"], counters, True, walked)
        if len(self.vault.display) != before:
            # values minted late in this walk may appear in parts walked earlier: one vault-only pass
            walked = []
            req["contents"] = self.walk(req["contents"], {"spans": 0, "hits": 0, "misses": 0}, False, walked)
        self.vault.save()
        self.last_walked = "\n".join(walked)
        return json.dumps(payload, ensure_ascii=False).encode(), counters, None


class Rehydrator:
    """Event-level rehydration. SSE bytes are assembled into complete `data:` events;
    text parts are rehydrated with a carried tail so a token split across two events
    ("...AADHAAR_" + "050") is still replaced. Non-text fields pass through."""
    HOLD = 24

    def __init__(self, vault: PseudonymMap) -> None:
        self.vault = vault
        self.raw = b""
        self.tail = ""

    def _fix(self, text: str, final: bool) -> str:
        joined = self.tail + text
        if final:
            self.tail = ""
            return self.vault.rehydrate(joined)
        cut = max(0, len(joined) - self.HOLD)
        while cut > 0 and (joined[cut - 1].isalnum() or joined[cut - 1] in "_\\"):
            cut -= 1   # never cut inside a possible token
        out, self.tail = joined[:cut], joined[cut:]
        return self.vault.rehydrate(out)

    def _walk(self, node, final):
        if isinstance(node, dict):
            return {k: (self._fix(v, final) if k == "text" and isinstance(v, str) and not node.get("thought")
                        else (self.vault.rehydrate(json.dumps(v)) and json.loads(self.vault.rehydrate(json.dumps(v))) if k == "args" else self._walk(v, final)))
                    for k, v in node.items()}
        if isinstance(node, list):
            return [self._walk(v, final) for v in node]
        return node

    def feed(self, chunk: bytes, final: bool = False) -> bytes:
        if PEEK["on"]:
            return chunk
        self.raw += chunk
        out = b""
        while True:
            i1, i2 = self.raw.find(b"\r\n\r\n"), self.raw.find(b"\n\n")
            cands = [(i, n) for i, n in ((i1, 4), (i2, 2)) if i >= 0]
            if not cands:
                break
            idx, n = min(cands)
            event, self.raw = self.raw[:idx + n], self.raw[idx + n:]
            self.sep = self.raw_sep = b"\r\n\r\n" if n == 4 else b"\n\n"
            out += self._event(event, False)
        if final:
            if self.raw.strip():
                out += self._event(self.raw, True)
                self.raw = b""
            if self.tail:
                out += sse_text_event(self.vault.rehydrate(self.tail))
                self.tail = ""
        return out

    def _event(self, event: bytes, final: bool) -> bytes:
        text = event.decode("utf8", "replace")
        if not text.startswith("data: "):
            return event
        try:
            payload = json.loads(text[6:].strip())
        except json.JSONDecodeError:
            return event
        fixed = self._walk(payload, final)
        return b"data: " + json.dumps(fixed, ensure_ascii=False).encode() + getattr(self, "sep", b"\r\n\r\n")


def sse_text_event(text: str, finish: bool = False) -> bytes:
    cand: dict[str, Any] = {"content": {"role": "model", "parts": [{"text": text}]}}
    if finish:
        cand["finishReason"] = "STOP"
    return (f"data: {json.dumps({'response': {'candidates': [cand]}})}\r\n\r\n").encode()


def make_handler(shield: Shield, annotate: bool):
    class H(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def read_body(self) -> bytes:
            if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
                out = b""
                while True:
                    size = int(self.rfile.readline().strip().split(b";")[0], 16)
                    if size == 0:
                        self.rfile.readline()
                        return out
                    out += self.rfile.read(size)
                    self.rfile.readline()
            n = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(n) if n else b""

        def send_local(self, code: int, body: bytes, ctype: str = "application/json") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def send_sse(self, events: list[bytes]) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            for ev in events:
                self.wfile.write(f"{len(ev):x}\r\n".encode() + ev + b"\r\n")
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/shield/status" or url.path == "/shield/status.json":
                with LOCK:
                    snap = dict(STATS)
                snap.update(vault_entries=len(shield.vault.display), cache_entries=len(shield.cache),
                            peek=PEEK["on"], pending_review=bool(shield.pending))
                if url.path.endswith(".json"):
                    return self.send_local(200, json.dumps(snap, indent=1).encode())
                rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in snap.items())
                html = ("<meta http-equiv=refresh content=2><title>Privacy shield</title><body style='font-family:sans-serif'>"
                        f"<h3>Privacy shield</h3><table border=1 cellpadding=4>{rows}</table>"
                        "<p><a href=/shield/vault>vault</a> · <a href=/shield/last-request>last request (wire view)</a> · "
                        "<a href='/shield/peek?on=1'>peek on</a> / <a href='/shield/peek?on=0'>peek off</a></p></body>")
                return self.send_local(200, html.encode(), "text/html")
            if url.path == "/shield/vault":
                return self.send_local(200, json.dumps(shield.vault.display, indent=1, ensure_ascii=False).encode())
            if url.path == "/shield/peek":
                PEEK["on"] = parse_qs(url.query).get("on", ["0"])[0] == "1"
                return self.send_local(200, json.dumps({"peek": PEEK["on"]}).encode())
            if url.path == "/shield/last-request":
                q = parse_qs(url.query).get("q", [""])[0]
                body = LAST_REQUEST["body"]
                hits = len(re.findall(re.escape(q), body, flags=re.I)) if q else None
                html = ("<title>wire view</title><body style='font-family:monospace;white-space:pre-wrap'>"
                        f"<form>search what left the laptop: <input name=q value='{q}'><button>find</button>"
                        f"{'' if hits is None else f' → {hits} hits'}</form>"
                        f"<p>{LAST_REQUEST['path']} at {LAST_REQUEST['when']} · {len(body)} bytes</p><hr>"
                        + body.replace("&", "&amp;").replace("<", "&lt;") + "</body>")
                return self.send_local(200, html.encode(), "text/html")
            return self._fwd()

        def do_POST(self):
            return self._fwd()

        def _fwd(self):
            body = self.read_body()
            counters = {"spans": 0, "hits": 0, "misses": 0}
            redact_ms = 0.0
            is_model_call = "streamGenerateContent" in self.path or "generateContent" in self.path
            if is_model_call and body:
                t0 = time.monotonic()
                body2, counters, synthetic = shield.redact_request(body)
                redact_ms = (time.monotonic() - t0) * 1000
                if synthetic is not None:
                    with open("shield.log", "a") as log:
                        log.write(json.dumps({"t": time.time(), "review_prompt": True, "redact_ms": round(redact_ms, 1)}) + "\n")
                    return self.send_sse([sse_text_event(synthetic, finish=True)])
                body = body2
                lowered = getattr(shield, "last_walked", "").casefold()
                leak = next((v for t, v in shield.vault.display.items()
                             if len(v) >= 4 and not t.startswith(("NUMBER", "AGE"))
                             and re.search(rf"(?<![\w@.]){re.escape(v.casefold())}(?![\w@.])", lowered)), None)
                if leak:
                    with LOCK:
                        STATS["blocked"] += 1
                    i = lowered.find(leak.casefold())
                    with open("shield.log", "a") as log:
                        log.write(json.dumps({"t": time.time(), "blocked_value": leak,
                                              "context": lowered[max(0, i - 120):i + 80]}) + "\n")
                    return self.send_sse([sse_text_event(
                        "🛡️ Privacy shield blocked this request: a protected value was still present in the outgoing text. "
                        "Nothing was sent.", finish=True)])
                LAST_REQUEST.update(body=body.decode("utf8", "replace"), path=self.path, when=time.strftime("%H:%M:%S"))
            hdr = {k: v for k, v in self.headers.items()
                   if k.lower() not in ("host", "content-length", "transfer-encoding", "accept-encoding")}
            hdr["Host"] = UPHOST
            hdr["Content-Length"] = str(len(body))
            t1 = time.monotonic()
            conn = http.client.HTTPSConnection(UPHOST, timeout=600, context=ssl.create_default_context())
            conn.request(self.command, self.path, body=body, headers=hdr)
            r = conn.getresponse()
            self.send_response(r.status)
            for k, v in r.getheaders():
                if k.lower() not in ("transfer-encoding", "content-length", "connection", "content-encoding"):
                    self.send_header(k, v)
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            rehydrator = Rehydrator(shield.vault)
            total = 0

            def emit(data: bytes) -> None:
                if data:
                    self.wfile.write(f"{len(data):x}\r\n".encode() + data + b"\r\n")
                    self.wfile.flush()

            while True:
                chunk = r.read1(65536)
                if not chunk:
                    break
                total += len(chunk)
                emit(rehydrator.feed(chunk) if is_model_call else chunk)
            tail = rehydrator.feed(b"", final=True) if is_model_call else b""
            if is_model_call and annotate:
                note = (f"\n\n_shield: {counters['spans']} new spans, {counters['misses']} new parts, "
                        f"{redact_ms:.0f} ms redaction, vault {len(shield.vault.display)}_")
                tail += sse_text_event(note)
            emit(tail)
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
            conn.close()
            upstream_ms = (time.monotonic() - t1) * 1000
            if is_model_call:
                with LOCK:
                    STATS["calls"] += 1
                    STATS["redact_ms_total"] += redact_ms
                    STATS["redact_ms_last"] = round(redact_ms, 1)
                    STATS["spans_total"] += counters["spans"]
                    STATS["cache_hits"] += counters["hits"]
                    STATS["cache_misses"] += counters["misses"]
                    STATS["bytes_out"] += len(body)
                    STATS["upstream_ms_total"] += upstream_ms
                    STATS["last"] = time.strftime("%H:%M:%S")
                tools = re.findall(r'"functionCall":\s*\{[^{}]*?"name":\s*"([^"]+)"', body.decode("utf8", "replace"))
                with open("shield.log", "a") as log:
                    log.write(json.dumps({"t": time.time(), "path": self.path, "bytes_out": len(body), "tools": tools[-3:],
                                          "redact_ms": round(redact_ms, 1), "upstream_ms": round(upstream_ms),
                                          "resp_bytes": total, **counters}) + "\n")
    return H


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--engine", default="gliner:knowledgator/gliner-pii-edge-v1.0")
    parser.add_argument("--vault", type=Path, default=Path("shield-vault-local-only.json"))
    parser.add_argument("--annotate", action="store_true")
    parser.add_argument("--numbers", type=int, help="also hide every run of N+ digits in data and tables")
    parser.add_argument("--always-hide", type=Path, help="file with one value per line to always hide")
    parser.add_argument("--review", choices=("chat", "off"), default="off")
    args = parser.parse_args()
    os.environ.setdefault("PII_THREADS", "4")
    t0 = time.monotonic()
    shield = Shield(args.engine, args.vault, args.numbers, args.always_hide, args.review)
    shield.pending_prompt = None
    print(f"shield ready on http://127.0.0.1:{args.port}  (engine loaded in {time.monotonic() - t0:.1f}s)", flush=True)
    print(f"status: http://127.0.0.1:{args.port}/shield/status", flush=True)
    http.server.ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(shield, args.annotate)).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
