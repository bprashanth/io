# Remote Linux experiment begins — DGX, 2026-09-27

The owner redirected work from native Windows sandbox conformance to an opt-in
remote Codex experiment. [Proposal](../proposals/remote-linux-codex.md) records the
scope and acceptance criteria. Local io is preserved.

Measured before implementation: Docker is available with AppArmor/seccomp; the
DGX has Tailscale address 100.82.28.38. The Pop!_OS peer (100.76.46.126) is currently
offline. Even with Docker's seccomp and AppArmor marked unconfined, `unshare -Ur`
fails writing uid_map on this host. Nested sandbox support must be demonstrated,
not assumed from the earlier host-level Linux pass.

Fresh user OAuth has not been completed. A request to authorize a fresh device
flow is pending. No existing developer login or API key will be borrowed.

Implementation plan: ordinary-user, ephemeral per-session container; pinned Codex;
streamed PTY; explicit file transfer; main-process-only connection capability.
A Cursor CLI gpt-5.4-mini-high worker is implementing the bounded Electron transport
and experimental renderer; parent owns container/security design and integration.

Not tested at this checkpoint: remote login, conversation, container isolation,
remote UI, two-machine transport. Evidence will be appended in a new entry.
