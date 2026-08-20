# Open semantic-critic screening

## Why this experiment exists

Full pipeline reruns mix planner randomness with critic quality. A planner can invent a bad comparison before the critic is called, or a critic can send a correct planner into a bad repair loop. `critic-replay-v1` therefore replays fixed executable plans and generic mutations against each reviewer. Critics receive the participant conversation, data structure, previous and candidate plans, and result schema, but no raw rows, min/max values, enumerated values or hidden answers.

The bank currently has 17 decisions across flat CSV, clean Excel, nested Excel, horizontally adjacent mixed-unit tables and PDF. It checks valid and invalid selector scope, explicit filters, ranking, derived rate versus numerator count, missing insights, unsupported causal claims, an extra-year PDF scope fault and loss of one requested measure. Mutations describe general failure shapes; none branch on sector words or expected numeric answers.

## What the fixed replay found

The best complete frontier reference is Gemini 3.7 Flash Low with the simple reviewer schema: 17/17 decisions, 99.614 recorded seconds and $0.0180165. A later repetition with a structured intent ledger scored 15/17: one response contained no valid JSON and one run inconsistently accepted the known extra-year PDF fault. Both repetitions are retained; the better run is not treated as guaranteed reliability.

Qwen 3.8 27B Low scored 15/17 in 392.879 recorded seconds and cost $0.0568313. It falsely rejected the corrected PDF plan and timed out on the missing nested-workbook insight. It is not a better always-on reviewer than the Gemini reference through OpenRouter.

Qwen 3 8B Low initially scored 15/16 in 209.518 seconds and $0.008510619, matching the then-current Gemini run's only semantic miss. It then failed the added numerator-count-versus-rate probe, as did Gemini before the prompt made conversation authority explicit. A structured two-stage critic that first records participant intent fixed that probe. In its full replay it made no semantic mistakes through 10 decisions, then three consecutive OpenRouter calls returned HTTP 429 while a concurrent Gemini bank was running. This run is operationally incomplete, not a 10/13 capability score. It is promising for local use but not yet promoted.

The smaller alternatives were not competitive as served by OpenRouter:

- Nemotron 3.5 Lightning stopped at 5/8 after one false rejection and two timeouts; 148.915 recorded seconds.
- Qwen 3.5 9B timed out on its first critic call at 120 seconds.
- Qwen 3.6 35B-A3B timed out on the single rate-versus-count probe at 60 seconds.

These latency results describe the available hosted providers, not eventual local throughput.

## Full webpage finding

GPT-OSS 20B plus Qwen 3 8B completed the three-turn smoke journey and produced a clean offline page with working selectors and downloads, no browser errors, no external requests and no overflow. Human inspection found the page visually solid. The independent oracle nevertheless failed it: the planner compared raw fully-immunised counts instead of deriving coverage from fully immunised divided by children due, and the critic accepted the planner's rewritten claim that the participant had explicitly requested a count.

This is not being repaired with an immunisation rule. The generic statistical guidance now says that group comparisons should not use a raw outcome count alone when a plausible base/eligible count exists, unless the participant explicitly asks for counts. More importantly, the critic must derive its intent ledger from the participant conversation before inspecting the candidate; candidate question/title/note are untrusted paraphrases.

The actual webpage evidence remains a failed run. It does not receive a passing score against the Antigravity smoke reference, even though it looks good.

## Current decision

Keep Gemini as the temporary semantic-review reference and escalation route. Continue testing the intent-ledger Qwen 8B critic without concurrent OpenRouter load; if it completes the fixed bank, rerun the full smoke and browser oracle. Do not promote Qwen 27B merely because it is larger. Do not add sector-specific production logic. After the critic contract is frozen, move to untouched cross-sector holdouts and paired Antigravity pages.

Evidence: [critic manifest](../benchmarks/critic-replay-v1/manifest.json), [Gemini 17/17](../benchmarks/runs/2026-08-20-open-critic-screening/critic-replay-v1/gemini37-flash-low/rep-04/result.json), [Qwen 27B](../benchmarks/runs/2026-08-20-open-critic-screening/critic-replay-v1/qwen38-27b-low/rep-01/result.json), [Qwen 8B intent-ledger run](../benchmarks/runs/2026-08-20-open-critic-screening/critic-replay-v2/qwen3-8b-low/rep-01/result.json), and [failed smoke screenshot](../benchmarks/runs/2026-08-20-open-critic-screening/smoke-001/split/gpt-oss-20b-low-qwen3-8b-low-critic/rep-02/turn-2/browser/desktop-initial.png).
