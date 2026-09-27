# io diagnostic capability check

This directory holds a local-only diagnostic wrapper around the existing sandbox suite.
It does not upload anything and it does not try to install elevated setup automatically.

## Prepare the runtime

From the repository root:

```sh
node app/io/tests/sandbox/prepare.js /tmp/io-probe-runtime
```

`prepare.js` fetches the pinned standalone Python runtime for the current platform and
prints the runtime path. The command also sets `IO_PROBE_RUNTIME` and `IO_PROBE_PYTHON`
for CI steps that consume its output.

## Run the diagnostic

```sh
node app/io/diagnostic/diagnose.js --runtime /tmp/io-probe-runtime/runtime --out /tmp/io-diagnostic
```

That command runs the real sandbox suite into `/tmp/io-diagnostic/raw-<timestamp>/`, then writes
`/tmp/io-diagnostic/capability.json`.

## Reclassify an existing report

```sh
node app/io/diagnostic/diagnose.js --runtime /tmp/io-probe-runtime/runtime --out /tmp/io-diagnostic --report-existing /path/to/results.json
```

Use `--report-existing` when tests or manual checks should classify a previously generated
`results.json` tree instead of running the probes again. The classifier accepts a directory
that contains one `results.json` tree, or a direct path to a `results.json` file.

## Output

`capability.json` records:

- `status`: `PASS`, `FAIL`, or `INCONCLUSIVE`
- `executionMode`: always `remote`
- `routingChanged`: always `false`
- `version`, `platform`, `build`, and `backend`
- the individual probe results and the rationale for the final status

The raw sandbox reports stay on disk under the output directory when the diagnostic runs
live. Synthetic fixture paths in reports can expose your username or workspace path, so
keep the artifacts local unless you have already redacted them.

Each run has a fresh raw directory, so old passing evidence cannot qualify a failed rerun. The subprocess has a five-minute timeout; this is a first full diagnostic, not yet a tuned startup micro-test. A missing standalone Python or unavailable sandbox yields INCONCLUSIVE. Download the bundled Codex first with `node app/io/fetch-codex.js` if the checkout has not been bootstrapped.
