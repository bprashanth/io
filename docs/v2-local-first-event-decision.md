# Local-first event decision

## The short answer

For the event, use a packaged local insight application, not a general coding
agent. Let a small local model attempt the data query, check its plan and result
shape in ordinary code, and send rejected work to Qwen 3.8 27B. Execute every
query locally in DuckDB and render one self-contained webpage locally. Keep a
frontier model as an optional layout adviser only; it receives a value-free
intent enum and column schema, never the raw question or real values.

The smallest useful model we measured is Arctic-Text2SQL-R1-7B Q4_K_M, a
4,683,074,144-byte GGUF. It did **not** clear the 85% standalone gate: 25 of 30
strict query cases passed. It is therefore not safe as an unsupervised answer
engine. With generic checks for requested grouping, order, units, named
categories and retained comparison periods, the router accepted 21 correct
answers, accepted no wrong answer, and escalated nine. Qwen 3.8 27B passed all
30 cases in the accounted OpenRouter run. Replaying the ladder therefore gives
30 of 30 final answers, with a 30% fallback rate on this deliberately difficult
query suite.

This is enough for an event prototype and a credible pitch. It is not yet a
claim that any ordinary Windows laptop can run it, that 20 simultaneous DGX
requests will meet the time budget, or that arbitrary scanned PDFs and damaged
workbooks are solved.

## What was actually measured

The frozen query gate had six general patterns and five plain-language
phrasings of each: derived rates and ranking, percentage-point change by group,
lowest-first ranking, two related measures, a cross-table join and missing-value
scope. It did not contain sector-specific routing rules.

| Candidate | Strict result | Decision |
|---|---:|---|
| XiYanSQL 3B BF16 | 11/30 (36.7%) | reject |
| XiYanSQL 7B BF16 | 19/30 (63.3%) | reject |
| Arctic 7B BF16 | 26/30 (86.7%) | accurate enough, but too large for the intended mid-grade laptop rung |
| Arctic 7B Q4_K_M | 25/30 (83.3%) | checked speculative laptop rung |
| Arctic 7B Q5_K_M | 24/30 (80.0%) | reject |
| Arctic 7B Q8_0 | 24/30 (80.0%) | reject; a larger quant did not recover quality |
| Qwen 3.8 27B, OpenRouter, low reasoning | 30/30 (100%) | trusted fallback finalist |

The Qwen run took 225.027 seconds in total and cost USD 0.02673396. The Q4 run
took 434.925 seconds on this host. Those figures are useful for replay, not a
Windows latency prediction. Q8 used about 7,952 MiB of GPU memory while running
and was both slower and less accurate than Q4, so quantization search stopped.

In the final three-turn product journey, the local call took 9.554 seconds on
the accepted first turn. The two routed turns spent 17.185 and 17.567 seconds
on the rejected local attempt, then 5.278 and 5.291 seconds on Qwen. The two
fallback calls cost USD 0.0040001 together. These model-call times are well
inside the provisional event turn budget on this host, but do not include a
Windows or 20-user load result.

The Arctic BF16 model also passed a separate 15/15 holdout, but its measured
query time and memory class make it a server/high-end-machine option rather
than the event default. The existing tuned 2B/9B Algebra models remain useful
design evidence for typed plans and deterministic execution. Their learned
dialect is place/scientific-specific and does not currently express arbitrary
tabular grouping and joins, so using those weights at the event would be an
unmeasured shortcut.

## The executable ladder

```text
participant file(s)
  -> local structure-preserving CSV/XLSX/PDF ingest
  -> Arctic 7B Q4 proposes one read-only DuckDB query
  -> local syntax, binding, scope, unit and result-shape checks
       -> accepted: execute locally
       -> rejected twice: Qwen 3.8 27B proposes the query
       -> Qwen still rejected: ask a plain clarification or fail closed
  -> local DuckDB result with source/page/sheet/table fields
  -> deterministic local visual selection and self-contained HTML
  -> browser checks, filtered CSV download and persistent conversation state
  -> optional frontier layout spec from value-free metadata only
```

Qwen 27B may receive the real data contract because the deployment target is a
trusted DGX on the event network. OpenRouter was used only to screen it with
synthetic/public fixtures. A real private deployment claim requires serving the
same model locally and replaying the frozen suite.

The frontier boundary is stricter. It serializes only:

- an enum such as `trend`, `change`, `comparison` or `ranking`;
- whether source and download controls are required;
- result column names, declared types and roles;
- a fixed allowlisted chart/layout contract.

It excludes the raw participant question because that sentence may contain
district names or copied cell values. It also excludes rows, samples, distinct
labels, aggregates, filenames, hashes, screenshots and generated HTML. Leak
scans passed on the five final rendered journeys. The current renderer did not
need to call a frontier model at all.

## What the webpages showed

We opened and exercised final pages for five data shapes:

- a three-turn agriculture CSV journey with a rate, trend and two-block
  comparison;
- a merged-heading Excel sheet with boys/girls indicators and provenance;
- a digital PDF table with page and table identifiers;
- a join between approved-budget and actual-spend CSVs;
- ecology averages with a selectable second indicator.

The agriculture journey used the selected Q4-to-Qwen ladder. The other four
pages used Q5 as a disposable planner while the quantization comparison was
still running. They qualify the generic ingest/execution/rendering shell across
those shapes; they do **not** qualify Q5, which later scored only 24/30, or prove
that Q4 handles every one of those files without fallback.

All final pages loaded with one SVG chart, made no external request, had no
browser or console error, did not overflow at 1440 pixels, and downloaded the
expected rows and provenance columns. We inspected the screenshots, not only
the HTML. The pages are clean and professional, though less visually ambitious
than Antigravity's best online first page.

For a concrete but deliberately unblinded visual grade, Antigravity's online
first page was about 9.0/10 and the local final pages were in the 8.3–8.6/10
range. That puts the local visual finish within roughly 5–8% of the observed
Antigravity page. The comparison is only about appearance: Antigravity's scored
page was stale after the follow-ups and failed offline, while the local final
page reflected turn three.

Human inspection mattered. It caught two bugs that SQL-only scoring missed:
Q4 had called a tonnes-per-hectare difference a percentage-point change, and a
renderer substring check treated `nitrate` as `rate` and displayed percentages.
The final generic checks reject the first error and token-based unit inference
fixes the second. Another clean-looking page initially omitted the two endpoint
years from its comparison download; period retention is now a routing
obligation.

## The direct Antigravity comparison

Antigravity 1.1.15 resolved to Gemini 3.7 Flash (High) in both agriculture
repetitions. Its first online page was more decorative than the local page, but
neither repetition completed a durable three-turn webpage journey.

In repetition one, turn two ended in a network failure and turn three never
ran. In repetition two, all three chat responses contained numerically useful
answers, but every result had `status: ERROR` because of an artifact-path
failure. More importantly, the webpage hash never changed after turn one. The
chat discussed the later trend and two-block comparison while the visible page
remained the original all-block 2024 ranking. Its online visual also depended
on Tailwind, Chart.js, Font Awesome and Google Fonts CDNs. With those requests
blocked, the chart failed with `Chart is not defined`.

The local ladder completed all three turns and the final webpage and download
contained Bhojpur and Wardha, their 2023 and 2024 endpoints, the 0.1 and 0.2
t/ha changes, and source. That is a measured win on this journey's reliability,
privacy and durable follow-up behavior. It is not general proof that the local
system beats Antigravity on every unseen file.

## Event delivery recommendation

Prepare one application before the workshop. Participants should not install
Python, Node, Ruby or Docker during the exercise. The prototype is Python, but
the event build should package the ingest, DuckDB executor, renderer and local
service as one signed Windows-friendly bundle. Install llama.cpp and the Q4
GGUF only on laptops that pass a hardware rehearsal. Unsupported laptops use
the same interface with the DGX as the first query tier.

Run Qwen 3.8 27B on the DGX behind an OpenAI-compatible endpoint for the event.
Keep OpenRouter as an explicit operational fallback for synthetic/public data
or consented use, not as the privacy story. Serve the generated page locally on
the participant machine where possible. A shared hosted page is a sensible
fallback for machines where local serving fails; the visible progress stream
and automatic page refresh preserve most of the “it is building my website”
effect.

For 20 participants, laptop Q4 attempts distribute the easy work. The frozen
suite's 30% escalation rate is a conservative capacity planning input, not a
measured concurrency result. A workshop rehearsal must still measure 20 mixed
requests, queue time, cancellation and fallback behavior against the local
Qwen endpoint.

## What to test next

1. Package and install the prototype on two representative Windows laptops:
   one CPU-only/low-memory machine and one 8 GB GPU machine. Record first page
   and follow-up latency.
2. Serve Qwen 3.8 27B locally on the DGX and replay the exact 30-case gate and
   the five saved journeys. Do not change the prompts during replay.
3. Run a 20-user burst with a realistic mix of easy local accepts and hard
   escalations. Set a queue timeout and prove the user sees a useful status.
4. Add product journeys for scanned PDF/OCR, multiple workbook regions and
   sheets, a plain-language “there is another table below” correction, and
   official-source discovery with citation identity checks.
5. Only after those pass, test a generic typed-plan fine-tune in the 3B–9B
   range. Do not tune to the benchmark questions or sectors; train on operators,
   table shapes and error recovery.

## Reproducible evidence

- [local, SSH and proposed Windows runbook](local-first-reproduction.md)
- [aggregate decision and exact run links](../benchmarks/results/v2-local-first-ladder-2026-08-21.json)
- [frozen query suite](../benchmarks/v2/query-suite-v2.json)
- [Q4 routed replay](../benchmarks/runs/2026-08-21-v2-query-gate-v2/arctic-text2sql-r1-7b-q4km/rep-01-full-final/router-replay-v2.json)
- [accounted Qwen 27B run](../benchmarks/runs/2026-08-21-v2-query-gate-v2/qwen38-27b-openrouter/rep-04-full-final-accounted/result.json)
- [final routed journey and screenshot](../benchmarks/runs/2026-08-21-local-first-cli/agriculture-q4/rep-05-final)
- [Antigravity repetition two](../benchmarks/runs/2026-08-21-v2-dashboard-journey/agriculture/antigravity-default/rep-02/agent/antigravity-summary.json)
