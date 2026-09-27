# Windows decision experiment: ordinary-machine handoff

The current hosted results do not establish a passing Windows backend. Do not ask
an NGO participant to approve privileged setup merely to make these diagnostics run.
The ordinary-user acceptance stage begins after a full backend passes CI, or as a
separately consented investigation on a disposable Windows test machine.

For a future test, use a dedicated standard (non-administrator) Windows account and
a synthetic checkout. Record Windows release/build, filesystem, administrator/UAC
context, restrictions, security software and whether setup required an administrator.
Never disable antivirus, grant root reads or choose no-sandbox to obtain a pass.

From PowerShell in the repository:

```powershell
node app/io/fetch-codex.js
node app/io/tests/sandbox/prepare.js
./app/io/tests/sandbox/windows/environment.ps1 -Out windows-local-results/environment
$runtime = Join-Path $env:USERPROFILE '.io-conformance-runtime/win32-x64/runtime'
node app/io/tests/sandbox/run.js --runtime $runtime --windows-diagnostic elevated --out windows-local-results/pinned-elevated
```

For the separately pinned candidate (does not upgrade io):

```powershell
node app/io/tests/sandbox/candidate.js 0.157.1
node app/io/tests/sandbox/run.js --runtime $runtime --candidate 0.157.1 --windows-diagnostic mxc --out windows-local-results/candidate-mxc
```

On currently measured hosts, candidate elevated rejects io's restricted-read policy
and MXC is unavailable. Do not reinterpret either as a pass. These commands may
require administrator-approved Codex setup; ordinary-account runtime and one-time
setup are distinct. Capture outcomes including refusal/policy/UAC limitations, not
just successful executions. Reports include local account/machine paths; inspect
before sharing. Never share `.sandbox-secrets` or authentication files.

No Windows 11 desktop version or ordinary-user run is represented by GitHub's
Windows Server/admin measurements. The existing startup `wallProbe` is narrower
than this suite and is not yet the proposed runtime conformance gate.
