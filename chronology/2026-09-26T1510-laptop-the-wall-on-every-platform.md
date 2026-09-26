# 2026-09-26, 15:10 IST — laptop: the wall proven on every platform, and a way to go on without it

Follows `2026-09-16T1206-laptop-verifying-the-dgx-work.md`. Screenshots in
`benchmarks/runs/2026-09-26-laptop/` (untracked). The app was driven on an isolated Xvfb
display (`:99`), because the desktop was at its lock screen; see "How it was tested".

## The asymmetry

Before today io proved the wall only on Linux, with a bubblewrap smoke test, and refused to
start Codex without it. On macOS and Windows `sandboxCheck` returned `ok: true, checked:
false` and io went ahead on trust, although nobody had run the wall on either. A Windows
participant would have seen "Protected by io" over an untested mechanism while a Linux one on
the wrong distribution was stopped dead. Worse, the "refuses `codex-start` without a wall"
the DGX entry of 2026-09-15 describes lived only in the page; `main.js` started whatever it
was asked to.

## What changed

**One probe, every platform** (`codex.js`, `wallProbe`, `classifyProbe`). io writes its real
profile into a scratch Codex home and runs one small python program through Codex's own
`codex sandbox -P io`. The program tries to read a file placed *beside* the folder and to
write one *inside* it. The wall is on only if the read is refused and the write works. That
exercises whatever Codex uses on the platform - bubblewrap, Seatbelt, the restricted token -
with io's actual profile, in about 80 ms here. Two things were needed to make it run:
`-P io` (the permission profile must be named; `-p` only picks the config layer), and on
Linux a `codex-linux-sandbox` alias on PATH in temp, because Codex re-executes itself under
that name inside bubblewrap and `codex sandbox` alone does not set the alias up
(`bwrap: execvp codex-linux-sandbox: No such file or directory`).

The probe is not vacuous: with the secret moved into temp, which the wall grants, the same
probe reads it and reports a leak. That control is a launcher test and runs for real on any
machine where the wall works.

**Loud everywhere.** A **Wall** indicator in the terminal bar on every platform: green "on,
checked on this computer", red "OFF: commands can reach your other files and the internet",
or red "OFF (developer bypass)". The footer has three states now: "Protected by io" (codes
and wall), amber "Codes only: no wall", red "NOT protected".

**When the wall fails**, a dialog says so in plain words and states the cost: questions and
file contents still leave only as codes, but the commands the assistant runs can open any
file, reach the internet and install software, and the three settings cannot be kept.

- Linux with Ubuntu's AppArmor restriction: **Set up the wall** installs the two-profile file
  through `pkexec`, so the password goes to the desktop's own prompt and never through io.
  Afterwards io probes again; the answer is the probe's, not the install's.
- Linux without `pkexec`: the manual command for an administrator, as before.
- macOS and Windows: "There is nothing io can set up for this", because there is nothing to
  install.
- If the setup fails or is declined: "The wall could not be set up: <why>. You can still use
  io on this computer, but only without the wall."

**Continue without the wall** starts Codex with the new `unwalled` setting: no permissions
profile, `sandbox_mode = "danger-full-access"`, still `-a never`, toolbox still registered.
It skips the three settings, which cannot be kept without a wall, and hides the Setting
control. Codex's own banner then reads `permissions: YOLO mode`, an independent confirmation.

**The gate is in the main process now.** `startSession` refuses a walled setting on a
computer where the probe failed (`error: 'nowall'`, which the page turns into the dialog),
and refuses `unwalled` on a computer where the wall works, so running without it stays a
fallback the person was warned about and never a shortcut.

`IO_SANDBOX_TEST=broken|fixable` simulates a failed wall for development, next to
`IO_CODEX_NO_SANDBOX`.

## How it was tested

Tests: 18 launcher (three added: unwalled writes no wall and no walled setting ever drops
it; the probe's verdicts; the non-vacuous control), 31 proxy.

In the app, on Xvfb `:99` with the real Codex and ChatGPT login:

| scenario | result |
|---|---|
| wall works (this laptop) | no dialog; bar "Wall on, checked on this computer"; footer Protected by io; `codex -p io -a never` |
| `IO_SANDBOX_TEST=fixable`, pkexec stand-in exiting 126 | dialog with Set up the wall; after it, "the administrator password was not given ... only without the wall" |
| continue without the wall, folder | bar red Wall OFF; footer amber Codes only: no wall; Setting hidden, toolbox kept; `danger-full-access`; banner "YOLO mode" |
| `IO_SANDBOX_TEST=broken`, chat box | dialog with "nothing io can set up for this on Linux"; Cancel starts nothing; continue gives a working unwalled conversation |

**Not tested, and why.** The real `pkexec` prompt and a *successful* install: the desktop was
locked and this Pop!_OS machine does not carry the restriction the setup fixes, so a
stand-in `pkexec` returning 126 exercised io's handling instead. The profile the setup
installs is the one proven on the DGX on 2026-09-15. The probe on macOS and Windows: written
platform-neutrally, never run; if it cannot start there, io says the wall could not be
proven, which is the safe direction to be wrong in. The main-process refusal of `unwalled` on
a walled computer: no path in the page can send it, so it is read, not run.

## A lesson about the tooling, for whoever drives the laptop next

ImageMagick `import -window <id>` grabs the X server while it captures. When the window
disappears mid-capture - here the splash, whose id the launcher picked up - `import` hangs
holding the grab and **every other X client blocks**: `xdpyinfo` hung with the machine idle.
Killing the stuck `import` released it. Every capture is now wrapped in `timeout 15`. And
when the desktop is locked, typed text goes to the lock screen's password box; three test
characters did, and were deleted unsubmitted. Drive on Xvfb when the owner is away.

## Correction to 2026-09-16T1206

That entry says the `matplotlib==3.11.2` pin hits "any Ubuntu 22.04 or Pop!_OS 22.04
participant laptop". It does not. Packaged builds carry python-build-standalone 3.12, where
the pin installs. Only `install.sh` from a checkout, which uses the machine's python and
accepts 3.10, breaks. A developer-path problem, not an event one. Still open.

## Still open

- The pin above.
- The viewer that does not come back after it is closed (GPU process crash on this laptop,
  2026-09-16); the repro is unfinished.
- Offline refusing to open a page without saying why.
- How many Ubuntu 24.04 laptops will be in the room, which decides whether the setup path or
  an organiser step at the door is the real answer.
