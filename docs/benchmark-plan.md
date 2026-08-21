# NGO data-dashboard benchmark plan

## The question

What is the smallest locally deployable model that can use Cline's normal agent
harness to do at least as well as Google Antigravity's default setup for the
kind of data work NGO staff ask for?

"At least as well" includes correct numbers, a working and understandable
website, useful follow-up changes, honest caveats, citations, and downloads. A
pretty dashboard with wrong data is a failure.

The first phase calls candidate models through OpenRouter. This makes the model
search cheap and quick, but does not prove that a local quantized copy performs
the same way. The winning hosted model is replayed locally in phase two.

## Who the benchmark represents

The benchmark user is an NGO staff member who may know their programme and data
well but is not assumed to know software development. Prompts use ordinary,
short Indian English. They may contain spelling mistakes and incomplete
sentences. The agent should make progress without requiring technical terms.

A typical session begins with a file or a request to find public data:

> one excel is there. make simple website showing district health position. i
> should select year and compare two districts. please show where each number
> came from

The same user then asks things such as:

- `only show 2021 to 2023`
- `compare gaya and nalanda`
- `why gaya is worse? don't guess if data cannot tell`
- `give source and page number`
- `download this filtered table`

The benchmark measures the whole conversation, not only the first page.

## Systems being compared

The baseline is the current stable Antigravity CLI (`agy`) using the default
agent, model, effort, and other settings presented to a fresh user. The runner
records what the default resolved to on that date.

The candidate is the current stable Cline CLI with its default agent behaviour,
except that it is explicitly connected to a candidate model through OpenRouter.
The starting candidate is `qwen/qwen3.8-27b`. Its OpenRouter endpoint and
downloadable `Qwen/Qwen3.8-27B` weights were verified directly on 2026-08-19.
Cline 3.0.55's ACP model list did not yet include the new slug and silently
selected another model in an early diagnostic run. That is a client-catalogue
defect to work around; the run is invalid and must not be scored as Qwen 3.8.
Every measured runner must assert the resolved model before sending a prompt.
The smoke currently uses OpenRouter's `:nitro` suffix because the default route
hit an upstream idle timeout. The suffix prioritises throughput while resolving
to the same Qwen 3.8 27B model. Treat it as a recorded provider-routing choice,
capture the actual provider when possible, and do not assume its latency or
reliability carries over to local replay.

Both official CLIs share their agent core with the corresponding graphical
product. Cline's ACP mode keeps one process and session alive across turns. If
that or Antigravity's conversation resume stops matching the GUI experience,
the fallback order is official TUI, Electron/VS Code automation, then a clearly
labelled neutral-harness diagnostic. A neutral harness does not replace the
primary product comparison.

The conclusion must name the full system:

> Cline version X plus model Y through OpenRouter was non-inferior to default
> Antigravity version Z on this benchmark.

It must not be shortened to "model Y is as good as Antigravity".

## Case bank

Start with about 20 carefully checked cases rather than 100 automatically
generated spreadsheets. Use three repetitions because agent runs vary. Divide
the bank before testing into a development set for model selection and an
untouched holdout set for the final claim.

Cases cover clean and messy CSV, multi-sheet Excel, digital and scanned PDF,
cross-source joins, changed district boundaries, official-source discovery,
citations, safe interpretation, filters, comparisons, and downloads. The suite
is representative rather than adversarial: most cases are straightforward
tasks a small NGO might actually bring to a workshop.

“Multi-sheet Excel” does not mean only choosing the widest rectangular tab.
The suite includes workbooks whose meaning is carried by merged headings,
formatting, blank separators, repeated headers, stacked subtables and tables
spread across tabs. Extraction evidence retains sheet names and cell regions.
Both products receive the same ordinary recovery prompts when the first result
misses a visually obvious region, for example “there is another table below.”
Success on the clean maternal-health workbook is not extrapolated to these
shapes.

Use archived official public data where practical. Deterministic scripts may
make messy variations, but each result must have an independently calculated
answer key. Preserve downloaded bytes, source URL, retrieval time, licence when
known, and SHA-256.

No benchmark or workshop fixture may contain private or identifying beneficiary
or health data. Both measured products send content to cloud services in phase
one.

## Fairness and isolation

Each agent/model/repetition receives a fresh copy of the same immutable case
inputs and exact messages. It cannot see sibling workspaces or previous output.
Versions, settings, permissions, timeouts, network policy, retries, and human
interventions are recorded.

Measured agents should run in equivalent per-run outer containers because the
Antigravity smoke test showed that a host process started in `/tmp` could still
search the user's home and discover benchmark/Cline artifacts. Mount only the
fresh workspace, minimum read-only credential material, and run-specific client
state; never mount the repository, sibling runs, the full home directory, or
the Docker socket. The generated application runs in a second disposable
container. A host run is accepted only as a documented fallback with an audit
of every observed tool path.

Both agents use the same benchmark agent-tools image. It contains ordinary
format and web utilities (Python, Node, curl, Excel and PDF readers), so an
Excel/PDF result measures the agent and model rather than whether one vendor's
minimal base image happened to include a parser. Record the image ID and package
versions with every batch.

## Scoring

The detailed machine-readable rubric lives in
[`../benchmarks/config/scoring.json`](../benchmarks/config/scoring.json).

| Area | Weight |
| --- | ---: |
| Data and calculation correctness | 35 |
| Working filters, comparisons, and downloads | 15 |
| Source and citation quality | 15 |
| Missing data, uncertainty, and safe interpretation | 10 |
| Usefulness to a non-technical NGO user | 10 |
| Visual quality and accessibility | 10 |
| Time and cost | 5 |

Wrong numbers, fabricated sources, an application that cannot be opened, or a
control that displays misleading data are critical failures. Critical failures
cannot be averaged away by visual quality.

Playwright opens every application at desktop and narrow viewport sizes. It
records screenshots, console errors, page errors, selected control states, and
downloads. Data checks compare visible and downloaded values with the oracle.
Visual review examines hierarchy, chart choice, units, labels, contrast,
clipping, responsive behaviour, and whether the page makes sense without a
developer explaining it.

Each site gets a primary workshop-online pass and a separate offline-resilience
pass. The online pass records external library/font requests; the offline pass
blocks them and exposes brittle CDN dependencies. Because the intended workshop
is connected, offline degradation is reported as an operational risk rather
than automatically treated as a primary critical failure.

A multimodal model can provide a blinded visual score, but deterministic checks
and a human review sample remain primary. Preserve the judge prompt and raw
response. Avoid using a Gemini model as the only judge of Antigravity.

## Choosing and replaying the model

Start with Qwen 3.8 27B. If it passes, move downward; if it fails, move upward
through candidates whose downloadable weights, licence, tool calling, context,
quantization and memory needs have been verified. Models from different Qwen
generations and MoE/dense architectures are labelled rather than treated as a
clean scaling curve.

Every run retains the exact messages, input hashes, agent events, generated file
hashes, browser evidence, scores, timing, usage and cost. Local replay also
records weights revision/hash, quantization, inference engine, chat/tool
template, context, hardware, memory and throughput. This evidence is what makes
the hosted and local results comparable.

Use a two-stage search. A frozen five-case subset screens models once. After at
least three paired cases, stop only for futility: a gap of 20 points or more
with no plausible recovery, or two excess critical failures. Candidates within
10 points complete all development cases and repetitions. The final paired
non-inferiority margin is 7 points, with 5- and 10-point sensitivity results.

Also report an operational quality/footprint frontier. A candidate within 10
points can be described as comfortably usable. A candidate up to 15 points
behind may still be recommended as an explicit efficiency tradeoff when it
offers a substantial memory/throughput benefit and the entire extra gap is
non-critical presentation or usability quality. It must have no material
regression in numerical correctness, citations, safety, or critical-failure
rate. This tier is not called equivalent to Antigravity.

If a single model is not the best operational answer, freeze and test a router:
start small, escalate to 27B or an 80B-class model on declared observable input
conditions or low-confidence/failure signals, and record every decision. The
router is one system and is scored on end quality, cost, latency, and escalation
rate. Concurrency for 10--20 NGO users is a later deployment benchmark, not a
claim from this hosted quality run.
