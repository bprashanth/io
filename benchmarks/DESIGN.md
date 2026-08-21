# Benchmark design

## Primary claim

Find the smallest declared, locally deployable candidate model for which Cline
is non-inferior to default Antigravity on multi-turn NGO dashboard work.

The hosted and local phases make different claims:

- **Hosted selection:** Cline plus model X through OpenRouter is non-inferior to
  default Antigravity on this frozen benchmark.
- **Local confirmation:** Cline plus the recorded local deployment of model X is
  non-inferior when the identical holdout runs are replayed.

## Experimental unit

An experimental unit is one complete ordered conversation for one case, agent,
model and repetition. Follow-ups remain in the same conversation and workspace.
The unit ends only after the final requested website has been launched and
browser-tested, or after a recorded timeout/failure.

## Splits and repetitions

- Smoke cases test machinery and never enter aggregate results.
- Development cases select the candidate model and may expose their oracles.
- Holdout cases are frozen before model selection and are run only for the final
  hosted comparison and exact local replay.
- Default target: 12 development cases, 8 holdout cases, 3 repetitions.
- Pair runs by case and repetition. Randomise competitor order within each pair.
- Freeze five development cases as a screening subset: one each for CSV,
  Excel, PDF, official web discovery, and uncertainty/caveat behaviour.

Any change to a holdout input, prompt, oracle, score, or threshold creates a new
benchmark version. Do not repair a bad holdout after seeing model output and
continue under the old version.

## Defaults and controlled deviations

Antigravity retains the default agent/model/effort. Cline retains default agent
behaviour but receives an explicit provider/model. Both receive equivalent
unattended file/command approval inside disposable workspaces. This permission
change is necessary for automation and must be recorded.

Do not add a benchmark-specific system prompt, framework requirement, chart
library, or technical launch instruction to one competitor. The natural user
prompt may ask for a website and for it to be shown. The harness discovers the
resulting application type after the run.

## Network policy

Cases are tagged `offline`, `provided-sources`, or `web-discovery`.

- Offline cases deny network except for model API calls and dependency retrieval.
- Provided-source cases include immutable downloaded source bytes.
- Web-discovery cases allow agent web access and judge source choice separately.

Record every allowed network exception. Once an application is built, run two
browser modes. The primary workshop-online pass allows ordinary library and
font CDNs but records every external request. Case data must still come from
retained bytes or an explicitly scored web-discovery source. A second offline
resilience pass blocks all origins except the application and is reported
separately; offline degradation is not, by itself, a primary critical failure
because the planned workshop experience is internet-connected.

## Application evaluation

The runner detects a documented start command or a common static/Vite/React/
Streamlit application. Detection and dependency installation happen identically
for both competitors and are recorded. Ports are allocated dynamically.

Playwright must navigate to the live page, save desktop and narrow screenshots,
exercise case-declared controls, compare visible values with the oracle, retain
downloads, and record console/page/request failures. Source inspection alone
cannot mark a website successful.

## Model selection

Start with `qwen/qwen3.8-27b`. Its OpenRouter endpoint and downloadable weights
exist, but the initial Cline 3.0.55 ACP catalogue was stale and caused a silent
fallback. That diagnostic run is invalid; the runner must assert exact model
selection before sending a prompt. Test smaller candidates if 27B passes and
larger declared candidates if it fails. Freeze the ladder metadata before
measured runs. Models from
different generations and MoE/dense architectures are named as such; total
parameter count is not treated as a controlled scaling variable.

Screen once on the five-case subset. A model may be stopped for futility after
at least three paired cases when it trails by at least 20 score points with no
plausible recovery, or has at least two excess critical failures. Never stop
early to declare success. Models within 10 points complete the development set
and three repetitions. Only frozen finalists run on holdout.

The smallest model passes only if it meets the frozen paired total-score margin,
the separate critical-failure margin, and has no material regression in data or
citation correctness. Thresholds in `config/scoring.json` are provisional until
pilot variance is measured; freeze them before running holdout.

Report strict equivalence and operational efficiency as different conclusions.
The latter may include a candidate up to 15 points behind only when the added
gap is presentation/non-critical usability, the capacity benefit is material,
and correctness, citations, safety and critical failures satisfy the same hard
gates. Never turn the 15-point tradeoff into an equivalence claim.

If no single small model passes economically, a model-mixture policy is allowed
as a separate finalist. Its routing rule must use observable input/task features
or an explicit low-confidence/tool-failure signal, be developed without holdout,
and be frozen before evaluation. Report escalation rate, route errors, combined
cost/latency, and worst-case quality. An oracle router is forbidden.

## Harness tracks

The primary track measures the products users will receive: default
Antigravity versus Cline's agent core with an exact candidate model. Follow-ups
must remain in one live conversation. If official headless integration fails,
try official TUI or editor automation before changing harnesses.

A neutral Codex or DeepSeek harness is permitted only as a diagnostic track to
answer whether a miss comes mainly from the model or Cline. It uses the same
workspace, messages, limits and grader but produces no Cline-equivalence claim.
DeepSeek Harness is developer-preview infrastructure and needs a credible
Windows/editor delivery path before it can become a workshop candidate.

## Visual review

Visual quality is scored from the rendered desktop and narrow pages, not source
code. Blinded review covers hierarchy, chart suitability, labels/units,
colour/contrast, clipping, responsive layout, and non-technical comprehension.

A multimodal judge may be one reviewer. Preserve its model, settings, exact
prompt, images and raw response. It cannot override a deterministic data error,
and it cannot be the only visual reviewer.

## Contamination controls

- Separate workspace and client state per experimental unit.
- No competitor output in case inputs or prompts.
- No shared writable dependency or browser profile directory.
- No agent gets access to `benchmarks/runs` or case oracles while working.
- The application container receives no Docker socket and no sibling mounts.
- Record any contamination or human intervention as a protocol deviation.

## Local replay

Local replay uses exact holdout bytes and messages from hosted runs. It may not
revise prompts to help the local model. Capture weights revision/hash,
quantization, inference engine, chat/tool template, context/output limits,
sampling, hardware, memory and throughput in addition to normal run metadata.
