# DGX V1 gateway evidence, 2026-09-27

- `integration.json`: 39 real Docker/gateway checks, two RSA-signed synthetic identities,
  persistent file/state storage, runtime restart/recreation, ownership denials, uploads,
  conflicts, downloads and fixed-port service routing.
- `lifecycle.json`: 19 additional checks: inter-container TCP isolation with a positive control,
  Codex cannot read controller state (positive control outside its sandbox), two synthetic
  conversation metadata entries/list/delete, and complete workspace/volume/network deletion.
- `diagnostic/capability.json`: live DGX Linux arm64 report, 17 properties PASS, executionMode
  remains remote; underlying evidence in its timestamped raw directory.
- `ui-results.json`: real Electron, local signed-identity gateway, real Docker and Codex browser
  OAuth startup, attachment round-trip, live-service download, diagnostic display, no renderer
  errors. No completed human authorization or model turn in this test.
- `cloudflare.json`: real public Access redirect, team signing-key verification of redirect
  metadata, production listener refusing absent credentials and non-app signed tokens.
- Screenshots (ignored by git; available on this DGX): `v1-initial.png`,
  `v1-local-diagnostic.png`, `v1-files.png`, `v1-browser-oauth.png`, `cloudflare-sign-in.png`.

The original signed-in prototype on port 8787 was never stopped or copied. New production
configuration listens on 8789; no Cloudflare admin/tunnel token was read. Local test credentials
and SQLite state live under `/tmp/io-v1-fixture`, never in these artifacts. The test-only gateway
on 8788 is not suitable as a Cloudflare tunnel destination.

Failures corrected during development: nested `session_meta.payload` parser; diagnostic dialog
showed a stale initial result if opened before background completion; test driver initially
missed the explicit upload confirmation and read the download before completion. The extra
controller-state test initially required PermissionError, while bwrap correctly hid the path
with FileNotFoundError; it now requires an existing outside-sandbox positive control and an
explicit filesystem denial, never interpreter failure. Lower-model review identified an
unbounded lifecycle lock map; weak references now retire unused locks.

Unmeasured: completed Cloudflare human sign-in, a fresh ChatGPT-authorized model turn/resume
through this new gateway, real Windows/macOS office diagnostic runs, arbitrary live-app rendering,
production containment/quotas/storage recovery and migration of the prior ephemeral workspace.

The initial CI run `36317584243` passed on GitHub Linux x64; its integration/lifecycle JSON is in
`ci-initial/`. Both that workflow and the legacy remote workflow passed all five jobs. The final
Electron rerun additionally verifies Access sign-out closes the client while preserving the
remote workspace. The final client rejects raw HTML error pages with a readable message.
