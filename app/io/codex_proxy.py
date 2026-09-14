#!/usr/bin/env python3
"""io's privacy proxy for a bundled Codex.

Codex is pointed at http://127.0.0.1:<port>/backend-api/codex (its `openai_base_url`) and at
http://127.0.0.1:<port>/backend-api/ (its `chatgpt_base_url`). Everything Codex sends to the
model provider therefore crosses this process, which is the one place io enforces the
approved privacy policy:

  outbound  every string in a request body -> known values become their vault tokens,
            unseen values found by the detector become new tokens (io's question policy)
  inbound   every string in a response -> tokens become the real values again, including
            streamed deltas where a token may be split across two chunks

Three representations exist at once: the real files on disk (untouched), what Codex sees
(real values, because it edits files and runs commands), and what leaves the machine
(tokens only). The proxy is the boundary between the last two.

Fail closed: no approved policy -> 403 on everything; an unknown path -> 403; a request
body the proxy cannot read (an encoding it cannot decode, bad JSON) -> 4xx, never forwarded;
a known value still present after transformation -> 403 and a log line. A WebSocket upgrade
is answered 426 so Codex falls back to plain HTTP SSE (verified against 0.154.0 source:
core/src/client.rs treats UPGRADE_REQUIRED as "use HTTP for this session").

Logging: request id, method, path, status, byte counts, substitution counts, event counts,
latency. Never headers with credentials, never bodies with real values. An optional dump
directory receives the *tokenised* request bodies and upstream responses, which is the
evidence that only tokens left.

The module is standalone: it takes a Policy object and never imports the service, so the
tests can drive it with a fake vault and a fake upstream.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import re
import ssl
import threading
import time
import traceback
import uuid
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

# Body strings whose value is protocol, not content. Everything else is transformed.
STRUCTURAL_KEYS = frozenset({
    "type", "role", "id", "call_id", "item_id", "response_id", "model", "status", "object",
    "tool_choice", "truncation", "include", "service_tier", "prompt_cache_key", "store", "stream",
    "effort", "summary", "verbosity", "format", "previous_response_id", "safety_identifier",
    "encrypted_content", "encoding", "detail", "mime_type", "container", "vector_store_ids",
    "parallel_tool_calls", "strict", "background", "prompt_cache_retention", "user",
})

# A delta that ends like this might be the first half of a token (NAME_001 split as
# "NAME_0" + "01"), so that tail waits for the next chunk. Longest thing worth holding.
HOLD_RE = re.compile(r"(?<![\w])[A-Z][A-Z_]{0,24}\d{0,2}$")
HOLD_MAX = 32

# The paths Codex 0.154.0 uses under its two base URLs, and how each is treated.
CONTENT_POSTS = {
    "/backend-api/codex/responses",
    "/backend-api/codex/responses/compact",
    "/backend-api/codex/memories/trace_summarize",
    "/backend-api/codex/alpha/search",
}
PASS_PREFIXES = ("/backend-api/codex/models", "/backend-api/wham/")


class Policy:
    """What the proxy needs from io. The service subclasses this with the live vault.

    outbound(text, role) -> text with private values replaced by tokens.
    inbound(text)        -> text with tokens replaced by their real values.
    leaks(text)          -> the known private values still present in text (should be []).
    ready()              -> False until the user has approved the tokenisation policy.
    """

    def outbound(self, text: str, role: str | None) -> str:  # pragma: no cover - interface
        raise NotImplementedError

    def inbound(self, text: str) -> str:  # pragma: no cover - interface
        raise NotImplementedError

    def leaks(self, text: str) -> list[str]:
        return []

    def code_for(self, value: str) -> str:
        """The code a private value maps to, for logs that must not carry the value."""
        return "?"

    def ready(self) -> bool:
        return True

    def version(self) -> int:
        """Changes whenever the vault grows. A string transformed under an older vault may
        still contain a value that has since become private, so cached results are keyed
        by this and never reused across a change."""
        return 0

    def not_ready_reason(self) -> str:
        return "the privacy policy for this folder has not been approved"


class Stats:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.requests = 0
        self.forwarded = 0
        self.refused = 0
        self.ws_fallbacks = 0
        self.substitutions = 0
        self.restorations = 0
        self.last: dict | None = None
        self.recent: list[dict] = []
        self.started = time.time()

    def record(self, entry: dict) -> None:
        with self.lock:
            self.requests += 1
            if entry.get("forwarded"):
                self.forwarded += 1
            elif entry.get("status") == 426:
                self.ws_fallbacks += 1       # protocol negotiation, not a refusal worth showing
            else:
                self.refused += 1
            self.substitutions += entry.get("subs", 0)
            self.restorations += entry.get("restored", 0)
            self.last = entry
            self.recent.append(entry)
            del self.recent[:-40]

    def snapshot(self) -> dict:
        with self.lock:
            return {"requests": self.requests, "forwarded": self.forwarded, "refused": self.refused,
                    "substitutions": self.substitutions, "restorations": self.restorations,
                    "last": self.last, "recent": list(self.recent[-12:]), "since": self.started}


class StreamRestorer:
    """Rehydrates a stream of text chunks without losing a token split across chunks."""

    def __init__(self, inbound: Callable[[str], str]) -> None:
        self.inbound = inbound
        self.held = ""
        self.prev_char = " "        # the char just before `held`; a token needs a boundary before it

    def feed(self, chunk: str) -> str:
        text = self.held + chunk
        m = HOLD_RE.search(text)
        # A tail can only start a token if it sits on a word boundary, and the boundary may
        # be the last char we already emitted.
        if m and (m.start() > 0 or not re.match(r"\w", self.prev_char)) and len(m.group(0)) <= HOLD_MAX:
            out, self.held = text[:m.start()], m.group(0)
        else:
            out, self.held = text, ""
        if out:
            self.prev_char = out[-1]
        return self.inbound(out) if out else ""

    def flush(self) -> str:
        out, self.held = self.held, ""
        if out:
            self.prev_char = out[-1]
        return self.inbound(out) if out else ""


def walk_strings(node: Any, fn: Callable[[str, str | None, str | None], str], role: str | None = None,
                 key: str | None = None) -> Any:
    """Apply fn(text, role, key) to every content string in a JSON value. Structural keys skipped."""
    if isinstance(node, str):
        return fn(node, role, key)
    if isinstance(node, list):
        return [walk_strings(x, fn, role, key) for x in node]
    if isinstance(node, dict):
        r = node.get("role") if isinstance(node.get("role"), str) else role
        out = {}
        for k, v in node.items():
            if k in STRUCTURAL_KEYS and isinstance(v, str):
                out[k] = v
            else:
                out[k] = walk_strings(v, fn, r, k)
        return out
    return node


class Proxy:
    def __init__(self, policy: Policy, upstream: str = "https://chatgpt.com", log: Callable[[str], None] | None = None,
                 dump_dir: Path | None = None, dev_upstreams: dict[str, str] | None = None) -> None:
        self.policy = policy
        self.upstream = upstream
        self.log = log or (lambda line: None)
        self.dump_dir = dump_dir
        self.stats = Stats()
        self.cache: OrderedDict[str, str] = OrderedDict()
        self.cache_lock = threading.Lock()
        self.server: ThreadingHTTPServer | None = None
        self.port: int | None = None
        # Development only: extra path prefixes routed to another upstream (an
        # OpenAI-compatible Responses server), used to exercise the proxy without OAuth.
        self.dev_upstreams = dev_upstreams or {}

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> int:
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):  # quiet; the proxy writes its own lines
                pass

            def do_GET(self):  # noqa: N802
                proxy.handle(self, "GET")

            def do_POST(self):  # noqa: N802
                proxy.handle(self, "POST")

            def do_DELETE(self):  # noqa: N802
                proxy.handle(self, "DELETE")

            def do_PUT(self):  # noqa: N802
                proxy.handle(self, "PUT")

            def do_PATCH(self):  # noqa: N802
                proxy.handle(self, "PATCH")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True, name="codex-proxy").start()
        self.log(f"proxy listening on 127.0.0.1:{self.port} upstream={self.upstream}")
        return self.port

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None

    # ------------------------------------------------------------------ transforms
    def _cached_outbound(self, text: str, role: str | None) -> tuple[str, int]:
        if not text or len(text) < 2:
            return text, 0
        key = hashlib.sha256(f"{self.policy.version()}\0{role or ''}\0".encode() + text.encode()).hexdigest()
        with self.cache_lock:
            hit = self.cache.get(key)
            if hit is not None:
                self.cache.move_to_end(key)
                return hit, 0
        out = self.policy.outbound(text, role)
        with self.cache_lock:
            self.cache[key] = out
            if len(self.cache) > 4000:
                self.cache.popitem(last=False)
        return out, (1 if out != text else 0)

    def transform_request(self, body: Any) -> tuple[Any, int]:
        """Every string through the policy. If the vault grew while walking (the scanner
        minted a code from one string that also occurs in a string already transformed),
        walk again under the new vault; the first run of a conversation refused its own
        first turn this way (2026-09-14) until the walk repeated."""
        subs = 0

        def fn(text: str, role: str | None, _key: str | None) -> str:
            nonlocal subs
            out, n = self._cached_outbound(text, role)
            subs += n
            return out

        for _ in range(3):
            v0 = self.policy.version()
            out = walk_strings(body, fn)
            if self.policy.version() == v0:
                return out, subs
        return out, subs

    def content_leaks(self, body: Any) -> list[dict]:
        """Known private values still present in the transformed content strings, reported
        as the code they map to and where in the body they sit (never the value itself)."""
        found: dict[str, set] = {}

        def fn(text: str, _role: str | None, key: str | None) -> str:
            for v in self.policy.leaks(text):
                found.setdefault(v, set()).add(key or "?")
            return text

        walk_strings(body, fn)
        return [{"code": self.policy.code_for(v), "keys": sorted(k)} for v, k in found.items()]

    def restore_value(self, body: Any) -> tuple[Any, int]:
        restored = 0

        def fn(text: str, _role: str | None, _key: str | None) -> str:
            nonlocal restored
            out = self.policy.inbound(text)
            if out != text:
                restored += 1
            return out

        return walk_strings(body, fn), restored

    # ------------------------------------------------------------------ request handling
    def handle(self, h: BaseHTTPRequestHandler, method: str) -> None:
        rid = uuid.uuid4().hex[:8]
        t0 = time.monotonic()
        path = urlsplit(h.path).path
        entry: dict = {"id": rid, "method": method, "path": path, "t": time.time()}
        try:
            self._handle(h, method, path, rid, entry)
        except Exception as exc:  # noqa: BLE001
            if not isinstance(exc, (OSError, http.client.HTTPException)):
                traceback.print_exc()
            entry["status"] = 502
            entry["error"] = f"{type(exc).__name__}: {exc}"[:200]
            self._reply(h, 502, {"error": {"message": f"io proxy: {type(exc).__name__}: {exc}"[:300]}}, entry)
        finally:
            entry["ms"] = int((time.monotonic() - t0) * 1000)
            self.stats.record(entry)
            self.log(json.dumps(entry, default=str))

    def _reply(self, h, code: int, obj: dict, entry: dict) -> None:
        body = json.dumps(obj).encode()
        entry["status"] = code
        try:
            h.send_response(code)
            h.send_header("Content-Type", "application/json")
            h.send_header("Content-Length", str(len(body)))
            h.send_header("Connection", "close")
            h.end_headers()
            h.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _handle(self, h, method: str, path: str, rid: str, entry: dict) -> None:
        if (h.headers.get("Upgrade") or "").lower() == "websocket":
            entry["note"] = "websocket refused, codex falls back to sse"
            return self._reply(h, 426, {"error": {"message": "io proxy speaks HTTP SSE only"}}, entry)

        if not self.policy.ready():
            entry["note"] = "not ready"
            return self._reply(h, 403, {"error": {"message": f"io: {self.policy.not_ready_reason()}"}}, entry)

        raw = b""
        length = int(h.headers.get("Content-Length") or 0)
        if length:
            raw = h.rfile.read(length)
        elif (h.headers.get("Transfer-Encoding") or "").lower() == "chunked":
            raw = self._read_chunked(h.rfile)
        entry["bytes_in"] = len(raw)

        enc = (h.headers.get("Content-Encoding") or "").lower().strip()
        if enc and enc != "identity":
            if enc == "zstd":
                try:
                    import zstandard  # type: ignore
                    raw = zstandard.ZstdDecompressor().decompress(raw, max_output_size=64 << 20)
                except ImportError:
                    entry["note"] = "zstd body, no decoder"
                    return self._reply(h, 415, {"error": {"message": "io proxy cannot read zstd bodies; request compression must be off"}}, entry)
            elif enc == "gzip":
                import gzip
                raw = gzip.decompress(raw)
            else:
                entry["note"] = f"unsupported encoding {enc}"
                return self._reply(h, 415, {"error": {"message": f"io proxy cannot read {enc} bodies"}}, entry)

        upstream, kind = self.route(method, path)
        if kind == "refuse":
            entry["note"] = "path not allowed"
            return self._reply(h, 403, {"error": {"message": f"io proxy: {method} {path} is not an allowed Codex endpoint"}}, entry)

        headers = {k: v for k, v in h.headers.items()
                   if k.lower() not in ("host", "content-length", "transfer-encoding", "connection", "content-encoding", "accept-encoding")}
        headers["Accept-Encoding"] = "identity"
        entry["auth"] = "bearer" if (h.headers.get("Authorization") or "").lower().startswith("bearer ") else "none"

        body_out = raw
        if method in ("GET", "HEAD") and kind == "dev":
            kind = "pass"                   # a GET has no body to transform (the dev route's /models)
        if kind in ("content", "dev"):
            kind = "content"
            try:
                body = json.loads(raw.decode("utf-8")) if raw else None
            except (UnicodeDecodeError, json.JSONDecodeError):
                entry["note"] = "body is not json"
                return self._reply(h, 400, {"error": {"message": "io proxy: request body is not JSON"}}, entry)
            body, subs = self.transform_request(body)
            entry["subs"] = subs
            body_out = json.dumps(body, ensure_ascii=False).encode("utf-8")
            # The final check runs over what the transform produced: the content strings.
            # Protocol constants ("auto", "text", tool names) are not content, and a vault
            # that happens to hold the word "Auto" must not stop every request (seen live
            # 2026-09-14 with a 1,473-code CRM export).
            leaks = self.content_leaks(body)
            if leaks:
                entry["note"] = f"stopped: {len(leaks)} private value(s) still present"
                entry["leak_count"] = len(leaks)
                entry["leaks"] = leaks[:5]     # tokens and key paths only, never the values
                return self._reply(h, 403, {"error": {"message": f"io stopped this request: {len(leaks)} private value(s) were about to leave"}}, entry)
            self.dump(rid, "request", body_out)
        if method not in ("GET", "HEAD"):
            headers["Content-Length"] = str(len(body_out))
        entry["bytes_out"] = len(body_out)

        url = urlsplit(upstream)
        conn_cls = http.client.HTTPSConnection if url.scheme == "https" else http.client.HTTPConnection
        conn = conn_cls(url.hostname, url.port, timeout=600, **({"context": ssl.create_default_context()} if url.scheme == "https" else {}))
        pre = self._prefix_for(path)
        target = (url.path.rstrip("/") + path[len(pre):]) if pre else path
        q = urlsplit(h.path).query
        if q:
            target += "?" + q
        headers["Host"] = url.netloc
        conn.request(method, target, body=body_out if method not in ("GET", "HEAD") else None, headers=headers)
        resp = conn.getresponse()
        entry["status"] = resp.status
        entry["forwarded"] = True
        ctype = (resp.getheader("Content-Type") or "").lower()

        h.send_response(resp.status)
        for k, v in resp.getheaders():
            if k.lower() in ("content-length", "transfer-encoding", "connection", "content-encoding"):
                continue
            h.send_header(k, v)
        h.send_header("Connection", "close")

        if kind != "content" or resp.status >= 400 and "event-stream" not in ctype:
            data = resp.read()
            if kind == "content" and "json" in ctype:
                try:
                    obj, n = self.restore_value(json.loads(data.decode("utf-8")))
                    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
                    entry["restored"] = n
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass
            h.send_header("Content-Length", str(len(data)))
            h.end_headers()
            h.wfile.write(data)
            return

        if "event-stream" in ctype:
            h.end_headers()
            self.stream_sse(resp, h.wfile, rid, entry)
            return

        data = resp.read()
        if "json" in ctype:
            try:
                obj, n = self.restore_value(json.loads(data.decode("utf-8")))
                data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
                entry["restored"] = n
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass
        self.dump(rid, "response", data)
        h.send_header("Content-Length", str(len(data)))
        h.end_headers()
        h.wfile.write(data)

    def _prefix_for(self, path: str) -> str:
        for pre in self.dev_upstreams:
            if path.startswith(pre):
                return pre
        return ""

    def route(self, method: str, path: str) -> tuple[str, str]:
        """-> (upstream base, kind) where kind is content | pass | dev | refuse."""
        for pre, up in self.dev_upstreams.items():
            if path.startswith(pre):
                return up, "dev"
        if method == "POST" and path in CONTENT_POSTS:
            return self.upstream, "content"
        if path.startswith(PASS_PREFIXES):
            return self.upstream, "pass"
        return self.upstream, "refuse"

    @staticmethod
    def _read_chunked(rfile) -> bytes:
        out = bytearray()
        while True:
            line = rfile.readline().strip()
            if not line:
                continue
            n = int(line.split(b";")[0], 16)
            if n == 0:
                rfile.readline()
                break
            out += rfile.read(n)
            rfile.readline()
        return bytes(out)

    # ------------------------------------------------------------------ SSE
    def stream_sse(self, resp, wfile, rid: str, entry: dict) -> None:
        """Parse events, restore strings, forward each event as soon as it is complete."""
        restorers: dict[str, StreamRestorer] = {}
        last_delta: dict[str, dict] = {}
        events = 0
        restored = 0
        dump_parts: list[bytes] = []
        buf = b""

        def stream_key(ev: dict) -> str:
            return "|".join(str(ev.get(k, "")) for k in ("type", "item_id", "output_index", "content_index", "summary_index"))

        def emit(raw_block: bytes) -> None:
            try:
                wfile.write(raw_block)
                wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                raise

        def flush_held(exclude: str | None = None) -> None:
            nonlocal restored
            for k, r in list(restorers.items()):
                if k == exclude:
                    continue
                tail = r.flush()
                if tail:
                    ev = dict(last_delta[k])
                    ev["delta"] = tail
                    restored += 1
                    block = b"data: " + json.dumps(ev, ensure_ascii=False).encode("utf-8") + b"\n\n"
                    dump_parts.append(block)
                    emit(block)

        def handle_event(block: bytes) -> None:
            nonlocal events, restored
            events += 1
            lines = block.split(b"\n")
            data_lines = [ln[5:].lstrip() for ln in lines if ln.startswith(b"data:")]
            other = [ln for ln in lines if not ln.startswith(b"data:")]
            if not data_lines:
                emit(block + b"\n\n")
                return
            payload = b"\n".join(data_lines)
            try:
                ev = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                emit(block + b"\n\n")
                return
            if isinstance(ev, dict) and isinstance(ev.get("delta"), str):
                k = stream_key(ev)
                flush_held(exclude=k)
                r = restorers.get(k)
                if r is None:
                    r = restorers[k] = StreamRestorer(self.policy.inbound)
                last_delta[k] = ev
                text = r.feed(ev["delta"])
                if text != ev["delta"]:
                    restored += 1
                if not text:
                    return                      # everything is held; nothing to send yet
                ev = dict(ev)
                ev["delta"] = text
            else:
                flush_held()
                if isinstance(ev, dict) and ev.get("type", "").endswith((".done", ".completed", ".added")):
                    # a done event carries the full text; the per-stream restorer is finished
                    for k in [k for k in restorers if k.split("|", 1)[1] == stream_key(ev).split("|", 1)[1]]:
                        restorers.pop(k, None)
                ev, n = self.restore_value(ev)
                restored += n
            out = b"\n".join(other + [b"data: " + json.dumps(ev, ensure_ascii=False).encode("utf-8")]) + b"\n\n"
            dump_parts.append(payload + b"\n")
            emit(out)

        try:
            while True:
                chunk = resp.read1(65536) if hasattr(resp, "read1") else resp.read(4096)
                if not chunk:
                    break
                buf += chunk
                while True:
                    i = buf.find(b"\n\n")
                    if i < 0:
                        break
                    block, buf = buf[:i], buf[i + 2:]
                    block = block.replace(b"\r\n", b"\n")
                    if block.strip():
                        handle_event(block)
            if buf.strip():
                handle_event(buf.replace(b"\r\n", b"\n").strip())
            flush_held()
        except (BrokenPipeError, ConnectionResetError):
            entry["note"] = "client went away mid-stream"
        finally:
            entry["events"] = events
            entry["restored"] = restored
            self.dump(rid, "response", b"".join(dump_parts))

    # ------------------------------------------------------------------ evidence
    def dump(self, rid: str, which: str, data: bytes) -> None:
        """Tokenised bodies only: what left, and what came back before restoration."""
        if not self.dump_dir:
            return
        try:
            self.dump_dir.mkdir(parents=True, exist_ok=True)
            n = len(list(self.dump_dir.glob("*-request.*")))
            stem = f"{n:04d}-{rid}" if which == "request" else next((p.stem.rsplit("-", 1)[0] for p in self.dump_dir.glob(f"*-{rid}-request.*")), f"{n:04d}-{rid}")
            (self.dump_dir / f"{stem}-{which}.txt").write_bytes(data)
        except OSError:
            pass


# ---------------------------------------------------------------------- a self-contained policy
class MapPolicy(Policy):
    """Deterministic mapping for tests and spikes: {"Alice Example": "NAME_001", ...}."""

    def __init__(self, mapping: dict[str, str]) -> None:
        self.forward = dict(mapping)
        self.back = {t: v for v, t in mapping.items()}
        vals = sorted(self.forward, key=len, reverse=True)
        self.fre = re.compile(r"(?<![\w@.])(?:" + "|".join(re.escape(v) for v in vals) + r")(?![\w@])", re.I) if vals else None
        self.tre = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in self.back) + r")\b") if self.back else None
        self.cf = {v.casefold(): t for v, t in self.forward.items()}

    def outbound(self, text: str, role: str | None) -> str:
        return self.fre.sub(lambda m: self.cf[m.group(0).casefold()], text) if self.fre else text

    def inbound(self, text: str) -> str:
        return self.tre.sub(lambda m: self.back[m.group(0)], text) if self.tre else text

    def leaks(self, text: str) -> list[str]:
        return sorted({m.group(0) for m in self.fre.finditer(text)}) if self.fre else []

    def code_for(self, value: str) -> str:
        return self.cf.get(value.casefold(), "?")
