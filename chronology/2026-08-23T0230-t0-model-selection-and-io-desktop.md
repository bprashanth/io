# 2026-08-23 02:30 — T0 model selection, two-lane gates, io desktop shim

Overnight experiment for step 1 of the order of work in
`proposals/pii_idli.md`: pick the laptop-tier ("T0") small model, measure how
far a participant can push it in the Ask lane and the Build lane without
turning the reach dial, and ship a desktop shim that can be tested on a
laptop tomorrow. Everything below was produced tonight; raw runs are under
`benchmarks/runs/2026-08-22-t0-ask-v1/`, `benchmarks/runs/2026-08-22-t0-build-v1/`
and `benchmarks/runs/2026-08-22-io-desktop-walk/`.

## Contracts (what T0 is allowed to do)

- **Ask lane**: the model writes one read-only DuckDB query; the laptop runs
  it; a deterministic auto-viz picks KPI / bar / line / table. Prompt = the
  live shell's prompt (stage 2). Two extra rules were tried as
  `--prompt-style io` / `io-quote` in `benchmarks/scripts/run_v2_query_gate.py`
  and measured neutral-to-negative for the 9B (addenda below), so the app
  ships the shell prompt unchanged.
- **Build / Report lane**: the model returns a JSON *plan* — title, 3–7
  panels each `{kind, title, sql, x, y, unit}`, optional narrative whose
  numbers must be `{{receipt}}` placeholders. The laptop executes every
  panel, lints the prose for typed digits, and renders with
  `benchmarks/t0/render_plan.py` (inline SVG, two templates). Runner:
  `benchmarks/t0/run_build_gate.py`; suite: `benchmarks/t0/build-suite-v1.json`
  (12 requests over the PII corpus tables and holdout-v2: dashboards, board
  reports, a "website page", "are girls and boys improving equally").

## Suites

- `query-suite-v2` (30), `query-holdout-v2` (30): frozen from stage 2.
- **`query-anchor-v1`** (new, 30 = 10 tasks × 3 phrasings, built by a
  delegated agent from a spec): synthetic mirrors of the three anchor demos
  plus two generic patterns — Sportathon baseline/endline (dropouts,
  improvement ranking, per-site change), Foundation-Without 30-household
  vulnerability composite and income-per-member with blanks, Lila-Poonawalla
  outreach vs applications with messy school spellings (exact join matches
  36 %, jaro-winkler ≥ 0.9 best-match 100 %), attendance 2023/2024 with
  *different headers for the same concept*, donations repeat-donor share.
  Fixtures are byte-reproducible (`benchmarks/v2/build_anchor_v1_fixtures.py`,
  seed 20260823; an early draft leaked set-iteration order and was fixed).
- **`query-anchor-v1.1`**: after the *references* (Gemini 3.7 Flash, Qwen 3.5
  27B) scored 0/3 on three tasks, their phrasings were made unit- and
  aggregation-explicit ("average of the monthly rates", "fall in percentage
  points as a positive number", "each application counts towards only its
  single best matching school"). Gold SQL unchanged; v1 results kept. The
  FW ranking task became order-insensitive because the small-integer
  composite legitimately ties.

## Ask-lane results (execution accuracy, shell prompt unless noted)

| model | fits 8 GB laptop | suite-v2 | holdout-v2 | anchor-v1.1 (io prompt) |
|---|---|---|---|---|
| **Qwen 3.5 9B** | yes (Q4_K_M 5.7 GB) | 25 | 23 | 16 |
| Ministral 8B (2512) | yes | 23 | 23 | 15 |
| Granite 4.1 8B | yes | 21 | 20 | 14 |
| Qwen3 8B | yes | 22 | 13 | – |
| Gemma 3 12B | marginal | 18 | 11 | – |
| Gemma 3n E4B | yes | 15 | 1 | – |
| Llama 3.1 8B | yes | 12 | 10 | – |
| Phi-4 (14B) | no | 23 | 23 | – |
| Ministral 14B | no | 22 | 23 | 17 |
| Qwen3 14B | no | – | 20 | – |
| gpt-oss-20B (low reasoning) | no | 26 | 21 | 20 |
| Nemotron-3 nano 30B-A3B | no | 20 | – | – |
| Gemma 4 26B-A4B | no (~16 GB) | 24 | 25 | 22 |
| Qwen 3.5 35B-A3B | no | 24 | 26 | 18 |
| Qwen 3.6 35B-A3B | no (~20 GB) | 27 | 25 | 23 |
| Qwen 3.5 27B (T1 reference) | no | 23 | 29 | 25 |
| Gemini 3.7 Flash (T2 reference, low reasoning) | — | 20 | 28 | 25 |

(anchor-v1 with the plain shell prompt and anchor-v1-io are also on disk;
the jaro hint alone did not move the fuzzy tasks for any model.)

## Build-lane results (12 requests; panels the laptop could execute and chart)

| model | plans valid | panels ok | fully clean pages | typed-digit violations | mean s |
|---|---|---|---|---|---|
| **Qwen 3.5 9B** | 12/12 | 83/89 | 7 | 0 | 27 |
| Gemini 3.7 Flash | 12/12 | 80/80 | 11 | 1 | 8 |
| Qwen 3.5 35B-A3B | 12/12 | 74/79 | 9 | 2 | 6 |
| Qwen 3.6 35B-A3B | 12/12 | 71/76 | 10 | 0 | 10 |
| Qwen 3.5 27B | 12/12 | 61/75 | 6 | 1 | 28 |
| Gemma 4 26B-A4B | 12/12 | 58/64 | 10 | 0 | 20 |
| gpt-oss-20B | 12/12 | 53/59 | 9 | 0 | 9 |
| Gemma 3 12B | 12/12 | 45/64 | 3 | 2 | 25 |
| Ministral 14B | 8/12 | 44/55 | 1 | 3 | 18 |
| Qwen3 8B | 12/12 | 41/53 | 5 | 2 | 13 |
| Llama 3.1 8B | 12/12 | 37/62 | 3 | 0 | 12 |
| Granite 4.1 8B | 12/12 | 35/45 | 7 | 2 | 7 |
| Ministral 8B | 6/12 | 31/38 | 2 | 2 | 15 |
| Gemma 3n E4B | 12/12 | 25/53 | 1 | 1 | 17 |

"Panels ok" is executable-and-chartable, not semantic truth. Human grading
of the 9B's twelve plans (titles vs SQL, screenshots): dashboards are
complete and clean; the recurring semantic fault is **proxy substitution** —
asked for a "disbursed amount" or an "application trend" the data does not
contain, it computed family income or grouped by date of birth under that
title. A contract rule asking for a `"missing"` list instead made the 9B
declare existing columns missing and dropped its executable rate from 93 %
to 83 % (35B-A3B also fell); rejected and kept under
`contract2-rejected-*`. The defence stays the receipt (SQL on every panel).

## Decision

**T0 = Qwen 3.5 9B for both lanes.** Among models that can live on an 8 GB
laptop it is best on Build by a wide margin and within two answers of the
best on Ask; no lane-specific second model is justified (the user's "20 %
gap" rule is not met by any laptop-sized pair). T1 stays Qwen 3.5 27B
(holdout 29/30, anchor 25/30). If T0 is served from OpenRouter on event day
anyway, Qwen 3.6 35B-A3B is the strongest cheap hosted option (Ask 27/25/23,
Build 71/76, ~10 s), but calling it "laptop" would misdescribe the tier.

Local feasibility of the pick: `unsloth/Qwen3.5-9B-GGUF` Q4_K_M served by
llama.cpp CPU-only with 8 threads: 60 tok/s prompt, 17 tok/s generation,
first Ask ~30 s, follow-ups 15–18 s with the prefix cache, 5.2–5.5 GB
resident (peak 5.6 GiB measured on real prompts). Under an **8 GB docker
cgroup the 8192-context server was OOM-killed**, and again under 7 GB with
`-c 6144 -b 256 -ub 256` and q8 KV cache; the gate was finally run uncapped
(`local_qwen3.5-9b-q4km-cpu8/`). A Build page is ~50 s locally. Accuracy of
the quantised local model is in the addenda.

## io desktop (app/io-desktop)

Electron window → `server/io_service.py` (stdlib HTTP, DuckDB, the same
renderer) → model via a local OpenAI-compatible URL or OpenRouter + key
(saved 0600 under `~/.config/io-desktop/`). Verified under Xvfb via CDP with
the local CPU model and via Playwright against the service with the 9B on
OpenRouter; screenshots in `benchmarks/runs/2026-08-22-io-desktop-walk/`.

Things the service does deterministically because the 9B could not:

- **Date columns are typed at load** (dd-mm-yyyy, ISO timestamps) — the
  9B's most common Build failure was casting text dates.
- **Topic-switch rule**: prior turns are carried only when the question's
  words do not point at other files; without it the 9B joined outreach to
  *donations* after a donations question.
- **Spelling-normalised join column**: when two files name the same things
  differently (≥ 85 % of values match approximately, < 80 % exactly), the
  smaller side gets a `"School (as in lpf_outreach)"` column computed with
  jaro-winkler best-match locally. With it the 9B answers the Lila Poonawalla
  reconciliation exactly (180/180 schools, zero-application schools
  included) where it scored 0/3 writing the matching itself; a two-sided
  variant and a separate bridge table both confused it (joined normalised to
  normalised, wrong join direction) and were discarded.
- Renderer guards: KPI with many rows → table; line over raw numeric pairs →
  scatter; long labels → horizontal bars; query order preserved on the x axis
  (an earlier alphabetical sort put months in the order May, June, March);
  ticks for tiny values; percentage-looking columns outside 0–100 get a
  visible "check this" flag (caught the 9B inverting enrolled/present to
  145 %); failed panels say so plainly with the error in the receipt.

## Limits of the 9B a participant will hit (measured)

- Sign and unit conventions must be stated ("endline minus baseline", "in
  percentage points, positive"); otherwise 0–1 of 3 phrasings pass.
- Aggregation level: it averages monthly rows unless told "average of the
  monthly rates per centre"; "biggest fall" came back per month.
- It reaches for a second file only when the question mentions it ("schools
  with zero applications" filtered `Applications Expected = 0`).
- Difference-of-averages vs average-of-differences when dropouts exist.
- Report prose is generic; numbers are right because they are receipts.
- Follow-up "only for girls" after a question on a file with no gender column
  silently switched files; the UI now shows a scope-change warning.

## Addenda (03:00–05:00)

- **Prompt rules do not help the 9B.** Hosted 9B on holdout: shell 23 and 21
  (two runs), shell + quoting/UNION rule 19, shell + both io rules 20; on
  anchor-v1.1: shell 19, io-quote 16, io 16. Run-to-run variance of the
  hosted 9B is about ±2, so the rules are at best neutral; the app now uses
  the stage-2 shell prompt unchanged (plus a bridge note when a normalised
  column exists). The gate keeps `io` and `io-quote` styles for the record.
- **Local quantisation costs real accuracy.** Q4_K_M on CPU with thinking
  off via `chat_template_kwargs` (this llama.cpp build ignores
  `--reasoning-budget 0` for Qwen 3.5; the first local run returned only
  reasoning and is kept as `*-thinking-leak-rejected`): holdout 16/30 and
  anchor-v1.1 15/30 with the io prompt, against 20/16 hosted with the same
  prompt. With the plain shell prompt the same local Q4_K_M scores **19/30**
  on holdout (hosted: 23 and 21), and Q5_K_M (6.6 GB file, 6.7 GiB resident)
  also scores 19/30 — so Q4_K_M is the laptop artifact and the local gap is
  two to four answers. Peak resident memory on real prompts is 5.6 GiB; an
  8 GB and a 7 GB docker cgroup both OOM-killed the server (mmap/page-cache
  accounting), so "fits an 8 GB laptop" means *just*, with nothing else
  open. Runs: `local_qwen3.5-9b-q4km-cpu8/` (io and shell),
  `local_qwen3.5-9b-q5km-cpu8/` (shell).
- **Report lane placeholder grammar.** `{{p5}}` on a multi-row panel used to
  resolve to a bare number, so prose said "15.12 L was the most generous
  city". Now `{{p5}}` renders "label (value)" of the first row, `{{p5[2]}}`
  the second, `{{p5[2].City}}` a named cell; 0-based indexes are accepted
  because the 9B counts from 0 about half the time; references to panels,
  rows or columns that do not exist render as "[not computed]" rather than
  raw braces. Residual limit: the 9B sometimes points a placeholder at the
  wrong panel (cities described with payment-mode figures) — the numbers are
  still receipts, the attribution is not. Report prose at T0 should be shown
  as a draft; T1 is the honest tier for narrative.

## Open

- Try an IQ3/Q3_K_M quant (~4.3 GB) if the event laptops turn out to have
  only 8 GB with the OS resident; or accept T0-hosted.
- Windows install path of the shim untested; Electron packaging (an
  installer rather than `npm start`) not attempted.
- T1/T2 dial positions, sheltering (vault, review sheet) and the egress
  monitor from the shield are the next steps of the proposal, not started.
