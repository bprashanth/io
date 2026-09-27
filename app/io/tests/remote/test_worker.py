#!/usr/bin/env python3
"""Integration tests for the remote worker API and isolation semantics."""

from __future__ import annotations

import copy
import base64
import contextlib
import http.client
import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.parse
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
REMOTE_DIR = REPO_ROOT / "app" / "io" / "remote"
SESSION_SCRIPT = REMOTE_DIR / "session.py"
CONFORMANCE_SCRIPT = Path("/opt/remote/conformance.py")
IMAGE = "io-remote-codex:experiment"
REPORT_PATH = Path(os.environ.get("IO_REMOTE_EVIDENCE", str(REPO_ROOT / "benchmarks/runs/2026-09-27-remote-codex"))) / "api-isolation.json"

_MISSING = object()


def _run(cmd, *, input_text: str | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _checked(cmd, *, input_text: str | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    proc = _run(cmd, input_text=input_text, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {' '.join(map(str, cmd))}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
    return proc


def _compact_conformance(payload: dict) -> dict:
    def summarize(section: dict) -> dict:
        checks = list(section["checks"].values())
        return {
            "total": len(checks),
            "allowed": sum(1 for c in checks if c["outcome"] == "allowed"),
            "denied": sum(1 for c in checks if c["outcome"] == "denied"),
        }

    return {
        "ok": bool(payload.get("ok")),
        "control": summarize(payload["control"]),
        "sandbox": summarize(payload["sandbox"]),
        "controlAfter": summarize(payload["controlAfter"]),
    }


def _default_report() -> dict:
    return {
        "auth": {
            "unauthed_401": False,
            "other_session_token_401": False,
            "origin_rejected_401": False,
        },
        "startup": {
            "fresh_sessions_signed_out": False,
            "start_without_login_fails": False,
        },
        "files": {
            "csv_roundtrip": False,
            "duplicate_upload_blocked": False,
            "traversal_blocked": False,
            "symlink_blocked": False,
            "fifo_blocked": False,
            "nested_download_allowed": False,
        },
        "isolation": {
            "separate_networks": False,
            "b_reads_own_content": False,
            "a_cannot_read_b_only_path": False,
            "tcp_between_containers_denied": False,
            "writes_and_auth_are_session_scoped": False,
        },
        "sentinel": {
            "host_control_reads_it": False,
            "sandbox_cannot_read_it": False,
        },
        "lifecycle": {
            "api_end_refuses_followup": False,
            "restart_clears_files_and_login": False,
        },
        "conformance": {"a": None, "b": None},
    }


class RemoteSession:
    def __init__(self, label: str, connection_dir: Path):
        self.label = label
        self.connection_path = connection_dir / f"{label}.json"
        self.container = ""
        self.network = ""
        self.url = ""
        self.token = ""
        self.port = 0
        self._destroyed = False

    def create(self, ttl: int = 600) -> "RemoteSession":
        proc = _checked(
            [
                sys.executable,
                str(SESSION_SCRIPT),
                "create",
                "--connection",
                str(self.connection_path),
                "--image",
                IMAGE,
                "--ttl",
                str(ttl),
            ],
            timeout=240,
        )
        data = json.loads(self.connection_path.read_text("utf-8"))
        self.url = data["url"]
        self.token = data["token"]
        self.container = data["container"]
        self.network = data["network"]
        self.port = int(urllib.parse.urlsplit(self.url).port or 0)
        if not self.port:
            raise RuntimeError("Remote session did not expose a port")
        self.wait_ready()
        return self

    def destroy(self) -> None:
        if self._destroyed:
            return
        self._destroyed = True
        if self.connection_path.exists():
            proc = _run(
                [
                    sys.executable,
                    str(SESSION_SCRIPT),
                    "destroy",
                    "--connection",
                    str(self.connection_path),
                ],
                timeout=120,
            )
            if proc.returncode == 0:
                return
        if self.container:
            _run(["docker", "rm", "-f", self.container], timeout=60)
        if self.network:
            _run(["docker", "network", "rm", self.network], timeout=60)
        if self.connection_path.exists():
            with contextlib.suppress(Exception):
                self.connection_path.unlink()

    def request(
        self,
        method: str,
        path: str,
        *,
        body=None,
        headers: dict | None = None,
        token=_MISSING,
        origin: str | None = None,
        timeout: int = 10,
    ) -> tuple[int, dict[str, str], bytes]:
        if token is _MISSING:
            token = self.token
        request_headers: dict[str, str] = {}
        if token is not None:
            request_headers["Authorization"] = f"Bearer {token}"
        if origin is not None:
            request_headers["Origin"] = origin
        if headers:
            request_headers.update(headers)
        payload: bytes | None
        if isinstance(body, dict):
            payload = json.dumps(body).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        elif isinstance(body, bytes):
            payload = body
            request_headers.setdefault("Content-Type", "application/octet-stream")
        elif body is None:
            payload = None
        else:
            raise TypeError(f"Unsupported body type: {type(body)!r}")

        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=timeout)
        try:
            conn.request(method, path, body=payload, headers=request_headers)
            resp = conn.getresponse()
            raw = resp.read()
            return resp.status, dict(resp.getheaders()), raw
        finally:
            conn.close()

    def request_json(self, method: str, path: str, **kwargs):
        status, headers, raw = self.request(method, path, **kwargs)
        payload = json.loads(raw.decode("utf-8")) if raw else {}
        return status, headers, payload

    def exec(self, *args: str, timeout: int = 120) -> subprocess.CompletedProcess:
        return _run(["docker", "exec", self.container, *args], timeout=timeout)

    def exec_python(self, source: str, *argv: str, timeout: int = 120) -> subprocess.CompletedProcess:
        return _run(["docker", "exec", "-i", self.container, "python3", "-", *argv], input_text=source, timeout=timeout)

    def container_ip(self) -> str:
        proc = _checked(["docker", "inspect", self.container], timeout=120)
        info = json.loads(proc.stdout)[0]
        networks = info["NetworkSettings"]["Networks"] or {}
        for net in networks.values():
            ip = net.get("IPAddress")
            if ip:
                return ip
        raise RuntimeError(f"No container IP found for {self.container}")

    def wait_ready(self, timeout: int = 180) -> dict:
        deadline = time.monotonic() + timeout
        last_error = None
        while time.monotonic() < deadline:
            try:
                status, _, payload = self.request_json("GET", "/status", timeout=5)
                if status == 200 and payload.get("loggedIn") is False:
                    return payload
                last_error = f"status={status} payload={payload!r}"
            except Exception as exc:  # pragma: no cover - exercised in live integration
                last_error = repr(exc)
            time.sleep(0.5)
        raise RuntimeError(f"Remote worker never became ready: {last_error}")

    def wait_gone(self, timeout: int = 60) -> None:
        deadline = time.monotonic() + timeout
        last_error = None
        while time.monotonic() < deadline:
            try:
                status, _, _ = self.request_json("GET", "/status", timeout=3)
                last_error = f"still reachable with status {status}"
            except (ConnectionRefusedError, ConnectionResetError, TimeoutError, OSError):
                if _run(['docker', 'inspect', self.container]).returncode != 0:
                    return
            time.sleep(0.5)
        raise RuntimeError(f"Remote worker stayed reachable after /end: {last_error}")

    def restart(self, timeout: int = 120) -> dict:
        original_port = self.port
        _checked(["docker", "restart", self.container], timeout=timeout)
        mapping = _checked(["docker", "port", self.container, "8787/tcp"]).stdout.strip()
        if int(mapping.rsplit(":", 1)[1]) != original_port:
            raise AssertionError("Restart changed the client endpoint")
        return self.wait_ready(timeout=timeout)


class RemoteWorkerIntegrationTests(unittest.TestCase):
    report = _default_report()
    conformance = {"a": None, "b": None}

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="io-remote-worker-tests-")
        cls.addClassCleanup(cls._tmp.cleanup)
        cls.a = RemoteSession("a", Path(cls._tmp.name))
        cls.addClassCleanup(cls.a.destroy)
        cls.a.create()
        cls.b = RemoteSession("b", Path(cls._tmp.name))
        cls.addClassCleanup(cls.b.destroy)
        cls.b.create()

    def _mark(self, *keys: str) -> None:
        target = self.__class__.report
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = True

    def test_10_auth_rejects_missing_origin_and_other_session_token(self) -> None:
        for session in (self.a, self.b):
            status, _, payload = session.request_json("GET", "/status", token=None)
            self.assertEqual(status, 401)
            self.assertEqual(payload["error"], "Unauthorized")
        self._mark("auth", "unauthed_401")

        status, _, payload = self.a.request_json("GET", "/status", token=self.b.token)
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"], "Unauthorized")
        status, _, payload = self.b.request_json("GET", "/status", token=self.a.token)
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"], "Unauthorized")
        self._mark("auth", "other_session_token_401")

        status, _, payload = self.a.request_json("GET", "/status", origin="https://example.invalid")
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"], "Unauthorized")
        self._mark("auth", "origin_rejected_401")

    def test_20_fresh_sessions_are_signed_out_and_start_without_login_fails(self) -> None:
        for session in (self.a, self.b):
            status, _, payload = session.request_json("GET", "/status")
            self.assertEqual(status, 200)
            self.assertFalse(payload["loggedIn"])
            self.assertFalse(payload["running"])
            self.assertIsNone(payload["mode"])
            start_status, _, start_payload = session.request_json(
                "POST",
                "/start",
                body={"cols": 80, "rows": 24},
            )
            self.assertEqual(start_status, 400)
            self.assertEqual(start_payload["error"], "Sign in with ChatGPT first")
        self._mark("startup", "fresh_sessions_signed_out")
        self._mark("startup", "start_without_login_fails")

    def test_25_browser_oauth_is_default_and_session_scoped(self) -> None:
        code, _, reply = self.a.request_json('POST', '/login', body={})
        self.assertEqual(code, 200)
        url = urllib.parse.urlsplit(reply['authUrl'])
        query = urllib.parse.parse_qs(url.query)
        self.assertEqual((url.scheme, url.netloc, url.path), ('https', 'auth.openai.com', '/oauth/authorize'))
        self.assertEqual(query['redirect_uri'], ['http://localhost:1455/auth/callback'])
        self.assertEqual(query['code_challenge_method'], ['S256'])
        state = query['state'][0]
        self.assertGreaterEqual(len(state), 16)
        try:
            for callback in ['/auth/callback?code=fixture&state=wrong',
                             'http://other.invalid/auth/callback?code=fixture&state=' + state,
                             '/auth/callback?code=fixture&state=' + state + '&state=duplicate',
                             '/status?code=fixture&state=' + state]:
                code, _, _ = self.a.request_json('POST', '/login/callback', body={'callback':callback})
                self.assertEqual(code, 400)
            callback = '/auth/callback?code=fixture&state=' + state
            code, _, _ = self.b.request_json('POST', '/login/callback', body={'callback':callback})
            self.assertEqual(code, 400)
            code, _, current = self.a.request_json('GET', '/status')
            self.assertFalse(current['loggedIn'])
            self.assertEqual(current['mode'], 'login')
        finally:
            self.a.request_json('POST', '/stop', body={})
        code, _, _ = self.a.request_json('POST', '/login/callback', body={'callback':callback})
        self.assertEqual(code, 400)

    def test_30_csv_upload_download_and_duplicate_reuse_original(self) -> None:
        name = f"sample-{secrets.token_hex(4)}.csv"
        original = b"name,value\nalpha,1\n"
        replacement = b"name,value\nomega,9\n"
        upload_status, _, upload_payload = self.a.request_json(
            "POST",
            f"/files?name={urllib.parse.quote(name, safe='/')}",
            body=original,
        )
        self.assertEqual(upload_status, 201)
        self.assertEqual(upload_payload["name"], name)
        self.assertEqual(upload_payload["size"], len(original))

        download_status, _, download_raw = self.a.request("GET", f"/file?name={urllib.parse.quote(name, safe='/')}")
        self.assertEqual(download_status, 200)
        self.assertEqual(download_raw, original)

        retry_status, _, retry_payload = self.a.request_json('POST', f'/files?name={name}', body=original)
        self.assertEqual(retry_status, 200)
        self.assertTrue(retry_payload['reused'])

        dup_status, _, dup_payload = self.a.request_json(
            "POST",
            f"/files?name={urllib.parse.quote(name, safe='/')}",
            body=replacement,
        )
        self.assertEqual(dup_status, 400)
        self.assertIn("existing file was not changed", dup_payload["error"])

        still_status, _, still_raw = self.a.request("GET", f"/file?name={urllib.parse.quote(name, safe='/')}")
        self.assertEqual(still_status, 200)
        self.assertEqual(still_raw, original)
        self._mark("files", "csv_roundtrip")
        self._mark("files", "duplicate_upload_blocked")

        traversal_name = "/state/sentinel"
        trav_upload_status, _, trav_upload_payload = self.a.request_json(
            "POST",
            f"/files?name={urllib.parse.quote(traversal_name, safe='/')}",
            body=b"bad",
        )
        self.assertEqual(trav_upload_status, 400)
        self.assertIn("simple filename", trav_upload_payload["error"])
        trav_download_status, _, trav_download_payload = self.a.request_json(
            "GET",
            f"/file?name={urllib.parse.quote(traversal_name, safe='/')}",
        )
        self.assertEqual(trav_download_status, 400)
        self.assertTrue(
            "Invalid result path" in trav_download_payload["error"]
            or "request failed" in trav_download_payload["error"]
        )
        self._mark("files", "traversal_blocked")

    def test_35_binary_image_upload_and_identical_retry(self) -> None:
        image = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aB9kAAAAASUVORK5CYII=')
        name = urllib.parse.quote('Synthetic photo ü.png')
        code, _, first = self.a.request_json('POST', '/files?name='+name, body=image)
        self.assertEqual(code, 201)
        code, _, retry = self.a.request_json('POST', '/files?name='+name, body=image)
        self.assertEqual(code, 200)
        self.assertTrue(retry['reused'])
        code, _, copied = self.a.request('GET', '/file?name='+name)
        self.assertEqual(code, 200)
        self.assertEqual(copied, image)

    def test_40_traversal_symlink_fifo_and_nested_download_rules(self) -> None:
        setup = """
from pathlib import Path
import os

root = Path('/workspace')
(root / 'nested' / 'dir').mkdir(parents=True, exist_ok=True)
(root / 'nested' / 'dir' / 'result.txt').write_text('nested-ok\\n')

state = Path('/state')
state.mkdir(parents=True, exist_ok=True)
(state / 'sentinel').write_text('sentinel-target\\n')

for entry in (root / 'testsymlink', root / 'testfifo'):
    try:
        if entry.exists() or entry.is_symlink():
            entry.unlink()
    except FileNotFoundError:
        pass

(root / 'testsymlink').symlink_to('/state/sentinel')
os.mkfifo(root / 'testfifo')
"""
        proc = self.a.exec_python(setup, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)

        symlink_download_status, _, symlink_download_payload = self.a.request_json(
            "GET",
            "/file?name=testsymlink",
        )
        self.assertEqual(symlink_download_status, 400)
        self.assertTrue("request failed" in symlink_download_payload["error"])

        symlink_upload_status, _, symlink_upload_payload = self.a.request_json(
            "POST",
            "/files?name=testsymlink",
            body=b"blocked",
        )
        self.assertEqual(symlink_upload_status, 400)
        self.assertIn("existing file was not changed", symlink_upload_payload["error"])
        self._mark("files", "symlink_blocked")

        begin = time.monotonic()
        fifo_status, _, fifo_payload = self.a.request_json("GET", "/file?name=testfifo", timeout=5)
        elapsed = time.monotonic() - begin
        self.assertLess(elapsed, 5.0)
        self.assertEqual(fifo_status, 400)
        self.assertTrue(
            "Only regular files up to 10 MiB can be downloaded" in fifo_payload["error"]
            or "request failed" in fifo_payload["error"]
        )
        self._mark("files", "fifo_blocked")

        nested_status, _, nested_raw = self.a.request("GET", "/file?name=nested/dir/result.txt")
        self.assertEqual(nested_status, 200)
        self.assertEqual(nested_raw, b"nested-ok\n")
        self._mark("files", "nested_download_allowed")

    def test_50_two_session_isolation_and_tcp_denial(self) -> None:
        self.assertNotEqual(self.a.network, self.b.network)
        self._mark("isolation", "separate_networks")

        name = f"b-only-{secrets.token_hex(4)}.txt"
        content = f"b-session:{secrets.token_hex(8)}\n"
        create_script = f"""
from pathlib import Path
p = Path('/workspace/{name}')
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text({content!r})
print(p.read_text().strip())
"""
        proc = self.b.exec_python(create_script, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), content.strip())

        b_status, _, b_raw = self.b.request("GET", f"/file?name={urllib.parse.quote(name, safe='/')}")
        self.assertEqual(b_status, 200)
        self.assertEqual(b_raw.decode("utf-8"), content)
        self._mark("isolation", "b_reads_own_content")

        a_status, _, a_payload = self.a.request_json("GET", f"/file?name={urllib.parse.quote(name, safe='/')}")
        self.assertEqual(a_status, 400)
        self.assertIn("request failed", a_payload["error"])
        self._mark("isolation", "a_cannot_read_b_only_path")

        b_ip = self.b.container_ip()
        tcp_probe = """
import socket
import sys

ip = sys.argv[1]
port = int(sys.argv[2])

sock = socket.socket()
sock.settimeout(1.5)
try:
    sock.connect((ip, port))
except OSError:
    print('denied')
else:
    raise SystemExit(1)
finally:
    sock.close()
"""
        net_proc = self.a.exec_python(tcp_probe, b_ip, "8787", timeout=30)
        self.assertEqual(net_proc.returncode, 0, net_proc.stderr)
        self.assertEqual(net_proc.stdout.strip(), "denied")
        self._mark("isolation", "tcp_between_containers_denied")

    def test_55_session_writes_and_auth_are_separate(self) -> None:
        name = 'b-only-' + secrets.token_hex(5)
        paths = ['/workspace/' + name, '/state/codex/' + name]
        for target in paths:
            made = self.b.exec_python("from pathlib import Path; p=Path("+repr(target)+"); p.write_text('B sentinel'); print(p.read_text())")
            self.assertEqual(made.returncode, 0, made.stderr)
            self.assertEqual(made.stdout.strip(), 'B sentinel')
            isolated = self.a.exec_python("from pathlib import Path; p=Path("+repr(target)+"); assert not p.exists(); p.write_text('A copy'); print(p.read_text())")
            self.assertEqual(isolated.returncode, 0, isolated.stderr)
            self.assertEqual(isolated.stdout.strip(), 'A copy')
            unchanged = self.b.exec_python("from pathlib import Path; print(Path("+repr(target)+").read_text())")
            self.assertEqual(unchanged.returncode, 0, unchanged.stderr)
            self.assertEqual(unchanged.stdout.strip(), 'B sentinel')
        self._mark('isolation', 'writes_and_auth_are_session_scoped')

    def test_60_auth_sentinel_is_visible_to_host_but_not_sandbox(self) -> None:
        sentinel = f"auth-sentinel-{secrets.token_hex(8)}"
        host_script = f"""
from pathlib import Path

sentinel = Path('/state/codex/test-auth-sentinel')
sentinel.parent.mkdir(parents=True, exist_ok=True)
sentinel.write_text({sentinel!r})
print(sentinel.read_text().strip())
"""
        host_proc = self.a.exec_python(host_script, timeout=60)
        self.assertEqual(host_proc.returncode, 0, host_proc.stderr)
        self.assertEqual(host_proc.stdout.strip(), sentinel)
        self._mark("sentinel", "host_control_reads_it")

        sandbox_script = """
from pathlib import Path
p = Path('/state/codex/test-auth-sentinel')
try:
    data = p.read_text().strip()
except Exception as exc:
    print('DENIED:' + type(exc).__name__)
else:
    print('READ:' + data)
    raise SystemExit(1)
"""
        sandbox_proc = self.a.exec_python(
            f"""
import subprocess

cmd = [
    '/opt/codex/bin/codex',
    'sandbox',
    '-p',
    'io',
    '-P',
    'io',
    '-C',
    '/workspace',
    '--',
    'python3',
    '-c',
    {sandbox_script!r},
]
proc = subprocess.run(cmd, capture_output=True, text=True)
print(proc.returncode)
print(proc.stdout.strip())
print(proc.stderr.strip())
""",
            timeout=180,
        )
        self.assertEqual(sandbox_proc.returncode, 0, sandbox_proc.stderr)
        lines = sandbox_proc.stdout.splitlines()
        self.assertGreaterEqual(len(lines), 2)
        self.assertEqual(lines[0].strip(), "0")
        self.assertTrue(lines[1].startswith("DENIED:"), sandbox_proc.stdout)
        self.assertNotIn("READ:", sandbox_proc.stdout)
        self._mark("sentinel", "sandbox_cannot_read_it")

    def test_70_conformance_probe_runs_in_both_containers(self) -> None:
        for label, session in (("a", self.a), ("b", self.b)):
            proc = session.exec("python3", str(CONFORMANCE_SCRIPT), timeout=240)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            compact = _compact_conformance(payload)
            self.__class__.conformance[label] = compact
            self.assertTrue(compact["ok"], compact)
            self.assertEqual(compact["controlAfter"]["allowed"], 13)
            self.assertGreater(compact["control"]["total"], 0)
            self.assertGreater(compact["sandbox"]["total"], 0)

    def test_80_logout_preserves_endpoint_and_files(self) -> None:
        # Explicitly fake cached credentials; no model call or real OAuth is made.
        fixture = (REPO_ROOT / 'benchmarks/runs/2026-09-14-io-codex/fixtures/auth-fixture.json').read_text()
        setup = self.a.exec_python("from pathlib import Path; Path('/state/codex/auth.json').write_text(" + repr(fixture) + "); Path('/workspace/logout-keep.txt').write_text('keep'); Path('/state/codex/sessions').mkdir(exist_ok=True); Path('/state/codex/sessions/old.jsonl').write_text('synthetic chat')")
        self.assertEqual(setup.returncode, 0, setup.stderr)
        _, _, before = self.a.request_json('GET', '/status')
        self.assertTrue(before['loggedIn'], 'fixture exercises cached ChatGPT login detection only')
        code, _, result = self.a.request_json('POST', '/logout', body={})
        self.assertEqual(code, 200, result)
        _, _, after = self.a.request_json('GET', '/status')
        self.assertFalse(after['loggedIn'])
        self.assertEqual(after['instance'], before['instance'])
        self.assertFalse(after['hasConversation'])
        check = self.a.exec_python("from pathlib import Path; assert not Path('/state/codex/auth.json').exists(); assert Path('/workspace/logout-keep.txt').read_text() == 'keep'")
        self.assertEqual(check.returncode, 0, check.stderr)

    def test_90_end_via_api_stops_worker_and_refuses_followup_requests(self) -> None:
        status, _, payload = self.b.request_json("POST", "/end", body={})
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.b.wait_gone()
        self._mark("lifecycle", "api_end_refuses_followup")

    def test_95_restore_deleted_workspace_keeps_private_connection(self) -> None:
        old_token, old_port = self.b.token, self.b.port
        _checked([sys.executable, str(SESSION_SCRIPT), 'restore', '--connection', str(self.b.connection_path), '--ttl', '600'])
        data = json.loads(self.b.connection_path.read_text())
        self.b.container, self.b.network = data['container'], data['network']
        self.assertEqual(data['token'], old_token)
        self.assertEqual(int(urllib.parse.urlsplit(data['url']).port), old_port)
        fresh = self.b.wait_ready()
        self.assertFalse(fresh['loggedIn'])
        code, _, listing = self.b.request_json('GET', '/files')
        self.assertEqual(code, 200)
        self.assertEqual(listing['files'], [])
        refused = _run([sys.executable, str(SESSION_SCRIPT), 'restore', '--connection', str(self.b.connection_path)])
        self.assertNotEqual(refused.returncode, 0, 'must not replace an existing workspace')

    def test_99_restart_clears_files_and_login_state(self) -> None:
        name = f"restart-{secrets.token_hex(4)}.txt"
        content = f"restart-{secrets.token_hex(8)}\n".encode("utf-8")
        upload_status, _, upload_payload = self.a.request_json(
            "POST",
            f"/files?name={urllib.parse.quote(name, safe='/')}",
            body=content,
        )
        self.assertEqual(upload_status, 201)
        self.assertEqual(upload_payload["name"], name)

        status = self.a.restart(timeout=420)
        self.assertEqual(status["loggedIn"], False)
        self.assertEqual(status["running"], False)
        self.assertIsNone(status["mode"])
        self.assertFalse(status["ended"])

        missing_status, _, missing_payload = self.a.request_json("GET", f"/file?name={urllib.parse.quote(name, safe='/')}")
        self.assertEqual(missing_status, 400)
        self.assertIn("request failed", missing_payload["error"])
        self._mark("lifecycle", "restart_clears_files_and_login")


def write_report(result: unittest.result.TestResult) -> None:
    payload = {
        "ok": result.wasSuccessful(),
        "image": IMAGE,
        "tests": {
            "run": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
        },
        "checks": copy.deepcopy(RemoteWorkerIntegrationTests.report),
        "conformance": copy.deepcopy(RemoteWorkerIntegrationTests.conformance),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RemoteWorkerIntegrationTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    try:
        write_report(result)
    except Exception as exc:  # pragma: no cover - only on benchmark export failure
        print(f"failed to write report: {exc}", file=sys.stderr)
        return 1
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
