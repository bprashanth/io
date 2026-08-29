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

## The Windows failure: GNU tar, not the network

Two Windows runs failed identically - window open at 1.2 s, splash at 2.1 s, then nothing
until the 40 minute budget expired. Neither run produced any evidence of its own failure:
the install log lives in a temp data dir the workflow did not upload, and the single splash
screenshot is from t=2.1 s, so it shows where the install *started*, not where it stopped.
I read that screenshot as "hung downloading python" and was wrong to.

So the first fix was the blind spot, and the third run said it outright:

    [python] downloading python 3.12.14 (46 MB) 100%
    [python] unpacking python
    FAILED: Error: tar exited 2
    tar (child): Cannot connect to C: resolve failed
    gzip: stdin: unexpected end of file

**GNU tar parses an `-f` argument containing a colon as `host:path`.** So
`-f C:\Users\...\cpython.tar.gz` is not a file, it is an attempt to resolve a network host
called "C". The download had finished cleanly at 100%. Reproduced here against GNU tar 1.35
with a byte-identical error message; the relative form extracts fine.

The bad assumption was mine, inherited from `installation/windows.md`: Windows 10+ has
bsdtar in `System32`. It does - but a machine with **Git for Windows** puts GNU tar ahead of
it on PATH, and the runner has Git for Windows. So will plenty of participants.

Two changes, kept together because laptops vary more than runners do:
- `tarExe()` asks for `%SystemRoot%\System32\tar.exe` by name on Windows rather than
  taking whatever PATH offers.
- The extract runs with `cwd` set to the destination and passes only basenames, so no
  argument carries a drive letter whichever tar answers.

### What the two hardening fixes were, and were not

Before the log existed I hardened the two places a hang could hide. **Neither fixed
Windows** - the real bug was a fast, clean failure the whole time. They stand on their own
merits for event wifi, and they are why the third run was diagnosable in three minutes
instead of forty minutes of silence:

1. **`download()` had no timeout at all.** A TLS connection that opens and delivers nothing
   never errors, never retries, never gives up - the same shape as the HF hub hang
   `service.py` already carries a comment about, reproduced in my own installer. Now 30 s
   to first response, 60 s between chunks, four attempts with backoff, truncation checked
   against content-length. Verified against a black-hole address: fails in 63 s.
2. **`run()` had no timeout either.** Eight minutes of child silence now kills it and
   reports the captured tail.
3. **The install log leaves the machine.** The smoke copies `<data>/install.log` next to the
   screenshots on both paths. The log is deduplicated too - a download was writing one line
   per chunk.

Also corrected while measuring: the splash claimed the python download was "about 11 MB".
That is the embeddable-zip figure from `installation/windows.md`, carried over by mistake.
The real tarballs are 46 MB on win-x64, 109 MB on linux-x64, 25 MB on macOS. The splash now
quotes the actual content-length and carries an elapsed clock, so a slow first run on an old
laptop reads as slow rather than frozen.

## Timings are a range, not a number

macOS passed twice on clean runners with very different results: **53.7 s** to the provider
screen on the first run, **124.2 s** on the second, same code path. The install log shows the
difference is entirely runner-to-PyPI and runner-to-HF throughput. A genuine first run is
"one to two minutes", not a fixed figure, and the install doc says exactly that.

Local cold run with the tar fix, packaged arm64 build: install 76 s, provider screen 78.2 s,
shelf 82.0 s.

## Green on all three

Run **33077672572**, cold first run on clean runners, driving the real shipped artifact
the way a participant would (unzip the zip, mount the dmg, extract the tarball):

| | install | provider screen | shelf | artifact |
|---|---|---|---|---|
| **win-x64** | 2m 16s | 139.3 s | 150.1 s | 106 MB zip |
| **linux-x64** | 51 s | 60.8 s | 67.4 s | 200 MB (AppImage + tar.gz) |
| **mac-arm64** | 49 s | 50.5 s | 60.4 s | 94 MB dmg |

Screenshots, `install.log` and `io.log` for each in
`benchmarks/runs/2026-08-27-packaging-ci/`. Windows is slower for the obvious reason: its
torch wheel is 121.9 MB against 111.2 MB on macOS, and Defender reads every file in
site-packages as pip writes it.

It took four CI runs. What the three failures were:

1. `io-linux-x86_64.AppImage` vs `io-linux-x64.AppImage` - electron-builder names AppImage
   artifacts by `x86_64` while `${arch}` is `x64` everywhere else. Staging looked for a
   name that was never produced. Artifacts are now resolved by glob.
2. A tar.gz check that could not pass, because the workflow's `--linux AppImage` on the
   command line overrides the target list in the config, so no tarball was built.
3. The two real ones, below.

## The two real Windows bugs

Neither was a packaging problem. Both were in code that had only ever run on POSIX.

**GNU tar reads `C:\...` as a remote host.** `-f C:\Users\...\cpython.tar.gz` is parsed as
`host:path`, so tar tried to resolve a machine called "C":

    tar (child): Cannot connect to C: resolve failed

Reproduced here against GNU tar 1.35 with a byte-identical message. The assumption I
carried over from `installation/windows.md` - Windows 10+ has bsdtar in System32 - is true,
but Git for Windows puts GNU tar ahead of it on PATH, and both the runner and plenty of
participants have Git for Windows. Fixed twice over: ask for `System32\tar.exe` by name,
and pass only basenames from a `cwd` so no argument carries a drive letter either way.

**`import resource` is POSIX-only.** With tar fixed the install completed - "scanner
cached", "done in 1m 59s" - and then the service died instantly. `engine/detect.py` had a
bare module-scope `import resource`, a module Windows does not have, so `service.py` died
at import before binding a port. torch and gliner are imported lazily inside functions and
were never the suspect. The single use is peak-RSS reporting in the benchmark CLI, code the
desktop app never runs; it is now an optional import with a `_max_rss_mb()` helper that
returns None where the platform cannot report it.

**This one is not only io's problem.** `extension/privacy-shield/server/detect.py` and
`benchmarks/pii/detect.py` are the other two copies of that file and still carry the same
line. Out of scope for this work order, but the shield has the same latent Windows failure.

## What the two hangs cost, and what fixed them

Both Windows failures were fast, clean errors that presented as 40 minutes of silence,
twice, because nothing carried the error out of the runner. The fixes that mattered were
not the timeouts - they were:

- `install.log` and `io.log` collected by the smoke on both the pass and the fail path.
- `io.log` moved out of Electron's `userData` (a different directory per platform, and not
  where anyone looks) into the data dir beside `install.log`, now recording the spawn
  command, spawn errors and the service exit code.
- Under `IO_SMOKE`, failure paths log and exit instead of opening a modal dialog. A modal
  in an automated run burns the entire budget before the harness can report anything.

The download and pip watchdogs added along the way did not fix Windows. They are still
right for event wifi - a stalled TLS socket that never errors is a real failure mode this
repo has already been bitten by once - but they were not the bug.

## The offline (fat) packs, all three

Run **33084523518**. Every one built on its own target OS - the wheels inside are compiled,
so a payload made anywhere else is useless - packed into `resources/`, and smoked with a
fresh data dir to prove it installs nothing.

| | file | size | provider screen | shelf | vs thin |
|---|---|---|---|---|---|
| **win-x64** | `io-win-x64-offline.zip` | **1.3 GB** | **5.7 s** | 24.5 s | 139.3 s |
| **mac-arm64** | `io-mac-arm64-offline.dmg` | **804 MB** | **4.2 s** | 19.0 s | 50.5 s |
| **linux-x64** | `io-linux-x64-offline.tar.gz` | **951 MB** | 20.5 s | 37.5 s | 60.8 s |
| | `io-linux-x86_64-offline.AppImage` | 995 MB | | | |

All three report `first_run_install: false`, and none of them produced an `install.log` at
all - the file is never created because the installer never runs. That is the evidence, not
the timing.

The spec guessed "~2 GB on a USB stick". Every platform comes in under that, Windows
included, and every file is under the 2 GB per-asset cap on GitHub releases.

Linux's 20.5 s is an artefact of the bench, not the product: the runner has no libfuse2, so
the AppImage self-extracts ~1 GB to /tmp before it starts. The tar.gz has no such cost and
is the artifact the install doc points at anyway.

## A third Windows-only bug, from the same family

The offline Windows pack would not build at all. The payload baked fine; 7-Zip then refused
it, 120 times:

    WARNING: The directory name is invalid.
    .\resources\hf-cache\hub\models--knowledgator--...\snapshots\<rev>\pytorch_model.bin

Every warning under `resources\hf-cache`, none under `resources\runtime`. The HuggingFace
cache stores `snapshots/<rev>/<file>` as a symlink into `blobs/<sha>`; harmless where it was
created, fatal once the tree is archived on Windows. It never appeared on Linux because
mksquashfs handles symlinks natively - which is exactly why the local arm64 fat AppImage had
built cleanly and told me nothing.

`bootstrap.js` now replaces every symlink in the cache with a **hard link** to the same blob:
identical bytes, identical disk usage, but an ordinary directory entry. Verified on the real
480 MB cache - 10 symlinks to 0, size unchanged, scanner still loads offline in 1.8 s with
the expected detections.

That is three Windows-only defects in a row (GNU tar, `import resource`, HF symlinks) and
none of them were packaging problems. All three were code that had only ever run on POSIX,
and all three would have hit a participant's laptop rather than a runner.

## Intel Macs cannot be supported, and it is not a packaging problem

The work order asked for a mac-x64 build. It cannot be made, and the reason is worth
recording so nobody spends another day on it.

macos-13, the last Intel image GitHub offers, would not schedule at all: two dispatches sat
queued for over two hours before being cancelled. Electron will happily cross-build an
Intel dmg on an arm64 runner, so that was tried next. The build and the dmg were fine. The
first run was not:

    ERROR: Could not find a version that satisfies the requirement torch==2.13.0
           (from versions: 2.2.0, 2.2.1, 2.2.2)

Checked against PyPI directly rather than trusting the message: **torch 2.2.2 is the last
release with a macOS x86_64 wheel**; 2.13.0 ships `macosx_14_0_arm64` only. And pinning
back does not rescue it, because **transformers 5.13.1 requires torch>=2.4**. There is no
pin of our stack that installs on an Intel Mac.

Supporting Intel Macs would mean downgrading transformers and gliner as well and
revalidating the scanner against a different model chain - a research question, not a build
flag, and untestable here without an Intel Mac. So mac-x64 is out of the matrix, and
`installation/INSTALL-mac.md` says plainly that Intel Macs are not supported and points
those users at a Windows or Linux machine.

This is the third time on this job that "the artifact built" and "the artifact runs" turned
out to be different questions, and the smoke is the only reason the difference was visible.

## Not done yet

**No Windows or macOS install doc.** They wait on the two screenshots a runner cannot
produce: SmartScreen "More info -> Run anyway" on first launch of the unsigned exe, and
Gatekeeper's right-click -> Open on the un-notarized .app. Those need one real Windows
laptop and one real Mac. `installation/INSTALL-linux.md` is written and linked from README.

**Nothing is signed.** A code-signing certificate removes SmartScreen; an Apple Developer ID
plus notarization removes Gatekeeper. Neither is needed for the event.

**Nothing is published anywhere durable.** The artifacts live as GitHub Actions artifacts,
which need a signed-in GitHub account to download even on a public repo - awkward for
handing to an organiser. A GitHub release gives plain public URLs and every file fits under
the 2 GB cap; S3 is the alternative if the URLs need to be controlled.

**Linux ships two offline artifacts** (951 MB tar.gz + 995 MB AppImage) where the event
only needs the tar.gz, since the AppImage needs a libfuse2 that Ubuntu 24.04 does not
install. Dropping the offline AppImage halves the Linux offline payload.
