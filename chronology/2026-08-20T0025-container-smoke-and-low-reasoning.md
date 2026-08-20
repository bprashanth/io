# Comparable container smoke completed; low reasoning was not cheaper end to end

The smoke gate now has equivalent outer-container runs for default Antigravity
and Cline with the exact Qwen 3.8 27B candidate. Each agent saw only a fresh
workspace, its run-specific state, its executable and CA certificates. The
generated sites ran separately in read-only, resource-capped application
containers.

Default Antigravity resolved to Gemini 3.7 Flash (High). It produced the most
feature-rich page and a correct download in 490.610 seconds, but retained six
visible 2022 mentions after the 2023-only follow-up and invented performance
bands absent from the data. Its unblinded smoke score is 89/100.

The first fully containerised Qwen repetition completed in 479.746 seconds. It
followed the 2023-only and no-guess instructions, kept the source, and rendered
cleanly at both viewports. Its downloaded rows were numerically correct but
omitted required year and source columns. Its unblinded smoke score is 92/100.

OpenRouter's live metadata says Qwen 3.8 27B defaults to xhigh reasoning and
also accepts medium and low. Cline ACP 3.0.55 does not currently transmit its
nominal thinking control, so a secret-free streaming proxy injected the
documented low-effort field and recorded provider evidence for every request.
All 38 requests resolved to `qwen/qwen3.8-27b`; 36 ran at Reka and two at
AkashML. The run used 810,226 prompt tokens, 409,248 cached prompt tokens,
23,341 completion tokens including 6,038 reasoning tokens, cost USD 0.43929290,
and took 540.072 seconds.

That low-effort page was factually correct and honest, but its download omitted
year and its narrow table overflowed by 15 px. Its unblinded score is 91/100.
Low reasoning therefore did not improve end-to-end speed or cost in this smoke;
the Cline tool loop and repeated context dominated. Preserve it as a controlled
negative result rather than selecting it for the measured default track.

The in-app browser was unavailable in the SSH session (zero connected browser
instances). The installed Playwright Chromium runner still opened the actual
served page, captured desktop and narrow full-page screenshots, exercised the
CSV download, and checked values, source, console errors and overflow.

The smoke case remains excluded from headline results. Its purpose is now
complete: Qwen 3.8 27B is credible enough for the frozen five-case screen, while
download schemas, mobile tables, unsupported interpretations and harness cost
must be scored explicitly.

## Evidence

- [smoke findings](../docs/smoke-findings.md)
- [low-effort ACP summary](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-08-acp-container-low/acp-summary.json)
- [low-effort provider summary](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-08-acp-container-low/openrouter-summary.json)
- [low-effort checks](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-08-acp-container-low/grading/checks.json)
- [low-effort preliminary grade](../benchmarks/runs/2026-08-19-smoke/smoke-001/cline/qwen3.8-27b/rep-08-acp-container-low/grading/preliminary-human.json)
