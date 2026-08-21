# Paired real-product smoke completes; 27B advances with benchmark corrections

The user explicitly authorized Antigravity's mandatory interaction-data
collection consent. The checkbox was enabled through the real Electron IDE;
promotional email consent remained disabled. The in-app browser plugin had no
available browser binding on this SSH host, so the existing Antigravity Electron
Chrome DevTools endpoint controlled the target window directly.

Onboarding exposed two invalid warm-ups, neither of which is scored. The first
post-consent prompt was saved but did not reach the model service after a one-
time account-settings decode error. After a clean restart in an isolated
temporary Git workspace, the IDE displayed Gemini 3.5 Flash (Low), but the
language server rejected its request because neither PlanModel nor
RequestedModel was set. Initialising the visible model selector resolved the
usable current default to Gemini 3.6 Flash (High). A diagnostic request proved
that model could act and was cancelled before any file change. The valid run
then began in a new conversation with the same clean CSV.

The valid Antigravity IDE 1.107.0 run used Plan mode, review-driven development,
Gemini 3.6 Flash (High), the exact input SHA-256
`2fcb5b573f9d323ddf69704e17982d22bed4d1d43ae79116b26b7fa0e4d76f83`,
and the three unchanged smoke messages. It required one workspace trust action,
one implementation-plan Proceed action, five command approvals and two Accept
All actions. The persisted conversation ID is
`747a06ff-1594-4ae2-9e07-fead454efe4e`.

Turn 1 produced a polished dark desktop dashboard with correct values, year and
district controls, charts, denominators, raw rows and prominent synthetic source
attribution. The page invented High/Moderate/Low performance thresholds,
described percentage-point changes as percentages, and called a weighted
aggregate an average. It made three external requests for Chart.js and fonts.
At 390 px it overflowed by 238 px and clipped chart/table content.

Turn 2 answered correctly in chat: Purnia was lowest in 2023 at 76.0%, 760 of
1,000, with no causal guess. It made zero file changes. The page retained seven
visible 2022 mentions and did not durably surface the lowest-district result.
This demonstrates why chat correctness alone is not product equivalence for the
intended NGO workflow.

Turn 3 repaired the export dimension. Antigravity added a visible download
button, a client-side CSV export and a standalone workspace file. The frozen
checker passed the download: each row contains district, year, numerator,
denominator, percentage and source with exact values. Both Cline GUI variants
had omitted year from their otherwise correct exports.

Antigravity completed in 594.967 seconds and emitted 35 planner-request log
records. The product exposes no session token or price metadata. Its own browser
subagent failed because the configured Playwright 1.57.0 arm64 driver URL
returned 404; independent Playwright checks opened and graded the generated
page. Credential-bearing startup logs were not copied. The raw conversation was
scanned for OAuth, JWT, bearer and OpenRouter key patterns before preservation;
none were found.

The preliminary paired results are:

| System | Score | Visual | Time | Durable turn 2 | Traceable export | Narrow overflow |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| Antigravity / Gemini 3.6 Flash High | 80.5 | 7.5 | 595 s | No | Yes | 238 px |
| Cline / Qwen 3.8 27B Xhigh | 91.2 | 9.2 | 844 s | Yes | No | 0 px |
| Cline / Qwen 3.8 27B Medium | 85.5 | 8.6 | 893 s | Yes | No | 0 px |

These are unblinded single-repetition diagnostic scores, not a statistical
equivalence claim. Xhigh is 10.7 points above Antigravity and Medium is 5.0
points above it. Both fit the user's 15-point deployment tolerance; Medium fits
the frozen seven-point margin on this smoke. Xhigh advances because it has the
best quality and Medium did not improve elapsed time or local model memory.

The prompt and documentation were reformulated without rewriting prior
chronology. Primary quality runs now use the actual IDE products; CLI/ACP may
stand in only after sampled equivalence. The next version must recognize button
groups as valid year controls, require durable page changes after website
follow-ups, require year/source in downloads, reject unsupported bands and
percentage-point errors, and retain narrow plus offline checks. The current
model bracket remains greater than 14B and at most 27B for tested combinations.

## Evidence

- [paired diagnostic aggregate](../benchmarks/results/product-gui-smoke-v1-diagnostic.json)
- [Antigravity run record](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/antigravity/default-ide-1.107.0/rep-01/run.json)
- [Antigravity persisted conversation](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/antigravity/default-ide-1.107.0/rep-01/session/conversation.pb)
- [Antigravity final desktop page](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/antigravity/default-ide-1.107.0/rep-01/screenshots-final/desktop.png)
- [Antigravity final narrow page](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/antigravity/default-ide-1.107.0/rep-01/screenshots-final/narrow.png)
- [Antigravity final deterministic checks](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/antigravity/default-ide-1.107.0/rep-01/checks-final.json)
- [Antigravity IDE evidence screenshot](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/antigravity/default-ide-1.107.0/rep-01/screenshots-ide/final.png)
- [product-GUI findings and reformulation](../docs/product-gui-smoke-findings.md)
- [reformulated execution prompt](../.prompt)
