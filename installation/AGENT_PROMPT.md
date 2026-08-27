# Brief for the packaging agent

Read `README.md`, `CLAUDE.md`, then the three files beside this one:
`windows.md`, `linux.md`, `mac.md`. They are the spec. This file is your work order.

## Mission

Make the io desktop app (`app/io/` only - NOT the Antigravity plugin) installable by a
person who has nothing preinstalled: no Python, no Node, no admin password. One
double-click artifact per platform, with the io icon on Windows and macOS.

## Order of work

1. **Windows first.** It is the platform participants actually bring and the one
   furthest from working. Thin zip first, then the fat (pre-baked, offline) variant.
2. Linux (AppImage) and macOS (DMG) after, to the same structure.
3. **One build pipeline for all three**: a single script or GitHub Actions workflow
   (matrix: windows-latest, ubuntu, macos-14) that produces all artifacts in one run.
   Prefer one `electron-builder` config with per-OS targets over three bespoke scripts.
4. Write the final user-facing install instructions per platform (screenshots of the
   SmartScreen / Gatekeeper prompts included) into `installation/`, and link them from
   the README Quick start. Keep the repo's plain style: short sentences, no jargon,
   no em-dashes.

## Rules of the road

- **Use cheaper models for the grinding.** Cursor `agent` CLI, `codex` CLI, or a lower
  Claude model for mechanical work: converting icons, writing boilerplate configs,
  transcribing pip pin lists, drafting per-platform docs. Keep architecture calls,
  anything touching `service.py`/`main.js` behavior, and final verification yourself.
- **Test like a human, with screenshots.** A build that compiles is not done; done is a
  screenshot of the provider screen after a cold double-click start, plus a measured
  startup time. For CI platforms, screenshots come out as workflow artifacts.
- **Linux testing runs beside the primary agent's live services.** Do not touch ports
  8801, 8802, 8890 or CDP 9333/9555/9666. Use service ports 8811+ and CDP 9800+.
- **Smoke scope only**: app opens -> splash/install runs -> service up -> provider
  screen -> shelf renders. No model requests, no API keys in CI. The primary agent's
  benchmarks cover the model path.
- Do not commit venvs, hf-cache, built artifacts, or anything from `~/.config`. Build
  outputs go to CI artifacts or a gitignored `dist/`.
- Append a `chronology/` entry as you go; commit in small, honest steps.
- When the smoke passes on all three platforms, stop and report: the user wants to
  discuss build optimisation (sizes, fat-zip logistics, signing) before you go further.
