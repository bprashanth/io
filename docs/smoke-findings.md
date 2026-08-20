# Smoke findings before the measured benchmark

These are unblinded engineering results. They establish that the runners work
and expose failure modes; they are not the final model comparison.

## Comparable outer-container runs

Default Antigravity resolved to Gemini 3.7 Flash (High). Its three-turn page was
the richest visually and the final download was correct, but the page retained
six visible references to 2022 after the user requested only 2023 and introduced
unsourced performance bands. Total time was 490.610 seconds. Preliminary smoke
score: 89/100.

Cline with exact `qwen/qwen3.8-27b:nitro` completed the same live multi-turn
conversation in an equivalent outer container. Its 2023 display, source and
caveat were correct, and the narrow page was clean, but that repetition's CSV
download omitted required year and source fields. Total time was 479.746
seconds. Preliminary smoke score: 92/100.

A controlled low-reasoning Cline repetition also resolved every request to the
exact Qwen 3.8 model. It made 38 successful requests through Reka and AkashML,
used 810,226 prompt tokens and 23,341 completion tokens (6,038 reasoning), cost
USD 0.43929290, and took 540.072 seconds. Displayed values, provenance and the
no-guess caveat were correct. The download included source but omitted year,
and the narrow table widened the 390 px page by 15 px. Preliminary smoke score:
91/100.

The Qwen scores being slightly above Antigravity here do not establish
non-inferiority. The case is tiny, grading was unblinded, and run-to-run defects
differed. The useful conclusion is narrower: the 27B candidate is capable
enough to enter the frozen screening set, and low reasoning is not presently a
speed/cost optimisation.

## Evidence

- [Antigravity preliminary grade](../benchmarks/runs/2026-08-19-smoke/smoke-001/antigravity/default/rep-04-container/grading/preliminary-human.json)
- [Qwen default-routing container grade](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-07-acp-container/grading/preliminary-human.json)
- [Qwen low-effort provider summary](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-08-acp-container-low/openrouter-summary.json)
- [Qwen low-effort deterministic checks](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-08-acp-container-low/grading/checks.json)
- [Qwen low-effort desktop screenshot](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-08-acp-container-low/browser/desktop.png)
- [Qwen low-effort narrow screenshot](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-08-acp-container-low/browser/narrow.png)
