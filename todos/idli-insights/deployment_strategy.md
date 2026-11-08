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
| 9 | The private model is reachable | Muse 30B on the DGX through an ssh tunnel (`laptop-up.sh`) | ❌ not shippable: decide hosted endpoint vs local model per install |
| 10 | Claude works | the `claude` CLI signed in (Anthropic account) on the machine | ❌ install needs a Claude sign-in step or a bundled key |
| 11 | Python runtime for the tools (DuckDB, pandas, openpyxl) | the repo's `.venv` | ❌ ship a bundled venv or a single binary for `cowork_mcp.py` |
| 12 | The tools' code itself | a git checkout of this repo | ❌ ship the `cowork/` tree inside the package |
| 13 | Nothing private leaves the machine except to the chosen model | Idli 30B is private; Idli 9B goes to OpenRouter (labelled "not private") | ⚠️ decide whether 9B ships at all |
| 14 | Updates: re-index Drive when it changes | manual: "re-index my Drive" in Start here | ❌ no incremental refresh yet |
| 15 | A second Google account on the same machine | one index per computer user; re-indexing another account replaces it | ❌ index per account |
| 16 | Photo/video location for searches like "event in December in Kolkata" | dates and names only | ❌ EXIF location needs the details panel or the Drive API |
| 18 | Muse answers a find question in 30-45 s (reasoning at ~30 tok/s); the 9B in ~7 s | measured in the OOBE run | ❌ cap or skip reasoning for simple turns; faster decode |
| 19 | Progress while indexing | `drive-index.localhost` tab + finish in chat | ✅ (tab opens in the background: P7) |
| 17 | Paseo's remote-debugging port | only for driving from the DGX during development | must NOT be on in a shipped build |

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
