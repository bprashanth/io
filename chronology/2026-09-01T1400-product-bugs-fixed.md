# 2026-09-01 14:00 - Event-eve fixes: the rupee crash, the vote wedge, and the escape hatches

Three Windows field reports (screenshots in /tmp/bugs/product, now reproduced and
understood) and the fixes, all verified on the real Electron app.

## Root causes

1. **The charmap crash was one line.** The compare-log write was the only place that
   combined `ensure_ascii=False` with an `open()` that never named an encoding - so
   Windows' cp1252 default met a rupee sign and raised. Reproduced on Linux with
   `LC_ALL=C python3 -X utf8=0`. Fix: `encoding="utf-8"` at that open, plus
   `PYTHONUTF8=1` in the Electron spawn so the whole class is retired on every platform.
2. **"nothing to vote on" was the same incident, second act.** `resolve_vote` marked the
   vote done two lines before the crashing write; the browser saw an error and kept the
   cards, the server had moved on. Fix: telemetry (tally + log) wrapped so it can never
   fail a vote, and `pending_vote` flips only after everything else ran.
3. **WinError 10054 is a network-level reset, not the API key** (a bad key would be a
   clean 401). Fix: one retry on connection-level failures; and when all three models
   still fail, the turn resolves itself into "check the wifi and ask again" - three
   error cards never demand a vote again.

## The escape hatches (new UI, top corner: folders | forget this chat | reload)

- **reload**: visible twin of Ctrl+R, and reload is now lossless - /api/state carries
  the whole conversation including a pending vote's cards, and the UI resumes exactly
  where the user was. A stale "nothing to vote on" self-heals by redrawing from truth.
- **forget this chat**: wipes the conversation only; scan, vault and decisions survive.
- **folders**: back to the landing page without losing anything. Scanned folders are
  cached in memory (file-signature checked), so returning is instant.
- Every error message now ends with "Press reload (top right); if it happens again,
  forget this chat."

## Verified like a human on the packaged Electron app (benchmarks/runs/2026-09-01-product-bugs/)

Scan 3.2s -> cards -> **reload mid-vote restores the three cards** -> vote lands ->
forget-this-chat empties the thread with input live -> switch to a second folder ->
back to the first: 0.00s server-side, straight into the restored chat -> final reload
resumes into the thread. Vote with the log file made unwritable: succeeds (the wedge is
dead). All-models-unreachable: friendly one-line answer in 1.5s, no vote UI.

## New edge found while testing (and fixed)

Returning to an already-scanned folder used to land in the review sheet with an
empty-looking chat (the thread only rebuilt at boot). Now opening an accepted folder
goes straight to its restored conversation - measured 1.0s.
