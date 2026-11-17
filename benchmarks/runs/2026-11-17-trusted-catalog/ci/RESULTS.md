# Trusted catalog on macOS, Windows and Linux (GitHub Actions, 2026-11-17)

Workflow: `.github/workflows/catalog-tools.yml` (branch `catalog-ci`). Scripts: `tools.py` (install and run),
`test_catalog_lib.py` (cowork's `lib/catalog.py` on each OS), `make_table.py`, `read_xlsx.py`, `check_face.py`.

- Runners: `ubuntu-latest` (linux-64, 4 cores, 16 GB), `macos-15` (osx-arm64, 3 cores, 7 GB), `windows-latest`
  (win-64, 4 cores, 16 GB). `macos-14` is no longer offered ("configuration not supported"), so macOS runs on 15.
- pixi 0.84.2 through `prefix-dev/setup-pixi` v0.11.3 (pinned by commit). Python 3.11 for the harness.
- The install goes through cowork's own code: `catalog.check`, `toolhome.write_manifest` (pixi.toml with all four
  platforms, as on a real computer), `toolhome.pixi_install` (plain pixi; on Linux the bubblewrap wall is switched
  off so the three columns compare like for like) and `toolhome.fetch_model` (silo replaced by a local server with
  no files, so every model comes from its public `source`, sha256 checked).
- No secrets. Every lock solved for all four platforms.

## Runs

| Run | What | Result |
|---|---|---|
| [44021722417](https://github.com/bprashanth/io/actions/runs/44021722417) | first try | macos-14 refused by GitHub; OCR test image unreadable (test bug); harness print crashed on Windows (test bug) |
| [44022490136](https://github.com/bprashanth/io/actions/runs/44022490136) | macos-15, OCR test fixed | 11/12 green; whisper fails to install on macOS; Hindi transcript crashes on Windows |
| [44022985402](https://github.com/bprashanth/io/actions/runs/44022985402) | lib fixes (UTF-8, system-requirements) | 11/12 green; `speech macos-15` red on purpose: the catalog entry needs `macos = "14.0"` (passes with it) |
| [44023586989](https://github.com/bprashanth/io/actions/runs/44023586989) | catalog.json from oss-desktop-eval ca338b17 (`macos = "14.0"` for the Whisper tools), CI-side retry removed | **12/12 green** |

## Per OS and tool

Install = `pixi install` seconds, cold (empty package cache: the first run that reached the tool) / warm (final
run 44023586989, cache restored). Models = download and sha256 check, cold. Run = the tool's checks in the final run. Env = the environment
on disk.

| OS | Tool | Install cold / warm | Models | Run | Env | Result |
|---|---|---|---|---|---|---|
| Linux | voice-piper | 2.4 / 0.9 s | 1.0 s | 1.9 s | 316 MB | pass |
| Linux | speech-whisper-small | 2.3 / 0.8 s | 4.3 s | 3.5 s | 551 MB | pass |
| Linux | ocr-tesseract | 4.4 / 1.0 s | 2.8 s | 2.3 s | 1013 MB | pass |
| Linux | face-blur | 4.5 / 1.3 s | 0.6 s | 0.9 s | 1015 MB | pass |
| macOS | voice-piper | 2.8 / 5.1 s | 3.4 s | 3.0 s | 269 MB | pass |
| macOS | speech-whisper-small | 2.1 s (with `macos = "14.0"` in the catalog) | 12.7 s | 9.8 s | 261 MB | pass (failed before the catalog fix) |
| macOS | ocr-tesseract | 8.3 / 2.3 s | 3.2 s | 5.7 s | 811 MB | pass |
| macOS | face-blur | 9.8 / 4.9 s | 0.6 s | 2.7 s | 646 MB | pass |
| Windows | voice-piper | 3.2 / 1.1 s | 3.2 s | 3.4 s | 274 MB | pass |
| Windows | speech-whisper-small | 2.0 / 1.0 s | 6.1 s | 5.4 s | 385 MB | pass (Hindi needed the UTF-8 fix) |
| Windows | ocr-tesseract | 5.4 / 1.2 s | 4.3 s | 3.2 s | 1394 MB | pass |
| Windows | face-blur | 5.9 / 1.4 s | 1.0 s | 2.4 s | 1112 MB | pass |

What each check does:
- speech: Piper says "The quick brown fox jumps over the lazy dog near the river bank." (lessac) and a Hindi sentence
  (pratham); Whisper small types the English back and at least 80% of the words must match (all three OSes got
  the same 8 of 10: every word, with "river bank" written as "riverbank"). The Hindi wav is also typed back (not gated): Devanagari came out on all three after the fix.
- ocr: a ruled 3 by 4 table drawn with Pillow goes through img2table to .xlsx and all six numbers must be in the
  cells; the same words as plain lines must come back with `-l eng`.
- face: the scikit-image astronaut (public domain, pinned by tag and sha256): exactly one face found, the face
  region changed (mean diff over 8) and the rest did not (under 3). Then a 2 s 640 px clip made with the
  environment's ffmpeg: faces in most frames, face region changed, sound kept.

## lib/catalog.py on each OS (job `lib`, green on all three)

| | Linux | macOS | Windows |
|---|---|---|---|
| `platform()` | linux-64 | osx-arm64 | win-64 |
| RAM (`_ram_bytes`) / second measure | 15.3 / 15.3 GB (/proc vs sysconf) | 7.0 / 7.0 GB (sysctl vs sysconf) | 16.0 / 16.0 GB (ctypes vs PowerShell CIM) |
| cores, GPU | 4, none | 3, apple | 4, none |
| free disk where tools go | 90 GB | 44 GB | 28 GB |
| symlinks where tools go | yes | yes | yes |
| `check()` on all 14 real entries | all fit | all fit | all fit |
| a tool not listing this platform | refused, "doesn't run on this computer (Linux)" | refused (Mac (Apple Silicon)) | refused (Windows) |

Also checked: low RAM and low disk are refused with the plain sentences, `fitting()` hides tools for other
platforms, the default tools home is `~/idli-insights/tools` under the user folder (USERPROFILE on Windows), and
the manifest for the four tools together parses. cowork's own `tests/test_catalog.py` also ran on each OS: all
pass except `test_tools_page_api`, which needs the project's Python packages (pandas, duckdb) that the CI job
doesn't install.

## Findings

1. **macOS: speech-whisper-small does not install as catalogued.** faster-whisper 1.2.1 needs `av>=11`; uv picks
   av 18.1.0, whose only Apple Silicon wheel is `macosx_14_0_arm64`. pixi assumes an older macOS, so uv builds av
   from source and fails (`pkg-config could not find libraries ['avformat', ...]`). `pixi lock` solved, so the
   catalog lists osx-arm64, but the install fails. With `[system-requirements] macos = "14.0"` in the pixi.toml
   it installs and works. The same applies to speech-whisper-turbo and voice-anonymise (same package).
   **Fixed** (oss-desktop-eval ca338b17): those three catalog entries now have `"system-requirements": {"macos":
   "14.0"}` in `pixi` (plus a caution), and toolhome writes it into the team's pixi.toml (the lib change below).
   The final run installed the catalog as it is, with no CI-side retry. A Mac older than 14 can't install these.
2. **Windows: tools that print Hindi crashed.** Unwalled runs (`toolhome._plain_env`) gave Python no UTF-8
   setting, so `print()` of Devanagari to a pipe raised `UnicodeEncodeError` (cp1252); the whisper example exited
   1 on the Hindi recording (run 2). Fix in lib: `PYTHONUTF8=1` in `_plain_env`, and `stackwall._run_plain`
   decodes the tool's output as UTF-8. **Fixed** (ca338b17); Devanagari out on Windows since run 3.
3. **Whisper's model can't come from its public source.** `models/whisper-small.tar` is our own archive; its
   `source` is a Hugging Face folder page, so `toolhome.fetch_model` without silo downloads HTML and throws it away
   (sha256 mismatch, as designed). CI fetched the four files at the pinned revision instead, checked against the
   sha256 of the files inside the silo tar. If silo is down, a person can't install the Whisper tools.
4. **The examples and toolhome disagree on where models live.** The examples read `$IDLI_FILES/models/<file>`
   (for example `models/piper/en_US-lessac-medium.onnx`); `toolhome.fetch_model` stores
   `<home>/models/<sha16>/<model name>` (for example `.../Piper English voice lessac (medium)`) and passes
   `IDLI_MODEL_*` variables. Nothing sets `IDLI_FILES`. CI copied files into the examples' layout. A Builder that
   runs the examples as written will not find the models. (Open: with the workflows agent.)
5. **OCR quality (same on all three OSes):** the example's default languages `hin+mar+eng` read English print with
   2 of 6 numbers wrong (124 as 24, 713 as 773); `-l eng` got all six. Tesseract's plain page mode (psm 6) read
   nothing from a ruled table, and img2table missed the table with 3 px rules and 32-40 px text (found it with
   1-2 px rules). Tables in phone photos will need checking.
6. GitHub no longer runs `macos-14`; `macos-15` is the oldest Apple Silicon image there.

## Lib change (applied on oss-desktop-eval as ca338b17)

`lib/toolhome.py`: `_plain_env` sets `PYTHONUTF8=1`; new `system_requirements(tools)` (highest version per key
from each tool's `pixi.system-requirements`) and `manifest_text` writes a `[system-requirements]` section.
`lib/stackwall.py`: `_run_plain` decodes output as UTF-8 with replacement. Tests: `test_system_requirements_pass_through`
and `test_plain_env_is_utf8` in `tests/test_catalog.py` (green on Linux, macOS and Windows).
