# Final V1 verification

Both workflows passed on final implementation `b6a6b3a` ("Add Access sign-out and readable
gateway errors with cross-platform CI evidence"):

- [Gateway/diagnostic 36317788598](https://github.com/bprashanth/io/actions/runs/36317788598): 5/5 jobs.
- [Legacy remote 36317788568](https://github.com/bprashanth/io/actions/runs/36317788568): 5/5 jobs.

[Final CI evidence](../benchmarks/runs/2026-09-27-v1-gateway/ci-final/) includes run metadata and
39+19 real Linux x64 gateway/container checks. Linux, Windows, macOS ARM and macOS Intel portable
client/diagnostic classification tests pass. This does not change prior native Windows sandbox
findings. Local final Electron interaction tests also pass, including Access sign-out preserving
the workspace. Launcher19/proxy34 remain green; no model credentials were used by CI.

Production-configured gateway is active on localhost8789. Old signed-in user session8787 remains
untouched. Only synthetic test workspaces/listeners were removed. Human Cloudflare authorization
and a fresh model conversation through this new gateway remain untested pending the owner
changing the tunnel destination to8789 and completing the acceptance flow. There is no need to
share passwords, API keys or the tunnel token. The main IO interface integration remains deferred.

All implementation/evidence is pushed on `remote-codex/experiment`; no main merge. Staged audit
found no file above1MiB, embedded JWTs or private keys. Screenshots are intentionally ignored.
Pre-existing untracked `docs/sandbox.md` was untouched.
