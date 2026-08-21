# DeepSeek Web v2 clears the development screen; 14B stops on correctness

The published DeepSeek Harness Web UI, version 0.1.0-rc.7, became the first
tested surface to carry Qwen 3.8 27B through all five routine NGO development
scenarios without a critical failure. This is a named alternative-harness
result, not a replacement for the counted Antigravity-versus-Cline product
pair.

The first Web attempt without a guardrail repeated Cline's wrong employment
denominator. A generic v1 guardrail made the model ask two clarifying questions;
operator answers selected the oracle definitions, so that 87-point run was not
strict. The generic v2 instruction removed the benchmark-specific choice: show
calculable alternative definitions, keep follow-ups in the durable page,
resolve “this table” from the immediate conversation, and export counts,
units, formulas and source fields.

The frozen v2 programme pilot completed all four user messages without a
clarification and scored 92. It showed completion as 14/19 and both plausible
employment definitions, refused causal guessing, updated the page after every
follow-up and delivered a verified CSV. The four-case continuation was frozen
before its first run. CSV scored 86, Excel 93, PDF 83 and official Census web
discovery 91. The five-case mean is 89.0, versus the already-counted
Antigravity CLI mean of 52.2 on the same cases. No v2 run had a critical
failure.

This result is strong but imperfect. CSV and PDF exports omitted requested
rows, and both pages overflowed a phone viewport. The PDF omitted the exact
synthetic fixture label and its first turn ended on a Reka rate-limit error;
the same session recovered. The Census page was correct and visually clear.
It found official Census catalogs 42526 and 42557, retained both workbooks,
showed exact and lakh values, updated the page for all follow-ups, and delivered
a three-row CSV with official source URLs. The operator independently opened
desktop and narrow screenshots, received HTTP 200 for both catalogs, and
confirmed that the remote A-01 workbook SHA-256 matched the retained file.

Two evaluator gaps were fixed only after the Census artifact existed. The
checker now accepts official catalog 42526, which the model independently
discovered and the prior allow-list omitted, and accepts an exact
persons/100,000 lakh conversion as well as a two-decimal rounded value. The
generated page and CSV did not change. Earlier v2 checker changes similarly
accepted ordinary semantic causal caveats and the `pt`/`pts` abbreviation.
Every change is recorded in the affected run metadata.

Efficiency is the main negative finding. Across five conversations, DeepSeek
Web made 264 model steps and used 3,083,961 uncached input tokens, 7,860,384
cache-read tokens and 221,932 output tokens. Model time totalled 3,690.376
seconds. OpenRouter returned metadata for 263 successful Reka generations,
with USD 5.63513765 total hosted cost. The Census conversation alone used 81
steps, 830.346 seconds of model time and 3.6 million session-reported uncached
plus cache-read input tokens. A local endpoint avoids hosted routing failures,
but the harness must compact context and avoid redundant re-verification before
it is a credible multi-user deployment.

The size search then moved below 27B. Qwen3 14B was frozen as an early-stop
DeepSeek Web v2 diagnostic with official Apache-2.0 weights. It was fast and
tool-compatible: one openable page in 49.752 seconds of model time. But the
page hard-coded only Gaya and Nalanda, silently dropping Purnia and Kishanganj,
and linked the synthetic source label to invented `example.org`. It also had
mojibake and 180 px phone overflow. The remaining turns were not sent under
the frozen stop rule. These correctness and citation failures cannot use the
optional 15-point visual-only relaxation.

Combined with the earlier 9B failures, the tested bracket is now above 14B and
at or below 27B for the exact models and harnesses tested. This does not prove
that every untested model between 15B and 26B fails. The practical next path is
to repeat and locally replay 27B in the Web harness, optimize the call loop,
and sample the actual Antigravity IDE/Electron surface before making an
apples-to-apples workshop recommendation.

## Evidence

- [DeepSeek Web v2 aggregate](../benchmarks/results/deepseek-web-qwen38-27b-guardrail-v2-development.json)
- [v2 four-case freeze](../benchmarks/config/deepseek-web-qwen38-27b-guardrail-v2-development.json)
- [generic v2 guardrail](../benchmarks/harnesses/ngo-data-guardrail-v2.txt)
- [programme v2 grade](../benchmarks/runs/2026-08-20-harness-diagnostics/dev-safe-programme-001/deepseek-web/qwen3.8-27b-default-reasoning-ngo-guardrail-v2/rep-01/grading/preliminary-human.json)
- [CSV v2 grade](../benchmarks/runs/2026-08-20-harness-development-v2/dev-csv-health-001/deepseek-web/qwen3.8-27b-default-reasoning-ngo-guardrail-v2/rep-01/grading/preliminary-human.json)
- [Excel v2 grade](../benchmarks/runs/2026-08-20-harness-development-v2/dev-xlsx-health-001/deepseek-web/qwen3.8-27b-default-reasoning-ngo-guardrail-v2/rep-01/grading/preliminary-human.json)
- [PDF v2 grade](../benchmarks/runs/2026-08-20-harness-development-v2/dev-pdf-health-001/deepseek-web/qwen3.8-27b-default-reasoning-ngo-guardrail-v2/rep-01/grading/preliminary-human.json)
- [Census v2 grade](../benchmarks/runs/2026-08-20-harness-development-v2/dev-web-census-001/deepseek-web/qwen3.8-27b-default-reasoning-ngo-guardrail-v2/rep-01/grading/preliminary-human.json)
- [Census desktop screenshot](../benchmarks/runs/2026-08-20-harness-development-v2/dev-web-census-001/deepseek-web/qwen3.8-27b-default-reasoning-ngo-guardrail-v2/rep-01/browser/desktop.png)
- [14B frozen early-stop manifest](../benchmarks/config/deepseek-web-qwen3-14b-guardrail-v2-early-stop.json)
- [14B rejection grade](../benchmarks/runs/2026-08-20-harness-diagnostics/dev-safe-programme-001/deepseek-web/qwen3-14b-nitro-default-reasoning-ngo-guardrail-v2/rep-01/grading/preliminary-human.json)
- [14B generated page screenshot](../benchmarks/runs/2026-08-20-harness-diagnostics/dev-safe-programme-001/deepseek-web/qwen3-14b-nitro-default-reasoning-ngo-guardrail-v2/rep-01/browser/desktop.png)
