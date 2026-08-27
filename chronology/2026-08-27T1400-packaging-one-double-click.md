# 2026-08-27 14:00 - packaging: one double-click artifact per platform

Work order: `installation/AGENT_PROMPT.md`. Specs: `installation/{windows,linux,mac}.md`.
Scope is `app/io/` only. The Antigravity plugin is untouched.

## The shape that came out of it

There is one io binary per platform. "Thin" and "fat" are the **same app**; the only
difference is whether the packer put a python runtime and a model cache inside
`resources/`. Resolution is always: use what shipped with the app, else use what the first
run installed under the user's data dir.

| | runtime | model cache |
|---|---|---|
| packaged fat | `resources/runtime` | `resources/hf-cache` |
| packaged thin | `<data>/runtime` | `<data>/hf-cache` |
| git checkout | `.venv` | `hf-cache` |

`<data>` is `%LOCALAPPDATA%\io`, `~/Library/Application Support/io`, or
`~/.local/share/io`. Nothing writes inside the app bundle: an AppImage is read-only
squashfs and a signed `.app` must not be modified after the fact. `app/io/runtime.js` is
the whole of that decision; `service.py` changed by six lines to take the cache location
from `HF_HOME` instead of assuming it sits next to `service.py`.

The git checkout path is unchanged. `install.sh` still works, `.venv` and `hf-cache` are
still found first, and a developer with the privacy-shield plugin installed still borrows
its venv. A **packaged** build never borrows: it owns its runtime or it installs one.
Half-borrowed is how you get an app that starts against an empty model cache and then
hangs on the first scan.

## Two deliberate departures from the spec

1. **python-build-standalone on Windows, not the embeddable package.**
   `installation/windows.md` asks for python.org's ~11 MB embeddable zip. Its stated
   reasons - no registry, no PATH, no admin - are equally true of python-build-standalone,
   which the same spec already chose for Linux and macOS, and which ships an
   `x86_64-pc-windows-msvc` `install_only` build with pip already in it. Taking it on all
   three removes the embeddable build's `._pth` edit, its missing `ensurepip`, and a
   Windows-only code path in the installer. Cost is about 30 MB on a 120 MB thin zip.
   Pinned in `app/io/pins.json`; switching back is one function.

2. **No install scripts. The first run is Node, inside the app.**
   `install.ps1` assumed Python and Node were already on PATH, which is exactly why the
   README says it does not work. `app/io/bootstrap.js` replaces both scripts: it fetches
   the pinned python tarball, unpacks it, pips the pinned packages, and warms the scanner -
   with no PowerShell, no execution policy, no bash on Windows, and real progress on the
   splash. The same file is the build-time tool for the fat artifacts
   (`node bootstrap.js --dest payload`), so thin and fat install byte-identical payloads.

## Verified so far

**Bootstrap, linux-arm64, from nothing** (`node bootstrap.js --dest …`): pinned CPython
3.12.14 fetched and unpacked, torch 2.13.0+cpu from the CPU index, all pins installed,
scanner cached. 1.4 GB runtime + 480 MB cache. The resulting interpreter loads the real
engine: imports in 1.7 s, GLiNER loads **offline** in 2.0 s, and
`"Call Ramesh Kumar on 9876543210"` returns person + phone at the expected scores.

**AppImage build**: `io-linux-arm64.AppImage`, 104 MB thin. `resources/app.asar` holds the
shell, `resources/io/` holds `service.py`, `engine/`, `ui/` as real files - nothing python
can be imported out of an asar.

**Icons**: `assets/io.jpg` square-cropped to a 1024 master, converted to a 7-size `.ico`
and a hand-written `.icns` (8 entries, header length matches file size, every payload
re-decodes). Conversion was done by the codex CLI per the work order; the verification is
first-party.

**Cold smoke, the packaged artifacts** (`installation/smoke/smoke.js`, driven over CDP with
the service on 8821+/8831+/8841+, so the primary agent's 8801/8802/8850/8890 were never
touched - confirmed still listening afterwards):

| | thin, empty data dir | fat, offline | warm |
|---|---|---|---|
| artifact | 104 MB AppImage | 930 MB AppImage | 104 MB AppImage |
| window open | 1.0 s | 9.0 s | 1.0 s |
| provider screen | **82.2 s** | **9.4 s** | **1.1 s** |
| shelf rendered | 87.0 s | 17.6 s | 5.9 s |
| installed anything | yes | no | no |

Screenshots and `results.json` in `benchmarks/runs/2026-08-27-packaging-linux/`. Three
things worth reading off that table:

- **The fat build is genuinely offline.** `first_run_install: false` is a before/after fact
  about `<data>/runtime`, not a guess: the fat run left no data dir on disk at all.
- **930 MB, not 2 GB.** The payload is 1.9 GB on disk (1.4 GB runtime + 480 MB cache);
  squashfs takes the AppImage to 930 MB. The Windows zip will not compress as well, but the
  spec's "~2 GB on a USB stick" is pessimistic.
- **The fat build's 9.4 s is an artefact of this box, not the product.** Without FUSE the
  AppImage has to extract 930 MB to /tmp before it runs (`APPIMAGE_EXTRACT_AND_RUN=1`).
  A machine with FUSE mounts it instead, which is the 1.1 s warm column.

Caveat on 82.2 s: pip's local wheel cache on this box was warm from earlier runs, so a
genuinely first-time install on event wifi will be slower. CI on a clean runner gives the
honest figure.

## One real bug the smoke caught

The first cold run never finished. The splash sat on "scanner cached" forever. The model
step had printed its success line and then refused to exit: 62 threads, 11 open sockets,
9% CPU, still alive after three minutes.

The cause is `hf_xet`, huggingface_hub's Rust transfer layer. After an actual download it
leaves a tokio runtime running - a dozen `hf-xet-*` threads plus a `tracing-appender` -
and those are not daemon threads, so the interpreter cannot finalise. With a **warm** cache
the same snippet exits in 4.5 s, which is why the standalone payload build had looked fine
and why this would have been an intermittent, unreproducible "it hung on my laptop" at the
event. `bootstrap.js` now flushes and calls `os._exit(0)` once the cache is warm. With that
in, the cold run finishes in 82 s.

This is the whole argument for smoking the real artifact rather than checking that a build
compiles.

## The AppImage does not survive a modern Ubuntu

Found while writing the "test it on your laptop" instructions, not by CI - CI sets
`APPIMAGE_EXTRACT_AND_RUN=1` and never sees it.

On Ubuntu 24.04 a plain double-click of the AppImage fails outright:

    dlopen(): error loading libfuse.so.2
    AppImages require FUSE to run.

24.04 ships libfuse3 and no longer installs libfuse2. The documented fix is
`sudo apt install libfuse2t64` - the admin password the whole artifact exists to avoid.
This box reproduces it exactly. Two workarounds do work without admin
(`APPIMAGE_EXTRACT_AND_RUN=1 ./io.AppImage`, or `--appimage-extract` then run
`squashfs-root/AppRun`) but neither is a double-click, and neither is something to put in
front of a participant.

So Linux now ships **both** targets. The `tar.gz` has no FUSE dependency at all: extract
anywhere, run `./io`. That is the one the install doc will point at; the AppImage stays for
distros that still carry libfuse2.

## CI, first run

`.github/workflows/package.yml`, run 33066644751, pushed to `windows`.

- **macOS arm64: pass.** Real DMG, mounted and copied out the way a person would, cold
  first run on a clean runner: provider screen at **53.7 s**, shelf at 63.5 s, install ran.
  Screenshots came back as workflow artifacts. This is a cleaner number than the local
  Linux 82.2 s because the runner's pip cache is genuinely empty - nothing was warm.
- **Linux x64: failed on staging, not on the app.** electron-builder names AppImage
  artifacts by `x86_64`, not the `x64` that `${arch}` uses everywhere else, so the build
  produced `io-linux-x86_64.AppImage` while the workflow looked for `io-linux-x64.AppImage`.
  My local arm64 build never showed it because arm64 stays `arm64`. The workflow now
  resolves every artifact by glob instead of by constructed name, on all three platforms.
- **Windows x64: built and staged fine, then the first run wedged.** Window open at 1.2 s,
  splash at 2.1 s, then nothing for the entire 40 minute budget:
  `the app window never loaded the service`.

  The splash screenshot the smoke captured says "downloading python 3.12.14", but that
  frame is from t=2.1 s and says nothing about where it actually stopped - a point worth
  being honest about, because the install log lives in a temp data dir the workflow never
  uploaded. The run produced no evidence of its own failure.

## What the Windows wedge changed

Three fixes, none of them Windows-specific, because "it hung and left no log" is the
failure mode that matters at an event.

1. **Every download has a deadline.** `download()` had no timeout at all: a TLS connection
   that opens and then delivers nothing never errors, never retries, and never gives up.
   That is the same shape as the HF hub hang `service.py` already carries a comment about,
   and I had reproduced it in the installer. Now 30 s to first response, 60 s between
   chunks, four attempts with backoff, and a truncation check against content-length.
   Verified against a black-hole address (10.255.255.1): fails cleanly in 63 s with
   `no response in 30s (after 2 attempts)` instead of hanging forever.

2. **Every child process has an inactivity watchdog.** pip and the model warm-up had no
   timeout either. Eight minutes of silence now kills the child and reports it with the
   captured tail.

3. **The install log leaves the machine.** The smoke copies `<data>/install.log` next to
   the screenshots on both the pass and the fail path, so a failed CI run is diagnosable
   without a second run. The log is also deduplicated - a download fired one line per
   chunk, which is not a log anyone can read.

Also corrected while measuring: the splash claimed the python download was "about 11 MB".
That was the embeddable-zip figure from `installation/windows.md`, carried over by mistake.
The real python-build-standalone tarballs are 46 MB on win-x64, 109 MB on linux-x64, 25 MB
on macOS. The splash now quotes the actual content-length instead of any baked-in number,
and carries an elapsed clock so a slow first run reads as slow rather than frozen.

## Not done yet

No fat artifact has been built for Windows or macOS. The `fat` job is gated behind a
`workflow_dispatch` input because each artifact is about 2 GB; only the linux-arm64 fat
build has actually been made and smoked, locally.

No install docs yet. They wait on the SmartScreen and Gatekeeper screenshots, which need a
real machine rather than a runner.

The user asked to stop and discuss build optimisation (sizes, fat-zip logistics, signing)
once the smoke passes on all three.
