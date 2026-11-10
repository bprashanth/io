# Idli: deployment strategy

What a person gets when they install "Idli" (an AppImage, a .dmg, a Windows installer: whatever wraps Paseo)
and open it for the first time, and what has to work with no help. A running list: tick items off as they
become true on a clean machine, add new ones as the walkthroughs find them.

Today's prototype of the first-run step: `benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/desktop/idli-bootstrap.py`
(safe to rerun), started by `desktop/idli-launch.sh`. On the laptop an "Idli" app-menu entry
(`~/.local/share/applications/idli.desktop`) runs the launcher; the plain Paseo entry skips the bootstrap. Paseo changes we depend on: [paseo_patches.md](paseo_patches.md).

## What the person sees on first open

```
Start here            <- heading 1: the setup chat (tab 0), a Drive tab, a Gmail tab
   Start here            Idli has already said: sign in to Google in the Drive tab, then say yes to indexing
Idli         <- heading 2: the private model at work (find files, forms, questions)
   Idli
Claude      <- heading 3: Claude teaches Idli a file, from fake data only
   Claude
```

1. They sign in to Google in the Drive tab (the only manual step before using it).
2. They say yes; Idli indexes Drive in 1 to 5 minutes (names, folders, dates, first rows, Muse summaries), on
   their machine.
3. Idli says "You're set. Go to Idli". From there: find a file, open its form, ask questions; teach a
   new file through Claude when Idli asks.

## Must work out of the box

| # | What | How today | Status |
|---|---|---|---|
| 1 | The three headings, in this order, with one workspace each | bootstrap creates projects and workspaces through the Paseo CLI | ✅ created; ❌ order needs patch P2 |
| 2 | Start here chat already open as the first tab, greeting shown, in Bypass mode | bootstrap: `paseo run --provider t4gc-cowork --mode bypassPermissions --title "Start here" hello` | ✅ |
| 3 | Drive and Gmail tabs in Start here | bootstrap opens them through Paseo's browser tools as the Start here chat | ✅ (needs the app running) |
| 4 | Model picker shows only: Idli 30B (private), Idli 9B (not private, optional), Claude | `setup-laptop.py` merges providers into `~/.paseo/config.json` | ⚠️ other providers (Claude, Codex, T4GC experiments) still listed |
| 5 | New Idli chats can use their tools | Paseo defaults Claude-based chats to Auto mode, whose safety check can't run on Muse, so every tool is blocked | ❌ patch P3, or the user picks Bypass |
| 6 | Instructions in each folder (`start-here/CLAUDE.md`, private folder `CLAUDE.md`) | bootstrap copies `idli/START-HERE.md` and `idli/CLAUDE.md` | ✅ |
| 7 | Drive index builds on "yes" and is shared by all workspaces | `drive_index` tool, `lib/driveindex.py`, DuckDB in `~/idli-insights/config/` | ✅ |
| 8 | Downloads of real files land without the user hunting for them | `file_get` triggers the export; the user clicks Save in the system dialog | ⚠️ works; silent with patch P1 |
| 9 | The private model is reachable | Muse 30B on the DGX through Cloudflare Access (`silo.idli.cc`, item 22) | ✅ for the team POC |
| 10 | Claude works | the installer's setup page installs Claude Code with Anthropic's installer (always: Idli 30B runs through it) and offers Sign in (`claude auth login`, with a code box when no browser window opens) or skip | ✅ install verified in CI on all three; ⚠️ sign-in untested on a real machine |
| 11 | Python runtime for the tools (DuckDB, pandas, openpyxl) | standalone CPython 3.12 inside the installer (`installer/build_payload.py`) | ✅ 2026-11-10, CI on Linux, macOS, Windows |
| 12 | The tools' code itself | inside the installer, copied to `~/idli-insights/app/cowork` on open (taught files kept) | ✅ 2026-11-10 |
| 13 | Nothing private leaves the machine except to the chosen model | Idli 30B is private; Idli 9B goes to OpenRouter (labelled "not private") | ⚠️ decide whether 9B ships at all |
| 14 | Updates: re-index Drive when it changes | manual: "re-index my Drive" in Start here | ❌ no incremental refresh yet |
| 15 | A second Google account on the same machine | one index per computer user; re-indexing another account replaces it | ❌ index per account |
| 16 | Photo/video location for searches like "event in December in Kolkata" | dates and names only | ❌ EXIF location needs the details panel or the Drive API |
| 18 | Muse answers a find question in 30-80 s (reasoning at ~30 tok/s) | measured in the OOBE run | ❌ see [optimizations.md](optimizations.md) #1, #5 |
| 19 | Progress while indexing | `drive-index.localhost` tab + finish in chat | ✅ (tab opens in the background: P7) |
| 20 | Cleanup: old chats, workspaces, downloads | Paseo's app only archives (chats: close the tab; workspaces: sidebar menu or Ctrl+Shift+Backspace); real delete is CLI only (`paseo delete <id>` / `--cwd <folder>`) and never touches files. All Idli workspaces share `~/idli-insights/cowork-real`, so no per-workspace folders pile up; what grows is `drive/` (downloads, `incoming/`, `working/`, checked copies), `teach/inbox` (fake copies), `~/.paseo` (chat history, 666 MB on 2026-11-09) and `~/idli-insights/archive/` (old browser profile set aside by `idli-reset`, 475 MB) | ❌ to do: (a) `idli-reset` / a periodic step deletes downloads, checked and working copies and teach requests older than a week, and old `archive/` entries; (b) a "clean up" option that deletes (not archives) old Idli chats via the CLI; (c) one-off for the dev laptop: delete old test chats, archive the 4 extra Idli workspaces, drop `archive/browser-profile-20261108`; (d) Paseo patch P10 |
| 21 | Chart code runs behind a wall on every system | Claude's chart code runs on real data under bubblewrap (`lib/chartkit.py` `wall()`): Linux only. Mac and Windows run it after the import check alone | ❌ move chart runs into **Pyodide** (Python in WebAssembly) inside Paseo's own Chromium: same wall on all three systems, no disk or network unless handed in. pandas, numpy, matplotlib all load in Pyodide. Cost: ~30 MB of packages to bundle, a few seconds on the first chart. Spike: run one saved chart (`charts/<id>.py` `make(tables, plt)`) in a hidden page, tables in as JSON/Arrow, SVG out. OK to skip for the 3-person POC; required before anyone outside the team |
| 22 | Muse reachable from any laptop, not just through the ssh tunnel | ✅ 2026-11-10: `silo.idli.cc` + a service token per person (`desktop/muse-connect.py`, `lib/muse.py`); verified end to end | to do: the first-run checklist asks for the token file instead of a terminal command. Original plan: `muse.idli.cc` on the existing Cloudflare tunnel → DGX `localhost:8185`, behind Cloudflare Access. POC: one Access service token per person, entered at first run, sent as headers through `ANTHROPIC_CUSTOM_HEADERS`; revoke per person. Later: sign in to Access in a window like the io.idli.cc gateway (no secret on disk). Never one shared token inside the installer |
| 23 | First run adopts what's there, asks for what's missing, works with less | ✅ 2026-11-10 (branch `idli-installers`): the installer's setup page (Idli code, Claude optional), then Paseo + bootstrap; without a code Paseo opens without Idli's chats | was: ❌ a setup checklist in Start here: Google (Drive tab), Muse (token check against `/v1/models`), Claude (found and signed in? else install with Anthropic's official installer and sign in; never redistribute the binary). Skipping Claude: Muse only (find, clean and ask on files already learned; teaching says it needs Claude). No Muse: Paseo is a browser with the Drive tab, and Start here says how to add a token |
| 17 | Paseo's remote-debugging port | only for driving from the DGX during development | ✅ the installed app starts Paseo without it (`lib/uiswitch.py` tab switching then does nothing: needs P7) |
| 24 | One-click installers | `installer/` + `.github/workflows/idli-installers.yml`: .deb, .dmg (arm64), Inno Setup .exe, unsigned; CI installs and smokes each, then a first open | ✅ CI green on all three; ❌ a teammate's real install; Intel Mac and Linux arm64 not built (Paseo ships no Linux arm64 build) |

## First-run order of operations (target)

1. Package installs Paseo (patched) + the Idli tools + runtime.
2. On first launch, the Idli plugin (or the launcher) runs the bootstrap: folders, providers, projects,
   workspaces, Start here chat, Drive and Gmail tabs, heading order (P2).
3. The person sees Start here with the greeting.

## Open decisions
- Where Muse runs for other people (item 9) and what it costs.
- Whether Idli 9B (OpenRouter) is offered at all outside development.
- Plugin vs launcher for the bootstrap: a Paseo plugin's lifecycle hooks can run it when the daemon starts, which
  works for any way of opening the app; a launcher script only for our shortcut.
