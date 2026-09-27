from __future__ import annotations

import contextlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient


GATEWAY_DIR = Path(__file__).resolve().parents[2] / "gateway"
if str(GATEWAY_DIR) not in sys.path:
    sys.path.insert(0, str(GATEWAY_DIR))

import server as gateway_server  # noqa: E402
from identity import AccessIdentity  # noqa: E402
from store import Store  # noqa: E402


ISSUER = "https://team.cloudflareaccess.com"
AUDIENCE = "io-gateway-test"


@dataclass
class Harness:
    private_key: rsa.RSAPrivateKey
    public_key: rsa.RSAPublicKey
    store: Store
    runtime: "FakeDockerRuntime"
    identity: AccessIdentity
    app: object


class FakeDockerRuntime:
    def __init__(self, endpoint_url: str = "http://worker.internal:8787"):
        self.endpoint_url = endpoint_url
        self.ensure_calls: list[dict] = []
        self.endpoint_calls: list[dict] = []
        self.delete_calls: list[dict] = []

    def ensure(self, workspace):
        self.ensure_calls.append(dict(workspace))

    def endpoint(self, workspace):
        self.endpoint_calls.append(dict(workspace))
        return self.endpoint_url

    def delete(self, workspace):
        self.delete_calls.append(dict(workspace))


class FakeAsyncResponse:
    def __init__(self, status_code: int = 200, body: bytes = b"ok", headers: dict | None = None):
        self.status_code = status_code
        self._body = body
        self.headers = headers or {"content-type": "text/plain; charset=utf-8"}
        self.closed = False

    async def aiter_bytes(self):
        yield self._body

    async def aclose(self):
        self.closed = True


class FakeAsyncClient:
    instances: list["FakeAsyncClient"] = []

    def __init__(self, *args, response: FakeAsyncResponse | None = None, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.response = response or FakeAsyncResponse()
        self.requests: list[SimpleNamespace] = []
        self.closed = False
        FakeAsyncClient.instances.append(self)

    def build_request(self, method, target, content=None, headers=None):
        request = SimpleNamespace(method=method, url=target, content=content, headers=headers or {})
        self.requests.append(request)
        return request

    async def send(self, request, stream=False):
        self.sent_request = request
        self.stream = stream
        return self.response

    async def aclose(self):
        self.closed = True


def mint_token(
    private_key: rsa.RSAPrivateKey,
    *,
    issuer: str = ISSUER,
    audience: str = AUDIENCE,
    subject: str = "user-1",
    email: str = "User@Example.com",
    expires_in: int = 3600,
    issued_at: int | None = None,
) -> str:
    now = int(time.time())
    iat = now if issued_at is None else issued_at
    payload = {
        "iss": issuer,
        "aud": audience,
        "sub": subject,
        "email": email,
        "type": "app",
        "iat": iat,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def auth_headers(token: str | None = None, **extra: str) -> dict[str, str]:
    headers = {}
    if token is not None:
        headers["cf-access-jwt-assertion"] = token
    headers.update(extra)
    return headers


@pytest.fixture(scope="module")
def rsa_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


@pytest.fixture
def harness(tmp_path, rsa_pair):
    private_key, public_key = rsa_pair
    store = Store(tmp_path / "gateway.sqlite3")
    runtime = FakeDockerRuntime()
    identity = AccessIdentity(ISSUER, AUDIENCE, keys=lambda token: public_key)
    app = gateway_server.create_app(store, identity, runtime)
    value = Harness(private_key=private_key, public_key=public_key, store=store, runtime=runtime, identity=identity, app=app)
    yield value
    with contextlib.suppress(Exception):
        store.db.close()


def test_identity_verification_rejects_missing_forged_wrong_issuer_aud_and_expired(harness):
    forged_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cases = [
        ("missing", None),
        ("forged", mint_token(forged_private, subject="user-1", email="user@example.com")),
        ("wrong issuer", mint_token(harness.private_key, issuer="https://other.cloudflareaccess.com")),
        ("wrong audience", mint_token(harness.private_key, audience="wrong-audience")),
        ("expired", mint_token(harness.private_key, expires_in=-5)),
    ]
    with TestClient(harness.app) as client:
        for _, token in cases:
            response = client.get("/identity", headers=auth_headers(token))
            assert response.status_code == 401
            assert response.json() == {"error": "Cloudflare Access sign-in required"}

        response = client.get("/identity")
        assert response.status_code == 401


def test_email_header_is_not_trusted_and_identity_is_normalized(harness):
    token = mint_token(harness.private_key, email="  Alice@Example.COM  ", subject="sub-1")
    with TestClient(harness.app) as client:
        response = client.get("/identity", headers=auth_headers(token, email="attacker@example.invalid"))
        assert response.status_code == 200
        assert response.json() == {"email": "alice@example.com", "executionMode": "remote"}

        workspace = client.post("/workspace", headers=auth_headers(token, email="attacker@example.invalid"))
        assert workspace.status_code == 200
        assert workspace.json()["workspaceId"].startswith("workspace_")

    row = harness.store.db.execute("SELECT email FROM workspaces WHERE subject=?", ("sub-1",)).fetchone()
    assert row["email"] == "alice@example.com"


def test_same_user_gets_one_workspace_even_when_email_changes_and_sqlite_reopen_persists(tmp_path, rsa_pair):
    private_key, public_key = rsa_pair
    db_path = tmp_path / "gateway.sqlite3"
    runtime = FakeDockerRuntime()
    identity = AccessIdentity(ISSUER, AUDIENCE, keys=lambda token: public_key)

    first_store = Store(db_path)
    first_app = gateway_server.create_app(first_store, identity, runtime)
    first_token = mint_token(private_key, email="First@Example.com", subject="same-user")
    with TestClient(first_app) as client:
        response = client.post("/workspace", headers=auth_headers(first_token, email="spoofed@evil.invalid"))
        assert response.status_code == 200
        first_workspace = response.json()["workspaceId"]
    first_store.db.close()

    # Reopen SQLite from disk and confirm the existing mapping is reused even after the email changes.
    reopened_store = Store(db_path)
    second_app = gateway_server.create_app(reopened_store, identity, runtime)
    second_token = mint_token(private_key, email="Second@Example.net", subject="same-user")
    with TestClient(second_app) as client:
        response = client.post("/workspace", headers=auth_headers(second_token))
        assert response.status_code == 200
        assert response.json()["workspaceId"] == first_workspace

    rows = reopened_store.db.execute("SELECT id, email FROM workspaces WHERE subject=?", ("same-user",)).fetchall()
    assert len(rows) == 1
    assert rows[0]["id"] == first_workspace
    assert rows[0]["email"] == "first@example.com"


def test_concurrent_same_user_creates_one_mapping(harness):
    token = mint_token(harness.private_key, email="Concurrent@Example.com", subject="concurrent-user")
    with TestClient(harness.app) as client:
        start = threading.Barrier(3)

        def hit_workspace():
            start.wait()
            return client.post("/workspace", headers=auth_headers(token))

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(hit_workspace) for _ in range(2)]
            start.wait()
            results = [future.result(timeout=15) for future in futures]

    assert len(results) == 2
    assert all(response.status_code == 200 for response in results)
    workspace_ids = {response.json()["workspaceId"] for response in results}
    assert len(workspace_ids) == 1
    rows = harness.store.db.execute(
        "SELECT COUNT(*) AS count FROM workspaces WHERE subject=?",
        ("concurrent-user",),
    ).fetchone()
    assert rows["count"] == 1


def test_other_identity_cannot_access_delete_or_proxy_guessed_workspace(harness):
    owner_token = mint_token(harness.private_key, subject="owner", email="owner@example.com")
    intruder_token = mint_token(harness.private_key, subject="intruder", email="intruder@example.com")

    with TestClient(harness.app) as client:
        workspace = client.post("/workspace", headers=auth_headers(owner_token))
        assert workspace.status_code == 200
        workspace_id = workspace.json()["workspaceId"]

        for method, path in [
            ("get", f"/workspaces/{workspace_id}/status"),
            ("post", f"/workspaces/{workspace_id}/end"),
            ("get", f"/workspaces/{workspace_id}/files"),
        ]:
            response = getattr(client, method)(path, headers=auth_headers(intruder_token))
            assert response.status_code == 404
            assert response.json() == {"error": "Workspace not found"}


@pytest.mark.parametrize(
    "headers",
    [
        {"origin": "https://evil.example"},
        {"sec-fetch-site": "same-site"},
        {"sec-fetch-site": "cross-site"},
    ],
)
def test_browser_origin_or_fetch_metadata_is_rejected(harness, headers):
    token = mint_token(harness.private_key, subject="browser-block")
    with TestClient(harness.app) as client:
        response = client.post("/workspace", headers=auth_headers(token, **headers))
        assert response.status_code == 403
        assert response.json() == {"error": "Browser API requests are not accepted"}


def test_port_allowlist_and_unknown_endpoints(harness, monkeypatch):
    harness.runtime.endpoint_url = "http://worker.internal:8787"
    FakeAsyncClient.instances.clear()
    fake_response = FakeAsyncResponse(status_code=200, body=b"upstream body", headers={"content-type": "text/plain"})

    def factory(*args, **kwargs):
        return FakeAsyncClient(*args, response=fake_response, **kwargs)

    monkeypatch.setattr(gateway_server.httpx, "AsyncClient", factory)

    token = mint_token(harness.private_key, subject="port-user")
    with TestClient(harness.app) as client:
        workspace = client.post("/workspace", headers=auth_headers(token))
        assert workspace.status_code == 200
        workspace_id = workspace.json()["workspaceId"]

        live = client.get(f"/workspaces/{workspace_id}/ports/8080", headers=auth_headers(token))
        assert live.status_code == 200
        assert live.headers["content-disposition"] == 'attachment; filename="workspace-service.html"'
        assert live.content == b"upstream body"

        instance = FakeAsyncClient.instances[-1]
        assert instance.sent_request.url == "http://worker.internal:8080/"
        assert "Authorization" not in instance.sent_request.headers

        unknown = client.get(f"/workspaces/{workspace_id}/does-not-exist", headers=auth_headers(token))
        assert unknown.status_code == 404
        assert unknown.json() == {"error": "Unknown endpoint"}

        bad_port = client.get(f"/workspaces/{workspace_id}/ports/9090", headers=auth_headers(token))
        assert bad_port.status_code == 404
        assert bad_port.json() == {"error": "Unknown endpoint"}


def test_signed_stream_ends_at_identity_expiry(harness, monkeypatch):
    import asyncio
    class SlowResponse(FakeAsyncResponse):
        async def aiter_bytes(self):
            yield b'data: {"kind":"state","data":"synthetic"}\n\n'
            await asyncio.sleep(10)
            yield b'data: expired\n\n'
    response = SlowResponse()
    monkeypatch.setattr(gateway_server.httpx, 'AsyncClient', lambda *a, **kw: FakeAsyncClient(response=response))
    token = mint_token(harness.private_key, subject='stream', expires_in=2)
    with TestClient(harness.app) as client:
        workspace = client.post('/workspace', headers=auth_headers(token)).json()['workspaceId']
        started = time.monotonic()
        result = client.get('/workspaces/'+workspace+'/events', headers=auth_headers(token))
        assert result.status_code == 200
        assert b'synthetic' in result.content and b'expired' not in result.content
        assert time.monotonic()-started < 4
        assert response.closed


def test_forwarded_email_without_signed_assertion_is_rejected(harness):
    with TestClient(harness.app) as client:
        response = client.post('/workspace', headers={'Cf-Access-Authenticated-User-Email':'owner@example.com'})
        assert response.status_code == 401
        assert not harness.runtime.ensure_calls
