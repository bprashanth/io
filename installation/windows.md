# io on Windows

The person double-clicks one thing and io opens. They do not have Python. They do not
have Node. They must never need an administrator password.

## The two artifacts

1. **Thin zip** (general use): `io-win-x64.zip` ~120 MB. Unzip anywhere, double-click
   `io.exe`. First run shows the existing splash and installs the Python environment and
   the scanner model (~500 MB download, 1.7 GB on disk, needs internet once).
2. **Fat zip** (the event): everything pre-baked - embeddable Python with all packages
   installed and the model already in `hf-cache`. ~2 GB on a USB stick. Unzip,
   double-click, working in under a minute, fully offline. This is what participants get.

## How it works

- **Electron is packaged, not assumed.** `electron-builder` (or electron-packager)
  produces a portable win-x64 folder: `io.exe` plus resources. Nobody installs Node.
  Give the exe the io icon (`assets/`, converted to .ico).
- **Python is the embeddable build, not an installer.** python.org ships an ~11 MB
  "embeddable package" zip: no registry, no PATH, no admin. `install.ps1` unpacks it
  inside the app folder, enables site-packages (the one-line `python3xx._pth` edit),
  bootstraps pip, then installs the same pinned packages as Linux:
  CPU torch (`--index-url https://download.pytorch.org/whl/cpu "torch>=2.2"`),
  `gliner==0.2.28`, `pandas`, `openpyxl`, `pypdf`. No poppler or other binaries needed -
  io reads PDFs with pypdf.
- **First-run flow** (already in main.js): splash -> `install.ps1` -> service starts ->
  provider screen. Windows work items: `pythonExe()` must prefer
  `.venv\Scripts\python.exe` / the embeddable `python.exe`; the detached daemon spawn
  uses the `start /b` path (exists, untested); ports and `HF_HUB_OFFLINE` logic are
  OS-independent and should carry over.

## The two prompts a user will see (and no others)

- **SmartScreen** on first launch, because the exe is unsigned: "More info" -> "Run
  anyway". Put a screenshot of this in the final install doc. (A code-signing
  certificate removes it; not needed for the event.)
- **Windows Firewall** the first time they press "share on your network" (the share
  listener binds 0.0.0.0): "Allow". Everything else is user-space; nothing elevates.

## Watch-outs

- Defender scans thousands of small site-packages files: first run on an HDD laptop is
  minutes, not seconds. The splash must stay honest about progress.
- Long paths: keep the unzip location shallow (`C:\io\` in instructions), or enable
  long-path awareness in the manifest.
- The fat zip must be built on win-x64 so the compiled wheels match.

## How to test

- **No Windows containers for us**: they need a Windows kernel host, and our box is
  Linux arm64 (a local VM here would be Windows-on-ARM - the wrong architecture).
- **GitHub Actions `windows-latest` is the test bench**: a workflow that builds the
  package, runs `install.ps1` from scratch, launches `io.exe` with
  `--remote-debugging-port`, and drives a Playwright smoke: app opens, provider screen
  visible, key form accepts input, folder shelf renders. Screenshots as artifacts.
  Smoke is startup-only - no model calls, no API key in CI.
- **One real x64 laptop for the last mile**: SmartScreen, Defender timing, the actual
  double-click feel. Any Windows 10/11 machine.
