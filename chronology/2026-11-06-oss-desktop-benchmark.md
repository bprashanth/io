# T3 desktop → Idli runtime → local Muse: behavioral benchmark

Owner authorized actual OSS desktop evaluation, screenshots and simple file experience;
confirmed hostname io.idli.cc and preference for server-side execution plus inference.
Cloned repositories using the requested hierarchy under
/home/beeps/src/github.com/bprashanth/{pingdotgg/t3code,getpaseo/paseo}.

[Benchmark and limitations](../benchmarks/runs/2026-11-06-oss-desktop/t3-private/README.md),
[machine-readable checks](../benchmarks/runs/2026-11-06-oss-desktop/t3-private/checks.json).

T3 released CLI and Linux ARM64 desktop0.1.7, Codex0.167.0, real local
muse-glimmer-30b Responses endpoint. No new model mock or provider API key used.
An isolated container runs T3 and Codex; Docker internal network denies public TCP.
A narrow model proxy reaches existing Muse, and a loopback HTTP/WebSocket gateway
allows the client to pair. No existing service, DNS or Cloudflare route changed.
This tests the target shape locally, not public io.idli.cc integration or multi-tenancy.

Behaviorally verified:
- Actual packaged desktop, local environment disabled, pairing with remote runtime,
  persisted connection and fresh DESKTOP_MUSE_OK reply. Headless secure-storage
  initially failed; isolated D-Bus/gnome-keyring fixed pairing. Electron --no-sandbox
  used for Xvfb test harness only; renderer shipping configuration is not qualified.
- Browser UI with same remote runtime: client-only final.csv attached, Python runs
  remotely, expected total636 matches result.csv; turn8388ms; CSV table preview works.
- Streaming, Stop generation/interrupted state, container restart and transcript/
  pairing restoration. Host auth file and Docker socket absent inside container.
- Paseo0.15.2 Codex→Muse CLI smoke passed in15602ms; daemon stopped. No comparable
  Paseo GUI/file benchmark, so recommendation is provisional, not a fair UX ranking.

Important discoveries: editor fill after attachment removes its chip; corrected test
attached after typing. Earlier input.csv was inside a mounted path and cannot prove
upload. Auxiliary title model initially differed from chat; explicitly configured it.
Codex fallback context exceeded Muse64k and a long thread failed; added explicit64k
window/45k compaction threshold, but compaction itself remains untested. Proxy originally
hid HTTP error bodies; fixed it. Generated CSV download UX wasn't established despite
working table preview. Do not equate server result-file assertion with laptop download.

Recommendation: continue T3 as first minimal-adaptation candidate. Model routing needs
configuration, not a new IO client implementation. Private product still needs fixed
auxiliary models/egress, context settings, a clear download action, per-user runtime
routing and native Access/pairing handling. Existing IO gateway protocol is not T3's.
Fresh Open-mode OAuth, Windows/macOS, full provider outage/fallback behavior, tenant
isolation and actual Cloudflare entry remain outstanding. Do not retire IO baseline yet.

Screenshots were visually inspected; curated copies are linked in benchmark README.
No credentials, pairing tokens, keyrings, runtime databases or full transcripts exported.
Cursor lower-model audit attempt needed login; Claude Haiku read-only audit completed
and provided useful source leads, independently checked during actual runs.

Test container and both temporary proxies stopped at completion. Private /tmp state
retained for deliberate resume; see benchmark RESUME.md. Existing IO service untouched.
