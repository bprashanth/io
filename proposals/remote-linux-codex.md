# Remote Linux Codex: architecture experiment

Owner-authorized 2026-09-27. This supersedes native Windows sandbox work as the
immediate experiment; it does not decide io's eventual architecture.

## Question and scope

Can io keep its terminal interaction while the entire Codex working environment
runs on Linux, using the person's own ChatGPT subscription login? Prove explicit
upload-copy → remote work → download-result, with isolation between sessions.
No API key or borrowed developer login counts as the OAuth demonstration.

Local mode remains the default. Remote mode is selected by an operator-provisioned
connection file, read only by Electron's main process. A separate experimental
screen reuses io's colours, bundled xterm and terminal controls. It must state
that uploaded contents leave the device and that this experiment does not use
local tokenisation. Use synthetic files initially. Moving the proxy is deferred;
we must not carry over the local mode's “Protected by io” claim.

## Smallest deployment

One Linux Docker container per session, provisioned by a trusted operator. Each
has its own network namespace, workspace and CODEX_HOME, and a random connection
capability. There is no public account-creation service or shared credential store.
The container runs as an ordinary UID, has no host data or Docker socket mount,
a read-only image, bounded memory/processes/tmpfs, and no restart policy.

The worker exposes authenticated HTTP only on a host loopback publication. Use an
SSH tunnel over Tailscale for the first laptop test; HTTPS termination via Tailscale
Serve can be added independently. The Electron client rejects cleartext non-loopback
URLs. A container IP is a separate network namespace, useful for local transport
checks; it is not evidence of a successful two-machine test.

Codex 0.154.0 comes from io's pinned bundle, including its sandbox helpers. Generate
its filesystem/network permissions with io's existing writeConfig implementation,
remove only local proxy routing, force ChatGPT login, disable escalation and hosted
web search, and supply remote-specific instructions. Commands stay offline and
cannot read CODEX_HOME/auth.json. Codex's controller needs outbound HTTPS for OAuth
and model requests. Do not confuse controller connectivity with command connectivity.

Nested bubblewrap may require explicit host AppArmor and Docker seccomp provisioning.
Measure that requirement; do not silently grant privileged containers or fall back
to unwalled commands. Document any relaxation as an experimental deployment limit.

## Authentication and lifecycle

Start fresh `codex login --device-auth` inside the container. Stream its URL/code to
io; the user authorizes in their own browser. Never copy the host's auth.json, accept
an API key, or send credentials back to the renderer. `login status` must identify
ChatGPT authentication before a normal conversation starts.

Credentials and workspace live in container tmpfs, not a host volume. Disconnecting
io leaves the session running; reconnecting to the same endpoint replays a bounded
terminal event buffer (explicit gap notice when too old). Codex process exit permits
restart/resume within the same container. Container stop/restart loses files, login
and conversation history. Explicit End destroys session data and stops the worker.
Provision an expiry as a backstop; connection capabilities are not long-term accounts.

The server operator/root remains trusted. Separate containers are not a proof
against kernel exploits or a production multi-tenant hosting design.

## Evidence and acceptance

1. **Credential-free:** real bundled Codex command probes, controlled TCP positive
   controls, parent/child filesystem/network checks; A/B file and auth isolation;
   bearer authorization; traversal/symlink rejection; stream replay, cancellation,
   unexpected process exit, reconnect and end/restart semantics.
2. **Human OAuth:** fresh device flow, ChatGPT login status, second session still
   signed out. Record status only, never credentials or active codes in benchmarks.
3. **Live interaction:** assistant text, real command stdout/stderr, cancellation,
   subsequent turn/resume, CSV manipulation with Python and downloaded result.
   Escalation is deliberately `never`; an escape request must be denied, not answered
   by an elevated execution button. A deterministic transport fixture cannot count
   as live ChatGPT evidence.
4. **Actual io:** open Electron, click controls and take screenshots. Verify original
   CSV hash is unchanged and output download contents match. Test both failed and
   working connection paths.
5. **Laptop next:** repeat OAuth/CSV flow from Pop!_OS over Tailscale. macOS/Windows UI
   launch, clipboard, file dialogs and reconnect remain separate validation surfaces.

Use benchmarks/runs/2026-09-27-remote-codex for redacted evidence and chronology for
findings. A matrix must distinguish passed, failed, simulated, and not run.

## CI now versus later

Linux CI can build the image, provision a scoped AppArmor profile if needed, run
actual Codex sandbox and two-session API/lifecycle tests with no model credentials.
Client protocol tests can run on Linux, macOS and Windows using deterministic HTTP
fixtures. Those fixtures prove transport behaviour, not OAuth or model behaviour.
Never put a personal OAuth cache in ordinary PR CI. A dedicated manual OAuth drive
on a trusted host is a separate demonstration. CI containers provide different
network namespaces, not a real desktop-to-server internet deployment.

Defer production TLS/account management, durable storage, retention/encryption,
quotas, multi-tenant orchestration, automatic sync, local executors/MCP bridging,
proxy/tokenisation redesign, Electron toolbox changes and native Windows sandbox
repairs. After evidence, compare native, fully remote, and later hybrid paths.

## Laptop feedback, September 27

The user demonstrated real ChatGPT OAuth and subsequent assistant replies through
the laptop client. The separate remote screen is temporary experiment UI. The
intended product is the main io interface with a remote execution backend; that
integration is not implemented yet. First fix the observed heartbeat warnings,
attachment path handoff and destructive session/account-switch confusion, then
verify a live model-driven file round trip. Changing an account uses Sign out
(clear authentication/chat, keep files); Delete workspace destroys the endpoint.
A different person still requires their own workspace/capability.

## Browser OAuth default, September 27

NGO-like test accounts may have device-code login disabled. Preserve that setting:
use ordinary Codex browser OAuth by default, with an io-owned short-lived loopback
callback relay over the existing authenticated session connection. Codex generates
PKCE/state, validates OAuth and stores credentials in that user's container. The
relay checks the active state, issuer and callback shape, cannot choose an arbitrary
upstream, and closes on completion/cancel/timeout. Device codes remain optional.
This is Codex's existing sign-in flow, not a new general-purpose io OAuth client.
The user subsequently confirmed browser authorization works with the unchanged
second account; see the [confirmation chronology](../chronology/2026-09-27T1506-dgx-remote-user-confirmation.md).

## Current routing versus future provisioning

Opening io does not create a container: an operator provisions it beforehand. The
private endpoint/capability config and SSH port mapping identify the existing
container; no account-to-container lookup exists. HTTP requests carry input and
controls, SSE carries terminal/state output, and files transfer explicitly. Closing
io preserves the container until deletion or expiry. Automatic provisioning/lookup
and io service authentication are future product work, separate from ChatGPT OAuth.
