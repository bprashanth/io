# 2026-08-26 04:00 - Robustness campaign: three io.xlsx org themes through both surfaces

Datasets and dialogs authored by a different model (codex/gpt-5.6-sol) from the real survey's
use-cases: Y-Ultimate (sports-for-development: site health, coach support, site map),
Foundation Without (30 households, vulnerability ranking, geo view), Lila Poonawalla
(scholarship excels, cross-year duplicates, disbursement status). Synthetic Indian-context
data, Hinglish notes, planted duplicates. Corpus: scratchpad (not committed); dialogs saved
with the run evidence.

## Antigravity + shield 0.3.1 (benchmarks/runs/2026-08-26-shield-robustness/)

Nine turns across the three themes: zero crashes, zero "server not running", zero Gemini
confusion, zero egress blocks. Scans 9-24 s. Vault growth is folder-proportional and global
(309 -> 363 -> 1530 across three orgs; each folder's people, no junk). Lila's dashboard was
built and written to disk. One cold-cache redaction spike (5 s) on the first call after a
daemon restart; steady state 13-570 ms.

The blocking shelter modal requested by the user is in 0.3.1: centre-screen "Privacy Shield
is reading the files in this folder - n/m (file). Nothing can leave until this finishes",
returns if dismissed early, stops returning when the scan ends (one final click if it was up
at completion - IDE modals cannot be closed programmatically). Verified with screenshots.

Rig findings (not product bugs, but demo-runbook rules):
- Rapid AG kill/relaunch cycles wedge Chrome's singleton: open Antigravity once and leave it
  running. Participants never relaunch in loops; automation must not either.
- The agent's own preview servers (python -m http.server) inherit AG's sockets and outlive
  it - after an AG exit, stray preview servers should be closed before relaunching.
- Never Cancel the relaunch prompt: the cancelled path leaves a window where the language
  server pokes a not-yet-routed proxy and shows a transient "connection to server is
  erroring" toast (heals by itself, but looks like a crash).

## io Electron app (benchmarks/runs/2026-08-26-io-electron-bench/)

The real desktop stack (Electron spawns its own service): provider key typed into the UI,
three themes in one session via the shelf, per-theme scan -> review -> Looks right -> three
chat turns -> share on your network.

| theme | scan | turns (all done) | share fetched |
|---|---|---|---|
| y-ultimate | 3 s | 23.6 / 33.5 / 22.9 s | 100 KB page |
| foundation-without | 15 s | 29.5 / 37.3 / 22.1 s | 49 KB page |
| lila-scholarships | 3 s | 23.5 / 4.8 / 31.4 s | 121 KB page |

The map ask produced a real geographic bubble view with rehydrated site names ("Dhanori
Activity Park") and honest meta ("706 rows sent as codes, google/gemini-3.7-flash, 22.9s").
No wedges, no stalls; reload-to-home between folders worked as designed.

**Bug found by the bench and fixed**: share ids were turn ids, and turn ids restart on every
folder load - all three themes shared `/p/3`, each overwriting the last. An NGO sharing two
dashboards would silently break their first link. Fix: one monotonic share id per shared
page (re-sharing the same page keeps its link). Verified: two folders share as /p/1 and /p/2,
distinct, each serving its own org's content (93KB attendance page, 112KB disbursement page).

**Startup wedge, root-caused and fixed**: "loading the on-device scanner" could hang forever -
caught live with a CLOSE-WAIT socket to the HF CDN and the warm-up thread blocked 6.5 hours at
0% CPU. The hub's startup check has no timeout. Fix: when the model is cached, load fully
offline (HF_HUB_OFFLINE) - in the io service and the shield daemon env. Warm-up is now ~4 s
deterministic; a "scanner ready" step replaces the lingering "loading..." label.
