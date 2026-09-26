#!/usr/bin/env python3
"""Integration tests for chat workspaces and file attachment handling."""

from __future__ import annotations

import atexit
import http.client
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path


TMP = tempfile.TemporaryDirectory(prefix="io-attachments-")
atexit.register(TMP.cleanup)

HOME = Path(TMP.name) / "io-home"
HOME.mkdir(parents=True, exist_ok=True)
os.environ["IO_HOME"] = str(HOME)
os.environ["IO_SCANNER"] = "regex"
os.environ["IO_SHELL_TOKEN"] = "synthetic-io-shell-token"


import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import service  # noqa: E402


SHELL_TOKEN = os.environ["IO_SHELL_TOKEN"]


class AttachmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), service.H)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self) -> None:
        for path in (service.DECISIONS_PATH, service.FOLDERS_PATH, service.CHAT_PRIVACY_PATH):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        service.S = service.State()

    def _request(self, path: str, body: dict | None = None, headers: dict | None = None, method: str = "POST"):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        payload = json.dumps(body or {}).encode()
        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)
        conn.request(method, path, body=payload if method != "GET" else None, headers=req_headers)
        resp = conn.getresponse()
        raw = resp.read()
        conn.close()
        return resp.status, json.loads(raw or b"{}")

    def _make_source(self, name: str, text: str, *, mtime: int = 1_700_000_000, root_name: str = "src") -> Path:
        root = Path(TMP.name) / root_name
        root.mkdir(parents=True, exist_ok=True)
        path = root / name
        path.write_text(text)
        os.utime(path, (mtime, mtime))
        return path

    def _start_chat_workspace(self) -> Path:
        status, payload = self._request("/api/chat-workspace")
        self.assertEqual(status, 200, payload)
        ws = Path(payload["folder"])
        self.assertTrue(ws.is_dir(), ws)
        return ws

    def _attach(self, src: Path, *, private: bool = False, token: str | None = None):
        headers = {}
        if token is not None:
            headers["X-IO-Shell"] = token
        status, payload = self._request("/api/attach", {"path": str(src), "private": private}, headers=headers)
        return status, payload

    def _codex_state(self) -> dict:
        status, payload = self._request("/api/codex", method="GET")
        self.assertEqual(status, 200, payload)
        return payload

    def test_attach_requires_shell_token_and_private_flag_persists(self) -> None:
        ws = self._start_chat_workspace()
        self.assertEqual(service.S.folder, ws)
        self.assertTrue(self._codex_state()["ready"])

        src_private = self._make_source("private.csv", "value\nalpha\n")
        status, payload = self._attach(src_private)
        self.assertEqual(status, 403)
        self.assertIn("attach a file", payload["error"])

        status, payload = self._attach(src_private, token=SHELL_TOKEN, private=True)
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["attached"], "private.csv")
        self.assertTrue(service.private_chat())
        codex = self._codex_state()
        self.assertFalse(codex["ready"])
        self.assertTrue(codex["private_chat"])

        src_public = self._make_source("public.csv", "value\nomega\n")
        status, payload = self._attach(src_public, token=SHELL_TOKEN, private=False)
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["attached"], "public.csv")
        self.assertTrue(service.private_chat())
        codex = self._codex_state()
        self.assertFalse(codex["ready"])
        self.assertTrue(codex["private_chat"])

    def test_same_name_same_size_same_timestamp_replacement_forces_rescan(self) -> None:
        ws = self._start_chat_workspace()
        src_v1 = self._make_source("sample.csv", "value\nalpha\n", mtime=1_700_000_100, root_name="src-v1")
        status, payload = self._attach(src_v1, token=SHELL_TOKEN)
        self.assertEqual(status, 200, payload)
        self.assertEqual(service.S.tables[0]["frame"].iloc[0, 0], "alpha")
        self.assertFalse(service.S.accepted)
        self.assertFalse(self._codex_state()["ready"])

        status, accepted = self._request("/api/accept")
        self.assertEqual(status, 200, accepted)
        self.assertTrue(self._codex_state()["ready"])

        src_v2 = self._make_source("sample.csv", "value\nomega\n", mtime=1_700_000_100, root_name="src-v2")
        self.assertEqual(src_v1.stat().st_size, src_v2.stat().st_size)
        self.assertEqual(int(src_v1.stat().st_mtime), int(src_v2.stat().st_mtime))

        status, payload = self._attach(src_v2, token=SHELL_TOKEN)
        self.assertEqual(status, 200, payload)
        self.assertEqual(service.S.folder, ws)
        self.assertEqual(service.S.tables[0]["frame"].iloc[0, 0], "omega")
        self.assertFalse(service.S.accepted)
        codex = self._codex_state()
        self.assertFalse(codex["ready"])
        self.assertFalse(codex["private_chat"])

    def test_corrupted_chat_privacy_json_keeps_private_mode_true(self) -> None:
        service.CHAT_PRIVACY_PATH.write_text("{")
        ws = self._start_chat_workspace()
        self.assertTrue(service.private_chat())
        self.assertTrue(self._codex_state()["private_chat"])

        src = self._make_source("corrupt.csv", "value\nalpha\n")
        status, payload = self._attach(src, token=SHELL_TOKEN, private=True)
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["attached"], "corrupt.csv")
        self.assertTrue(service.private_chat())
        saved = json.loads(service.CHAT_PRIVACY_PATH.read_text())
        self.assertTrue(saved[str(ws)])


if __name__ == "__main__":
    unittest.main(verbosity=1)
