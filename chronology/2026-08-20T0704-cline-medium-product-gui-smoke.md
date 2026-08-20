# Medium effort saves hosted cost but not elapsed time or traceability

The real VS Code 1.134.0 and Cline extension 4.1.10 product surface completed a
second strict `smoke-001` conversation using OpenRouter
`qwen/qwen3.8-27b`, Medium reasoning, Act mode and default provider routing. A
fresh copied workspace held the same CSV SHA-256
`2fcb5b573f9d323ddf69704e17982d22bed4d1d43ae79116b26b7fa0e4d76f83`.
All three frozen user messages were sent unchanged in one persisted session,
`1787188371042_u7qsy`.

The page's visible arithmetic is correct. Turn 1 shows Nalanda 90.0%, Gaya
85.0% and Purnia 76.0% for 2023 and the correct 2022 values, denominators and
synthetic source. Turn 2 restricts the durable page to 2023 and correctly calls
Purnia lowest at 76.0% (760 of 1,000) without guessing a reason. Turn 3 adds a
working client-side CSV download with the same three district values.

Two noncritical defects distinguish this run. First, the model invents green
at 85% or above, amber at 70% or above, and red below 70% without a definition
in the data or request. The encoding is visible through bar colour even though
the page does not print a legend. Second, the exported CSV again omits the year
field. Its filename contains 2023 and its values match the screen, but the rows
are not independently traceable to the requested year. The frozen checker also
expects values in HTML table rows, while this page uses correctly labelled
bars; that interface mismatch is recorded separately from the genuine export
and semantic defects.

The preliminary unblinded visual review is 8.6/10 and the diagnostic smoke
score is 85.5/100 with no critical failure. This remains uncounted because the
Cline client profile was reused and a paired Antigravity IDE artifact does not
yet exist.

Medium recorded 406,082 input, 15,973 output and 64,288 cache-read tokens at
USD 0.20813530 over 893.337 seconds. Against the same model at Xhigh, Medium
cost 17.0% less and emitted 37.6% fewer output tokens, but took 5.8% longer,
used only 1.7% less uncached input, and reduced preliminary quality by 5.7
points. Eight inspected Run Command approvals and two Proceed While Running
actions were required. The result does not show an end-to-end throughput win,
and reasoning effort provides no local weight-memory saving.

The user reported completing Antigravity authentication on a laptop. The
server IDE still shows its first-run Terms page with Next disabled until the
separate interaction-data collection checkbox is selected. That consent was
not inferred from authentication and remains pending explicit authorization;
promotional email is still unchecked.

## Evidence

- [Medium run record](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-medium-vscode-extension-4.1.10/rep-01/run.json)
- [exact persisted session](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-medium-vscode-extension-4.1.10/rep-01/session/session.json)
- [raw structured messages](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-medium-vscode-extension-4.1.10/rep-01/session/messages.json)
- [turn 1 checker](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-medium-vscode-extension-4.1.10/rep-01/checks-turn-01.json)
- [turn 2 checker](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-medium-vscode-extension-4.1.10/rep-01/checks-turn-02.json)
- [final checker and download preview](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-medium-vscode-extension-4.1.10/rep-01/checks-final.json)
- [final desktop screenshot](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-medium-vscode-extension-4.1.10/rep-01/screenshots-final/desktop.png)
- [final narrow screenshot](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-medium-vscode-extension-4.1.10/rep-01/screenshots-final/narrow.png)
- [preliminary visual review](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-medium-vscode-extension-4.1.10/rep-01/grading/visual-human.json)
