# Local/remote decision evidence

Previous baseline: `../2026-09-27-sandbox-conformance/ci-36296400960`.
New experiment runs will be archived here by GitHub run id. No model credentials
or real user data are required. Windows Server results are not Windows 11 results.

## Source inspection before execution

- Product stays at Codex 0.154.0. Candidate release 0.157.1 is separately pinned in
  `app/io/tests/sandbox/candidate-pins.json`, including archive SHA256 and peeled
  source commit `36650394c5b38c2990ccf2a3457165ca3e9d9726` (annotated tag object is
  different). No floating latest package will be used by the experiment.
- 154 includes an early MXC adapter/availability metric, but no selector. 157
  exposes strict `windows.sandbox="mxc"`; `features.prefer_mxc` is disabled in
  these experiments so an elevated test cannot silently select MXC.
- [Pinned 157 MXC README](https://github.com/openai/codex/blob/rust-v0.157.1/codex-rs/mxc-sandbox/README.md)
  requires usable native PSEC and never uses the older AppContainer fallback.
- [Microsoft OS matrix](https://github.com/microsoft/mxc/blob/main/docs/process-container/os-version-support.md)
  distinguishes 24H2/25H2 from 25H2+ native PSEC. The broad MXC product floor is not
  the support floor for Codex's native-only integration. Runtime probes remain key.
- [Microsoft MXC README](https://github.com/microsoft/mxc) currently describes it as
  maturing and advises against treating its profiles as security boundaries. A
  passing small regression suite would not override that upstream qualification.
- [GitHub runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
  states Windows runners use administrator accounts with UAC disabled. Metadata
  collection records actual image/build/account/UAC/filesystem/firewall context.

The lower-model Cursor CLI source audit suggested desktop/token differences as an
error-5 hypothesis. That is not a demonstrated cause. We first rerun the actual
released backends and retain allowlisted `.sandbox/sandbox.log` files (never secret
caches). A command-launch failure cannot prove network confinement.

Validation before first CI: unchanged harness classification tests, 19 launcher
checks and 34 proxy tests pass on DGX. Windows behavior awaits native execution.

## First measurement: run 36310702342

All six required jobs failed. On both Server 2022 and 2025, pinned elevated now
launches and passes 13/17 properties: outside filesystem/junction boundaries and
public internet denial hold, but parent/child loopback and host-interface TCP
connect (four violations independently acknowledged by the host receiver). This
is not arbitrary LAN reachability: the non-loopback endpoint is the runner itself.
Error 5 did not reproduce on these clean jobs; the old and new 2025 images and
Codex binary hashes match. Earlier diagnostic order and Node 20 versus 22 are
hypotheses for a focused next run, not established causes.

Candidate elevated rejects default root-deny policies on both images, explicitly
requiring effective `:root` read access. Upstream has a test asserting this rejection
(`windows_elevated_setup_rejects_default_root_deny`); no grant will be widened here.
Candidate MXC explicitly reports unavailable on both images. No candidate passes,
so the planned ordinary-account acceptance and startup-smoke implementation gate
has not been reached. A daily sandbox log naming change was found in source;
collection now includes only `sandbox.YYYY-MM-DD.log` and legacy `sandbox.log`.

## Repeats and launch timing

- `ci-36310871779`: repeat six-case matrix with daily logs. Same candidate failures;
  clean pinned Server 2022 also had error 5 once, so history is not its sole trigger.
- `ci-36310871868`: 2x2 Node 20/22 and clean/prior-unelevated comparison on Server
  2025. Clean runs launched but violated local TCP; both prior-history runs failed
  first Offline launch with error 5. Open launched in all four.
- `ci-36311032651`: same 2x2 plus explicit two-second, same-profile retry only after
  error 5. Both history cases fail first then launch on retry. Original stderr and
  `firstAttempt` are preserved. All four final probes still have four local-TCP
  violations; none passes. This is strong setup-timing evidence, not a complete
  proof of the exact failed access check or a product workaround.
- `ci-36311032673`: final unchanged six-case matrix; both pinned runs launch and
  violate local TCP, elevated candidate rejects root-deny, MXC unavailable.

Source corroboration: 154 `windows-sandbox-rs/src/bin/setup_main/win.rs`,
`spawn_read_acl_helper`, starts the read-ACL helper with `.spawn()` and no wait;
refresh delegates read roots. This is a likely race mechanism. We did not rebuild
Codex with instrumentation or identify the exact object/ACE denied at process start.
No permission was broadened and no Windows product backend was changed.

`observations.json` indexes all 26 case reports from the five runs. Prior weakened
unelevated preparations remain separately named artifacts and never count toward
acceptance. `dgx-regression` contains a real 17/17 passing Linux arm64 run with the
same harness. Existing 19 launcher and 34 proxy checks and synthetic classifier
checks pass; no new UI behavior was introduced in this experiment.

Recommendation and limits: [narrative](../../../narrative/2026-09-27-local-remote-execution-decision.md).
Ordinary account, Windows 11 23H2/24H2/25H2, and Windows 10 remain NOT RUN. No Windows
backend passed the prerequisite gate; no local Windows support is claimed. No
pricing/latency benchmark, production fallback, or startup smoke gate was built.

Daily sandbox logs are committed as `.log.txt` (original `.log` files remain ignored).
Only synthetic-run allowlisted logs are archived; no authentication/secret caches.
[Final chronology](../../../chronology/2026-09-27T1531-dgx-execution-decision-results.md)
records conclusions, provenance and deferred stages.
