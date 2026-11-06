# Simplified Open/Private desktop evaluation

Added a prominent ordered “how to test” checklist to the rollout guide and linked
it from README. Clarified remote V1 versus local settings in conversation: remote
uses direct ChatGPT OAuth only, not OpenRouter/Muse; local Open still has a filesystem
wall, while legacy unwalled fallback is separate. Windows does not use bwrap.

[Agent handoff proposal](../proposals/oss-desktop-open-private-agent-handoff.md)
records the new two-mode product, candidate research, endpoint/protocol/auth questions
and test requirements. T3 Code, Paseo and Happy official repositories/docs reviewed.
Initial preference is evaluating T3 first, Paseo alongside it; no UI integration or
cross-platform replacement claim yet. No new client installed or live service altered.

Read-only Muse checks: localhost8181 /health ok, /v1/models muse-glimmer-30b,
idli-muse container running. Historical Silo Codex→Muse generation evidence found.
[Observations](../benchmarks/runs/2026-11-06-oss-desktop/observations.json).
Requested idli.io.cc differs from existing io.idli.cc; new public routing is unverified.
Private inference routing and private remote execution are separate designs; the
handoff requires an explicit choice and honest labels before implementation.
