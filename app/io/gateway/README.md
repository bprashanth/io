# V1 gateway experiment

Separate launcher; ordinary `app/io/run.sh` still opens the existing IO mode.
V1 always runs remotely. Local capability reports do not change execution.

## Server

Requires Linux Docker, the existing nested-user-namespace AppArmor setup, Node and Python 3.12+.
The gateway is a trusted host operator with Docker access. Do not mount its socket or state in
user runtimes. The runtime image retains the earlier experimental seccomp/AppArmor exceptions;
this is not yet an audited production hosting system.

```sh
node app/io/fetch-codex.js
sudo apparmor_parser -r app/io/remote/io-remote.apparmor
docker build -f app/io/remote/Dockerfile --build-arg CODEX_TARGET=linux-arm64 -t io-remote-codex:v1 app/io
python3 -m venv ~/.local/share/io-gateway/venv
~/.local/share/io-gateway/venv/bin/pip install -r app/io/gateway/requirements.txt
~/.local/share/io-gateway/venv/bin/python app/io/gateway/server.py \
  --issuer https://YOUR-TEAM.cloudflareaccess.com --audience YOUR-APPLICATION-AUD --port 8787
```

Use `linux-x64` for an x64 server. The issuer and application AUD are public configuration,
not the tunnel token. The gateway does not need Cloudflare administrative credentials.
Cloudflare Tunnel should point the single protected hostname at `http://localhost:8787`.
Do not replace a live legacy runtime on that port without preserving its state first; use
`--port 8788` during deployment preparation. Run one gateway process (not multiple Uvicorn
workers), since runtime lifecycle locks are process-local. SQLite and Docker named volumes
persist across process restarts. Keep the state directory private and outside the checkout.

## Laptop

After installing the existing Electron dependencies (`cd app/io && npm ci`), from repo root:

```sh
IO_GATEWAY_URL=https://io.idli.cc app/io/gateway/run.sh
```

PowerShell:

```powershell
$env:IO_GATEWAY_URL='https://io.idli.cc'
& .\app\io\node_modules\.bin\electron.cmd .\app\io\gateway\desktop.js
```

1. Sign in to Cloudflare in the isolated IO sign-in window. Access policy controls who enters.
2. IO creates/reopens your persistent workspace automatically.
3. Choose **Sign in with browser** for ChatGPT, using the existing localhost OAuth callback.
   No device-code setting is needed. These are separate identity and Codex authorization steps.
4. Upload a copy, start a conversation, download results. New conversations share workspace files.
5. Closing IO leaves the workspace and active process running. Reopen to reconnect. Access expiry
   requires closing/reopening IO to sign in again. **Sign out of IO** clears the local Access
   session and closes the app, so next launch can use another approved identity; it keeps the
   remote workspace and ChatGPT login. Explicit Delete workspace removes files/auth.

If an identity provider rejects the embedded sign-in window, that provider flow still needs
an external-browser Access handoff; don't enable a weaker Access policy to bypass it.

## Local diagnostic

Startup runs the synthetic suite using a previously prepared standalone Python runtime. Without
one, the report is INCONCLUSIVE and remote access still works. Prepare it once:

```sh
node app/io/tests/sandbox/prepare.js
```

Or set `IO_DIAGNOSTIC_RUNTIME=/path/to/runtime`. The Local diagnostic button shows the report
and can rerun it after selecting a runtime directory. Reports stay in Electron user data;
there is no automatic upload. The current full suite is a five-minute-bounded diagnostic,
not a guarantee that a future different OS/Codex build is safe. See [diagnostic](../diagnostic/README.md).

## Protocol

`POST /workspace` returns `{workspaceId,state,executionMode,persistent}`. Every subsequent
request to `/workspaces/<id>/...` must carry a valid Cloudflare app assertion. The desktop sends
its Access cookie to Cloudflare; the gateway checks the signed assertion, issuer, audience,
expiry, subject and human email. Identity is issuer + subject, not mutable email.

The worker endpoints are forwarded through an explicit allowlist. `/end` deletes the workspace
and both volumes. `/conversations` lists IDs; `/start` accepts `conversationId` or creates a new
conversation. Only one terminal is active per workspace; a new chat stops the previous terminal.
Closing a terminal does not delete its saved conversation. Deleting one removes its transcript;
Codex internal ancillary indexes are not a secure transcript erasure guarantee.

`GET /workspaces/<id>/ports/8080` fetches only `/` from a fixed container port, with no forwarded
credentials and no redirects. It returns an attachment, not active content on the gateway
origin. For the proof, the operator starts `python3 -m http.server 8080 --bind 0.0.0.0 --directory
/workspace` inside the chosen container. This is not automatic exposure of servers started
inside Codex's Offline network namespace. Rendering arbitrary apps is deferred.

## Reproducible local checks

```sh
python -m pytest app/io/tests/gateway/test_gateway.py
python app/io/tests/gateway/serve_fixture.py /tmp/io-v1-fixture
# another terminal, same venv:
python app/io/tests/gateway/integration.py /tmp/io-v1-fixture /tmp/io-v1-evidence
xvfb-run -a node app/io/tests/gateway/ui-drive.js /tmp/io-v1-fixture /tmp/io-v1-evidence
```

The fixture binds only loopback 8788 and mints signed synthetic identities using an ephemeral
RSA key. It is not a production auth mode. Never route the Cloudflare tunnel to it. Its private
SQLite state and `.jwt` files belong outside git. Test cleanup must delete both test workspaces
through `/end`, then stop the fixture server. The production CLI has no signature-bypass flag.

## Current DGX deployment

The user service `io-v1-gateway.service` currently listens on **127.0.0.1:8789**, configured for
`t4gc.cloudflareaccess.com` and the verified `io.idli.cc` application audience. Change the
Cloudflare tunnel destination to `http://localhost:8789` to reach V1. The previous signed-in
prototype remains on 8787; its workspace is not automatically assigned to a Cloudflare user.
Use `systemctl --user status io-v1-gateway.service` on the DGX for service status. This service
configuration is machine-local; credentials and database are not committed.

Human acceptance: after changing the destination, launch V1 on the laptop, complete both
logins, attach a small CSV and ask Codex to total a column and create `result.csv`. Download it,
start a second conversation, reopen the first, close/reopen IO, and confirm the same files and
conversations remain. Test a second approved Cloudflare identity with its own ChatGPT login;
it should receive an empty separate workspace. Do not delete your original 8787 session until
any files you need have been downloaded.
