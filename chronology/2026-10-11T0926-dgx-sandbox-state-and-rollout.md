# Current DGX sandbox state and minimum laptop rollout

## Measured

Fresh [October 11 evidence](../benchmarks/runs/2026-10-11-dgx-sandbox/README.md):
- Local actual bundled Codex 0.154.0 conformance: 17/17 PASS, positive controls included.
- Fresh synthetic Docker runtime: creation succeeded, inner sandbox readiness true, no login;
  container/network and private temporary connection file removed after the check.
- `io-v1-gateway.service` active; unauthenticated localhost:8789 `/identity` returns 401.
- Old remote 8787 container is absent. Other unrelated containers were untouched.
- Global AppArmor unprivileged-userns restriction remains 1. `/etc/apparmor.d/io-bwrap` includes
  grants for system bwrap and this checkout's bundled bwrap path.
- This checkout and origin branch are at `fdc6457` before these documentation changes. The
  laptop's current revision is not observed; reported775d06b would predate V1 by eight commits.

## Correction and reconciliation

`docs/io-codex.md` still described the DGX as unable to run bwrap and the wall as untested.
Those were stale September 14 statements. Explicit AppArmor provisioning enabled the later
successful runs; current tests confirm that state still holds. The October 1 Docker/user-bus
permission denials belonged to this coding-agent session, not IO's command sandbox. Access is
restored today and the actual sandbox was tested, not inferred from access to Docker.

The earlier instruction to use Cloudflare→localhost:8789 remains the remote V1 route. Check
whether the tunnel already targets 8789 before changing it. No dashboard or authenticated
Cloudflare request was performed today. Port8787 was the old ephemeral prototype, not an
alternate entry to the new identity gateway.

## Changes

Updated canonical sandbox and Codex docs, plus gateway deployment notes. Added
[local/remote rollout guide](../docs/execution-and-laptop-rollout.md): per-machine full
qualification for local use; one gateway plus two-laptop/two-identity real acceptance for
remote use. Narrow startup wallProbe is not full qualification. Native Windows remains
unsupported by existing evidence; passing remote client CI does not repair that.

The guide separates a small managed pilot from production readiness: current outer container
AppArmor/seccomp exceptions, missing disk/admission controls and untested restore operations
remain limitations. It records the private-state backup and coordinated code/image/service
update requirements. No application code, auth, policy grants or live service settings changed.
The untracked owner draft `docs/sandbox.md` remains untouched; `docs/sandboxing.md` is canonical.
The October 1 checkpoint files are preserved as historical evidence and included now that Git
writes are available; their account of the restricted session remains true for that date.

## Validation and outstanding acceptance

19 launcher checks and 34 proxy tests passed. A lower-model Cursor CLI read-only documentation
audit found no remaining contradictions in the three updated canonical/rollout pages. No GUI rerun is needed for these documentation-only changes.
Existing September CI/GUI evidence is linked rather than reclassified as fresh testing.

Not tested: current Cloudflare dashboard destination, human Cloudflare+ChatGPT authorization,
real model conversation through the gateway, ordinary laptop qualification, concurrent real
users or backup restoration. Those are the next pilot acceptance tasks, not claims established
by HTTP 401, signed test identities or this fresh sandbox run. Main UI consolidation remains
out of scope. No private runtime-state snapshot was created.
