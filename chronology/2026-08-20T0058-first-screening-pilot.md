# First paired screening pilot completed; measured protocol is ready to freeze

A first full five-turn pair on `dev-csv-health-001` compared default
Antigravity with Cline ACP 3.0.55 calling the exact Qwen 3.8 27B model through
OpenRouter's throughput route. This pair is calibration evidence only and is
excluded from every aggregate because its outputs were used to refine the
oracle's accepted download shapes and clarify browser network policy.

Default Antigravity resolved to `gemini-3.7-flash-high` at high effort. Its
page was visually richer and it completed in 346.363 seconds. The displayed
rates, changes and no-guess answer were correct, but it added unsupported
performance bands, did not carry the final district comparison into the page,
and overflowed a 390 px viewport by 557 px. The page depended on Tailwind,
Chart.js and Google Fonts CDNs and became unusable with those origins blocked.
Its preliminary unblinded score was 88/100.

Cline made 37 requests that all resolved to `qwen/qwen3.8-27b`; OpenRouter
routed 18 to Reka and 19 to Chutes. The run used 1,185,416 prompt tokens,
249,600 cached prompt tokens, 35,471 completion tokens including 13,324
reasoning tokens, cost USD 0.55738250 and took 970.407 seconds. Its values,
percentage-point changes and no-guess answer were correct. The dependency-free
page survived the offline pass, but remained sparse, did not carry the final
comparison into the page and overflowed the narrow viewport by 231 px. Its
preliminary unblinded score was 86/100.

The two-point pilot gap is inside the strict seven-point margin and makes the
27B candidate worth a complete screen. It is not a conclusion. Cline's long
self-testing loop is also evidence that harness overhead may dominate cost and
latency, so a neutral or DeepSeek harness remains an allowed diagnostic track.

The shared agent environment is now an immutable arm64 image,
`io-benchmark-agent-tools:2026-08-20`, ID
`sha256:3ebc6514c7372bc8cf9f2c533c0716784bd127862f9739cb57739b921d544378`.
It provides the same Python, Node, spreadsheet, PDF and shell tools to both
products. Five deterministic screening cases cover CSV, Excel, PDF, an
aggregate programme-safety question and official Census web discovery.

The workshop-online browser pass is frozen as primary because the intended
workshop has internet access; public library and font requests are allowed and
recorded. An offline-resilience pass blocks all external origins and is
reported separately. This keeps the scenario realistic without hiding a
material deployment property.

## Evidence

- [pilot findings](../docs/pilot-findings.md)
- [shared image manifest](../benchmarks/config/agent-tools-image.json)
- [screening case bank](../benchmarks/cases/CASE_BANK.md)
- [Antigravity preliminary grade](../benchmarks/runs/2026-08-20-screening-pilot/dev-csv-health-001/antigravity/default/rep-01/grading/preliminary-human.json)
- [Qwen preliminary grade](../benchmarks/runs/2026-08-20-screening-pilot/dev-csv-health-001/cline/qwen3.8-27b-nitro-xhigh/rep-01/grading/preliminary-human.json)
- [Qwen provider summary](../benchmarks/runs/2026-08-20-screening-pilot/dev-csv-health-001/cline/qwen3.8-27b-nitro-xhigh/rep-01/openrouter-summary.json)
