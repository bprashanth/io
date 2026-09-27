# DGX: sandbox baseline established; Windows needs a different backend

This completes the scoped first pass described in
[the proposal](../proposals/sandbox-conformance-ci.md). The suite is implemented and has
run on all four requested native CI targets. It measures bundled Codex commands directly,
not whether io permits a session to start. The required aggregate job is deliberately red.

## Observations and evidence

Three CI runs are archived in
[benchmarks](../benchmarks/runs/2026-09-27-sandbox-conformance/README.md):

1. [36296098245](https://github.com/bprashanth/io/actions/runs/36296098245), cb3386b:
   both Mac architectures pass; Linux cannot start bubblewrap; Windows rejects literal `/tmp`.
2. [36296267568](https://github.com/bprashanth/io/actions/runs/36296267568), 0e7cdc4:
   Linux passes after io's narrow AppArmor setup; both Macs pass; Windows now rejects the
   backend's inability to implement restricted reads. No network escape is claimed by this run.
3. [36296400960](https://github.com/bprashanth/io/actions/runs/36296400960), 5888d11:
   repeats those required results and adds explicitly separate Windows backend diagnostics.

The final required matrix has 17 PASS cells each for Linux x64, macOS Intel and macOS arm64,
and 17 EXECUTION ERROR cells for Windows x64. Linux probes run as uid 1001 after the setup;
Mac probes as uid 501. The exact runtime is standalone Python 3.12.14; the complete Codex
package is SHA-256-checked and reports `codex-cli 0.154.0`. Runner image versions, source
hashes, profiles, before/after controls and raw stdout/stderr are in each artifact.

Windows exact-profile error, directly from Codex:

> Restricted read-only access requires the elevated Windows sandbox backend

This is not io showing a warning or blocking the experiment: Electron and `sandboxCheck`
are never invoked by the probe runner. The pinned Codex backend itself refuses this policy.
The local tag rust-v0.154.0 source agrees: `windows-sandbox-rs/src/lib.rs` and
`unified_exec/backends/legacy.rs` reject restricted reads for the WRITE_RESTRICTED-token
backend. Its restricting SIDs apply to writes, not reads.

## The actual Windows network violation

To isolate networking, a diagnostic adds `":root" = "read"` to the generated policy while
keeping networking disabled and selecting the existing unelevated backend. This intentionally
relaxes the read contract so Codex can start; it is NOT io conformance and cannot satisfy the
aggregate gate. Its artifacts are outside the aggregate download pattern, and the reporter
also rejects `diagnostic` / `conformanceEligible: false` even if misrouted into that pattern.

In this diagnostic, Offline Python parent AND child each returned:

> connected to 172.66.147.243:443

That was example.com's resolved numeric address. They used direct AF_INET/SOCK_STREAM
connections, no proxy-aware HTTP client or DNS inside the sandbox, and sent no content to
the public endpoint. Loopback and non-loopback local receivers independently acknowledged
four parent/child messages while networking was disabled. Both unconfined before/after
controls and the Open sandbox controls worked. Outside writes and junction writes were
blocked; outside reads succeeded as expected under this deliberately broader diagnostic.

Thus the first pass has genuine forbidden network behavior to report, rather than only a
warning or startup failure. It does NOT establish that the rejected full io policy can be
bypassed. The account was GitHub's `runneradmin`; standard-user Windows is not measured.

## Elevated diagnostic, not a completed fix

A second diagnostic preserves the complete filesystem/network policy and changes only
`[windows] sandbox` to `elevated`. Offline failed during SpawnChild:

> CreateProcessAsUserW failed: 5 (Access is denied.)

Open then executed successfully, allowed workspace operations and network access, and denied
outside reads/writes and junction access for parent and child. This is useful evidence that
the elevated filesystem implementation can enforce the intended grants, but the Offline
failure means the overall diagnostic remains FAIL. The experiment used different fresh
Codex homes for the two profiles, as recorded; do not infer a successful offline transition.
Do not change io's default to elevated and call the problem solved on this evidence alone.

## Changes and validation

- Added direct Python parent/child probes, Node orchestration, strict result classification,
  and native four-target CI. No model secrets, package publishing or main-branch changes.
- Controls run before/after; Open is an additional network-allowed sandbox control. Host
  sentinel checks and receiver events independently detect violations. A crashed interpreter,
  missing row/report, duplicate row/target or unavailable control cannot make the gate green.
- Repaired the invalid Windows `/tmp` grant, retaining the real Windows temp directory.
- Exported the existing narrow `linuxFix` helper for explicit CI provisioning. AppArmor
  remains enabled and probe processes remain unprivileged. Initial stock failure is preserved.
- Added separate diagnostics without changing io's default Windows backend. Documented which
  diagnostics alter the policy and made them ineligible for the required aggregate gate.
- 19 launcher tests pass on DGX with the wall control actually executed. Harness integrity
  checks pass locally and in all native jobs. DGX arm64 direct conformance also passes all
  17 properties. Source/profile/artifact evidence, not source inspection alone, supports the
  native Linux/Mac results. Smaller Cursor models handled bounded probe/report/test plumbing.

The experiment branch `sandbox-conformance/initial-baseline` was pushed to run the requested
CI. No PR, merge, release, protected-branch setting change or main push was performed.
Preexisting September 14 untracked evidence and `docs/sandbox.md` remain untouched.

## Next stage and what was not tested

First resolve Windows at the Codex level: investigate elevated Offline SpawnChild error 5,
including runtime/workspace ACLs, sandbox identities and cold setup, then rerun the exact
contract under ordinary-user operation with any administrator provisioning explicitly
separated. Do not hide unsupported restricted reads by granting read-all; the diagnostic
shows why that is not io's intended guarantee. Any pin change should retain these same probes.

macOS did not fail the anticipated way: bundled Codex already supplies Seatbelt enforcement.
No additional io Seatbelt implementation was necessary for this direct baseline. This does
not prove io's actual launch/session path yet; that is the next stage after Codex conformance.

Not tested here: ordinary-user Windows, other Windows desktop/OS builds, Linux without setup
beyond the failed baseline, every supported Mac version, privileged IP raw sockets, IPv6/UDP,
all possible filesystem escapes, or any model-selected tool call. The network probes are
ordinary direct TCP sockets. This is a regression contract, not an exhaustive escape audit.

Proxy/tokenization, credentials, attachment transitions, Electron viewer/toolbox, io's
fail-closed behavior and privileged broker/tool paths remain explicitly deferred. No browser
screenshots are claimed for this headless stage. See the
[field note](../narrative/2026-09-27-sandbox-conformance-before-io.md) for the interpretation.
