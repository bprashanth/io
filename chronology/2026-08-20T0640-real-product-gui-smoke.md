# Real editor automation works; Cline GUI completes strict smoke with one export defect

The benchmark moved from CLI and alternative-harness diagnostics to the actual
editor products. The official Antigravity IDE and VS Code were installed on the
arm64 SSH host, then launched under Xvfb and controlled through their Electron
Chrome DevTools endpoints. Antigravity reports IDE 1.107.0 at commit
`15487b3041e65228cae24980a3f796c905ef582c`; VS Code reports 1.134.0 at commit
`110a328ea54b42367b803ec53ee0bf52ef26b419`. VS Code has Cline extension
4.1.10, which is newer than the 3.0.55 CLI used in counted screening.

Antigravity IDE authentication succeeded through a localhost OAuth callback
forwarded over SSH. Authentication is not the remaining blocker. The IDE's
first-run Terms page makes interaction-data collection consent mandatory: when
the checkbox allowing Google to use interactions for product/model improvement
is cleared, the Next button disables. That external privacy choice was left
unchecked pending explicit user authorization. Promotions remain unchecked.

Cline was configured through its real extension onboarding with OpenRouter
`qwen/qwen3.8-27b`, Xhigh reasoning, default provider routing and Act mode. A
fresh workspace received the exact `smoke-001` CSV. The three frozen plain-
language turns were sent unchanged in one live session. Cline's persisted
session identifies source `vscode`, model `qwen/qwen3.8-27b`, extension version
4.1.10 and session `1787187129391_8jlt0`.

Turn 1 built an openable, dependency-free dashboard. The browser checker found
both years and every exact district percentage, the synthetic source label and
no document-level overflow at 390 px. The operator opened both desktop and
narrow screenshots; the page has a clear year control, summary cards,
horizontal district bars, denominators, a details table and source footer.

Turn 2 correctly locked the durable page to 2023, removed visible 2022
mentions and stated that Purnia was lowest at 76.0% without guessing a cause.
Turn 3 added a Download CSV button and generated the correct ordered district
values. The final frozen checker still failed the export check: the CSV omits a
year field. Although its three rows match the visible 2023 table, the file is
not independently traceable to 2023. This is a noncritical functionality and
traceability defect, not a wrong-number or display/download disagreement.

The preliminary unblinded visual review scored the final rendered page 9.2/10.
The full diagnostic smoke score is 91.2/100 with no critical failures, but it
is not counted: the current GUI reused an existing Cline client profile and no
paired Antigravity IDE artifact exists yet.

Operational cost is the larger warning. The three-turn session lasted 844.1
seconds. Cline recorded 412,921 input tokens, 25,616 output tokens, 42,336
cache-read tokens and USD 0.25085125. The default approval surface required
seven inspected Run Command approvals and one Proceed While Running action.
One multiline Node command was mangled by terminal shell integration before
the agent recovered with a temporary script. Xhigh is therefore a useful
quality baseline, not yet a practical default for a simple NGO CSV task.

The immediate next paired step is the identical Antigravity IDE smoke after
the terms-consent decision. A controlled Cline Medium or High effort variant
is then justified, with the same page, correctness and export checks; it cannot
trade away the missing year/source traceability merely to improve latency.

## Evidence

- [Cline GUI run record](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-xhigh-vscode-extension-4.1.10/rep-01/run.json)
- [Cline exact session metadata](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-xhigh-vscode-extension-4.1.10/rep-01/session/session.json)
- [Cline raw structured messages](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-xhigh-vscode-extension-4.1.10/rep-01/session/messages.json)
- [turn 1 deterministic checker](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-xhigh-vscode-extension-4.1.10/rep-01/checks-turn-01.json)
- [turn 2 deterministic checker](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-xhigh-vscode-extension-4.1.10/rep-01/checks-turn-02.json)
- [final deterministic checker](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-xhigh-vscode-extension-4.1.10/rep-01/checks-final.json)
- [final desktop screenshot](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-xhigh-vscode-extension-4.1.10/rep-01/screenshots-final/desktop.png)
- [final narrow screenshot](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-xhigh-vscode-extension-4.1.10/rep-01/screenshots-final/narrow.png)
- [preliminary visual review](../benchmarks/runs/2026-08-20-product-gui-smoke/smoke-001/cline/qwen3.8-27b-xhigh-vscode-extension-4.1.10/rep-01/grading/visual-human.json)
