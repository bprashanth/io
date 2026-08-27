# io on Linux

Today this works from a git checkout (`app/io/install.sh` then `run.sh`) and assumes
python3 and npm exist. The target matches Windows in structure: one artifact, one
double-click, no preinstalled runtimes assumed.

## The artifact

**AppImage** (`io-linux-x64.AppImage`, plus arm64 if cheap): one executable file,
`chmod +x` once (or "Allow executing" in the file manager), double-click, done.
electron-builder emits it directly and embeds the icon and .desktop entry.

- **Thin**: first run installs the Python env + model next to the AppImage's data dir
  (`~/.local/share/io/env`), same pinned packages as Windows, same splash.
- **Fat** (event): AppImage + pre-built env + hf-cache in one tarball; first run finds
  them and skips every download.

## Python

Do not assume system python3 (Ubuntu has it, but parity and pinning matter): bundle a
standalone CPython (python-build-standalone or `uv python install`) into the env dir,
exactly mirroring the Windows embeddable approach. Same package pins as
`installation/windows.md`.

## How to test

Local, on this machine - but the primary agent's services occupy ports 8801, 8802 and
8890 and its Electron/CDP debug ports. **Use 8811+ for the service and 9800+ for CDP.**
Smoke scope: AppImage launches, splash runs the first-run install, service comes up,
provider screen renders, shelf renders after a folder is added. Startup time measured
and screenshotted like a human. Model calls are out of scope for the smoke.
