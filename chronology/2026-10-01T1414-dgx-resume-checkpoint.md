# Resume here: remote IO experiment checkpoint

## Observed on 2026-10-01

Owner reports server and laptop on `remote-codex/experiment` at
`775d06b5691100000aed7d5ef049ecb27c10355d`, with an empty git diff.
This agent's checkout instead reports `fdc6457fa2f91f38b9d9506901823a5a0dd52200`
on the same branch, eight commits ahead. The reported commit is an ancestor and predates
V1 gateway/local-diagnostic work. Do not treat the machines as synchronized until checked in
the actual terminals. No branch, service or runtime was changed for this checkpoint.

Tracked changes were empty before adding this checkpoint; `docs/sandbox.md` was already
untracked and was left untouched. `git diff` alone does not report untracked files.
Machine-readable observations: [checkpoint.json](../benchmarks/runs/2026-10-01-resume-checkpoint/checkpoint.json).

Docker and the user service bus are inaccessible under this session's permissions. Their
errors do not prove either service is down. Current laptop, Cloudflare route and remote branch
head were not independently verified. The Git directory is read-only: these new checkpoint
files are not committed/pushed by this agent.

## Where the implementation stands

- Earlier `775d06b`: remote container prototype and browser OAuth callback/CI work.
- `3704531`: Cloudflare identity → persistent user workspace → private Docker runtime;
  local synthetic diagnostic, always-remote V1, conversation selection, explicit file copies.
- `b6a6b3a`: Access sign-out, readable gateway errors and CI evidence.
- `fdc6457`: final verification record. This is the locally observed V1 baseline.

The last measured September baseline is 58 gateway/container checks, DGX diagnostic17/17,
real Electron interaction/screenshots, and two CI workflows with five successful jobs each.
Those portable client tests do NOT mean native Windows sandbox conformance passed.
See [final verification](2026-09-27T1737-dgx-v1-final-verification.md) and
[existing benchmark index](../benchmarks/runs/2026-09-27-v1-gateway/README.md).
No benchmark or UI test was rerun for this documentation-only checkpoint.

Still unverified in this record: a completed Cloudflare human login followed by a fresh
ChatGPT-authorized model conversation through the V1 gateway, and real office laptop
capability reports. Earlier direct remote OAuth success is not proof of that new full path.
Main IO UI consolidation, automatic local/remote routing and production hosting hardening
remain deferred. Codex stays pinned to0.154.0.

## Minimum checkpoint before taking a break

1. Compare `git branch --show-current`, `git rev-parse HEAD`, and `git status --short` on both
   actual machines. Keep the mismatch above explicit; do not reset either checkout to resolve it.
   If the intended shared baseline is V1, fetch and fast-forward to the branch containing
   `fdc6457` or a verified successor. Stop if fast-forward fails. Preserve untracked owner work.
2. Commit this chronology entry and its one JSON manifest on the chosen shared branch, then
   push and fast-forward the other machine. Optional lightweight tag:
   `git tag io-v1-checkpoint-2026-10-01` and
   `git push origin io-v1-checkpoint-2026-10-01` after the checkpoint commit.
   The tag protects a recognizable code/evidence revision; it does not snapshot a running server.
3. There is no need to rerun the entire suite, rebuild images or redesign anything merely to pause.
   If a workspace contains irreplaceable files, download them or make a separate private backup
   before leaving. Never add auth caches, JWTs, gateway SQLite data or workspace archives to git.

This checkpoint preserves the reproducible experiment and its evidence, NOT live files/login.
A true runtime backup also needs a consistent gateway SQLite backup (including WAL state),
matching per-user Docker state/workspace volumes, image identity and service configuration,
kept privately outside the repo. No such backup was performed here. The legacy tmpfs runtime
is ephemeral and must not be relied on to retain data over the break.

## Exact resumption sequence

Start by reading this file; do not reconstruct the project from the chat transcript.

On both machines, verify branch/HEAD/status as above. For an ordinary authorized terminal,
fast-forward synchronization, if needed, is:

```sh
git fetch origin
git merge --ff-only origin/remote-codex/experiment
```

On the server, check rather than assume the previous deployment:

```sh
systemctl --user is-active io-v1-gateway.service
docker ps --filter name=io-v1- --format '{{.Names}} {{.Status}} {{.Ports}}'
docker ps --filter name=io-remote- --format '{{.Names}} {{.Status}} {{.Ports}}'
curl --max-time 5 -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8789/identity
```

Expected unauthenticated HTTP401 means the gateway listener is answering; it does not prove
authenticated routing. Last September layout was V1 gateway8789, legacy prototype8787,
test-only fixture8788 (stopped). Confirm the live Cloudflare tunnel targets the V1 gateway;
never point it at the signed-fixture test server. Do not delete a legacy workspace to free a
port without checking for needed files. If setup is missing, use the
[gateway README](../app/io/gateway/README.md), not the old connection-file/SSH instructions.

On the laptop, from a checkout that actually contains V1:

```sh
IO_GATEWAY_URL=https://io.idli.cc app/io/gateway/run.sh
```

First useful next experiment: complete Cloudflare login and ChatGPT browser OAuth; upload a
synthetic CSV (`name,value` with rows `alpha,2` and `beta,3`); ask Codex to write a total of5 to
`result.csv`; download and check it. Start a second conversation, reopen the first, then
close/reopen IO and verify files/conversations persist. Use Sign out of IO to test a second
approved identity gets a separate workspace. Record actual results/screenshots and the exact
code revision in a NEW chronology entry and benchmark directory. Do not infer success from
old fixtures. The local diagnostic remains non-gating: all V1 work executes remotely.

Agent starter: “Read this checkpoint and linked evidence, verify both revisions and service
state, then finish the authenticated laptop → Cloudflare → gateway → Codex acceptance test.
Do not expand into main UI consolidation or native Windows sandbox repair yet.”
