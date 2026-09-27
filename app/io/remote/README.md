# Remote Linux experiment

Opt-in, operator-provisioned sessions; local io stays the default. Read
[the proposal](../../../proposals/remote-linux-codex.md) before using real data.
This experiment sends uploaded copies to the server and uses direct ChatGPT model
traffic, **without io's local masking proxy**. It is not a production hosting service.

## Server: build and create a session

Linux Docker, Node (to fetch the bundle), Python 3, and permission to provision
AppArmor on Ubuntu 24.04 are needed. From the repository root:

```sh
node app/io/fetch-codex.js
sudo apparmor_parser -r app/io/remote/io-remote.apparmor
docker build -f app/io/remote/Dockerfile --build-arg CODEX_TARGET=linux-arm64 -t io-remote-codex:experiment app/io
python3 app/io/remote/session.py create --connection ~/.local/share/io-remote/laptop.json --port 8787
```

Use `linux-x64` on an Intel/AMD Linux host. The image pins its base digest and reuses
io's pinned Codex package (currently 0.154.0). Each session gets a separate Docker
network, capability, workspace and CODEX_HOME. No host login/data volume is mounted.

**Experimental host requirements:** the named AppArmor profile grants user namespaces
with otherwise unconfined AppArmor, and the session disables Docker's default seccomp
filter so nested bubblewrap can work. It drops all initial capabilities, sets
no-new-privileges, and does not use privileged mode, host networking/PID namespaces,
or a Docker socket mount. This is a tested sandbox experiment, not hardened container
hosting. Narrower container syscall/LSM policies are an explicit follow-up.
The host/root/Docker operator can inspect session credentials and is trusted.

Startup runs the existing real Codex parent/child conformance probe with positive
controls. Failed controls, missing sandbox support, or escapes prevent readiness.
Commands have offline networking and minimal reads plus workspace writes. The Codex
controller can reach ChatGPT for login/model traffic. `/status` reports readiness,
ChatGPT authentication, terminal lifecycle and the pinned version, never auth contents.

## Client on this server

```sh
cd app/io
IO_REMOTE_CONNECTION="$HOME/.local/share/io-remote/laptop.json" ./run.sh
```

This skips local scanner/Python/Codex bootstrap. The connection capability stays in
Electron's main process. The file must be private (`chmod 600` on Unix).
Use **Sign in**, authorize the displayed fresh device code in your own browser, then
**Start/resume**. Device login may need enabling in ChatGPT security settings.
See [official authentication guidance](https://developers.openai.com/codex/auth).
No API key, copied auth.json, or existing developer login is needed.

## Pop!_OS laptop via Tailscale

DGX currently: `100.82.28.38` (`gx10-0a47`). The user demonstrated laptop ChatGPT login and multiple live replies on September 27.
A live model-driven attachment/result round trip remains to be verified.

1. Copy the private connection file over SSH to the laptop (it contains a bearer
   capability; do not paste it into chat or commit it). The file is scoped to that
   single container. The server operator provisions one per person.
2. Forward the server's **loopback** listener over authenticated SSH/Tailscale:

   ```sh
   ssh -N -L 127.0.0.1:8787:127.0.0.1:8787 beeps@100.82.28.38
   ```

3. Keep the connection URL `http://127.0.0.1:8787` on the laptop and launch io with
   `IO_REMOTE_CONNECTION` pointing at the copied file. On Windows PowerShell use
   `$env:IO_REMOTE_CONNECTION = 'C:\path\laptop.json'` before opening io.
4. Sign in, attach a synthetic CSV, ask for a Python-generated summary, download it,
   close/reopen io, and ask a follow-up in the same session. Verify both local original
   and downloaded contents. Interrupt a long turn. Use **Sign out** to change your login, or **Delete workspace** to destroy the server session.

Alternatively supply an HTTPS endpoint with a valid certificate. Non-loopback HTTP
is rejected. No Tailscale Serve configuration or public endpoint is created by this
code. The SSH approach uses the owner's existing server account for this experiment;
NGO onboarding/account provisioning is deferred.

## Lifecycle and limits

- Window close/disconnect: session remains; reconnect replays up to 2 MiB of terminal
  output. Missing older output is explicitly reported. This is a terminal replay,
  not a durable event store. Duplicate keys after ambiguous network failures are not
  automatically retried.
- Codex exit: restart/resume inside the same still-running container. Login persists.
- Container restart/stop: tmpfs credentials, conversation history and files disappear.
  Reusing a container across people is unsupported; provision a new session/capability.
- Sign out: stops Codex, removes ChatGPT credentials and saved chat/replay, keeps
  the endpoint and uploaded files. This is for changing your own account; a different
  person needs a separate workspace/capability.
- Delete workspace: kills Codex, exits worker, Docker removes the ephemeral container.
  Restarting the client cannot recreate it.
- Expiry: four hours by default (`--ttl`, maximum one day); then worker exits.
- Uploads: one regular file, 10 MiB maximum, no overwrite. Identical retries reuse
  the existing copy; different contents require a new name. While the assistant is
  running, attachment stages a message with its remote path. Review it and press Enter.
  An image is a workspace file for the image tool, not a local inline attachment.
  Downloads: explicit save
  dialog, regular files only, no symlink traversal. No folder sync or local execution.
- Approvals/escalation: `never`, consistent with io offline. No UI grant can bypass
  the Linux sandbox; an elevated-execution approval workflow is not in this experiment.

Remove the connection and leftover empty Docker network after end/expiry:

```sh
python3 app/io/remote/session.py destroy --connection ~/.local/share/io-remote/laptop.json
```

To restore a deleted/expired session for the **same owner**, the server operator can
reuse the original connection file, port and capability:

```sh
python3 app/io/remote/session.py restore --connection ~/.local/share/io-remote/laptop.json
```

This creates an empty, signed-out workspace; it cannot recover old files. Existing
client configuration and SSH forwarding can be reused. Restore refuses to replace
a container that still exists. Tailscale supplies connectivity to the host; SSH
forwarding is used because this prototype listens only on server loopback. The
private client config supplies that endpoint and its bearer capability, not your
ChatGPT credentials. Direct tailnet HTTPS hosting is a separate deployment option.

## Verification

```sh
node --test app/io/tests/remote/test_client.js
python3 app/io/tests/remote/test_worker.py
# A dedicated disposable session; this drive starts/cancels device login, but never authorizes it.
IO_REMOTE_CONNECTION=/path/to/test.json xvfb-run -a node app/io/tests/remote/ui-drive.js
```

The UI drive needs Electron dependencies in app/io and Playwright from
installation/smoke. It uses actual Electron controls and the real sandbox, with native
file dialogs supplied deterministic test paths. It does **not** demonstrate a model
answer: Python is invoked through Codex's sandbox by the operator harness. Device
codes are masked in screenshots. Live OAuth/ChatGPT conversation remains a separate
human-authorized test. The CI workflow runs client fixtures on four OS targets and
real container probes on Linux, without model credentials.

Additional actual-Electron renderer regression check (scripted server; no real login/model):

```sh
xvfb-run -a node app/io/tests/remote/ui-regressions.js
```

It checks heartbeat handling, duplicate image attachment and unsent path draft,
compact layout, sign-out/delete controls, and readable connection errors.
