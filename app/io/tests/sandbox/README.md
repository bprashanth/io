# Bundled Codex sandbox conformance

Scope and stages: [proposal](../../../../proposals/sandbox-conformance-ci.md).
This suite exercises commands directly, without Electron, io startup gates, LLMs or keys.
A red job is useful baseline evidence, not an expected-failure pass.

From repository root:

```
node app/io/fetch-codex.js
node app/io/tests/sandbox/prepare.js
node app/io/tests/sandbox/run.js --runtime /absolute/path/to/standalone/runtime --out sandbox-results
```

`prepare.js` prints the runtime path and sets `IO_PROBE_RUNTIME`/`IO_PROBE_PYTHON` for later
GitHub Actions steps. It downloads only Python from io's pins, not reader packages or models.
For a local existing standalone runtime use `--runtime` and, if needed, `--python`.
The target must match the host's native architecture. System Python/venvs with an executable
outside the granted runtime are intentionally rejected; do not broaden grants to the home
folder to accommodate them.

`run.js` calls `codex.writeConfig` for Offline and Open, then executes `codex sandbox` with
each. It never asks io's `sandboxCheck` whether it should proceed. Unconfined controls run
before and after using identical paths/interpreter/targets. Forbidden files are beside the
workspace under the account home, never temp. Workspace names contain spaces; the escape
path is a symlink on Unix or a directory junction on Windows.

Networking uses ordinary direct TCP sockets to numeric IPv4 addresses, ignoring proxy
variables. Loopback and a non-loopback runner interface have an actual nonce-acknowledging
receiver. The public target defaults to example.com:443, resolved once outside the sandbox;
that probe only connects/closes and sends no content. `--external-host` selects a different
public control. A failed reachable control is a failure, never a successful denial.

Outputs: complete structured results, raw per-run stdout/stderr, actual generated profiles,
and a readable summary. Verdicts separate VIOLATION (forbidden action succeeded), CONTROL
ERROR (positive control unusable), EXECUTION ERROR (sandbox/interpreter failed), and PASS.
Host-side sentinel contents and listener events independently corroborate the probes.
Exit status is nonzero unless all required properties pass. Missing binaries, runtime or
observations never skip. Generated artifacts contain synthetic values and machine paths.

`node app/io/tests/sandbox/test_contract.js` checks harness classification using synthetic
observations; those tests are not sandbox evidence. `report.js <artifact-root> <output-dir>`
requires exactly one complete report for each of linux-x64, darwin-x64, darwin-arm64 and
win32-x64. Missing/duplicate reports or cells fail the aggregate gate.

The Windows baseline uses io's existing unelevated mode and the runner's actual account;
recorded group memberships identify that context. It does not claim ordinary-user Windows
coverage. Linux execution makes no automatic AppArmor or root-mode accommodation. Preserve
an unsupported result before any separately labeled administrator setup experiment.

Initial native baseline: [run 36296098245](https://github.com/bprashanth/io/actions/runs/36296098245).
Both Mac architectures passed. Stock Ubuntu could not start bubblewrap; Windows rejected
io's literal `/tmp` grant. The subsequent workflow explicitly installs io's narrow userns
AppArmor profile before the Linux probes and labels the report `io-apparmor-userns`.
`setup-linux.js` exports the exact applied profile as an artifact. This is a supported-setup
measurement, not a stock Ubuntu claim; the original failure remains in the archived baseline.
