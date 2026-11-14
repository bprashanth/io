# Claude Code masking proxy

Implemented in `lib/ccproxy.py`, with the shared vault in `lib/privacy.py` and
synthetic regressions in `lib/test_ccproxy.py`.

From this COWORK directory, using Python with pandas, duckdb and openpyxl installed:

```sh
.venv/bin/python -I lib/ccproxy.py --data-dir /path/to/data --port 8870
```

In another terminal, in that data directory, use an already subscription-authenticated
Claude Code installation:

```sh
unset CLAUDECODE
ANTHROPIC_BASE_URL=http://127.0.0.1:8870 claude
```

Configure files in the data directory's `privacy.json` using the existing privacy
review UI or `privacy.set(data_dir, file, mode='mask', columns={...})`. The proxy
seeds all selected columns across all tabs of every mask-mode file. It leaves the
source files unchanged. Programmatic `lib.ccproxy.ensure(data_dir)` starts a
detached proxy on an available loopback port and returns that port; repeated calls
reuse the same instance. Its port, PID and instance identity are in
`<data_dir>/.idli/ccproxy.json`.

## Behavior

- `POST /v1/messages` and `/v1/messages/count_tokens`: recursively mask strings in
  system and message content, including tool results and nested tool inputs.
  Reuse privacy's known-value, close-match and regex detection. GLiNER receives
  only remaining text from the last user message's direct text blocks, excluding
  tool results and closed or unclosed `<system-reminder>` sections.
- Scanner endpoint: `IDLI_SCANNER`, defaulting to `https://privacy.idli.cc/scan`
  when launched through the CLI or `ensure`. `IO_PRIVACY_TOKEN` is used by the
  existing Scanner without being logged. Scanner failure falls back to regex and
  known-value matching and is recorded as `regex only`.
- A bounded cache uses SHA-256 of each string plus its scanning policy and vault
  revision. File/settings changes and new private values invalidate old results.
  A second local pass catches values discovered later in the same request.
- One persistent `<data_dir>/vault/session.json` assigns stable, unique codes
  across files, including codes minted by scanners and validators. Cross-process
  locking coordinates privacy UI and proxy writers. Unambiguous old per-file
  vaults migrate while retaining their codes.
- Numeric strings are matched only against selected, vaulted values as whole
  tokens; values with fewer than four digits stay clear. Native JSON numbers
  retain their types; a known private numeric literal causes refusal.
- Thinking and redacted-thinking blocks retain their values exactly. Tools,
  model and metadata are excluded from transformation. The final leak check
  covers the entire decoded body, including excluded fields, object keys and
  numeric literals; known leaks cause an Anthropic-shaped HTTP 403 before any
  upstream call or wire capture.
- JSON responses restore strings and keys except signed thinking blocks. SSE
  restores `text_delta` and JSON-escaped `input_json_delta` values, with separate
  buffers per content block. Partial codes wait for more data; a trailing buffer
  is emitted as an extra delta before `content_block_stop`. Thinking/signature
  deltas and other events pass through unchanged.
- Other API routes pass through. Authorization and Anthropic headers pass through
  without inspection or logging. The server binds only `127.0.0.1`.
- One content-free JSONL record per request goes to `<data_dir>/ccproxy.log`:
  UTC time, path without query, status, substitution count, scanner status and
  refusal flag. `--wire-log` additionally saves the exact forwarded masked bodies
  in `<data_dir>/ccproxy-wire/`; it never saves headers or refused bodies.
  Vaults, state, log and wire files use owner-only file permissions.
- `--upstream http://127.0.0.1:PORT` supports a fake upstream for local testing;
  production defaults to `https://api.anthropic.com`.

## Verification

All checks ran using synthetic data and local fake services, without live
subscription calls or reading authentication files:

```sh
.venv/bin/python -m pytest -q lib/test_ccproxy.py lib/test_privacy.py
# 22 passed (15 proxy cases including parametrization, 7 existing privacy cases)
.venv/bin/python -m lib.test_formkit
.venv/bin/python -m lib.test_fixkit
.venv/bin/python -m lib.test_driveindex
# Each printed ALL PASSED.
```

Tests copy `2026-11-13-grounded-9b/fixtures/drive/households.xlsx` to a temporary
workspace and mask `household_head` and `ward`. Coverage includes nested tool
arguments/results, signed blocks, scanner scope and reminders, caching, vault
growth, multi-file and concurrent-process allocation, numeric boundaries,
legacy migration, every split point of a streamed code, interleaved blocks,
JSON escaping, refusals with no upstream traffic, credential forwarding checked
only in memory, logs and wire captures, count_tokens, GET/HEAD passthrough,
malformed/encoded requests, upstream failures, detached startup/reuse/restart,
and the actual isolated CLI against a fake upstream. End-to-end assertions check
that upstream receives codes and the client receives real names, paths and tool
arguments for both JSON and streamed replies.

## Limits

This is a text/JSON proof of concept, not a shell or networking sandbox. CLI tool
execution, other destinations, and routes outside the two Messages endpoints
are outside the masking policy. Images/binary content are not protected by text
matching. Chunked or compressed request bodies are refused, as are compressed
upstream Messages responses; the proxy requests identity encoding upstream.

Signed thinking is preserved, so a signed block containing a known real value
causes refusal. Unknown names can escape in tool output; only known/close values
and regex validators apply there. A failed scanner can miss unknown typed names.
Ambiguous short numbers remain visible by design. Values remain reserved in the
vault after settings change, to preserve existing code meanings.

Conflicting legacy per-file code assignments are refused rather than guessed;
use a fresh data directory with the source files and privacy settings in that
case. Cross-process locks use Unix `fcntl`; Windows is not supported by this POC.
The optional live Claude subscription smoke test was not run.
