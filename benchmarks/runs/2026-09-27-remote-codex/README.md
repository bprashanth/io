# Remote Linux Codex evidence — DGX, 2026-09-27

Synthetic data only. OAuth credentials/capabilities/device codes are excluded.

| Check | Evidence | Result |
|---|---|---|
| Actual pinned Codex in Docker; workspace, outside read/write, symlink, parent/child TCP | container-conformance.json; api-isolation.json | Pass on DGX Linux arm64 |
| Before/after unsandboxed positive controls | api-isolation.json | 13 allowed checks per control per container |
| Two session tokens/workspaces/auth directories and network separation | api-isolation.json | Pass; synthetic auth sentinel, not real OAuth credentials |
| Upload/download, duplicate protection, traversal, symlinks, FIFO, nested results | api-isolation.json | Pass |
| Worker restart: stable endpoint, changed instance, tmpfs erased; end | api-isolation.json | Pass |
| Client SSE reconnect, dedup, gap, UTF-8, input order, instance reset, redirects | client-tests.txt | Pass with scripted HTTP fixture |
| Actual Electron CSV copy → real Codex sandbox/Python → explicit download | ui-results.json; screenshots | Pass; command issued by operator harness, not model |
| Fresh device authorization prompt and cancellation | ui-results.json | Pass; no user authorization completed |
| Local-mode regression tests | regression-tests.txt | 19 launcher + 34 proxy passed |
| ChatGPT-authenticated conversation, subsequent turn, model-driven command and cancellation | — | Not run; human OAuth pending |
| Pop!_OS ↔ DGX over Tailscale | — | Not run; peer was offline |
| Packaged remote client / native Mac and Windows GUI | — | Not run locally |

`api-isolation-first.json` preserves a failed early run. Two assertions expected
verbatim error text instead of the worker's deliberately generic GET errors; another
used the host's conformance.py path inside the container. Those test bugs were fixed.
The restart failure also exposed Docker's changing dynamically allocated host port;
provisioning now explicitly binds a selected port and the test asserts it stays fixed.

The first real UI drive caught missing PTY controlling-terminal setup: Ctrl+C did
not terminate device login. The worker now establishes the controlling terminal before
exec. The successful rerun records interruption as true. No early failed drive is
being counted as a pass.

Screenshots (git-ignored, available on the DGX): upload-confirmation.png,
remote-results.png, device-login-redacted.png. The device code and raw login log are
masked. Native file dialogs receive deterministic test paths through Electron's test
harness; the renderer's buttons, confirmations, transfer, and results list are real.

`container-conformance.json` is an initial full probe capture. The final integration
report includes both containers and before/after controls against the final image.
The fixture client checks and real container checks are deliberately separate claims.

CI results will be recorded in a subsequent chronology entry; see the new
remote-codex workflow for the four client targets and Linux x64 container job.

Final CI: [36300866276](https://github.com/bprashanth/io/actions/runs/36300866276),
all five jobs passed. Redacted report and run/job metadata are in ci-36300866276/.
This adds actual Linux x64 server evidence and four-platform transport fixture evidence.
