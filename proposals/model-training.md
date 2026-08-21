# Notes on why to train a model

Biggest open question to resolve first: exec accuracy of the LoRA 2b on the query slot with grammar-constrains. Maximum up to 9b.

If it clears say ~85% with one auto-escalation allowed, we're good; if not, 27b takes is invoked on query resolution too and concurrency becomes the constraint.

1-5 is the thinking, 6 below is the plan to execute.

## 1. Shrink the creative surface

Both antigravity and cline are open ended agentic codegenerators. A model that fits on a laptop will never win the openended race against them. The insight out game isn't open ended though. I suspect the socialsector game isn't, either. And if the game we're playing isn't open ended, then we can create a harness where trained llms fill constrained slots.

The trick is figuring out those slots.

Let's spec out the insights stack..

1. Data
2. Query - training (makes malformed output in a small model structurally impossible)
3. Spec/standards
4. Render/visualize

The data layer is your excel, csv, pdf.

Currently, the open ended agents "install" a bunch of dependencies all of which are _different_ on different laptops. But if our goal is to serialize these data sources into something that lets us focus on a higher layer of the stack, the problem is much simpler.

Just give people a single binary, no install drama - runs on any OS. This will kill the "agent installs python/ruby and hopes" step.

The query layer is something we can tune a small model on. This takes your english / indian-english and converts it to SQL. Or, more specifically, some algebra that supports the types of queries we observe NGOs making. _This_ is where a 2b/9b model fits. It is essentially a translation task, and one that is narrow enough that it can have a grammar-constrain decoding (explain: "outlines"/GBNF?). This layer needs to guarantee zero hallucinations (database queries and algebra tend to do that).

Now typically, the next layer would just be a visualization layer - but we have a privacy problem. Assume a frontier model produces the best visualizations and we dont want to pass NGO data to frontier models. What do we do?

Well, we can figure out a spec for the output of a query and pass that spec to the frontier model. Ask if for a visualization. Then "hydrate" that visualization with the real data client side. This way the real data never leaves a laptop.

This brings us to the rendering / charting layer. We send schema + column types + redacted summary stats to gemini and get a spec back. Gemini converts this into html, or a declarative chart spec (say vega-lite or echarts option json).

The final layer is rendering. Here we need to figure out - do we just embed the output of gemini in a template? If there is sufficient variance in the ouptuts returned by gemini maybe we can? This is what guarantees non-technical user never sees breakage. But the risk is templates look all the same. So we need to see if whatever is returned by gemini can make these templates look different..

## 2. Lower expectations on SMLs

This architecture kills the 8b model writes HTML idea. JSON -> HTML is a template job with 0% failure, an 8b doing it lead to weird overflows in the webpage and breaks user trust. We can still use a big model/small model split, but only as: 27b=composition/planning; small model = query translation.

This can take SMLs within spitting distance of frontier models.
Open ended website building does not.
Qwen 3.8 27b is an amazing model but trying to replicate that in a 9b isn't happening unless the prompter knows to code, or unless we know how to constrain the problem.

## 3. Escalations

This is the "i don't understand, figure it out" button. This needs escalations.

A laptop running a 2b/4b escalates to a 27b escalates to a frontier (but the frontier sees _only_ the schema). The users phrasing forces an escalation / replan -> SQL errors, spec fails schema check, headless screenshot fails a sanity diff (blank panel, overflow etc). The semantic meaning of figure it out translates to a retry against a higher model wti hthe break unsurfaced.

## 4. Installs and "watching it build"

The best local story may be one signed .exe (Tauri or go binary embedding duckdb + webview + harness). Double-click and done. No docker/runtime roulette. A server side hosting is appealing but could break trust.

Watching it build (like antigravity sometimes does) is a cool experience but can be mirrored by replacing playwright with progressive skeleton rendering. First the dashboard skeleton appears, then panels stream in as queries execute. Maybe streaming the plan/reasoning in the side panel covers the remaining interactivity (what's happening when the dashboard isn't bulding).

This still leaves us with how to get variety without hardcoding. Vega lite's spec space is huge. Maybe that's enough, or maybe the frontier model generating the site is enough for variety. Maybe even ghost themes are enough. We really should not have to go fully ruby install for this alone.

## 5. Event vs data

Lets say we just use the event for training data.

Event: openrouter + harness.
Log every query/dataset/schema/spec/escalation.
Use that as the prompt corpus for the SML tuning.

The other option is to train the SML using scraped and synthetic data.

## 6. Plan

GOAL: benchmark insight pipelines on fixed task suite; screenshot-confirm like a human.
OUT OF SCOPE TONIGHT: installers, Tauri/.exe, server hosting, model tuning.

ORDER OF WORK (sequential; reallocate remaining time if a stage fails):
  S0 harness skeleton: DuckDB ingest + M-Schema serializer (schema->prompt) +
     spec->template render (vega-lite/echarts) + headless screenshot.
     This is an eval rig, not the product.
  S1 datasets + gold: [paths to real datasets] OR synthesize 3-4 NGO-realistic sets
     (district/state/year granularity; inject messiness: mixed date formats, state
     spelling variants). Author gold SQL IN DUCKDB DIALECT, verify it executes,
     freeze gold SQL + gold RESULT SETS per task per dataset. Commit BEFORE any
     pipeline run. T7 gold accepts either IQR(1.5x) or z>2 outlier definitions.
  S2 QUERY-SLOT EVAL (gating): xiyan-3b-2504 | xiyan-7b-2504 | arctic-text2sql-r1-7b |
     qwen3-8b (control) | qwen-27b on NL->SQL, DuckDB dialect.
     PREFLIGHT: download each from HF, load, run one smoke query BEFORE the suite;
     record quant in score.json (3b at q4 = laptop rung; 7b+ at q8/fp16 = server).
     Output handling: prompt for bare SQL; validate via sqlglot parse + DuckDB
     EXPLAIN; on dialect error, one sqlglot transpile attempt (sqlite/postgres ->
     duckdb, log it); on exec error, retry. Grammar-constrained decoding
     (GBNF/outlines) is an ABLATION on one model only, not the default path.
     Metric: EXECUTION accuracy (result-set match vs gold), not SQL string match.
     >=5 phrasings per task, terse/Indian-English style. T2 runs multi-turn with
     T1 context.
     DECISION GATE: smallest model >=85% (one auto-escalation allowed) takes the
     laptop rung. If none passes, laptop rung = escalate-only; best 7-8b takes the
     server query slot. Report per-model per-task accuracy either way.
  S3 PIPELINES (only S2 survivors in query slot):
     P2 harness: query-model + 27b spec + template render
     P3 harness: query-model + frontier(schema-only) spec + local hydrate
     P0 antigravity / P1 cline+qwen-27b: populate from EXISTING run artifacts ONLY.
     Do NOT launch antigravity unattended; if artifacts missing, leave row blank.

TASK SUITE (per 3-4 real-ish NGO datasets):
  T1 basic agg dashboard ("show me a dashboard of X")
  T2 drilldown follow-up ("break that down by district")
  T3 temporal compare ("compare 2019 vs 2020")
  T4 cross-dataset join ("match states across these two files")
  T5 trend/correlation ("is X related to Y over time")
  T6 colocation ("show all X within Y" or "show all places with X and Y")
  T7 search/match ("show all outliers" or "values that don't match a pattern")
  ...expand in subsequent iterations using event data.

ESCALATION + PRIVACY (hard requirement): unknown/failed queries escalate up the
ladder. 27b may see real data; frontier NEVER does — frontier calls go through a
wrapper that samples distinct cell values per column and asserts none appear in
the outbound payload (schema + column types + redacted stats only). Any hit =
failed run + logged.

RUBRIC per run:
  correctness: compare hydrated spec data vs gold result sets (JSON, not OCR)
  render integrity: headless screenshot; VIEW each image; fail on overflow/blank/
    clipped labels/missing axes/empty panel
  aesthetics: model-as-judge 1-5 (hierarchy, labels, palette coherence, density).
    Judge = frontier ONLY if datasets are synthetic (screenshots contain data
    values); if real datasets, judge with local 27b. Copy best/worst 5 shots to
    review/ for human check.
  time-to-first-visual (cap 90s), total (cap 4min)
  retries to success (cap 3; count escalations by rung; transpile = 0.5 retry)
  variety: within-dashboard >=3 chart types where data supports it; across suite
    fail if >60% single type

OPS: artifacts at runs/{pipeline}/{query_model}/{dataset}/{task}/{trial}/
  (query.sql, result.csv, spec.json, shot.png, score.json). Skip cells whose
  score.json exists (resumable). Hard cap 10min/cell then mark failed, move on.
  Append to RESULTS.md after every cell; chronology commit per stage.

MORNING DELIVERABLES: RESULTS.md (pipeline x task matrix + per-model query-slot
  accuracy), DECISION.md (smallest model clearing 85% or "none"; recommended
  query model per rung; 27b vs frontier spec verdict w/ aesthetic scores;
  binding constraint for 20-user event), review/ screenshots.
