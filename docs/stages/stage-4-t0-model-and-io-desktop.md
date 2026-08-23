# Stage 4 — The laptop tier: one small model, two lanes, a desktop shim (2026-08-23)

**Question.** Which small model is the "Laptop" (T0) rung of the reach dial in
`proposals/pii_idli.md`, and how far can a participant push it — questions,
follow-ups, "build me a dashboard", "write me a report" — before the dial, not
the model, has to move?

**Outcome: Qwen 3.5 9B, for both lanes, with the laptop doing the parts a 9B
cannot.** Seventeen candidates were run on three Ask suites (the frozen
stage-2 suite and holdout, plus a new 30-item *anchor* suite mirroring the
Sportathon / Foundation-Without / Lila-Poonawalla asks and the "different
headings for the same terms" case) and a new 12-request Build/Report gate.
Among models that fit an 8 GB laptop (Q4 ≤ 6 GB) the 9B is best on Build by a
wide margin (83/89 executable panels, 0 typed-number violations) and within two
answers of the best on Ask (suite 25/30, holdout 23/30, anchor 16/30). No
lane-specific second model is justified. T1 stays Qwen 3.5 27B (holdout
29/30, anchor 25/30). Full tables and method:
`chronology/2026-08-23T0230-t0-model-selection-and-io-desktop.md`.

**The T0 contract (what the model is allowed to do).** Ask: one read-only
DuckDB query; the laptop runs it and picks the chart. Build/Report: a JSON
plan of panels with SQL and a narrative whose numbers are `{{receipt}}`
placeholders; the laptop executes, lints typed digits out, and renders
deterministically (`benchmarks/t0/render_plan.py`). The model never sees a row
and never states a number. This is the "T0 honesty rule" of the proposal made
concrete, and it is why the 9B's pages are *clean*: the renderer, not the
model, owns layout, labels, scales and fallbacks.

**What the laptop does because the 9B cannot (measured, each a fixed
failure).** Dates typed at load (text-date casting was the top Build
failure); a topic-switch rule for prior turns (it joined the wrong file after
a subject change); a locally computed spelling-normalised join column when two
files name the same things differently (with it the Lila-Poonawalla
reconciliation is exact, 180/180; without it 0/3); KPI→table, line→scatter,
long-label→horizontal-bar guards; a visible "check this" flag on
percentage-shaped columns outside 0–100 (caught an inverted rate).

**Where the 9B stops (say it on the day).** Conventions must be spoken:
"endline minus baseline", "fall in percentage points, positive", "average of
the monthly rates". It reaches for a second file only when the question names
it. Asked for something the data lacks it may compute a proxy under that
title — the receipt shows the SQL. Report prose is generic. A prompt rule
asking it to list "missing" items made it worse and was rejected with
evidence.

**Local feasibility.** `Qwen3.5-9B-Q4_K_M.gguf` (5.7 GB) on llama.cpp CPU,
8 threads, thinking off via the chat template: 17 tok/s generation, first
answer ~30 s, follow-ups 15–18 s (prefix cache), a page ~50 s; holdout
19/30 locally vs 23/21 hosted (Q5_K_M also 19/30, so Q4 is the artifact).
Peak 5.6 GiB resident; docker cgroups at 8 GB and 7 GB both OOM-killed it,
so an 8 GB laptop fits it only with nothing else open. On event day T0 is
served from OpenRouter (the proposal says so); the local path is for the
claim, not the demo.

**The shim.** `app/io-desktop/`: Electron window over a stdlib Python service
(DuckDB + the renderer); Settings takes a local OpenAI-compatible URL *or* an
OpenRouter key (stored 0600 outside the repo). Sidebar: files loaded, reach
dial (Laptop live), egress counter (calls, bytes, rows = 0); every answer
shows "sent: column names only · rows: 0", the SQL receipt and a CSV download.
Verified under Xvfb through the real Electron window and via Playwright
against the service; screenshots in `benchmarks/runs/2026-08-22-io-desktop-walk/`.
Install: `./install.sh && npm start` (README in the folder).

**Evidence.** `benchmarks/runs/2026-08-22-t0-ask-v1/` (per-sample records for
every model × suite, including the rejected v1 phrasings and the OOM-killed
local run), `benchmarks/runs/2026-08-22-t0-build-v1/` (plans, executed
results, rendered pages, screenshots for the top candidates, the rejected
contract-2 runs), `benchmarks/v2/query-anchor-v1{,.1}.json` +
`benchmarks/v2/anchor-v1/` fixtures, `benchmarks/t0/`.

**Follow-up (2026-08-23 09:00, `chronology/2026-08-23T0900-…`).** Challenged
on overfitting, specialists, the T1 reference, generic builds and live data;
answered with runs. Unseen messy sectors (agri xlsx with title/footer rows,
WASH CSV with duplicate headers and comma numbers, MFI month-wide ledger):
loader hardened, 9B 8/12 vs Qwen 3.8 27B 9/12 through the real app; Arctic
7B Q8 19/30 holdout, 13/30 anchor (below the 9B, no Build); **T1 reference is
Qwen 3.8 27B** (holdout 30/30, 73/73 panels); a third *page* lane (webpage /
form / PWA, rows injected as `window.data` at view time, syntax + runtime +
"shows real data" checks with one repair) — 9B 5/8 on the page gate, Qwen 3.6
35B-A3B 7/8, so that lane is where a stronger hosted model is worth naming;
live re-run on file change (pages re-execute their receipts, last answers
recompute, no model call) — the FW edit-and-reorder demo works inside io;
exported pages are still static (duckdb-wasm is the next item).

**Left open.** A ~4 GB quant for 8 GB laptops with the OS resident; Windows install of the shim;
packaging as an installer; T1/T2 dial positions; sheltering (vault, lazy
review, egress monitor from the shield) — the next steps of the proposal.
