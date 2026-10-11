# DGX sandbox recheck, 2026-10-11

`diagnostic/capability.json` and its raw timestamped reports: fresh 17/17 local conformance
PASS using pinned Codex 0.154.0 and the existing standalone Python runtime. Covers both profiles,
positive controls, child execution, filesystem/symlink and loopback/host/public TCP properties.

`container-smoke.json`: fresh synthetic container using `io-remote-codex:v1` completed its
inner sandbox readiness probes, with no ChatGPT credentials. The test container/network and
private connection file were removed afterward. This is a container startup/sandbox check,
not a repeat of the entire gateway or authenticated model-conversation suite.

`host-status.json`: safe current service/image/host facts. Gateway active, unauthenticated8789
returns 401, old 8787 container absent. AppArmor's global userns restriction remains enabled;
the installed per-binary grant permits bundled bwrap. Docker and user-service access now work
for this coding-agent session. October 1 permission failures were not a bwrap failure.

No human Cloudflare login, live model conversation, laptop GUI test or current tunnel-dashboard
verification was performed. Prior CI and GUI evidence remains in the September 27 run directory.
