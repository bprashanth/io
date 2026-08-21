# Real-product GUI smoke: findings and benchmark reformulation

The strict three-turn real-editor smoke is complete. It compares the current
Antigravity IDE against current VS Code/Cline with Qwen 3.8 27B at Xhigh and
Medium effort. All systems received the same CSV hash and exact plain-language
messages in one live conversation. Every generated website was opened at
desktop and 390 px widths and its download was inspected.

| System | Preliminary score | Visual /10 | Time | Durable 2023 follow-up | Traceable export | Narrow overflow |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| Antigravity 1.107.0 / Gemini 3.6 Flash High operational default | 80.5 | 7.5 | 595 s | No | Yes | 238 px |
| Cline 4.1.10 / Qwen 3.8 27B Xhigh | 91.2 | 9.2 | 844 s | Yes | No: year omitted | 0 px |
| Cline 4.1.10 / Qwen 3.8 27B Medium | 85.5 | 8.6 | 893 s | Yes | No: year omitted | 0 px |

These are unblinded single-repetition diagnostics. Xhigh is 10.7 points above
Antigravity; Medium is 5.0 points above it and is inside the frozen seven-point
margin. The result is enough to advance 27B, not to claim statistical product
equivalence.

## What each product did better

Antigravity produced the most elaborate desktop dashboard and the only correct,
self-identifying export. The downloaded rows carry district, year, numerator,
denominator, percentage and source. It also completed sooner than either Cline
variant, although Antigravity does not expose session tokens or vendor cost.

Cline better matched the intended NGO interaction. Both variants changed the
website after the user said “show only 2023,” removed the old year and put the
correct Purnia result into the durable page. Both remained responsive with no
document overflow. Xhigh avoided unsupported status bands and produced the
clearest balanced page.

Antigravity's second turn is the central product failure: its chat answer was
exact and cautious, but it changed zero files. The website therefore did not
reflect the conversation. Its page also overflowed at phone width, relied on
remote Chart.js and fonts, invented status thresholds, and called percentage-
point changes percentages. Both Cline variants failed export traceability by
omitting year; Medium additionally invented colour thresholds.

## What the smoke changed in the benchmark

The primary baseline must be the real Antigravity IDE, not an assumption that
its CLI is identical. The fresh IDE initially displayed an unusable stale model
state. After the selector was initialised, the operational default resolved to
Gemini 3.6 Flash (High). Future runs must record both displayed and request-
resolved defaults and fail closed on mismatch.

Browser assertions must be semantic. A year button group is a valid selector;
requiring a literal HTML `select` creates a false failure. Conversely, seeing
correct values somewhere on a page is insufficient after “show only 2023”; the
page must remove stale years and carry the chat result into its controls,
summary and export.

The next suite should retain the deterministic 390 px overflow test, add an
offline/CDN-blocked pass, reject unsupported bands and percentage/percentage-
point errors, and require year plus source in every filtered download. The five
ordinary case types remain CSV, XLSX, PDF, safe interpretation and official-web
discovery. Run one isolated product-GUI repetition per case first, repair only
harness defects, then freeze two additional repetitions and the holdout.

## Model decision

Advance Qwen 3.8 27B at Xhigh as the real Cline finalist. Medium's hosted bill
was 17% lower, but it was slower, lower quality, and offers no local weight-
memory saving. Do not test 9B again in default Cline. Do not accept the tested
14B result under the 15-point trade-off because it omitted input rows and
fabricated a citation. The measured viable bracket remains above 14B and at or
below 27B; intermediate 15B--26B candidates are the next legitimate downward
search after the 27B confidence suite passes.

DeepSeek Web + the generic NGO guardrail remains the strongest five-case
capability track at mean 89.0 with no critical failures, but its 264-step,
USD 5.64 loop is not yet operationally credible. Use its guardrail ideas to
improve Cline/local UX; do not pool it with the product pairing.

## Evidence

- [paired machine-readable diagnostic](../benchmarks/results/product-gui-smoke-v1-diagnostic.json)
- [Antigravity raw run](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/antigravity/default-ide-1.107.0/rep-01/run.json)
- [Cline Xhigh raw run](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-xhigh-vscode-extension-4.1.10/rep-01/run.json)
- [Cline Medium raw run](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-medium-vscode-extension-4.1.10/rep-01/run.json)
