# Laptop feedback regressions — 2026-09-27

User screenshots `/tmp/malformed_{1,2,3}.png` demonstrate real OAuth and live
assistant replies on the laptop, plus heartbeat errors, repeat-upload failure and
an unreachable deleted endpoint. These personal screenshots are not committed.

- `worker-tests.txt`, `api-isolation.json`: 13 passing tests using actual pinned
  Codex/container sandbox. Includes identical CSV/PNG retry, conflict preservation,
  account/chat clearing, restore on same port/capability, and existing isolation.
  Logout uses explicitly synthetic OAuth state, never a real user credential.
- `client-tests.txt`: two transport test groups, including heartbeat/id-only events
  and a genuinely malformed JSON control, against a deterministic HTTP fixture.
- `ui-regressions.json`: actual Electron against a scripted worker. No live model or
  account. Upload/draft, repeated PNG, layout at 820x640, sign-out and errors pass.
- `ui-results.json`: actual Electron plus real dedicated container; CSV copy,
  operator-issued sandbox Python, download, device-code display/cancellation.
  This does not prove model-directed tool use or successful device authorization.
- `first-worker-tests.txt`: initial restore check failed because HTTP shutdown
  precedes Docker removal. Harness now waits for actual container removal.
- Local PNGs are ignored: compact signed-in screen, small window, delete warning,
  readable disconnect, upload/result, and redacted device login. Parent inspected
  compact and error screenshots. No real account credentials are in this evidence.

Live image interpretation, login with a second real email, and integration into the
main io UI remain unverified/unimplemented. See the linked chronology entry.
