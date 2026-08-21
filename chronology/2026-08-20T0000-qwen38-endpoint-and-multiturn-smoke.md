# Qwen 3.8 27B exists; the catalogue was stale, and the real multi-turn run worked

The proposed model ID was correct. A direct OpenRouter endpoint request on
2026-08-19 returned `qwen/qwen3.8-27b`, five active endpoints and up to 262,144
tokens of context. The public `Qwen/Qwen3.8-27B` weights also exist under
Apache-2.0; the Hugging Face revision checked was
`1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.

Cline 3.0.55's OpenRouter ACP catalogue had not caught up. It omitted the new
slug, and an early diagnostic silently selected Claude Sonnet 5. That run is
invalid. The runner now fails closed for catalogue models. For this new model we
use Cline's supported OpenAI-compatible provider with OpenRouter's base URL and
the exact free-text model ID. This is not a replacement harness; it is the same
Cline agent path that will later point at a local vLLM endpoint. Cline's saved
message metadata records the requested Qwen model on every model response.

The first exact default-route attempt read the CSV and planned the page, but its
upstream stream went idle before the first edit. We retained it as a provider
failure. OpenRouter's `:nitro` routing suffix then selected the same underlying
Qwen 3.8 27B model while prioritising throughput. That run completed all three
prompts in one live Cline ACP session in 341.252 seconds.

The result got the important things right. It showed the 2023 figures, identified
Purnia as lowest at 76.0%, said the file contained no evidence for a reason, kept
the source label, and downloaded the exact three 2023 rows. The page opened with
HTTP 200 and no browser, console or request errors. Cline reported 332,505 input
tokens, 150,528 cache-read tokens and 18,315 output tokens. Its generic
OpenAI-compatible adapter reported zero cost, so that zero must not be treated
as provider billing.

The rendered page was clean and easy to read on desktop, but materially behind
the Antigravity smoke page in visual richness. More importantly, its table made
the 390 px page 146 px too wide, clipping the right-hand source column. This is
a presentation failure, not a numerical failure, and is exactly why browser
screenshots and mobile checks are part of the benchmark.

Two older-generation diagnostics gave additional harness evidence. Qwen 3.5
27B completed the conversation and produced correct numbers, source and CSV,
but had overlapping chart labels and a horizontally clipped mobile table. Qwen
3.6 27B wrote JavaScript files wrapped in literal `<script>` tags, causing page
syntax errors and a blank chart/table. These are smoke diagnostics, not model
selection results.

The first Antigravity host run resolved its default to Gemini 3.7 Flash (High)
and produced a more polished, working dashboard. It also demonstrated that
Antigravity could search outside a temporary workspace and see unrelated home
files. Host agent runs are therefore diagnostic. The generated applications
already run in separate resource-capped containers; equivalent outer agent
containers are the next smoke gate before measured cases.

## Evidence

- [model ladder and verified revision](../benchmarks/config/model-ladder.json)
- [exact Qwen 3.8 multi-turn summary](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-06-acp-nitro/acp-summary.json)
- [raw Qwen 3.8 ACP trace](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-06-acp-nitro/acp.ndjson)
- [Qwen 3.8 desktop screenshot](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-06-acp-nitro/screenshots/desktop.png)
- [Qwen 3.8 narrow screenshot](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-06-acp-nitro/screenshots/narrow.png)
- [Qwen 3.8 deterministic checks](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-06-acp-nitro/browser/checks-final.json)
- [default-route idle failure](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-05-acp-compatible/acp-summary.json)
- [Qwen 3.5 diagnostic checks](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.5-27b/rep-01-acp/browser/checks-final.json)
- [Qwen 3.6 browser errors](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.6-27b/rep-01-acp/screenshots/events.json)
- [Antigravity desktop screenshot](../benchmarks/runs/2026-08-19-smoke/smoke-001/antigravity/default/rep-01/screenshots-final/desktop.png)
- [Cline ACP runner](../benchmarks/scripts/cline_acp_runner.py)
