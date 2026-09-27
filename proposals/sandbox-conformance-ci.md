# First pass: bundled Codex sandbox conformance

Status: first-pass implementation authorized by the owner on 2026-09-27. Subsequent stages
are deliberately separate. This supersedes the broad first-pass CI suggestion in
[the design-input entry](../chronology/2026-09-27T0955-dgx-security-ci-design-input.md).

## The question and stages

Does io's bundled Codex enforce the minimum command-sandbox contract io relies on across
Linux x64, native macOS x64, macOS arm64 and native Windows x64?

1. Build and run direct sandbox conformance probes; preserve the current behavior, including
   failures. Diagnose actual command behavior without invoking io's startup warning/gate.
2. After the baseline is understood, make the contract pass at the Codex sandbox level on
   each platform. Distinguish configuration fixes from upstream limitations or changes to
   the pinned release. Do not weaken the contract to make the matrix green.
3. Exercise io's actual launch/session path with the same probes and confirm it preserves
   those guarantees. Only then call the integrated application conformant.
4. Add the remaining security surfaces in separately scoped work.

The hypothesis supplied by the owner is Linux passes and macOS/Windows allow prohibited
operations. Test it; do not encode expected failures by operating system. Codex itself can
invoke native platform backends (including Seatbelt), so absence of Seatbelt code in io is
not proof of a macOS failure. A connection actually succeeding is a boundary violation;
a startup failure is an inability to demonstrate the contract, not evidence of a network
escape. Both fail the required suite, but reports must distinguish them.

## Runtime and policy

Use the complete Codex package pinned by `app/io/codex-pins.json` (currently 0.154.0),
verify its archive hash and runtime version, and call its `sandbox` subcommand directly.
Generate configuration with the actual `codex.writeConfig`, defaulting to Offline. Record
that configuration. Do not use `sandboxCheck` or Electron to decide whether to run probes.
Use standalone Python from io's Python pins, needing only its standard library. No model,
API key, proxy, scanner, Electron installation or live LLM response is needed.

CI matrix: `ubuntu-24.04` x64, `macos-15-intel` x64, `macos-14` arm64,
`windows-2025` x64. Explicit labels still receive updates: capture runner image version,
OS build, interpreter location/version, process architecture, account privilege context,
Codex version and package/binary hashes. Linux arm64 on the DGX is supplemental evidence,
not a replacement for x64 CI. A normal-user Windows experiment is desirable after the
baseline, reported separately from GitHub's default administrator/UAC-disabled context.

## Minimum contract

| Property | Required behavior |
|---|---|
| Workspace read and write | Both succeed and content is verified |
| Outside read | Denied: io intends read isolation as well as write isolation |
| Outside write | Denied, and the host verifies the sentinel was not changed |
| Direct TCP | Parent cannot connect to a reachable numeric address without proxy/DNS mediation |
| Child filesystem | Child cannot read/write the forbidden location |
| Child network | Child cannot make the same direct TCP connection |
| Path traversal | Symlink on Unix / directory junction on Windows does not expose outside content or allow writing it |

Each forbidden operation must succeed in an unconfined control using the same interpreter,
paths and destinations. Run controls before and after the restricted run. Also exercise the
same Codex launcher with io's Open profile: workspace operations and networking must work,
while filesystem isolation remains required. This distinguishes unavailable networking or
a dead command runner from enforcement. Report each destination separately: loopback,
runner non-loopback address, and a public TCP endpoint resolved by the harness before probing.
The public probe only connects/closes; no private data or application requests are sent.
Local listeners acknowledge synthetic nonces and record received attempts.

Sentinels live under a dedicated directory in the account's home, beside the workspace,
not under temp, the runtime, the bundled package, or any other explicitly granted root.
Check canonical paths and the generated grants. Keep probe code/manifest inside the workspace.
Child execution uses the same interpreter and inherits the policy. Use ordinary TCP sockets
(AF_INET/SOCK_STREAM), not privileged raw IP sockets and not HTTP clients honoring proxy vars.

## Test discipline and output

- Missing binary, wrong architecture/version, missing runtime, failed controls, crashes,
  missing output and unsupported policy all fail; none may silently skip or count as denial.
- Scrub no-wall/no-sandbox/test simulation settings. Never fall back to unwalled execution
  for the restricted run. Run trusted setup separately from the unprivileged probes.
- Do not disable AppArmor globally, run probes as root, broaden grants, or modify the
  product profile merely to obtain a passing baseline. If Ubuntu needs io's documented
  narrow AppArmor setup, preserve the initial result and label any after-setup experiment.
- Record successful forbidden operations as violations even if another check also errors.
- Check host-side file contents and local listener events, not just process exit codes.
- Preserve JSON, per-run stdout/stderr, generated profiles and a human-readable matrix even
  when a job fails. No provider credentials or real user data in artifacts.
- CI jobs use contents-read, no release publishing, no paid models, fail-fast false, and
  artifact upload/summary aggregation even after failure. Branch CI is sufficient initially;
  PR runs can gate subsequent changes. Do not treat baseline red as an expected-failure pass.

Rows in the matrix: workspace read/write; outside read/write blocked; direct TCP blocked;
child outside read/write blocked; child TCP blocked; symlink/junction read/write blocked.
Cells distinguish PASS, VIOLATION, CONTROL ERROR and EXECUTION ERROR, with evidence paths.
A report generated from incomplete/missing matrix artifacts must itself fail.

## Deliberately later

Provider proxy/tokenization; credentials and secret leakage; private attachment transitions;
Electron viewer/toolbox isolation; io fail-closed behavior; privileged broker/tool paths;
other full-application functionality. CI bootstrap is supporting plumbing, not a mandate to
expand the tests into those surfaces. Screenshots are not needed for this headless first pass;
real browser testing resumes when the integrated io stage begins.
