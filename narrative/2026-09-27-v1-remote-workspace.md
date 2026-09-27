# A stable remote workspace, with local evidence collected separately

The earlier experiment answered whether a remote Linux Codex could feel interactive and use
an ordinary user's browser OAuth. V1 adds the missing ownership/lifecycle layer: Cloudflare
identity locates a persistent workspace, and a runtime can restart without changing that handle.
The client needs only the gateway address and workspace ID, not Docker or SSH knowledge.

[DGX measurements](../chronology/2026-09-27T1728-dgx-v1-gateway.md) establish two-user routing,
file persistence, isolation checks and an actual Electron path. They do not yet establish a
completed Cloudflare-authorized model turn. That remains an explicit human acceptance step.

The local report is deliberately informational. A PASS on this Linux build does not route the
user locally, and a Windows violation does not prevent the same user from reaching the remote
workspace. This lets office deployment gather evidence without making sandbox compatibility
part of V1's execution decision. Production hardening, pricing, arbitrary live-app rendering and
main-interface consolidation are separate decisions, not implied by this proof.
