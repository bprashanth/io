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
