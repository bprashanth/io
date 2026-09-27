# Windows local execution does not meet the contract; recommend verified local plus remote

The available-host experiment is complete. Recommendation: outcome C as the product
direction, retaining local execution on validated platforms and an explicit remote
offer otherwise. For Windows now, use the remote experiment. This is a recommendation,
not an implementation of automatic provisioning/fallback or a local Windows release.

## Measured results

[Evidence and all reports](../benchmarks/runs/2026-09-27-execution-decision/README.md).
All selected Windows jobs remain red; no expected-failure conversion makes them green.

| Backend | Server 2022 | Server 2025 |
|---|---|---|
| Shipped 0.154.0 elevated, clean | Runs with 4 local TCP violations; one repeat hit error 5 | Runs with 4 local TCP violations |
| Candidate 0.157.1 elevated | Rejects restricted-read policy | Rejects restricted-read policy |
| Candidate 0.157.1 strict MXC | Native MXC unavailable | Native MXC unavailable |

When 154 launches, 13/17 properties pass: workspace/Python/child execution works;
tested outside-file/junction reads and writes are denied; public-internet TCP is
denied. Parent and child each reach loopback and the host's own non-loopback address,
with nonce acknowledgments from the receiver. Those four violations are not proof
of arbitrary LAN reachability, but do violate io's unchanged offline contract.

157 elevated says `elevated Windows sandbox requires effective :root read access`
(backticks in actual stderr). Upstream source explicitly tests rejection of default
root-deny. We did not widen reads. MXC is selected strictly, never silently replaced
by another backend. 154 only contained an early adapter/probe; 157 wires MXC into
actual command selection. Its native-only requirement is narrower than the broad
Microsoft MXC product support matrix. Neither measured server has native PSEC.

## Error-5 investigation: correction and refinement of the earlier baseline

The September 27 10:44 baseline observed failure at SpawnChild/CreateProcessAsUserW.
New clean runs with the same 154 binary and Server 2025 image start successfully,
so that error is not an inevitable outcome of the pinned backend.

A 2x2 Node 20/22 versus clean/prior-unelevated sequence reproduces error 5 after the
prior sequence on both Node versions. The same command/profile after a two-second
wait succeeds on retry in both cases. First-attempt stderr/results are retained.
One separate clean Server 2022 repeat also failed first launch, so history is not
the sole trigger. Source shows `spawn_read_acl_helper` starts asynchronously with
no wait. Together these strongly support a setup/read-ACL timing race; we have not
instrumented the exact object/ACE denied by CreateProcessAsUserW. Firewall setup
logs success before the failed child launch. No evidence establishes UAC or missing
administrator privilege as the cause on these already-admin runners.

Retry is a labeled experiment only, not a product fix. It does not repair the four
network violations and cannot justify enabling local Windows execution.

## Changes and verification

Added a staged [proposal](../proposals/local-remote-execution-decision.md), separate
hash-pinned candidate package, backend-selection experiment flags, daily-log
allowlisted collection, environment metadata and two CI workflows. Shipped Codex
pin/profile/backend and the remote server are unchanged. Candidate and diagnostic
reports remain ineligible for the original all-platform product conformance gate.
Synthetic log files are archived as `.log.txt`; no .sandbox-secrets/auth caches.

Runs: [initial matrix](https://github.com/bprashanth/io/actions/runs/36310702342),
[repeat with logs](https://github.com/bprashanth/io/actions/runs/36310871779),
[history/Node split](https://github.com/bprashanth/io/actions/runs/36310871868),
[same-policy retry](https://github.com/bprashanth/io/actions/runs/36311032651),
[final matrix](https://github.com/bprashanth/io/actions/runs/36311032673).
There are 26 principal case reports plus separately labeled weakened-preparation
artifacts. A real DGX Linux arm64 regression passes 17/17. Harness classification,
19 launcher checks and 34 proxy tests pass. Cursor CLI gpt-5.4-mini-high performed
source audits; parent reviewed findings against source and live CI evidence.

## Limits and next stage

NOT RUN: non-admin Windows, Windows 11 23H2/24H2/25H2 desktops, Windows 10, managed
enterprise/AV variants. GitHub Windows Server/admin results do not stand in for
those. No backend passed the prerequisite for ordinary-account acceptance, so that
stage and the proposed Windows startup smoke implementation remain gated. Asked
owner about a laptop; no machine information was supplied during this round.
The [ordinary-machine handoff](../proposals/windows-ordinary-user-handoff.md) records
commands and evidence needed when a viable backend is available.

No io user-interface feature changed here, so no new app screenshots are claimed.
Remote OAuth and UI screenshots remain the separately established baseline. No
production hosting, billing, auto-upload, proxy/viewer changes, durable storage or
main-UI integration were added. Costs/latency comparisons are qualitative, not new
measurements. A later startup gate must test actual behavior and invalidate cached
results after relevant changes; existing wallProbe is narrower than this contract.

[Narrative recommendation](../narrative/2026-09-27-local-remote-execution-decision.md).
