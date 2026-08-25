# Open lane vs the Antigravity reference (2026-08-24)

Reference: stage 3, Antigravity 1.107 + privacy shield on the scholarship corpus —
dashboard with 300 / 103 / 61 / 136 / 67.2 % all correct
(`benchmarks/runs/2026-08-22-antigravity-ide-shield-v2/04-dashboard-built-through-shield.png`).
Frontier: google/gemini-3.7-flash, same as `benchmarks/runs/2026-08-21-remote-dashboard/`.
Gold recomputed with pandas: total 300; Disbursed 55 + Approved 48 = 103; Rejected 61;
Pending 60 + Under Review 76 = 136; avg marks 67.2; District Gaya = 96.

io open lane (this run): folder → shelter (stage-3 vault: 12 columns hidden, 2 224 tokens;
review modal = 02) → schema + per-column stats + 20 tokenised sample rows per table sent
(7.9–20 kB; final consistency pass over the whole payload; leak gate asserts 0 vault values
outbound) → model returns a free HTML page → io rehydrates tokens and injects the REAL rows
as window.data at view time → the page's own JavaScript computes over the full data.

| run | model | result |
|---|---|---|
| scholarship dashboard | gemini-3.7-flash, 1 call, 53 s | all reference numbers correct; donut 55/61/76/60/48 exact; 5 filter dropdowns + search; District=Gaya filter → 96 (= gold) (04, 05) |
| fitness dashboard | gemini-3.7-flash, 1 call, 55 s | 200 records, gold avg sit-up improvement 2.9 on page; flaw: the Location filter bound to school-villages, not the 6 sites (06) |
| outreach question (text) | gemini-3.7-flash, 7 s | reasoned, honest about working from sample+stats, some speculation — the ask lane is the correct tool for this |
| scholarship dashboard | qwen/qwen3.8-27b (t4gc dial), 2 calls, 204 s | all reference numbers correct (08) |

First attempt (kept in history) failed exactly the way that motivates the design: asked to
compute figures itself, the model re-emitted the whole CSV into the page, hit the output
ceiling, and every KPI rendered 0. The benchmarked remote-dashboard method (sample out,
window.data in) fixed it in one step.

Harness verdict for this phase: **not needed** — a one-shot frontier call through the shelter
matches the Antigravity-with-shield reference on numbers and exceeds it on interactivity,
at ~$0.02–0.09 and ~1 minute. Known limits: regex-only detector (a name typed inside free
text that never appears in a name column can survive — GLiNER upgrade path noted in backlog);
text answers speculate beyond the sample; model may bind a filter to a wrong column.
