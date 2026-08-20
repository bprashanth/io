#!/usr/bin/env python3
"""Minimal streaming OpenRouter proxy for auditable reasoning-effort runs.

The proxy never logs headers, prompts, tool schemas, or response text. It may
inject only the documented OpenRouter `reasoning.effort` field, then records
request hashes, generation IDs, resolved model names and final usage metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


LOG_LOCK = threading.Lock()


def append_record(path: Path, record: dict[str, Any]) -> None:
    with LOG_LOCK, path.open("a") as handle:
        handle.write(json.dumps(record, separators=(",", ":")) + "\n")


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "io-openrouter-proxy/0.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def _forward(self) -> None:
        server = self.server
        assert isinstance(server, AuditProxyServer)
        started = time.time()
        request_body = b""
        forwarded_body: bytes | None = None
        request_meta: dict[str, Any] = {
            "time_unix": started,
            "method": self.command,
            "path": self.path,
            "reasoning_effort_injected": server.reasoning_effort,
        }
        try:
            if self.command in {"POST", "PUT", "PATCH"}:
                request_body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                document = json.loads(request_body) if request_body else {}
                request_meta.update(
                    requested_model=document.get("model"),
                    stream=document.get("stream"),
                    message_count=len(document.get("messages", [])),
                    tool_count=len(document.get("tools", [])),
                    incoming_reasoning=document.get("reasoning"),
                    request_sha256=hashlib.sha256(request_body).hexdigest(),
                )
                if server.reasoning_effort:
                    document["reasoning"] = {"effort": server.reasoning_effort}
                forwarded_body = json.dumps(document, separators=(",", ":")).encode()
                request_meta["forwarded_request_sha256"] = hashlib.sha256(
                    forwarded_body
                ).hexdigest()

            upstream_url = server.upstream.rstrip("/") + self.path
            allowed_headers = {
                "authorization",
                "content-type",
                "accept",
                "user-agent",
                "http-referer",
                "x-title",
            }
            headers = {
                key: value
                for key, value in self.headers.items()
                if key.lower() in allowed_headers
            }
            upstream_request = urllib.request.Request(
                upstream_url,
                data=forwarded_body,
                headers=headers,
                method=self.command,
            )
            with urllib.request.urlopen(upstream_request, timeout=server.timeout) as response:
                self.send_response(response.status)
                for key, value in response.headers.items():
                    if key.lower() not in {
                        "connection",
                        "content-length",
                        "content-encoding",
                        "transfer-encoding",
                    }:
                        self.send_header(key, value)
                self.send_header("Connection", "close")
                self.end_headers()

                buffer = b""
                generation_ids: set[str] = set()
                response_models: set[str] = set()
                providers: set[str] = set()
                final_usage: dict[str, Any] | None = None
                while True:
                    chunk = response.read1(16 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        line = line.strip()
                        if line.startswith(b"data:"):
                            payload = line[5:].strip()
                            if payload and payload != b"[DONE]":
                                try:
                                    event = json.loads(payload)
                                except json.JSONDecodeError:
                                    continue
                                if event.get("id"):
                                    generation_ids.add(str(event["id"]))
                                if event.get("model"):
                                    response_models.add(str(event["model"]))
                                if event.get("provider"):
                                    providers.add(str(event["provider"]))
                                if event.get("usage"):
                                    final_usage = event["usage"]
                request_meta.update(
                    status=response.status,
                    duration_seconds=round(time.time() - started, 3),
                    generation_ids=sorted(generation_ids),
                    response_models=sorted(response_models),
                    providers=sorted(providers),
                    usage=final_usage,
                )
        except urllib.error.HTTPError as error:
            payload = error.read()
            self.send_response(error.code)
            self.send_header("Content-Type", error.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(payload)
            request_meta.update(
                status=error.code,
                duration_seconds=round(time.time() - started, 3),
                error=f"HTTPError: {error.reason}",
            )
        except Exception as error:
            payload = json.dumps(
                {"error": {"message": f"benchmark proxy: {type(error).__name__}: {error}"}}
            ).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(payload)
            request_meta.update(
                status=502,
                duration_seconds=round(time.time() - started, 3),
                error=f"{type(error).__name__}: {error}",
            )
        finally:
            self.close_connection = True
            append_record(server.log_path, request_meta)

    do_GET = _forward
    do_POST = _forward
    do_PUT = _forward
    do_PATCH = _forward
    do_DELETE = _forward


class AuditProxyServer(ThreadingHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        handler: type[BaseHTTPRequestHandler],
        *,
        upstream: str,
        log_path: Path,
        reasoning_effort: str | None,
        timeout: float,
    ):
        super().__init__(address, handler)
        self.upstream = upstream
        self.log_path = log_path
        self.reasoning_effort = reasoning_effort
        self.timeout = timeout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument(
        "--upstream",
        default="https://openrouter.ai/api",
        help="upstream prefix; the incoming /v1 path is appended to this value",
    )
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--ready-file", type=Path)
    parser.add_argument("--reasoning-effort", choices=("low", "medium", "high", "xhigh"))
    parser.add_argument("--timeout", type=float, default=900)
    args = parser.parse_args()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    server = AuditProxyServer(
        (args.listen, args.port),
        ProxyHandler,
        upstream=args.upstream,
        log_path=args.log,
        reasoning_effort=args.reasoning_effort,
        timeout=args.timeout,
    )
    host, port = server.server_address
    if args.ready_file:
        args.ready_file.write_text(json.dumps({"host": host, "port": port}) + "\n")
    print(json.dumps({"host": host, "port": port}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
