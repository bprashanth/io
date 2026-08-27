# io on macOS

Same shape as Windows: one artifact, one double-click, no Python or Node assumed, no
admin password.

## The artifact

**DMG** with `io.app` (electron-builder `dmg` target; icon from `assets/` as .icns).
Two builds or a universal binary: **arm64 (Apple Silicon) is the one that matters**;
x64 only if a participant needs it.

- **Thin**: first run installs the Python env + model into
  `~/Library/Application Support/io/env` via the same splash -> install script flow
  (install.sh works on macOS with small path guards; python from python-build-standalone
  or `uv`, never the system python).
- **Fat** (event): dmg + pre-built env + hf-cache, offline first run.

## The one prompt

We are unsigned and un-notarized: Gatekeeper blocks a plain double-click on first open.
Right-click -> Open -> Open (or System Settings -> Privacy & Security -> Open Anyway).
One screenshot of this in the final doc. (An Apple Developer ID + notarization removes
it; not needed for the event.)

## Watch-outs

- torch CPU wheels for macOS arm64 exist on PyPI directly (no special index url) -
  the install script needs an OS branch for that.
- The detached daemon spawn and `lan_ip()` are POSIX paths already; should carry over.

## How to test

No macOS runners on our hardware; **GitHub Actions `macos-14` (arm64)** builds and
smokes it the same way as Windows (Playwright over CDP, screenshots as artifacts). A
single manual run on any Mac covers Gatekeeper.
