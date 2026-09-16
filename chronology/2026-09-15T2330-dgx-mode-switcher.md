# 2026-09-15, 23:30 IST — DGX: changing the setting mid-conversation

Follows `2026-09-15T2305-dgx-conversation-viewer-charts.md`. Real sandbox, real relaunch.
Evidence under `benchmarks/runs/2026-09-14-io-codex/drive-switch/` (six screenshots and
`results.json`) and `benchmarks/runs/2026-09-15-dgx/wall-open-recheck/`.

## What was built

A **Setting** control in the terminal's top bar (Offline / T4GC tools / Open), preselected
to the folder's choice and hidden in a conversation, which has no folder to put a setting
on. Changing it writes the new profile, kills the running Codex, waits for its exit so the
late-exit guard from 2026-09-15T1159 is not tripped, and launches
`codex resume --last -p io` (plus `-a never` under Offline). The service, proxy and vault
are untouched; the thread continues. A grey note in the terminal says so before the
relaunch, and the choice is remembered per folder as before. `codex-switch` in `main.js`,
`sessionArgs` in `codex.js`, with a launcher test for the command lines.

## Does a resumed session take the new wall, or keep the old one?

This was the one thing the laptop handoff said needed proving. Measured with `codex exec`
against the same `CODEX_HOME`: a session started under T4GC tools (`enabled = false`),
then the profile rewritten to Open, then `codex -p io exec resume --last` with a curl
probe. The resumed session reports `sandbox: workspace-write [workdir] (network access
enabled)` and the probe returns `200 exit=0`. So the wall comes from the profile file as it
is at launch, not from the session being resumed, and the profile flag must be repeated on
the resume command line. Note `codex exec resume` takes no `-p` after `resume`; it goes
before `exec`. The interactive `codex resume` accepts it in either position.

## The drive, and a wrong result on the way

`drive.js --switch`: start under T4GC tools, ask for "banana", then the curl probe under
each setting with a switch in between.

| setting | thread continued | `[permissions.io.network]` written | curl https://example.com |
|---|---|---|---|
| T4GC tools (start) | — | `false` | `000 exit=6` |
| → Open | yes, "banana" still on screen | `true` | `200 exit=0` |
| → Offline | yes | `false` | `000 exit=6` |

The first run of this drive reported Open as `000 exit=6` too, and an hour went into the
wrong place before the cause turned out to be the drive itself: the probe matched any
`exit=` on screen, so it read the tools-phase answer as Open's, and then switched to
Offline while Open's command was still running. That is what the red "Conversation
interrupted" line in screenshot 03 is: a switch mid-turn interrupts the turn, and the
resumed thread records it. The probe now waits for one more result line than the screen
already had. Worth keeping in mind for a person too: switching while Codex is working
interrupts what it was doing, which is the honest outcome, but the control could disable
itself while a turn is running. Not done.

## Tests

30 proxy, 13 launcher (one added: the resume command lines, and that Offline still
cannot escalate after a switch).
