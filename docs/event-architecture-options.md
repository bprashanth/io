# Event architecture options: local, private data-to-insight dashboards

## Decision we are trying to make

The immediate setting is a workshop with about 20 NGO participants. Each person
brings an unfamiliar CSV, Excel workbook or PDF, or asks the system to find a
public dataset. They use short, ordinary questions to get a finished desktop
dashboard, inspect it, ask follow-up questions and download a useful result.

The event can use OpenRouter. The longer-term decision is the smallest open
model and delivery design that preserves the useful part of Antigravity without
its lock-in. It may run on each laptop, on a shared DGX Spark, or as a hybrid.

This is not primarily a coding benchmark. A successful participant should not
have to diagnose JavaScript, install a missing package mid-task, interpret a
traceback, or tell the model which chart library to use. A bounded automatic
retry is acceptable. Repeated crashes, silent stale pages and unbounded waiting
are failures because they destroy confidence even if an expert could repair
them.

## Measured decision on 21 August

The option study has now produced an event prototype decision. Use Arctic
Text2SQL 7B Q4_K_M as a checked speculative laptop planner, route rejected
queries to Qwen 3.8 27B on the trusted DGX, execute in local DuckDB, and render
a self-contained page deterministically. Q4 scored 25/30 by itself, below the
85% standalone gate. The generic router accepted 21 correct plans, accepted no
wrong plans, and escalated nine; the qualified Qwen run scored 30/30. This is a
30/30 routed replay, not a claim that Q4 alone is sufficient.

The optional frontier tier is now layout-only. It receives a value-free intent
enum and result column name/type/role, not the raw question, rows, categories,
aggregates or screenshot. The fuller decision, exact evidence and remaining
Windows/concurrency work are in
[`v2-local-first-event-decision.md`](v2-local-first-event-decision.md).

## Requirements frozen for the event study

- Desktop only for the next phase. Pages must not clip, overflow, show raw code,
  or look unfinished at the declared 1440 by 1000 viewport. Phone layout is not
  scored.
- Correct numbers, denominators, units, filters and exports remain critical
  gates. Attractive fabrication cannot pass.
- The system must preserve source, sheet/page/table and data-vintage information
  when those are available. Online discovery must prefer and retain the official
  downloaded source.
- A follow-up about the website must change the durable website, not merely the
  chat answer.
- The participant may respond to a failure with plain language such as “I don't
  understand; you figure it out.” The system gets at most two automatic repair
  attempts before an explicit fallback or a clear, useful data limitation.
- Provisional time budgets are five minutes to the first useful page and two
  minutes for a normal follow-up, with a ten-minute hard stop per turn. These
  are event-operability budgets, not quality bonuses, and will be revised only
  before the event benchmark is frozen.
- Private beneficiary-level data must stay local. A schema-only remote call may
  contain column names, declared types, requested chart semantics and synthetic
  placeholder values, but not the participant's rows or real aggregates.

## The important decomposition

The safest small-model design separates jobs that full coding agents currently
mix together:

```text
file or downloaded source
  -> structure-preserving ingest and candidate table regions
  -> model proposes a small validated analysis plan
  -> DuckDB executes the plan over local data
  -> deterministic result bundle with provenance
  -> renderer selects and fills a suitable visual family
  -> self-contained webpage, export and citations
```

The model never supplies the displayed numbers. It selects named columns and
operators; code validates those choices and computes the result. The renderer
accepts only the computed result bundle, not arbitrary executable code. This
turns many hallucinations into rejected plans that can be repaired or escalated
before the user sees a page.

For Excel and PDF, “ingest” cannot mean flattening the file to the largest
apparent table. The intermediate representation must retain sheet/page, cell or
bounding-box coordinates, merged ranges, formulas, blank separators and
candidate table regions. The model may select or revise regions from the user’s
question, while the deterministic layer parses and verifies the chosen cells.
This allows an ordinary follow-up such as “there is another table below” to
redirect extraction without requiring a cell range. The current clean XLSX
adapter does not yet implement that general region-selection layer and its
result must remain narrowly labelled.

The existing tuned scientific-Algebra models fit only the plan-compilation
slot. They are not proposed as installation agents or HTML authors. The current
9B-004d evidence is strong for its admitted scientific operations, but its
v2.4 draft lacks general GROUP and join semantics. Arbitrary NGO tables need a
small additional tabular contract and deterministic DuckDB binding before the
LoRA can be claimed to fit this workflow. Its documented local endpoint was
offline when this phase began, and the owning repository forbids restarting
shared model services without separate authority, so no live result is inferred
from historical scores.

## Candidate paths to measure

| Path | Data sent away | Expected strength | Main risk | 20-user implication |
|---|---|---|---|---|
| OpenRouter coding agent | complete fixture during the public/synthetic event test | closest drop-in workshop experience | cost, privacy, variable tool reliability | API absorbs concurrency |
| 27B plan compiler + deterministic executor/renderer | local rows may remain local if only the profile is sent | strong language understanding without fragile generated code | shared-model queue and profile privacy | needs batching/queue measurements on DGX |
| tuned 2B or 9B Algebra compiler + deterministic executor/renderer | none | small, auditable and potentially laptop-capable | existing dialect is scientific, not general tabular GROUP/join | 2B could be per laptop; 9B may need capable laptops or DGX |
| small local compiler with 27B fallback | local by default; fallback policy decides | cheap happy path with bounded recovery | routing errors and unpredictable escalation rate | plausible event and DGX path |
| local analysis + schema-only frontier layout | value-free intent enum and schema only | high visual ceiling without sharing real values or raw questions | generated layout may not hydrate safely | remote calls are small and parallelisable |
| shared server analysis and hosted page | depends on chosen compiler | simplest participant installation | less visible local “magic”, hosting/auth lifecycle | operationally easiest for mixed Windows laptops |

An 8B model should not be used merely to turn trusted JSON into HTML if a
deterministic renderer can do that more reliably. A styling model earns its
place only if blinded visual review shows a material gain across different data
shapes without introducing broken interactions.

## Proposed fallback ladder

The first model receives the dataset contract and question. Validation, column
binding, execution and page checks are deterministic. Escalation is permitted
only for observable reasons:

1. the plan is not valid JSON after one constrained repair;
2. it names absent or incompatible columns/operators;
3. execution produces an impossible denominator, empty result inconsistent
   with the requested slice, or a failed invariant;
4. the browser reports a page error, missing required content or broken export;
5. the model explicitly returns a typed clarification because the data cannot
   distinguish two materially different interpretations.

The participant is not shown a traceback. The system retries once, then routes
to the next declared model. It may finally use the event's frontier fallback.
Every route decision, duration and repair is recorded. A holdout result cannot
be used to invent a new routing rule.

## Installation and delivery experiments

Test these in increasing operational complexity:

1. A self-contained static HTML result opened directly in the browser. This is
   the least fragile viewing path, but follow-ups regenerate the file.
2. One signed Windows-friendly application bundle containing the ingest,
   executor and renderer. Avoid asking participants to install Python, Node,
   Ruby and Docker independently.
3. A local single-runtime service installed before the workshop, with the IDE
   opening its stable result URL. Python is acceptable for a prototype; a
   packaged executable is the actual Windows test.
4. A shared authenticated server and hosted result page, retained as the event
   fallback for unsupported laptops. The IDE can stream progress while a
   loading page refreshes into the completed report.

Docker is useful for benchmark isolation and a controlled server deployment,
but is a poor default participant dependency on 20 varied Windows laptops. It
adds installation, virtualisation and resource failure modes unrelated to the
insight task.

## Evidence needed before a recommendation

- Re-run routine CSV, XLSX, PDF, safe-interpretation and official-web cases as
  complete multi-turn journeys.
- Add stacked-subtable, merged-heading and cross-sheet workbook cases, including
  a plain-language correction turn, and compare the recovery path directly with
  Antigravity.
- Add a schema-only layout ablation and a deterministic-renderer ablation.
- Test the tuned 2B/9B compilers live only when their owner-approved endpoints
  are available; preserve weights, prompt layout and cache identity because the
  prior work found model-id cache collisions.
- Measure the smallest compiler first, escalation rate, first-page and
  follow-up latency, API cost, model memory and projected DGX capacity.
- Open every generated page, exercise controls and downloads, inspect browser
  errors, save a desktop screenshot and grade visual quality as a person would.
- Perform a separate Windows installation rehearsal before treating any local
  laptop route as workshop-ready.

The next benchmark may conclude that different stages have different winners.
The desired result is not a model leaderboard; it is the smallest dependable
system that gives NGO staff correct, attractive and revisable insight without
requiring technical rescue.
