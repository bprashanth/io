# V1 remote runtime and local diagnostic

Accepted scope, 2026-09-27: implement a separate experiment; main IO consolidation follows later.
V1 always executes remotely. The synthetic local report informs a future V2 decision and never
changes routing, weakens policy, or uploads diagnostic evidence automatically.

## Protocol and identity

Desktop → Cloudflare Access/Tunnel (`io.idli.cc`) → loopback gateway → private runtime.
Validate Access RS256 signatures against the configured team's HTTPS JWKS, exact issuer and
application audience, expiry and human subject/email. Never trust the email header alone.
Key identity by issuer + subject, retaining normalized email only as display metadata.
SQLite stores one opaque `workspace_<random>` per identity, runtime generation and private
worker capability. Every operation, including event streams and live-service requests, checks
ownership. Container IDs, IP addresses and capabilities stay server-side.

Desktop uses a separate sandboxed Access sign-in window, then keeps the Access cookie in its
main process. ChatGPT browser OAuth remains the existing system-browser + localhost callback
relay; these are two different logins. Access expiry requires signing in again; SSE connections
must end by JWT expiry. No independent password database or unsigned development header.
Local tests use generated RSA keys and signed synthetic identities, in a test-only server entry.

## Runtime and persistence

One container/network and two named volumes (workspace, Codex state) per user; one active PTY
at a time, multiple saved Codex conversations. Closing the client leaves the workspace running.
Reopening locates the same workspace. Runtime restart preserves files/auth/conversations;
explicit workspace deletion removes container, network and both volumes. Conversation deletion
removes only its saved transcript. SQLite survives gateway restart. Provisioning failures retain
recoverable records; never return a ready runtime before its inner conformance probe passes.

Retain pinned Codex 0.154.0 and real Linux Offline command policy. Outer runtime: unprivileged
UID, read-only root, dropped capabilities, no-new-privileges, memory/CPU/PID limits, separate
networks, no published ports/Docker socket/host-root mount. Existing nested-bwrap seccomp and
AppArmor exceptions remain an explicit experimental limitation, not production hardening.
Persistent volumes have no disk quota yet; storage exhaustion and orphan recovery remain
operator concerns. Never place gateway database/tokens in the checkout.

## Milestones and evidence

1. Signed identity, deterministic concurrent workspace creation, restart/reconnect, ownership
   denials with two identities, negative JWT controls, no public runtime ports.
2. Reuse real Codex terminal/SSE and OAuth relay; enumerate/resume separate conversation IDs.
   Distinguish actual authorized model turns from login-startup or synthetic session fixtures.
3. Explicit copy upload → remote work → download. Collision rejects changed contents;
   path/symlink protections retained. Local originals are never overwritten automatically.
4. Fixed operator-started HTTP service on container port 8080, fetched through an authorized
   gateway endpoint with a strict port allowlist. Return bytes as an attachment, not executable
   HTML on the gateway authentication origin. This proves routing only; rendering arbitrary
   untrusted apps needs a separate-origin design. Offline sandbox network namespaces do not
   automatically expose model-started servers to the worker.
5. Laptop diagnostic wraps the same 17-property suite, with positive controls and
   PASS/FAIL/INCONCLUSIVE classification, platform/build/version/backend, raw evidence and
   explicit remote execution mode. No model calls, real documents, automatic privilege setup
   or automatic telemetry. Run locally and wire repeatable CI tests where credentials are absent.

Cloudflare human login and an ordinary Windows/macOS laptop cannot be claimed from localhost
fixtures. Record what was measured here and exact remaining user steps. Preserve the existing
signed-in prototype while the new gateway is tested on a different loopback port.

## Deferred

Main UI integration, local/remote selection, production deployment hardening, billing, quotas,
K3s, Teleport, durable backup/encryption policy, retention/suspension, folder sync, hybrid MCP,
public per-container ports, provider masking redesign and broader security surfaces.
