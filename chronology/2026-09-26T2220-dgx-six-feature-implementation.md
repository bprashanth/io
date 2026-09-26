# DGX: attachments, provider switching, and thin setup

Implemented the six requests in `.prompt/dgx_handoff_0926.md` on `io_codex_3`, which
already contained the handoff branch through main. The user's instruction authorized these
changes and the associated documentation. No push. The initial boundary verification is
[the preceding entry](2026-09-26T2145-dgx-handoff-verification.md).

## Measured

Evidence: [scripts and results](../benchmarks/runs/2026-09-26-dgx/README.md).
The actual Electron app ran under Xvfb, driven through Playwright, with bundled Codex and
live OpenRouter GPT-5 mini. Synthetic files and conversations only. The in-app Browser had
no available browser instance, so the standalone Electron driver was used. Native file
selection was stubbed; attachment/privacy/review/settings controls were clicked normally.

- Conversation curl: exit 0, HTTP 200. Public attachment: still HTTP 200. Private attachment:
  exit 6, HTTP 000. The generated sandbox profile was used for each probe. The resumed
  thread remembered Mango Garden, and Codex acknowledged the attachment after review.
- The review displayed NAME codes. Removing the key made the next provider request fail
  locally; restoring it worked on the next turn without restarting the app or Codex.
  No raw key was found in the generated profile, tested Codex environment, dumps or log.
- A controlled ChatGPT usage fixture preselected the fallback before a question. A real
  Codex request to the fixture received a quota refusal; Switch and resend sent the original
  user question to live OpenRouter, which answered it. This is NOT a real exhausted account.
- Resume with a synthetic foreign encrypted reasoning item succeeded; that item did not go
  upstream. Visible context survived. A new marker added to AGENTS.md appeared in the next
  resumed request. Fresh handover also recovered Mango Garden. The live model ran Python
  inside the wall, read a CSV, and wrote the correct total, 50.0.
- An empty readers-only installation with pip cache disabled took 19.828 seconds and used
  475,333,882 bytes. It downloaded standalone Python (84 MB) and reader/tool packages, no
  torch, GLiNER or model weights. This was an empty directory on the existing DGX, NOT a
  freshly imaged OS. A synthetic scan through the privacy server detected person/place/phone.
- With the server unavailable, the real UI offered another server, an on-device download,
  and pattern matching. Choosing patterns reached the home screen.
- The packaged Linux arm64 app opened the isolated key settings and reported an actual,
  non-simulated successful wall probe. Long pasted text, Shift+Enter, scrolling and a smaller
  window were exercised and photographed. Final inspection caught and fixed a seven-pixel
  overlay drift caused by the textarea's inline baseline space.

## Causes and changes

The initial launcher test falsely skipped the wall: its supposed outside secret lived in
allowed `/tmp`, and it used the wrong sandboxCheck signature. Both denial and readable
control now run. This corrects the verification, not the wall itself.

Private attachment is enforced by the shell and service. Stop and confirm the old process
has exited before copying, invalidate any accepted review, persist sticky privacy, and
require a working wall before resuming offline. A same-size, same-timestamp replacement must
be rescanned; a regression exercises this. Damaged privacy metadata fails closed. A later
public attachment cannot reopen a private conversation. The service attachment route is
shell-authenticated. The status bar separately reports command networking.

The OpenRouter credential lives in the Electron main process and Python proxy, with a
0600 local store (memory only on portable runs). The isolated password window validates
keys, shows only their suffix and reported allowance, and supports immediate replacement
and removal. Updates reach Python over child stdin with acknowledgment. Neither Codex nor
the main renderer receives the secret. Requests use OpenRouter's Responses endpoint,
`openai/gpt-5-mini`, the existing tokenization gate, and ZDR/data-collection restrictions.
OAuth/account headers, foreign reasoning ciphertext and provider cache references are
removed. Responses and error logging scrub current and previously used keys.

Quota preflight uses Codex app-server `account/rateLimits/read`; refusal detection also
observes proxy responses. The fixture shape was checked against bundled Codex source
(numeric reset timestamps), not guessed from an invented error string. A browser drive
exposed that background title generation can overwrite the proxy's most recent user input.
Retry now reads the last visible user turn from the actual saved Codex thread instead.

Provider changes first resume the current thread. If continuity is rejected, the UI offers
a fresh session with bounded visible user/final-assistant history in AGENTS.md; a subsequent
failure offers a plain fresh start. The history reader uses real JSONL payload wrappers,
exact folder matching, and omits hidden reasoning and symlinks. Measured rereading of
AGENTS.md on resume supersedes the earlier hypothesis that it might be ignored.

Thin setup now defaults to readers-only and explicitly offers scanner fallback. Local
scanner requests and fat-build preparation still download the model. The checkout installer
pins matplotlib 3.10.9 for Python 3.10 compatibility; packaged Python remains independent.
Packaging now includes new modules plus the previously omitted toolbox and viewer preload,
and resolves packaged UI assets from the resources directory.

Smaller Cursor CLI `agent --model gpt-5.4-mini-high` runs handled textarea/bootstrap work,
fixture tests, documentation edits and a read-only review. Privacy design, integration,
credential handling and final verification were reviewed by the coordinating agent.

## Retest

77 tests pass: launcher 19, proxy 34, bootstrap 8, key store 6, handover 2, quota 5,
attachments 3. Python tests used `app/io/.venv/bin/python`; system Python lacks required
packages and is not an equivalent test environment. The launcher boundary test did not
skip. Final Electron drives and Linux arm64 packaging passed. `git diff --check` passed.
Screenshots remain local, as required. The thin archive is under
`~/.local/share/io-builds/2026-09-26/io-linux-arm64-thin.tar.gz`.

## Not tested and remaining decisions

- No macOS/Windows execution or stock Ubuntu/AppArmor failure recovery was possible here.
  Run the existing launcher suite on their actual runners; both denial and readable control
  must execute. Building alone is not evidence for those walls.
- No real exhausted ChatGPT account or real ChatGPT-encrypted cross-provider history was
  available. The quota response was a fixture followed by a live fallback; foreign
  ciphertext was synthetic. Do not describe either as a real ChatGPT transition.
- Context-overflow classification has regression coverage; the full two-stage UI recovery
  was not forced with an enormous live thread. Fresh handover itself was measured live.
- Codex warns that metadata for gpt-5-mini is unavailable; ordinary replies and tool calls
  worked. A future curated model catalog could remove this warning, but guessing capability
  metadata here would conceal uncertainty.
- No clean-OS install, full Python 3.10 source install, new on-device model download, or
  hardware USB transfer was measured. The 19.8-second figure depends on DGX networking.
- Laptop-specific viewer GPU crash and event laptop inventory remain with the owner.

Suggested next improvement: run the existing non-vacuous wall test in macOS/Windows CI,
recording both successful and refused reads as artifacts. This needs real platform evidence
before calling either platform protected; it is a proposal, not a claim made by this change.
