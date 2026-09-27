# Keep verified local execution; use remote for Windows until the contract passes

The experiment supports outcome C as the product direction: retain local execution
where the required behavior has been established and offer remote Linux when it
has not. For Windows today, the dependable experiment baseline is remote. This is
not a recommendation to enable Windows local execution behind a warning.

Two separate obstacles prevent a straightforward local Windows fix. Pinned Codex
0.154.0 elevated can execute the Python/child probes and protect the tested outside
files/junctions, but its Offline policy still lets parent and child connect to
services on the same host. Public-internet TCP is blocked. This distinction matters:
blocking an external website is not the complete network boundary io requires.
There are also launch failures sensitive to initialization/history. A two-second
same-policy retry recovered the reproduced error-5 failures on Node 20 and 22;
source shows asynchronous read-ACL setup. This strongly suggests a setup race,
but the exact denied object was not instrumented. Recovery does not fix networking.

Upgrading is not an immediate solution. Separately pinned 0.157.1 elevated refuses
io's default-deny read policy and requires root reads. The same version exposes MXC,
but that path needs native Windows process-security capabilities unavailable on
both hosted images tested. Codex deliberately does not use MXC's older AppContainer
fallbacks. Passing a small suite would also not remove upstream MXC maturity limits.

This evidence rules out declaring local Windows supported now. It does not prove
that every Windows 11 desktop fails, nor that Windows can never work. Windows Server
CI is not desktop or non-admin coverage. No backend passed the gate for the next
ordinary-account acceptance stage; no runtime smoke/automatic fallback UI was added.
Linux with documented setup and both Mac CI targets remain the prior passing
baseline, subject to real-device validation and a fuller startup gate before a broad
product guarantee.

Local execution retains the cost and privacy advantages of avoiding hosted command
compute and keeping io's existing tokenizer local. It still uses online ChatGPT
model requests. Remote simplifies execution control but entails hosting cost,
upload/download latency and explicit consent to server processing. Current remote
mode has no local masking proxy, durable storage, production provisioning or billing.
No cost or latency benchmark was conducted in this round, so those comparisons are
qualitative rather than invented prices or timings.

The next product step should be a separate scoped proposal for a synthetic startup
contract gate on supported local platforms, explicit remote consent/provisioning,
and pricing disclosure. Continue native Windows only with a concrete backend/policy
fix that can pass the unchanged suite, then test under a standard user on real
Windows 11 builds. Do not use an OS allowlist or a partial smoke test as a substitute.

[Proposal](../proposals/local-remote-execution-decision.md) ·
[Evidence](../benchmarks/runs/2026-09-27-execution-decision/README.md)
