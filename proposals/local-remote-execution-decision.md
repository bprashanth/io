# Local versus remote execution decision experiment

## Decision and scope

Choose A: local-first, B: remote-first, or C: verified local execution with an explicit
remote offer on unsupported/inconclusive machines. Do not choose a weaker sandbox
or silently upload files to make a platform work. No production architecture switch
is authorized by a passing CI diagnostic alone.

Local means Codex, files, execution and the existing tokenizing proxy stay on the
user machine. Remote means the current separate io client controls Codex in a Linux
container. The remote experiment is architecturally viable (including user-confirmed
ordinary browser OAuth), but has no production account provisioning, billing,
durable storage, or local masking proxy. Its model-driven file round trip remains
less thoroughly demonstrated than its deterministic transfer/tool tests.

## Unchanged acceptance contract

Reuse `app/io/tests/sandbox/run.js` and `probe.py`: workspace read/write and ordinary
Python/subprocess work; forbidden reads/writes denied; raw numeric-IP TCP denied
Offline; parent and child confinement; junction/reparse traversal denied. Open is
an additional network-positive control with the same filesystem boundaries.
Unconfined controls before/after must succeed; independent host sentinels and TCP
receivers corroborate observations. A missing backend, missing observation, crashed
interpreter, inconclusive control or unavailable host cannot count as a pass.
Preserve the original Windows unelevated failure as baseline evidence.

## Stages

1. **Pinned elevated diagnosis.** Codex 0.154.0, exact io permission profile with
   only backend changed. Reproduce Offline CreateProcessAsUserW error 5, retain
   sandbox logs without `.sandbox-secrets`, and record OS/build, token/group context,
   filesystem, UAC, firewall and endpoint-security metadata. Compare startup paths
   with Open. Test targeted hypotheses individually; do not grant root reads, allow
   network or disable desktop isolation in a purported conformance fix.
2. **Candidate and MXC.** Pin the newer released package separately from io's
   product pin, with release tag, archive/binary hash and source identity. First
   establish whether MXC is actually selectable in the released executable; a crate
   or availability metric is not evidence of an execution backend. If unwired,
   document that and specify a separately labeled source-build experiment; do not
   silently run elevated under an MXC label. Compare the same probes and semantics.
3. **Ordinary Windows account.** After a backend passes hosted CI, run under an
   explicitly non-admin account. Separate one-time administrator provisioning from
   runtime identity. Hosted standard-user tests are useful diagnostics but are not
   ordinary Windows 11 desktop acceptance. Record whether IT/admin setup is needed.
4. **Desktop coverage.** Seek Windows 11 24H2, 25H2/current, and an older maintained
   build where available; record exact builds, edition, filesystem and restrictions.
   Windows 10 is a separate support decision. Hosted Windows Server 2022/2025 must
   never be mislabeled Windows 11. Unavailable targets remain NOT RUN.
5. **Startup smoke design.** Only after a candidate backend passes, package fast,
   synthetic checks matching the established contract. Existing io wallProbe is
   narrower and must not be represented as full conformance. Cache validity must
   include Codex/bundle hash, profile, backend, OS build, user and relevant setup;
   invalidate after upgrades and meaningful policy changes. A historical pass is
   not a permanent security guarantee. Measure duration before choosing a budget.
6. **Recommendation.** Publish the measured support matrix, ordinary-user setup
   burden, failure causes, costs/latency where measured, and an A/B/C recommendation.
   Unknown desktop results may justify C as a direction, not local Windows release
   support. Distinguish present recommendation from conditions that would change it.

## Accessible test surfaces now

DGX: source/package inspection, harness validation and Linux regression. GitHub:
real Windows Server runners and explicitly created standard accounts; full native
Linux/Mac suite remains available. No Windows 11 laptop/VM is currently available
in this session. Ask owner for a real-machine run once it can answer a concrete
question. Do not invent Windows 11 coverage from server build numbers.

All experimental runs have a separate label and output directory. No model keys or
user OAuth caches are needed. Product Codex stays 0.154.0 until a deliberate upgrade
review includes proxy compatibility and all target platforms. A failed experiment
job remains failed; artifact collection may continue but cannot change its verdict.

## Comparison and decision criteria

| Dimension | Local | Remote prototype |
|---|---|---|
| Sandbox | Per-device verified contract needed | Controlled Linux environment, outer hardening pending |
| Windows | Backend + OS + account/policy dependent | Execution independent; client compatibility still matters |
| Our compute cost | Low, not literally zero | Ongoing CPU/RAM/storage/network/operations |
| User hardware | Local Python/tools/scanner need resources | Lower execution requirements |
| Files | Local paths; no transfer to server | Explicit upload/download copies |
| Latency | No remote execution hop; model still remote | Network hop plus model latency |
| Offline | Local tools possible; ChatGPT conversation still needs network | Needs server connectivity |
| Operations | Cross-platform packaging/setup/support | Hosting, isolation, credentials and lifecycle |
| Upgrade risk | Codex + OS/policy interactions | Controlled server updates plus client protocol |
| Privacy | Existing local tokenization; provider traffic still exists | Server processes uploaded contents; no masking proxy yet |

A requires useful real Windows desktop coverage without unacceptable setup/support
burden. B is appropriate if no credible local support set remains after targeted
remedies. C is appropriate if a meaningful tested set passes but environment
variation remains. Current working hypothesis is C, not a predetermined result.
Fallback is an offer requiring informed consent to upload and disclosed hosted
pricing before workspace creation, never an automatic file transfer or charge.

## Deferred

Hybrid per-tool execution, MCP/local bridging, billing implementation, orchestration
at scale, durable storage, remote/main-UI integration, automatic sync and broader
proxy/viewer security tests. No new user flow is built merely to display an unproven
compatibility result.

## Evidence

Write chronology entries, reproducible commands and synthetic artifacts under
`benchmarks/runs/2026-09-27-execution-decision/`. Archive failures and source findings,
then synthesize into narrative once results support a recommendation.

## Decision after the September 27 available-host experiments

Recommend C as the product direction, with current Windows execution remaining
remote. Pinned elevated violates local TCP isolation even when its launch works;
newer elevated refuses restricted reads; strict MXC is unavailable on both hosted
images. A delay recovers the reproduced pinned launch error, without fixing the
boundary. No permission widening, product pin bump or Windows support claim.
The ordinary-user and Windows startup-smoke stages remain gated, not silently
completed. Desktop builds are NOT RUN. The next agent can use the
[ordinary-machine handoff](windows-ordinary-user-handoff.md) once a backend remedy
can meet the unchanged contract. [Narrative](../narrative/2026-09-27-local-remote-execution-decision.md)
records the recommendation and what could change it.
