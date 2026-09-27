# User-confirmed browser OAuth and current remote architecture

After the browser-login implementation, the user reported: "Ok this works".
Record this as user-confirmed browser OAuth on the second, ordinary NGO-like test
account with device-code login left disabled. This updates the pending human
verification in the earlier browser-OAuth entry; it is not an automated test result.
No additional model-driven file-analysis round trip was reported.

The subsequent discussion clarified the current implementation:

- An operator provisions one Docker container per session before io connects.
  Opening io or signing into ChatGPT does not create a container.
- The private connection JSON contains an endpoint and bearer capability. The
  laptop's SSH forwarding over Tailscale maps local port 8787 to the DGX loopback
  port published for that container. There is no account-based container lookup.
- ChatGPT browser OAuth signs Codex into the user's account inside that container.
  This is separate from future io service authentication/provisioning.
- io sends terminal input and lifecycle controls as HTTP requests through the
  authenticated connection. Server-Sent Events stream PTY output and state back.
  Files use separate explicit upload/download requests. Codex talks to OpenAI from
  the server; the client is not streaming remote desktop video.
- Window close/disconnect preserves the container. Reconnect replays a bounded
  terminal buffer (up to 2 MiB). Sign out clears authentication/chat but retains
  files and endpoint. Delete workspace or default four-hour expiry destroys the
  ephemeral container and its tmpfs data.
- Docker isolates each session. Codex's nested Linux/bubblewrap sandbox restricts
  commands and children to the intended filesystem policy and offline networking.
  The Codex controller has internet access for OAuth/model traffic. Outer container
  hardening remains unfinished: current AppArmor and seccomp relaxation is explicit.

Automatic user-to-container provisioning/lookup, main io interface integration,
durable storage and production hosting remain future work. These clarifications
are descriptions of the prototype, not claims that those product layers exist.

Related: [browser OAuth implementation](2026-09-27T1400-dgx-browser-oauth.md),
[proposal](../proposals/remote-linux-codex.md),
[operator/client guide](../app/io/remote/README.md),
[benchmark evidence](../benchmarks/runs/2026-09-27-browser-oauth/README.md).
