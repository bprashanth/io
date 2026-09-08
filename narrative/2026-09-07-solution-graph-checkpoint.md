# The solution graph: everything we tried before the second event

A checkpoint written 2026-09-07, before the second Insight Out event, so that
nothing we tried is lost when the event data starts pruning branches. Between
2026-08-19 and 2026-09-02 this repo went through seven distinct generations of
architecture. Three things survived to event day: the privacy shield (a nice to
have), the privacy filter, and the blind test - the latter two became io. 

This document records every generation, including the dead ends and the
unfinished runs, because each one is a node in a graph of solutions that the
event results will now score.

Each section starts with a plain justification of why the experiment was run,
then what was tried, what was measured, and what carried forward. Sections are
being filled in one at a time; a heading with (to be written) is a stub.

## Where this started

For the first two Insight Out events, and the 340-run frontier benchmark that
followed them, see [remembrancer.netlify.app](https://remembrancer.netlify.app/). 

Those findings shaped everything below. In summary: 
Frontier agents' best answers are excellent; the problem is
"the floor" and the variance between their answers. For the social sector, this could result in wasted resources (best case) or the complete exclusion of beneficiaries. 

The three goals set there: 
1. patch the data holes
2. move the domain knowledge into the tool
3. make the best day the every day

None of those were completely achieved in time for IO 3. 
What we did achieve was a stepping stone that could lead us to all 3, with community participation. 

## Gen 0 - looking for a local-size alternative to Antigravity (Aug 19-20)

> After the first Insight Out event we started to realize a bunch of our
> problems stemmed from one fact: mainstream AI wasn't built for the social
> sector. The benchmark after that event showed us that the ceiling is high,
> the floor is too low.

It was clear that trying to benchmark against Antigravity in all directions
was going to be a waste of time. Most of our users don't need the vastness of
a frontier model. It was unlikely they were ever going to produce music, build
games or solve hard math problems. The more likely use case - our goal at the
event - was to give a small NGO a general-purpose way to understand an
unfamiliar file without needing a data analyst or computer programmer sitting
beside them. While there are several other goals, this is the one that
dominates our thinking right now.

So with that goal, can we match Antigravity? Doing so would require us to:

1. Create a benchmark: diverse input formats, different questions, first fired
   at Antigravity and then at "solution X" (the competitor we would have to
   define). Doing this would save us months, if not years, of product time.
2. Understand the components of Antigravity: Antigravity is really three
   things combined: an LLM (the thing you pick on the dropdown), a harness,
   and an IDE.
3. Understand what the user base wants: they don't really need an IDE. And, as
   mentioned above, we assume the benchmark represents their input data
   formats and language, for the main goal we identified of building a
   dashboard.

Running multiple iterations of this setup we found the following:

1. Qwen 3.8 27B is good enough to continue as a serious Antigravity
   alternative on the benchmark.
2. The harness matters more than the model. The same 27B did badly in Cline's
   native harness and much better in DeepSeek's harness.
3. The harness is also going to drive costs. It controls how many calls are
   made to the LLM, which answers are accepted and which are rejected.

The other models we tried and discarded: having found the 27B, we decided to
binary-search downward to close the gap. We assumed that anything larger than
~30B parameters was too big to run efficiently for, say, 20 concurrent users
at the event. So our only choice was to go down. And even there, the question
was practical - is there an alternative we can just hand users to run on
their own laptops? Model swaps inside the same harness helped us discern:
* Qwen 3.5 9B couldn't produce a working page
* Qwen3 14B dropped half the districts and invented a citation. 

So: above 14B, at or below 27B.

The findings of Gen 0 in a nutshell:

> The things we can do to change the core model are limited. We can run a
> model on a laptop. We can run one on our own server. Or we can invoke a
> frontier model remotely. In the first two we can fine-tune, build
> special-case models, and route requests - or sub-requests - to individual
> models. That's about it.
>
> The harness is the opposite: _around_ the model we control everything. What it
> reads. What it is allowed to say. What runs the numbers. What checks the
> answer. What draws the page. What leaves the laptop. How many times it gets
> called. What it remembers for next time.
>
> The next two weeks were spent pulling these levers and documenting which
> ones moved the result.

Scope: Antigravity CLI and IDE as the reference; Cline (CLI and extension) and
DeepSeek (SDK and Web, with the NGO guardrail v1/v2) driving Qwen 3.8 27B;
model screens of Qwen 3.5 9B and Qwen3 14B; the reasoning-effort proxy; the
finding that the harness matters more than the model.

## Gen 1 - The split pipeline: model plans -> code computes (Aug 20)

(to be written)

Scope: constrained JSON plans, DuckDB as the only calculator, deterministic
renderer, browser checks; GPT-OSS 20B as planner; the independent-critic track
(critic-replay bank, Gemini reference, the failed self-critic ablation); the
bounded Census connector; the region extractor for irregular workbooks.

## Gen 2 - The local-first SQL ladder (Aug 20-21)

(to be written)

Scope: XiYanSQL and Arctic-Text2SQL (four quants) as laptop tiers; the regex
router; the 30/30 routed-replay claim; the foundation re-verification that
demolished it; holdout-v2 and the ten-model general screen; the rejected
algebra LoRAs; the never-run fine-tune and grammar-constrained decoding plans.

## Gen 3 - Sheltered mode: v0 privacy filter (Aug 21)

(to be written)

Scope: the PII engine race (regex, Presidio, three GLiNER variants, remote
27B); the column classifier and pseudonymiser; the which-Sameer problem; the
envelope ablation (schema-only vs tokenised sample vs full rows); the finding
that the dashboard gap was a renderer gap, not a model gap.

## Gen 4 - The privacy shield for stock Antigravity (Aug 21-22)

(to be written)

Scope: proxy interception of Antigravity's model traffic; the 0.2.x lifecycle;
the discovery/replacement split; the 0.3.x pivot to discovery-at-rest; one
engine shared with io.

## Gen 5 - io's kernel: model tiers, lanes, and the harness question (Aug 22-24)

(to be written)

Scope: seventeen candidates for the laptop tier; the plan/receipt contract;
Qwen 3.5 9B for Ask and Build, Qwen 3.8 27B as the reference tier; the page
lane; local llama.cpp feasibility; Codex and Hermes measured against io (no
harness at T0); the open lane; astronaut skills; the Telegram shell.

## Gen 6 - The minimal io reset (Aug 24-26)

(to be written)

Scope: the declutter to provider -> folder -> review sheet -> chat; doc
scanning; ~name~ lookup; share on LAN; the payload ROI ablation
(bm25+manifest); the big-folder guard; the robustness campaign; the workshop
lane probe.

## Gen 7 - The blind test and the event kit (Aug 27 - Sep 2)

(to be written)

Scope: the model switcher built and then deliberately removed; the three-model
blind fanout with votes and reasons; the room board; simulation packets;
packaging for three OSes (thin/fat/portable/offline); the DS4 SSD-streaming
experiment and its dense-27B fallback; event-eve product bugs.

## Parked and unfinished 

Two-step payload router - tier-2 vote classification - hive_mind - DS4 on a
real NVMe drive - duckdb-wasm exports - kernel/shell package split -
workshop/actions lane - ONNX scanner - the three router replacements never
tested (27B-as-checker, self-consistency, no small tier) - holdout-v3
discipline - disk scan cache across restarts - date-coarsening spread
heuristic - the LoRA fine-tune and grammar-constrained decoding experiments -
astronaut auto-compaction.
