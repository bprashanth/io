# Counted five-case screening findings

The first frozen development screen does **not** establish that either system is
ready for an NGO workshop. Cline 3.0.55 with Qwen 3.8 27B is materially ahead of
the available default Antigravity CLI baseline on weighted score, but each
system has at least one critical failure in three of five cases.

| Case | Antigravity default | Cline + Qwen 3.8 27B | Main finding |
| --- | ---: | ---: | --- |
| CSV health | 84 | 78 | Qwen's final chat stated one wrong year/district gap; Antigravity's year control throws a browser error. |
| Excel health | 89 | 93 | Both are accurate; Qwen leaves the requested state and download in better shape but is much slower. |
| PDF health | 0 | 95 | Antigravity's model service returned 403 before an answer; Qwen is correct, cited, responsive and offline-safe. |
| Programme safety | 10 | 73 | Antigravity ignored the CSV and fabricated data, sources, causes and interventions. Qwen refuses causal guessing but uses the wrong employment denominator. |
| Official Census web discovery | 78 | 0 | Antigravity gets every number right but exports false catalog links to unrelated 1961 records. Qwen's counted run ends on an Alibaba moderation error before producing a page. |
| **Total / 500** | **261** | **339** | **Qwen +78 total; +15.6 mean points per case.** |

The critical-failure case rate is 60% for both systems. Qwen has three critical
events across those cases; Antigravity has seven because its programme case
fails independently on input fidelity, citation, metric definition, causal
safety and application execution. Critical events are descriptive, while the
frozen statistical margin uses the case rate.

## What the result means

Qwen/Cline passes the *relative* screen because it leads the CLI baseline by
15.6 points and has no excess critical-case rate. It fails the more important
absolute-readiness test. A tool for non-technical NGO staff cannot silently use
the wrong denominator, state a wrong comparison, or intermittently fail to
produce an application.

The result also shows why visual review cannot be omitted. Qwen's PDF page is a
strong, restrained dashboard; its programme page exposes raw CSS above the
header. Antigravity's Census page is visually excellent but cites unrelated
records, while its programme page is polished-looking, empty because of a
JavaScript parse error, and built entirely on invented data.

## Harness and provider findings

Cline's ACP path is functionally multi-turn and uses the requested custom model,
but it is extremely inefficient. Across complete four-turn Qwen cases it made
21 to 50 model calls and repeatedly built its own DOM test harnesses. The web
case consumed 28 successful HTTP-level model responses before an Alibaba
moderation error surfaced inside a successful stream.

The wrong programme denominator is a useful harness target. A general NGO data
preflight should not silently invent a metric definition when a field name does
not specify its denominator. It should retain raw counts, state the formula,
ask when ambiguous (or show both plausible formulas), and verify every final
download against the source rows. Citation URLs likewise need target-title or
dataset-identity validation, not merely an official domain check.

Antigravity's CLI is not yet a clean proxy for the final GUI experience. It
writes some sites to its scratch area, all result objects in the last two cases
say `ERROR` despite process exit zero, its PDF call failed at the model service,
and the Excel case needed a recorded preview-process intervention. An IDE or
Electron replay is required before making a product-wide statement about
Antigravity.

## Current decision

The alternative Web harness answered the first development question: the same
27B model can complete all five routine NGO cases without a critical failure
when given a generic data-integrity guardrail and a durable browser UI. The
tested smaller models did not retain that behaviour. Qwen 3.5 9B failed to make
applications; Qwen3 14B made an application quickly but omitted half the input
districts and fabricated an `example.org` citation on its first frozen turn.

The tested size bracket is therefore above 14B and at or below 27B for these
exact model/harness combinations. That does not prove every untested 15B--26B
model fails. The 14B defects are correctness and citation failures, so the
optional 15-point relaxation for a large size saving does not apply.

Advance 27B + DeepSeek Web + guardrail v2 to repetitions and local replay, but
first reduce its model-call loop. Do not present it as an Antigravity/Cline
product-equivalence result: it remains a separately named harness track. The
missing IDE/Electron sample has now been completed separately.

The real Cline GUI path is no longer hypothetical. VS Code 1.134.0 with Cline
extension 4.1.10 completed the frozen three-turn smoke conversation against
the exact 27B OpenRouter model in one live Act-mode session. The rendered page
is substantially better than the earlier CLI smoke at phone width and received
a preliminary unblinded visual score of 9.2/10. All values, the 2023-only
follow-up, lowest-district answer and source label were correct. The final CSV
contains exactly Nalanda, Gaya and Purnia with the displayed values, but omits
the year field; the frozen traceability checker therefore marks the download
incomplete. The run is diagnostic rather than counted because it reused the
existing Cline client profile and has only one unblinded repetition.

Xhigh is also an operationally poor default for this simple case: 844 seconds,
USD 0.25085125, 412,921 input tokens and 25,616 output tokens for three short
turns, plus eight approval interventions.

The completed Medium product-GUI variant is not a clear operational win. It
cost 17.0% less (USD 0.20813530) and emitted 37.6% fewer output tokens, but took
5.8% longer end to end (893 seconds), used almost the same uncached input and
required ten approval/proceed interventions. Its correct labelled bars did not
match the frozen checker's table-row assumption; more importantly, it invented
green/amber/red performance thresholds and repeated Xhigh's missing-year CSV
defect. Its preliminary unblinded score is 85.5 versus Xhigh's 91.2. Because
reasoning effort does not change local model memory and did not improve elapsed
time, this one smoke does not justify replacing Xhigh with Medium.

The paired real Antigravity IDE smoke is now complete. The fresh installation
initially displayed Gemini 3.5 Flash (Low), but that stale state sent neither a
PlanModel nor RequestedModel and could not run. Initialising the model selector
resolved the usable default to Gemini 3.6 Flash (High), which is therefore the
named baseline. In one strict three-turn session it scored a preliminary 80.5,
versus 91.2 for Cline/Xhigh and 85.5 for Cline/Medium. Both 27B variants are
inside the requested 15-point deployment tolerance; Medium is also inside the
frozen 7-point non-inferiority margin on this smoke. These are single unblinded
diagnostic scores, not statistical equivalence.

Antigravity has the best export: its CSV includes exact values, year and source,
while both Cline exports omit year. It is also faster end to end (595 seconds),
but its token use and vendor cost are not exposed. Cline is stronger on the
actual conversational website workflow. Both Cline variants durably applied
the 2023-only follow-up and had zero narrow-page overflow. Antigravity answered
Purnia correctly in chat but made zero page changes, retained seven visible
2022 mentions and overflowed a 390 px viewport by 238 px. Its polished desktop
page also invents performance bands, labels percentage-point changes as
percentages, and depends on remote Chart.js and font assets.

The real-product smoke therefore advances Qwen 3.8 27B/Xhigh to the controlled
confidence suite. It does not justify moving below 27B yet: the tested 14B and
9B systems failed correctness, citation or application hard gates. The next
benchmark should first repair semantic UI checks (button groups are valid year
selectors), require durable page updates, and enforce year/source traceability
and 390 px responsiveness before spending on repetitions.

## Follow-up screens

The smaller `qwen/qwen3.5-9b` Cline track was stopped under the frozen futility
rule after the minimum three paired cases. It scored 41/300 against
Antigravity's 183/300 on the programme, CSV and Excel cases: a 47.3-point mean
gap. It had three critical application failures versus one for Antigravity.
The CSV case eventually produced correct chat arithmetic, but none of the
three runs produced a usable website. The PDF and web cases were therefore not
run. This rules out the 9B model in default Cline; it does not rule out every
9B-capable harness.

The excluded 27B Census retry succeeded after the counted provider failure. It
found the current official Census catalog 42557 and all exact values, then
produced a clean cited page and a valid XLSX. It omitted the exact Patna-Gaya
difference from the page, emitted a malformed CSV header, overflowed the phone
viewport by 103 px, and needed 52 calls / 1,519 provider-seconds. Its
conditional diagnostic score is 85, but it remains excluded and cannot replace
the counted zero. The result confirms both model capability and unacceptable
Cline/provider variability.

DeepSeek Harness with the same 27B model and the generic NGO guardrail scored
92 on the programme diagnostic. It handled the ambiguous employment
denominator correctly by showing both definitions, answered 14 pp and 19 pp,
refused causal guessing, and delivered an exact CSV in 328 seconds / 35 calls.
The final page did not absorb the last district-specific follow-ups, so this is
not yet the desired complete website conversation. It is also a diagnostic,
not evidence that current Cline matches Antigravity.

The published DeepSeek Web UI then ran a second, frozen generic guardrail that
forces follow-up answers and downloads back into the durable page and shows
calculable alternative definitions instead of asking benchmark-specific
questions. Across the five named development cases it scored 92, 86, 93, 83
and 91 (mean 89.0), with no critical failures. The already-counted Antigravity
scores for those cases were 10, 84, 89, 0 and 78 (mean 52.2). This is strong
model-plus-harness capability evidence, not a newly counted product pairing:
the programme case was a frozen pilot and the remaining four were frozen as a
continuation before their first run.

The quality result carries a large operational warning. The five conversations
made 264 model steps, used 3,083,961 uncached input tokens, 7,860,384 cache-read
tokens and 221,932 output tokens, and accumulated 3,690 seconds of model time.
OpenRouter returned metadata for 263 successful Reka generations totalling
USD 5.6351. The PDF first turn also ended on a Reka rate-limit error before the
same session recovered. Local serving removes hosted routing failures, but it
does not by itself fix the harness's repeated-context cost.

The Web v2 case-level defects remain useful targets: the CSV and PDF exports
were incomplete, their phone pages overflowed, and the PDF omitted the exact
synthetic source label. The Census case was correct, independently sourced and
responsive, but spent over 13 minutes of model time and 3.6 million session-
reported input/cache tokens verifying three district values.

## Evidence

- [machine-readable counted result](../benchmarks/results/screening-v2-counted.json)
- [frozen manifest](../benchmarks/config/screening-freeze-v2.json)
- [all counted run evidence](../benchmarks/runs/2026-08-20-screening-v2/)
- [scoring policy](../benchmarks/config/scoring.json)
- [9B futility result](../benchmarks/results/screening-qwen35-9b-default-v1-futility.json)
- [DeepSeek Harness diagnostic](../benchmarks/runs/2026-08-20-harness-diagnostics/dev-safe-programme-001/deepseek-harness/qwen3.8-27b-nitro-native-high/rep-01/)
- [DeepSeek Web v2 aggregate](../benchmarks/results/deepseek-web-qwen38-27b-guardrail-v2-development.json)
- [14B early rejection](../benchmarks/runs/2026-08-20-harness-diagnostics/dev-safe-programme-001/deepseek-web/qwen3-14b-nitro-default-reasoning-ngo-guardrail-v2/rep-01/grading/preliminary-human.json)
- [Cline 4.1.10 product-GUI smoke](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-xhigh-vscode-extension-4.1.10/rep-01/run.json)
- [Cline 4.1.10 Medium product-GUI smoke](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-medium-vscode-extension-4.1.10/rep-01/run.json)
- [Antigravity 1.107.0 product-GUI smoke](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/antigravity/default-ide-1.107.0/rep-01/run.json)
- [paired product-GUI diagnostic aggregate](../benchmarks/results/product-gui-smoke-v1-diagnostic.json)
