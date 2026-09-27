# Browser OAuth for ordinary NGO accounts

The second test account refused device-code login unless its security setting was
enabled. User requested normal browser OAuth and wants the test account to retain
its ordinary settings. The default Sign in now runs pinned Codex `login`, without
`--device-auth`; the old flow is an explicit fallback. No account setting changed.

Electron temporarily owns laptop loopback port 1455 and relays a state-matched
callback over the existing bearer-authenticated io channel. The worker forwards
only `/auth/callback` to container localhost:1455. Codex retains PKCE, token exchange
and per-session credential storage. No extra SSH tunnel, public callback listener,
or copied local auth cache. URLs/callback parameters are not shown in the UI/logs;
normal Codex auth cache remains inside the container as before.

Reviewed official authentication docs and the pinned rust-v0.154.0 login source.
The source revealed Codex persists credentials then waits for `/success`; relay
explicitly completes that fixed local route, stripping redirect query claims and
never forwarding arbitrary redirects. This avoids leaving a successful login
process occupying the terminal. Completion still requires saved ChatGPT auth.

Cursor CLI gpt-5.4-mini-high handled renderer edits and a separate localhost test
file; parent implemented/reviewed protocol and worker changes. Its tests caught an
unvalidated optional issuer; both client and worker now reject a mismatched issuer.

Validation: 14 real container tests, eight Node callback/transport groups, Python
callback-completion fixture, real Electron browser-start/cancel/retry/fallback
screenshots and prior attachment/layout checks. Existing 19 launcher and 34 proxy
checks pass. UI browser opening was captured rather than completing authorization.
We have NOT proven successful browser OAuth with the user's second account; that
requires their authorization. No successful OAuth claim is inferred from fixtures.

Deployed by checking the laptop workspace was signed out, without chat/files and
only awaiting the old device login. Cancelled that obsolete attempt, rechecked
signed-out status, and restored with the final image using the same connection
capability/port. Existing copied config and SSH tunnel remain usable. Four-hour TTL
still applies. No unrelated workspace data was discarded.

[Evidence](../benchmarks/runs/2026-09-27-browser-oauth/README.md),
[guide](../app/io/remote/README.md), [proposal](../proposals/remote-linux-codex.md).
