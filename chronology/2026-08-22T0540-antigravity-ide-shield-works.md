# The privacy shield works inside the real Antigravity IDE; the routing rules were not what the CLI suggested

Driving Antigravity 1.107.0 under Xvfb with the packaged extension reproduced the
user's laptop failure ("relaunch"/"starting" for ever) and found the cause: the
IDE's agent traffic comes from the app-level language server, which ignores the
`--cloud_code_endpoint` flag and the `jetski.cloudCodeUrl` setting for planner
calls and honours only `CLOUD_CODE_URL` from the app environment at launch. The
daemon must already be listening at launch (a dead port stalls the window),
and the setting applied right after launch is needed as well. Several apparent
hangs were an artefact of a leftover instance holding the DevTools port.

Extension 0.2.0 now: spawns the daemon detached; Enable shows a modal and
relaunches Antigravity with the variable through a detached helper; Disable
relaunches without it; the setting is written at activation and removed on
disable/quit; status bar polls the daemon regardless of who started it; Open
server folder and Show daemon log commands; installer pins CPU-only torch.

Shield fixes from the IDE run: streamed tool-call arguments carry a tail so
tokens split across events rehydrate; any file written by the agent is
rehydrated on disk as a backstop; review decisions keyed by header signature;
prose GLiNER limited to names/places; generic vault-token regex; spaced digit
runs for --numbers.

Through the UI: review -> ok -> dashboard; misleading headers (names under
"Item", phones under "Qty", 12-digit ids under "Notes") caught by content; free
text with lowercase names, Hinglish and a phone caught; cold-start of the
packaged build end to end. Egress had zero hits for every private value.

Open: the GLiNER threshold lets a few over-redactions through (Alias/Taluka as
village on 5-row files); ration-card style spaced digits only with --numbers;
the relaunch helper is untested on macOS/Windows; Linux desktop launches via a
.desktop file do not pass env vars, so the helper relaunch is the supported path.

Evidence: `benchmarks/runs/2026-08-22-antigravity-ide-shield/`.
