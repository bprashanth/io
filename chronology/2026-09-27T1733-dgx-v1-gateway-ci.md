# V1 gateway CI and final client checks

[Initial V1 entry](2026-09-27T1728-dgx-v1-gateway.md) recorded the local experiment.
Both workflows for `3704531` ("Add identity-routed persistent remote workspaces and a non-gating
local diagnostic") passed all five jobs each:

- [V1 gateway + diagnostic, run 36317584243](https://github.com/bprashanth/io/actions/runs/36317584243):
  Linux real Docker gateway integration/lifecycle, plus portable classification and client/relay
  tests on Linux x64, Windows x64, macOS ARM64 and macOS Intel.
- [Legacy remote experiment, run 36317584219](https://github.com/bprashanth/io/actions/runs/36317584219):
  real Linux sandbox/container regression and the same four client platforms.

[Downloaded CI evidence](../benchmarks/runs/2026-09-27-v1-gateway/ci-initial/) reproduces 39 routing,
file/persistence and 19 lifecycle/isolation checks on GitHub's Linux x64 runner. This tests a
host client through the gateway to private Docker IPs. It is not a human Cloudflare login or a
native Windows sandbox pass. CI needs neither model credentials nor a signed-in human.

Final client review added explicit **Sign out of IO** (clear local Access browser session, close
client, preserve remote workspace), distinct from ChatGPT sign-out. A real Electron rerun verified
that the workspace remains reachable after Access sign-out. HTML responses from Access/gateway
errors are now summarized as a readable sign-in error instead of printed into the UI; the
transport test exercises a synthetic HTML 403. This follow-up changes no sandbox contract.

The original user runtime on 8787 is still untouched. The new `io-v1-gateway.service` is active
on loopback 8789. Local test workspaces and their volumes/networks were removed after testing;
the fixture listener is stopped. The actual Cloudflare team login screen was viewed and its
redirect metadata signature verified. No email/OTP/password was submitted. Owner still needs
to switch the tunnel destination to 8789 and complete the two logins/model-turn acceptance test
in [gateway README](../app/io/gateway/README.md).

The current evidence is sufficient for the implemented separate POC, but not to claim all ten
human-facing success criteria have been demonstrated. Main-interface consolidation is deferred.
