# Foundation re-verification of the local-first ladder

Date: 2026-08-21. Scope: re-derive the claims behind the current event
decision (`v2-local-first-event-decision.md`) from the raw runs, then run one
realistic out-of-sample holdout and a small-model screen. Aggregate:
[`benchmarks/results/foundation-reverification-2026-08-21.json`](../benchmarks/results/foundation-reverification-2026-08-21.json).

## Verdict in one paragraph

The *model ranking* in the saved evidence is honest and reproduces: XiYan ≪
Arctic 7B (~25/30) < Qwen 3.8 27B (28–30/30). Almost everything built on top
of that ranking does not survive contact with realistic data. The "generic"
router is regex tuned to the 30 dev phrasings; out-of-sample it accepts wrong
answers (6 of 22 accepted for Arctic Q4) and escalates correct ones. The
"30/30 routed replay" was never run through the router (the router rejects
Qwen's own correct answers for a whole task family, so the shell would fail
closed on them). Qwen's 30/30 is the best of three reps (28, 28, 30). The
dashboard-quality gap to Antigravity is much larger than the "within 5–8%"
wording, and the Antigravity "stale page" evidence is confounded by a harness
error. Separately: a 2026 general 9B model matches Arctic Q4 on the dev suite
and beats it on the holdout, the 27B gains +20 points from the shell's prompt
while Arctic gains nothing, and the small Qwen 3.5/3.6 models that Codex wrote
off as "timed out / no usable JSON" were victims of a runner bug (thinking
models returning empty `content`), not capability.

## What reproduces

| Claim | Status | Evidence |
|---|---|---|
| Arctic Q4 25/30, Q5 24/30, Q8 24/30, BF16 26/30 on gate-v2 | reproduces by rescoring saved SQL against current gold/evaluator | rescoring in aggregate JSON |
| XiYan 3B 11/30, 7B 19/30 | reproduces (older manifest wording; 1–4 phrasings differ) | same |
| Qwen 3.8 27B 30/30 | reproduces for rep-04; reps 01/03 rescore to 28/30. Honest figure ≈ 96% | `runs/2026-08-21-v2-query-gate-v2/qwen38-27b-openrouter/` |
| Frontier envelope is value-free | holds; contains intent enum, column names/types/roles, layout contract | `agriculture-q4/rep-05-final/turn-3/frontier-layout-envelope-not-sent.json` |
| Final pages load offline, no console errors, download works | holds for the agriculture page (browser-check.json) | `agriculture-q4/rep-05-final/browser/` |
| Q4 weight SHA-256 `9c0052…` | verified before my runs | — |

## What does not hold

### 1. The suite is small, clean and partly edited after seeing failures

"30 cases" is 6 tasks × 5 paraphrases on fixtures of 7–21 rows with clean
snake_case headers. Phrasings name the columns almost verbatim ("employed at
6 months over enrolled"). Four manifest revisions exist; edits added words like
"as a percentage" / "for each district" after models failed. Gold SQL never
changed, so the rescoring is fair, but the suite measures easy, well-specified
questions only. Q4/Q5/Q8 at 25/24/24 are indistinguishable at n=30; "Q4 beat
the larger quants" is noise, not a finding.

### 2. The router is overfit and contradicts its own oracle

`replay_query_router.py` patterns include `"higher" and "in order"` (phrasing
5 of task 1), `"region and period"`, `"give region"`, `"worst first"` — the
dev phrasings themselves. It was edited twice *after* the holdout-v1 result
that was labelled "frozen, may not be changed". Its period-retention rule
escalates every "change between two years" answer, including the gold SQL's
own shape, so:

- current router on Qwen's 30/30 run: 25 accepted, **5 correct answers
  escalated** → in the shell this is fail-closed, so the real ladder on the
  frozen suite is 25 accepted + 5 stops, not 30/30;
- current router on holdout-v1 (BF16): 12 accepted, 3 correct answers escalated
  (recorded as 15/0 with the earlier router);
- holdout-v1 was only ever run with BF16, never with the chosen Q4 tier.

On the new holdout-v2 (below) the router accepted **6 wrong Arctic answers of
22 accepted** and 4 wrong Qwen answers, while its escalations were mostly false
positives ("percentage request has no ×100" on columns that are already
percentages; "change omits periods" on a correct relative-growth answer). The
"accepted zero wrong answers" claim was an in-sample artifact.

### 3. The gate measured a different prompt than the shell uses

The gate prompt says "You are a SQLite expert" and executes on DuckDB; the
shell prompt is a DuckDB prompt with known category values and rules. Several
Arctic failures on realistic data are SQLite-tolerant `GROUP BY` shapes that
DuckDB rejects. The two prompts were never compared until now (see §5).

### 4. Dashboard quality and the Antigravity comparison

Open the two screenshots side by side:
`runs/2026-08-21-local-first-cli/agriculture-q4/rep-05-final/browser/desktop-initial.png`
and
`runs/2026-08-21-v2-dashboard-journey/agriculture/antigravity-default/rep-02/browser-final/desktop.png`.
Antigravity produced a four-KPI, three-chart, ranked-table dashboard whose
numbers all check (3.20/2.70/2.50 t/ha, weighted 2.79, YoY +6.67 %). The local
page charts one delta with odd axis ticks (0.22/0.17/0.11/0.06), buries the
2023/2024 endpoints in a table and has one insight card. The XLSX page has
colliding 2023 labels and "Table 2; Table 1" provenance on every row. An honest
unblinded grade is ~6.5–7/10 vs ~9/10, not 8.3–8.6 vs 9.0.

The "page hash never changed after turn one" finding is literally true but the
cause is the headless Antigravity CLI refusing `write_to_file` to `/workspace`
("artifacts must be in …/brain/") on every turn inside the container harness.
A real IDE user would not hit that. The only clean evidence that Antigravity
goes stale on follow-ups is the phase-1 real-IDE smoke. The CDN-offline failure
is real.

### 5. GPT-OSS

GPT-OSS 20B is not in the current ladder; it lived in the earlier JSON-plan
"split pipeline" and was demoted to diagnostic. Measured here with the same gate:
28/30 on gate-v2 (above Arctic's 25) and 22/30 on holdout-v2 (above Arctic's
19, below the 2026 general models). Codex's instinct was defensible; it just
was not the best small option available.

## New measurements

### Holdout-v2 (frozen before the first model run)

`benchmarks/v2/query-holdout-v2.json`, fixtures generated by
`benchmarks/v2/build_holdout_v2_fixtures.py` (seed 20260821): headers with
spaces/units/parentheses, `State Total` rows mixed into a district factsheet,
`NA` cells, a 360-row loan register with text dates, share-of-total,
conditional counts, relative growth, null-aware averages, years-as-columns and
two joins. 10 tasks × 3 terse phrasings. Gold is unrounded; the manifest uses
`numeric_abs_tolerance: 0.06` so a model's `ROUND(x,1)` still counts (the gate
runner now supports separate abs/rel tolerance; old manifests are unaffected
and rescore identically).

| Model | Prompt | Holdout-v2 | Gate-v2 | Secs/30 | Router accepted-wrong (holdout) |
|---|---|---:|---:|---:|---:|
| Arctic-Text2SQL 7B Q4 (local llama.cpp) | gate | 19/30 | 25/30 | 414 | 6 |
| Arctic-Text2SQL 7B Q4 (local) | shell | 19/30 | — | 453 | 7 |
| Qwen 3.8 27B, low reasoning | gate | 23/30 | 30/30 | 289 | 4 |
| Qwen 3.8 27B, low reasoning | shell | **29/30** | — | 320 | 1 |
| Qwen 3.5 27B, no thinking | shell / gate | **29/30** | **29/30** | 102 | 1 |
| Qwen 3.6 35B-A3B, no thinking | shell / gate | 25/30 | 27/30 | 108 | 1 |
| Gemma 4 31B, no thinking | shell / gate | 25/30 | 25/30 | 87 | 3 |
| **Qwen 3.5 9B, no thinking** | shell / gate | **24/30** | **25/30** | 128 | 3 |
| Gemma 4 26B-A4B (4B active), no thinking | shell / gate | 24/30 | 23/30 | 95 | 4 |
| GPT-OSS 20B, low | shell / gate | 22/30 | 28/30 | 105 | 3 |

Single reps, n = 30, OpenRouter providers; treat one-answer differences as
noise. Remote small models were not served locally yet.

What the failures are: across every model the dominant holdout miss is the
`State Total` row inside the district column. With schema only, models cannot
know it exists; with the shell's known-category list most still include it
unless told that aggregate rows are not detail rows. That is a generic rule,
not a sector rule, and it is the single cheapest accuracy win available.

### Runner defects fixed

- Thinking models (Qwen 3.5/3.6, Gemma 4) returned empty `content` with
  `reasoning.effort=low`; the runner scored that as failure. This is the real
  cause of Codex's "Qwen 3.5 9B timed out / no usable JSON". `--reasoning-effort
  none` now sends `reasoning.enabled=false`; these models then answer in 3–5 s.
- `--prompt-style gate|shell|shell-plus` lets the gate measure the prompt the
  shell actually uses. `shell-plus` adds the aggregate-row rule and has not
  been measured yet.

## What this means for the event foundation

1. **Keep**: DuckDB as the only calculator, read-only SQL parsing, local
   rendering, the frontier envelope policy, the evidence discipline
   (runs/results/chronology).
2. **Replace the laptop tier**: Arctic Q4 buys nothing over a 2026 general 9B
   (equal on the dev suite, worse on realistic data, cannot use context, and is
   a single-purpose model that cannot clarify, title or plan). Qwen 3.5 9B or
   Gemma 4 26B-A4B are the candidates; both must still be served locally and
   timed.
3. **Replace the router**: regex obligations do not generalise. Options to
   measure next: (a) 27B-as-checker on the small model's SQL + result sample,
   (b) small-model self-consistency (two phrasings of the plan agree), (c) no
   small tier at all — one DGX 27B call is ~3.5 s with thinking off, which may
   make the whole laptop tier unnecessary for 20 users.
4. **Keep the 27B tier, reconsider which**: Qwen 3.5 27B without thinking
   matched Qwen 3.8 27B low-reasoning at a third of the latency and cost. Serve
   one locally on the DGX before choosing.
5. **Dashboard**: the deterministic renderer is correct but thin. The gap to
   Antigravity is composition (KPIs, endpoints + delta, ranked table), which a
   value-free layout spec from any 27B/frontier can provide without seeing
   data. This is the largest remaining product gap and was under-reported.

## Not done here

No local serving of the 9B/27B candidates, no Windows, no concurrency, no
re-grading of the XLSX/PDF shapes, no new dashboard work. Holdout-v2 is now
seen by these models; do not tune rules against it and re-report. Next rules
need holdout-v3.
