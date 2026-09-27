# DGX: first native Codex sandbox CI matrix

[Run 36296098245](https://github.com/bprashanth/io/actions/runs/36296098245), commit cb3386b,
executed the direct suite on all four requested native targets. Evidence is archived under
[ci-36296098245](../benchmarks/runs/2026-09-27-sandbox-conformance/ci-36296098245/).
The [matrix](../benchmarks/runs/2026-09-27-sandbox-conformance/ci-36296098245/sandbox-conformance-matrix/matrix.md)
is intentionally red. No expected-failure allowance, no io UI gate, no model credentials.

| Target | Observation |
|---|---|
| macOS Intel (macos-15-intel) | All 17 properties PASS |
| macOS arm64 (macos-14) | All 17 properties PASS |
| Linux x64 (ubuntu-24.04) | Both unconfined controls pass; both Codex runs fail to start |
| Windows x64 (windows-2025) | Both unconfined controls pass; both Codex runs reject the profile |

Linux stderr: Offline `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`;
Open `bwrap: setting up uid map: Permission denied`. Windows stderr:
`Error: filesystem path /tmp must be absolute, use ~/..., or start with :` (backticks omitted).
These are EXECUTION ERROR cells, not evidence of filesystem or network escape.

The hypothesis that macOS would require additional Seatbelt code in io was refuted for
these runners/pins: io's generated profile already activates Codex's own native sandbox.
The controlled paths and direct TCP probes pass on both architectures, including child
processes and symlink traversal. This says nothing yet about io's integrated launch path.

The local DGX arm64 [baseline](../benchmarks/runs/2026-09-27-sandbox-conformance/dgx-baseline/summary.md)
also passed all 17 properties using freshly downloaded standalone Python 3.12.14. A
[negative classification control](../benchmarks/runs/2026-09-27-sandbox-conformance/harness-negative-control.json)
feeds the real unconfined observations to the classifier and correctly produces violations.
The harness's synthetic classification/matrix integrity checks pass; they are not sandbox
observations. Smaller Cursor gpt-5.4-mini-high agents wrote Python probe plumbing and report/
classification tests; the coordinating agent reviewed them and fixed duplicate-row handling.

## Next experiment

To get past launch errors and measure command enforcement:

- Remove the literal Unix `/tmp` grant on Windows only; retain Windows' actual temp grant.
  This is a product profile syntax repair, not a relaxation of the intended boundary.
- On the Linux runner install the exact narrow AppArmor userns profile io already offers,
  using an exported existing `linuxFix` helper. Keep the probes unprivileged, leave AppArmor
  enabled and record `provisioning: io-apparmor-userns`. Preserve the above stock-image failure.
  This subsequent run will be explicitly after setup, not a claim about stock Ubuntu.

Retest before the next push: 19 existing launcher tests pass with no wall skip on DGX;
classification integrity checks pass; all 17 direct DGX probes pass again. No Windows/Mac
execution beyond the archived baseline is claimed yet. Standard-user Windows, other OS
builds, io's launch gate, model tools, proxy, credentials, viewer and broker remain outside
this measurement. First-stage screenshots are inapplicable: this suite is headless.
