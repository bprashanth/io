# Local execution or shared remote execution: minimum pilot

As of 2026-10-11, this checkout and the remote branch were at `fdc6457`, which contains V1.
`775d06b` predates it by eight commits. Check the actual laptop revision rather than assuming
matching branch names mean matching code. No native Windows fix or automatic local/remote
selection was introduced. This page describes an explicitly managed pilot, not a production
release guarantee.

## A. Execute on each person's laptop

There is no server or Cloudflare dependency for this path. Use the existing main application.

1. Fetch/fast-forward the agreed branch, install the app's normal dependencies and fetch its
   pinned Codex. Use one tested revision on all pilot laptops; do not mix candidate Codex builds.
2. Prepare standalone Python and run the full diagnostic on each laptop. The existing desktop
   startup `wallProbe` is too narrow to substitute for this qualification.

   ```sh
   node app/io/fetch-codex.js
   node app/io/tests/sandbox/prepare.js
   node app/io/diagnostic/diagnose.js \
     --runtime "$HOME/.io-conformance-runtime/$(node -p 'process.platform + "-" + process.arch')/runtime" \
     --out /tmp/io-local-qualification
   ```

   Require `capability.json` status PASS, inspect the version/backend and all required rows.
   FAIL or INCONCLUSIVE does not qualify a machine. On Linux, apply the offered narrow AppArmor
   setup if needed, then retest. Do not enable a no-wall bypass, broaden roots or ignore a failed
   positive control to make a report green. Retest after relevant OS/Codex/profile changes.
   This report says `executionMode: remote` because it was designed for V1; it does not switch
   either launcher. Choosing local execution here is an explicit pilot/operator decision.
3. Launch the existing local app on Linux/macOS with old remote/development overrides removed:

   ```sh
   env -u IO_REMOTE_CONNECTION -u IO_CODEX_NO_SANDBOX -u IO_CODEX_NO_WALL \
     -u IO_SANDBOX_TEST app/io/run.sh
   ```

   Complete ChatGPT browser login and a synthetic file→command→result test in Offline mode.
   Close/reopen and verify expected conversation behavior. Do not choose the legacy unwalled
   fallback for a supported laptop. Record its OS/build, pinned version and report.

Linux has demonstrated support after appropriate host setup. Mac sandbox CI passed, but each
actual desktop install still needs this acceptance test. Native Windows remains unqualified
by current evidence; “whatever works” means passing the same contract, not merely launching.
A local-capable office rollout can initially limit support to the machines that pass. It does
not need to wait for Windows remediation. GUI packaging/signing and broader proxy/viewer tests
remain separate work; the command sandbox suite alone does not prove the entire app secure.

## B. Execute on this Linux server, from many laptops

One shared gateway and hostname serve all users. One persistent workspace/container belongs
to each Cloudflare identity; several conversations share it. Laptops require neither Docker
nor their own native Codex sandbox for remote execution.

1. **Server, once:** verify `systemctl --user is-active io-v1-gateway.service` and an unauthenticated
   `curl --max-time 5 -i http://127.0.0.1:8789/identity`. Expected: active and HTTP 401.
   These were verified October 11. The image and nested command sandbox were also tested.
2. **Cloudflare, once:** confirm the existing `io.idli.cc` tunnel targets `http://localhost:8789`
   and Access permits every intended pilot identity. Change it only if it still targets 8787.
   Current tunnel destination was not verified through the dashboard. The old 8787 prototype
   container is no longer running here. No SSH tunnel or per-user connection JSON is needed.
3. **Each laptop:** use the same tested V1 revision, install Electron dependencies once, launch:

   ```sh
   npm ci --prefix app/io
   IO_GATEWAY_URL=https://io.idli.cc app/io/gateway/run.sh
   ```

   Windows PowerShell:

   ```powershell
   npm ci --prefix app/io
   $env:IO_GATEWAY_URL='https://io.idli.cc'
   & .\app\io\node_modules\.bin\electron.cmd .\app\io\gateway\desktop.js
   ```

   Log into Cloudflare, then ChatGPT using browser OAuth. Device-code sign-in need not be enabled.
   Missing local diagnostic prerequisites may yield INCONCLUSIVE; V1 still executes remotely.
4. **Acceptance before inviting everyone:** test two different allowed Cloudflare identities
   from two laptops concurrently. For each, upload a synthetic CSV, ask Codex to compute a
   result, download it, start/resume two conversations, close/reopen and confirm persistence.
   Verify one identity cannot access the other's workspace. Restart the gateway and each test
   runtime and verify reconnection and persistence. Record this real authenticated result;
   signed test identities and previous CI are not a substitute for this missing human test.
5. **Small office pilot operations:** back up the gateway mapping database and matching workspace/
   auth volumes privately and consistently, test restoration, monitor free disk/container health,
   and assign an operator for restart/update failures. Current per-container CPU/memory/PID limits
   exist; disk quotas, admission limits, idle reclamation and production hardening are not built.
   Do not describe arbitrary-scale or unattended production use as proven.

All V1 traffic goes through the gateway; closing IO keeps the workspace. “Sign out of IO” clears
local Access state; it does not delete the server workspace. “Delete workspace” does delete
its files/auth. Files are uploaded copies, and model traffic is not locally masked in this
remote experiment. Main IO interface consolidation is still deferred.

## Testing and pushing a stable pilot revision

Use `remote-codex/experiment`, review `git status --short` (including untracked files), and push
an explicitly reviewed commit. Require the V1 gateway and legacy remote CI workflows to pass.
Keep their run links and the real two-laptop acceptance results in chronology/benchmarks. Then
tag that accepted revision and deploy the same tag on pilot laptops and server; retain the
previous server image/code and private backups for rollback. Updating server source alone does
not rebuild its Docker image or restart its gateway service: deploy those deliberately together.
Do not put auth caches, SQLite state, connection capabilities or user documents in git.

Minimal recommendation: offer A only on individually qualified machines; use B for the common
cross-platform pilot after the real two-user acceptance test. V1 does not automatically choose
between them. No broad redesign is needed to perform those next tests.
