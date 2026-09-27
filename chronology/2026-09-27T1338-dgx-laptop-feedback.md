# Remote laptop feedback and fixes

The user's three screenshots prove fresh ChatGPT login and real multi-turn assistant
replies from their laptop. They also exposed three prototype bugs: comment-only SSE
heartbeats parsed as JSON, repeat attachment conflicts plus no model-visible remote
path, and End destroying the endpoint when the user intended an account switch.

Fixed heartbeat parsing (genuine malformed JSON still reports an error), readable
transport errors, identical-file upload retries without overwriting conflicts, and
an explicit bracketed-paste attachment-path draft that the user reviews/submits.
Added Sign out: stop Codex, clear authentication, cached chat and replay, retain
workspace files and endpoint. Delete workspace now explains permanent server/data
removal. Added operator restore for an absent container, preserving the original
owner's capability/port while creating a fresh signed-out empty workspace.

Cursor CLI gpt-5.4-mini-high performed the renderer grinding work; parent reviewed
and corrected its semantics, safe paste, policy badge, and real narrow-window
horizontal overflow caught by Playwright. Login chrome collapses after sign-in.
The intended product remains the main io interface; this separate experiment UI is
not that integration.

Validation: 13 actual-container tests pass, two client transport groups pass, actual
Electron fixture regressions pass with no page errors, and real-container Electron
CSV/operator-Python/download/device-flow-display checks pass. The first restore
harness run exposed Docker removal lag after HTTP exit; waiting for actual removal
fixed the test without weakening readiness. The fixture logout test uses synthetic
ChatGPT state and cannot count as second-account OAuth. The user still needs to
retry live image interpretation and a generated-file round trip.

Server 8787 was absent after the user's End action. Restored the original owner
connection, then deployed the final image only after checking signed-out, idle and
empty state. Same copied client config and SSH tunnel remain valid. Four-hour TTL
still applies; closing the app preserves the session, deletion/expiry does not.
No user login material was copied. The earlier workspace is unrecoverable tmpfs.

Evidence: [benchmark](../benchmarks/runs/2026-09-27-remote-laptop-fixes/README.md).
Docs: [operator/client guide](../app/io/remote/README.md),
[proposal](../proposals/remote-linux-codex.md).

Existing local regressions: 19 launcher checks and 34 proxy tests pass. The first
proxy invocation used system Python and lacked pandas; rerunning with the existing
`.venv-v2` environment passed all 34.
