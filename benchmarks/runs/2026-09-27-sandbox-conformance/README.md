# Direct Codex sandbox conformance, 2026-09-27

Scope: [proposal](../../../proposals/sandbox-conformance-ci.md).
Results and limits: [chronology](../../../chronology/2026-09-27T1044-dgx-codex-sandbox-baseline-established.md).
Suite and reproducible commands: [README](../../../app/io/tests/sandbox/README.md).

| Evidence | What it measures |
|---|---|
| `dgx-baseline/` | All 17 properties pass locally on Linux arm64 with the existing AppArmor grant |
| `harness-negative-control.json` | Real unconfined observations classified as violations; a harness check, not a sandbox run |
| `ci-36296098245/` | Initial native baseline: Macs pass, stock Linux and Windows fail to launch |
| `ci-36296267568/` | After Windows temp-path correction and explicit Linux AppArmor setup: Linux/Macs pass, Windows backend rejects restricted reads |
| `ci-36296400960/` | Repeated required matrix plus separate Windows backend diagnostics |

Each `sandbox-<target>` artifact includes results.json, generated io profiles, per-run stdout/
stderr and summary.md. `sandbox-conformance-matrix` includes the required aggregate matrix.
The final matrix remains FAIL; there are no expected-failure passes or skipped boundaries.

`ci-36296400960/diagnostic-windows-backends/unelevated-network` adds root read permission
solely to let that backend execute network probes. Parent/child direct TCP connects succeed
in Offline: this violates the network contract. Its read successes are expected under that
explicitly broader diagnostic, not an escape from io's rejected full policy.

`.../elevated` changes only the backend. Open enforces filesystem boundaries; Offline fails
CreateProcessAsUserW with error 5. This is not a proven fix and does not change io's default.
Diagnostics are ineligible for the required matrix even if manually copied into its inputs.

These files contain synthetic sentinel values and public/runner-local network addresses.
No model requests, real user data, API keys or browser sessions are involved. Public TCP
probes connect/close without transmitting content. Local listeners exchange synthetic nonces.
