# Harness options and what each result means

## Primary workshop comparison

The primary result must compare the products NGO participants would actually
use:

- Antigravity's default agent, model and effort in one live multi-turn session;
- Cline's normal agent core in one live multi-turn session, pointed at the exact
  candidate model.

Cline ACP is acceptable for unattended measurement because it drives Cline's
agent core and keeps a live session across follow-ups. When a new OpenRouter
model is missing from Cline's catalogue, configure Cline's supported
OpenAI-compatible provider with `https://openrouter.ai/api/v1` and the exact
free-text model ID. This is also the future local-vLLM configuration path. The
runner must still assert and record the session model, and the provider/model in
the persisted request metadata where available. Silent fallback invalidates the
run.

If ACP behaviour differs materially from the extension, try Cline's official
TUI and then VS Code/Electron automation. Preserve the same messages,
workspace, permissions and time limits. Editor automation is slower and more
fragile, so use it to validate equivalence on a sample rather than as the first
choice for every repetition.

That editor path is now proven workable on this SSH-only arm64 host. The
official Antigravity IDE 1.107.0 and VS Code 1.134.0 with Cline extension
4.1.10 run under Xvfb and can be controlled through their real Electron
workbenches with the Chrome DevTools Protocol. Antigravity IDE authentication
also completed through an SSH port-forwarded localhost OAuth callback.

The user explicitly authorized Antigravity's mandatory interaction-data
consent; promotional email consent remained disabled. Onboarding exposed two
default-state defects. The first transition produced an account-settings decode
error. After restart, the visible Gemini 3.5 Flash (Low) state generated neither
a PlanModel nor RequestedModel. Initialising the selector resolved the usable
default to Gemini 3.6 Flash (High). The run names that operational resolution
and retains the failed warm-ups rather than scoring them. Extension 4.1.10 is
also newer than the Cline 3.0.55 CLI used in counted screening, so extension and
CLI results continue to name their versions separately.

The first actual Cline GUI smoke used the frozen three-turn `smoke-001`
conversation in one live session with OpenRouter `qwen/qwen3.8-27b`, Xhigh
reasoning and Act mode. It produced a polished responsive page, answered the
2023 follow-up correctly and added a working CSV download. Turn 1 and turn 2
passed all deterministic checks. The final checker rejected the export because
the correct three rows omit a year column, so the downloaded file is not
self-identifying as 2023. The run took 844 seconds, used 412,921 input, 25,616
output and 42,336 cache-read tokens, cost USD 0.25085125, and required seven
Run Command approvals plus one Proceed While Running action. This validates
the real multi-turn product surface but also shows why Medium/High effort and
approval ergonomics need controlled follow-up tests.

The matching Medium-effort replay is now complete in a separate fresh
workspace and live Cline session. It retained the correct arithmetic, 2023-only
follow-up, Purnia answer, source and responsive layout. It rendered labelled
bars instead of table rows, introduced unsupported green/amber/red thresholds,
and again exported correct values without a year column. Medium cost USD
0.20813530 (17.0% below Xhigh) and reduced output tokens by 37.6%, but its 893-
second wall time was 5.8% worse and it needed eight Run Command plus two
Proceed While Running actions. This is not an efficiency-quality dominance:
reasoning effort changes neither model size nor local weight memory, and the
measured run did not improve throughput.

The paired Antigravity IDE run used the same input hash and three unchanged
messages in one Plan-mode session. Its desktop page is the most visually
ambitious of the three and its final CSV is the only export containing both
year and source. It answered the lowest-district follow-up correctly in chat,
but made zero durable page changes, retained 2022 content, overflowed the narrow
viewport by 238 px, and introduced unsupported performance bands and a
percentage/percentage-point label error. Antigravity took 595 seconds and 35
observed planner requests; token and price metadata were not exposed. Its own
browser subagent failed on an arm64 Playwright-driver 404, so independent
browser checks supplied the actual screenshots and deterministic grading.

The preliminary paired scores are Antigravity 80.5, Cline/Xhigh 91.2 and
Cline/Medium 85.5. This advances 27B/Xhigh, but does not establish statistical
equivalence: each is one unblinded diagnostic repetition with documented state
deviations. The next official-agent runs should use isolated client profiles and
semantic browser assertions, then repeat the five ordinary NGO case types.

## Diagnostic harnesses

Codex and DeepSeek Harness can run the same cases as diagnostic tracks. They
answer a different question:

> Can this model do the work with a stronger or different orchestration layer?

If a model fails in Cline but succeeds there, the result supports improving or
replacing the harness. It does not show that today's Cline workshop experience
matches Antigravity. Record diagnostic runs separately and never pool their
scores with the primary Cline track.

DeepSeek Harness is especially relevant if its plugin/tool architecture repairs
small-model tool-use failures. Before recommending it to NGOs, it still needs a
credible Windows-facing package that can accept files, keep a conversation,
launch the generated website, and expose follow-up questions without terminal
knowledge.

The official repository at commit
`141eb6fef83422698aef7a981029e843e8161534` provides two relevant surfaces:

- `npx @deepseek-ai/dsh web` starts a browser UI, detects SSH, offers workspaces
  and multi-turn sessions, and documents custom OpenAI-compatible providers;
- `deepseek-harness-sdk` provides a replayable Python benchmark path with
  persistent sessions and JSONL logs.

The SDK 0.1.0rc7 installed successfully on this arm64 host. Its checked-in
minimal composition is explicitly POSIX-only and `danger-full-access`, not a
Windows agent. In the first valid diagnostic it read host skill-directory
listings outside the staged workspace, so future runs require an outer
container. The Web UI is the plausible end-user surface, but it is labelled a
developer preview and its Windows packaging remains to be exercised rather
than assumed.

The initial Python diagnostic scored 92 on the programme case, but did not
carry all follow-ups into the page. A second generic guardrail was therefore
tested in the actual published DeepSeek Web UI. It requires durable page
updates, traceable exports and calculable alternative metric definitions. The
27B Web track scored 92, 86, 93, 83 and 91 across programme, CSV, Excel, PDF
and official-web cases, with no critical failures. The named-track mean is
89.0 versus 52.2 for the already-counted Antigravity CLI artifacts.

That is the strongest multi-case model-capability result and makes DeepSeek Web a
credible workshop-surface candidate. It is not an apples-to-apples conclusion
about Cline or Antigravity: DeepSeek Web is a different harness, still a
developer preview, and its Windows packaging has not been verified. The
Antigravity IDE/Cline sample replay is now complete; the actual chosen
NGO-facing local UI still needs Windows packaging and repeated cases.

Efficiency is the principal harness defect. Five Web conversations made 264
model steps and consumed 3.08M uncached input, 7.86M cache-read and 222K output
tokens. OpenRouter metadata reported 263 successful Reka generations costing
USD 5.6351. The Census conversation alone used 81 steps and 830 seconds of
model time. A practical local system needs context compaction, fewer redundant
self-checks and a cheaper deterministic data-inspection layer before any
10--20-user capacity projection.

Size bracketing also rules out a naive small-first router today. Qwen 3.5 9B
failed tool/application production in both tested harnesses. Qwen3 14B was
tool-compatible and fast, but its first ordinary dashboard omitted two of four
districts and fabricated a source URL, so the frozen early-stop rule rejected
it. Those are hard-gate failures, not visual polish that can be accepted under
the optional 15-point small-model trade-off. The measured bracket is
`14B < viable size <= 27B` for the tested combinations, with intermediate
models still an open search space.

## Reasoning-effort controls

OpenRouter currently reports that `qwen/qwen3.8-27b` supports `low`, `medium`
and `xhigh` reasoning effort, with reasoning enabled and `xhigh` as the model
default. Cline 3.0.55 exposes a `--thinking` ACP option, but its ACP adapter
currently sends `thinking: false`; the flag is therefore not adequate evidence
that a provider request used a particular effort.

Controlled effort variants use the normal Cline ACP session through a small,
auditable OpenAI-compatible streaming proxy. The proxy changes only the
documented `reasoning.effort` request field. It records request hashes,
generation IDs, resolved model, provider, tokens, cost and latency without
logging prompts, credentials or response text. These variants remain Cline
product-track results, but the injected setting must be named explicitly; they
are not Cline's out-of-box setting.

The first low-effort smoke did not improve efficiency. It completed correctly
but made 38 model calls, resent 810,226 prompt tokens, took 540.072 seconds and
cost USD 0.43929290. This suggests the agent/tool loop and repeated context are
material costs. Do not assume fewer reasoning tokens means a faster or cheaper
end-to-end session; test `medium` only if the measured cases show a reason to.

## Small-to-large routing

A frozen router is a valid finalist when one model is not the best operational
choice. It should start with the smallest capable model and escalate only on
declared observable conditions, for example:

- scanned/OCR PDF or multi-file join;
- repeated tool or syntax failure;
- failed deterministic self-check;
- unsupported citation/source request;
- explicit low-confidence signal with a calibrated threshold.

The router may not inspect the oracle or holdout label. Report end quality,
route decisions, escalation rate, latency, cost and estimated local memory
footprint. A 27B-first policy that occasionally escalates can be preferable to
serving 80B or 122B for every user.

## Containers

Use separate outer containers for the agent and generated application. Agent
containers prevent cross-run discovery; application containers make browser
evaluation reproducible and safe. Containers add credential/state wiring and
browser networking work, but those are one-time runner costs and are worth the
isolation. A host-only smoke run is diagnostic until its observed paths have
been audited.

Do not test local-model concurrency in the hosted OpenRouter phase. The later
DGX replay records quantization, engine, memory and throughput; only a separate
load test can support a 10--20 concurrent-user claim.


## 2026-08-23 update — harness vs io on the NGO corpus

Measured with the chosen laptop model (Qwen 3.5 9B) and Qwen 3.8 27B on 22
sector ask cases: a generic agent loop (Codex CLI in a container) is no more
correct than io's plan/receipt lanes, 10–15× slower, 20–35× the tokens, and
reads raw rows into the model unless given io's own tools. Decision recorded
in `chronology/2026-08-23T1400-harness-question-and-ngo-corpus.md`: no
harness inside io for T0; `benchmarks/t0/harness-skill/` is the interface for
higher-tier agents.
