# DGX: workflow proposal and security CI design input

The owner requested that the workbook discussion become a proposal, and asked for an inline
brief to pass to another agent designing cross-platform security CI. Added
[workbook-to-tracker](../proposals/workbook-to-tracker.md). No workflow implementation,
security behavior change, GitHub dispatch or push was requested or performed.

Inspected `.github/workflows/package.yml`, `installation/smoke/smoke.js`, `app/io/codex.js`,
`fetch-codex.js`, `codex-pins.json`, launcher/proxy/key/attachment tests, and renderer boundaries.
The existing workflow packages and cold-start-smokes Linux x64, Windows x64, macOS arm64,
and macOS x64 (the latter on arm64/Rosetta). It is not a security suite, has no PR trigger,
and runs on pushes to windows/main or manual dispatch. Its contents-write permission serves
release publishing; a separate security workflow should only need contents-read and no
provider secrets. No recent GitHub run history was inspected; these are configuration facts.

Codex is pinned to 0.154.0 / rust-v0.154.0, with non-null package SHA-256 values for all five
targets including Linux arm64. Fetch verifies the tarball and extracts the complete package,
including codex-code-mode-host. It writes VERSION.json; the app resolves its own bundled
binary, not PATH. The fetcher still permits a future null hash as a first-fetch convenience;
CI should reject null pins, execute --version, and check packaged resources. Model aliases
are not immutable model snapshots. Electron/node dependencies have semver ranges; a CLI pin
alone does not make the whole environment immutable.

The previous DGX result remains 77 passing tests, not 77 proven cross-platform tests.
Concrete harness issues: the launcher skips absent binaries/runtime and skips the wall
control if the wall fails, while still incrementing its pass count. The control hardcodes
.venv/bin/python3, unlike the platform-aware sandboxCheck test. Fixtures/assertions also
contain POSIX paths and a Unix command lookup. Key-store mode assertions intentionally skip
Windows; Windows ACL privacy remains unproven. Handover symlink fixtures need Windows-aware
handling. Python proxy/service tests import reader dependencies despite a stale stdlib-only
comment. No tests were rerun for this documentation-only turn.

A required boundary test must independently prove inside read/write succeeds, outside
read/write fails, and a readable control exposes its synthetic sentinel. Place forbidden
fixtures outside workspace, temp, runtime, package and other granted roots; temp is explicitly
granted. Distinguish denial from absent files, broken Python and process startup failure.
Use io's real profile and bundled binary, without bypass flags, simulated verdicts or silent
unwalled fallback. Add direct TCP network probes with reachable controls and receiver-side
observations; a curl error alone can be DNS, unavailable destination or proxy configuration.
The command wall, provider proxy, viewer, and privileged toolbox are distinct test surfaces.

Windows deserves first investigation. io sets [windows] sandbox="unelevated". Current
[OpenAI Windows documentation](https://learn.chatgpt.com/docs/windows/windows-sandbox)
describes weaker environment-level offline controls for that mode. The local Codex source
checkout reports tag rust-v0.154.0; its windows-sandbox-rs/src/env.rs also contains dead proxy
addresses and tool-offline environment controls. This is a reason to test direct sockets,
not evidence that a Windows escape was executed. Filesystem policy compatibility and native
command/process lifecycle remain unmeasured here.

[GitHub's runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
lists native Linux arm64 and Intel/arm64 Mac runners in addition to x64 Linux/Windows.
Use explicit OS labels and capture image/build/architecture; labels still receive updates.
Windows hosted jobs run as administrators with UAC disabled, so their default user is not
representative of a participant's ordinary account. A standard-user Windows run and real
Windows desktop acceptance remain necessary before making broad end-user claims.

Recommended order to the designer: strict native sandbox probes, portable proxy and key/
attachment tests, then packaged Electron viewer/toolbox/attachment transitions with synthetic
provider responses. Report protected+usable separately from correctly refusing an unsupported
wall. Missing controls, skipped probes, startup errors and inability to enforce the policy
must not satisfy the security claim. Linux AppArmor before/after setup should be separately
reported; never quietly disable AppArmor or run the tested command as root to turn a check green.
No claim is made that a single hosted OS image proves every supported laptop distribution.
