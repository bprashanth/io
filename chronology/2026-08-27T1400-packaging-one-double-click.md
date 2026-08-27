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

**Cold smoke, packaged AppImage, empty data dir** (`installation/smoke/smoke.js`, driven
over CDP on 9802 with the service on 8811+, so the primary agent's 8801/8802/8850/8890 were
never touched - confirmed still listening afterwards):

| | thin, nothing installed | warm, everything present |
|---|---|---|
| window open | 1.0 s | 2.0 s |
| provider screen | **88.2 s** | **2.1 s** |
| shelf rendered | 93.4 s | 6.6 s |
| ran an install | yes | no |

Screenshots in `installation/smoke/out-linux-arm64-{thin,warm}/`. The warm column is the
same code path a fat build takes - everything present, `first_run_install: false` - so 2.1 s
is the number a participant with the offline zip should see. Caveat on the 88.2 s: pip's
local wheel cache on this box was warm from earlier runs, so a genuinely first-time
install on event wifi will be slower. CI on a clean runner will give the honest figure.

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
in, the cold run finishes in 88 s.

This is the whole argument for smoking the real artifact rather than checking that a build
compiles.

## Not done yet

Windows and macOS have never been run. `.github/workflows/package.yml` is the bench for
both - build, unpack the real artifact the way a participant would, cold smoke over CDP,
screenshots as artifacts - but it has not been dispatched. The fat job is gated behind a
`workflow_dispatch` input because each artifact is about 2 GB.

The user asked to stop and discuss build optimisation (sizes, fat-zip logistics, signing)
once the smoke passes on all three.
