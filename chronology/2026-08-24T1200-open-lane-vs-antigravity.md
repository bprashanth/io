# 2026-08-24 12:00 — The open lane: io as free as Antigravity, shield built in

Phase-1 demo requirement (`proposals/demo_and_flow.md`): a clean transition — Antigravity →
Antigravity + shield → io with the privacy filter integrated and **no other meddling**: point at a
folder, ask anything, the frontier does whatever it wants. Head-to-head target: the stage-3
Antigravity-with-shield scholarship dashboard (300/103/61/136/67.2 %), same frontier
(Gemini 3.7 Flash, as in the 2026-08-21 remote-dashboard benchmark).

## What was built

- **`shelter.py`**: the stage-3 vault inside io. Column classifier (cached, hand-reviewable at
  `<folder>/.io/pii-classes.json`), PseudonymMap vault (`.io/vault-local-only.json`), tokenised
  tables, a review summary, a final consistency pass over every outbound payload (the shield's
  repair-before-refuse) and a leak gate that blocks the call if any vault value survives.
- **Open lane** (explicit lane chip; lanes are now user-chosen — Auto/Ask/Build/App/Open — per
  demo_and_flow): requires the reach dial off Laptop; first use shows "What leaves the laptop"
  (columns hidden and why — the same 12 columns the stage-3 shield reviewed); sends schema +
  per-column stats (computed locally) + 20 tokenised sample rows per table; the model returns a
  free HTML page (or a text answer); io rehydrates tokens and injects the REAL rows as
  `window.data` when the page is viewed, so the page's own JavaScript computes over the full
  true data. Egress line: "sent: N tokenised rows (0 real names/numbers — checked)". The reach
  dial buttons are now live and reach-aware everywhere.

## Results (`benchmarks/runs/2026-08-24-open-lane-v1/`, screenshots 01–08)

Scholarship + Gemini Flash, one call, 53 s: **every reference number correct** (300, 103, 61,
136, 67.2 %; donut 55/61/76/60/48 exact; taluka and scheme bars match the verified counts), with
search + five working filter dropdowns — District=Gaya filters to 96, which is the pandas gold.
Fitness workbook: correct aggregate (avg sit-up gain 2.9), one flaw (a filter bound to the wrong
column). t4gc dial (Qwen 3.8 27B): all numbers correct after one syntax repair, 204 s. A text
question is answered from sample+stats with honest hedging but some speculation — the receipts
lanes remain the correct tool for questions.

The first attempt failed instructively: told to compute figures itself, the model re-emitted the
entire CSV inside the page, hit the output-token ceiling, and every KPI showed 0. The
already-benchmarked method (sample out, `window.data` in) fixed it — numbers computed in the
browser over real data are correct by construction.

## Harness verdict for this phase

**Not needed.** One shot through the shelter matches the Antigravity reference on numbers and
beats it on interactivity, at ~1 minute and ~$0.02–0.09. No agent loop, no file writes, nothing
to intercept. (The two earlier harness measurements stand for the record: agents recompute what
the browser can compute, slowly, and read raw files when confused.)

## Honest limits (also in backlog)

Regex-only detector: a name typed inside free text that never appears in any name column can
survive redaction (GLiNER upgrade path exists — the stage-3 shield's model, 181 MB CPU).
Open-lane numbers are the model's arithmetic in JS, not receipted queries — the UI says so under
every open page. Filter-to-column binding can be wrong. Sub-sampled files over 160 kB.
