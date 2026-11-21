# Idli alpha release

Prepared 2026-11-18. Two downloads per release: the **app** (the Idli build of Paseo) and the **kit** (Idli itself,
installed into the app with one command). Built by `.github/workflows/idli-alpha.yml`.

## What's in it

- **The app:** Paseo 0.15.2 (`getpaseo/paseo` at `e896c05b`) with Idli's UI patch
  (`benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/desktop/paseo-idli-split.patch`, the same as idli26 on
  the test laptop). It has the Drivey split, the Builder (Claude Code first, `/sandbox`), sandboxes, Minis with
  ask, turn on and fork, and Idli's chart and question cards. The app keeps Paseo's name and data folders, so an
  existing Paseo install is replaced, not duplicated.
  - Linux x64: `.tar.gz` and `.AppImage`
  - macOS Apple Silicon: `.dmg` (ad-hoc signed, not notarized)
  - Windows x64: `Setup .exe` and `.zip` (unsigned)
- **The kit** (`idli-kit-<version>.tar.gz` / `.zip`): Idli's code (`cowork/`, tracked files only, made with
  `git archive`), the private model's settings template, and `cowork/desktop/install-idli.py`. The kit script
  refuses to build if anything in it looks like a credential.
- **Not in it:** no tokens, OAuth client files or account data. Testers get those from the owner, out of band.

## Installing (testers)

1. **Install the app** and open it once.
   - **macOS:** open the `.dmg` and drag Paseo to Applications. The first open is blocked because the app isn't
     notarized. Either right-click Paseo, choose Open, then Open; or run
     `xattr -dr com.apple.quarantine /Applications/Paseo.app` once.
   - **Windows:** run the Setup `.exe`. SmartScreen says "Windows protected your PC": click More info, then Run
     anyway. (Idli itself doesn't run on Windows in this alpha: see Known gaps.)
   - **Linux:** unpack the `.tar.gz` and run `./Paseo`, or `chmod +x` the AppImage and run it.
2. **Install Claude Code, Python 3.10+, Node 20+ and npm.**
3. **Install Idli from the kit:**
   ```sh
   tar -xzf idli-kit-<version>.tar.gz
   python3 idli-kit/cowork/desktop/install-idli.py --token <the token file from the owner>
   ```
   - It copies Idli to `~/idli-insights/app/cowork`, makes its Python environment, and adds Idli's chat options to
     Paseo (`~/.paseo/config.json`, backed up first).
   - It then lays out Start here, Drivey and the Builder.
   - Rerun it to update: the code is replaced and the Python environment is kept.
4. **Quit and reopen Paseo.** In Start here, Logins signs in to Google.

## Building (owner)

- **CI:** push the `idli-alpha` branch, or run the workflow by hand (its `only` input builds one target, e.g. `mac`).
  - **Jobs:** `tests` on Linux, macOS and Windows; `kit`; `app` per target (build, then Paseo's own packaged-app
    smoke: the app starts, its daemon comes up with every built-in plugin, and the UI loads); and a draft
    prerelease for `idli-v*` tags only.
  - **Where the outputs go:** every output is a workflow artifact; nothing is published without a tag.
- **Locally (Linux):** check out Paseo at `e896c05b`, then:
  ```sh
  git apply <io>/benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/desktop/paseo-idli-split.patch
  npm ci && npm run build:desktop -- --publish never --linux tar.gz --x64
  bash <io>/benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/desktop/make-idli-kit.sh <version> <out dir>
  ```
- **Checked on the DGX (2026-11-18):**
  - The Linux arm64 build took 4 min 44 s: a 160 MB tar.gz, 484 MB unpacked.
  - Paseo's packaged-app smoke passed under xvfb in 33 s.
  - The packed UI carries Idli's patch.
  - The kit is 1.2 MB.
  - `install-idli.py` ran clean in an empty home with a stand-in `paseo` CLI, and a rerun kept the Python
    environment.
  - The CI test set passed with an empty HOME: 327 passed, 6 skipped.

## Known gaps (alpha)

- **Windows:**
  - The app builds and starts, but Idli's chat launchers are shell scripts and Paseo starts them directly, so the
    kit refuses to install on Windows.
  - The way forward is either WSL2 (as in `narrative/PAGES_AND_TOOLS.md`) or Python launchers.
  - CI runs the tests on Windows for information only.
- **Unsigned:**
  - macOS needs the Gatekeeper step above, and Windows the SmartScreen step.
  - There is no auto-update. Stock Paseo's updater would download Paseo's own releases over Idli's UI, so the build
    points it at this repo (`bprashanth/io`), where no update channel is published (checked: `app-update.yml` in
    the build names `bprashanth/io`). Install new alphas by hand.
- **The private model lives on the DGX:**
  - Idli's 9B and 30B are served by the DGX router through silo (Cloudflare Access).
  - Each tester needs a silo Access token file, given out of band. `--token` checks it and never prints it.
  - The DGX must be up.
- **Google sign-in:**
  - Idli's OAuth app is published but unverified. Testers click Advanced, then "Go to idli (unsafe)".
  - It is capped at 100 users.
  - The client file (`~/.config/idlisseus/io_oauth_client_gcp.json`) comes from the owner and is never shipped.
- **Escalation:** the outside query service for Mini questions needs `~/.config/idlisseus/openrouter.json`, also
  given out of band. Without it, Idli maps questions with the 9B alone.
- **No sandbox wall:** transform blocks and Mini scripts are guarded by the import check, not by bwrap
  (`todos/idli-insights/p1/sandboxing_later.md`).
- **Known failures:** 11 tests (`lib/test_chat.py` 10, `lib/test_home.py` 1) fail on every machine and are left
  out of CI.
- **Name:** the app still says Paseo. Renaming it changes its data folders, so that waits for a beta.

## Pushing (owner, after review)

The repo is public. Everything below is outward-facing.

```sh
cd ~/src/github.com/bprashanth/io
git status                                  # only the unrelated modified PNGs and old traces should remain
bash -ic 'declaude origin/main'             # strip Claude trailers from the branch's commits
git log origin/main..HEAD --format=%B | grep -ci 'co-authored-by: claude'   # expect 0
git push --force-with-lease origin HEAD:idli-alpha    # CI: tests, kit, the three app builds
gh run watch                                # or the Actions tab
# when green and checked by hand:
git tag idli-v0.1.0-alpha.1 && git push origin idli-v0.1.0-alpha.1   # a draft prerelease with every artifact
```

Review the draft release, then publish it. Hand testers the token file and the OAuth client file privately.
