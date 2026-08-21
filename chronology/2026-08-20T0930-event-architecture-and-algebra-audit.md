# Event requirements and first split-architecture audit

The next phase was reframed around an approximately 20-person NGO workshop,
not a generic coding-agent contest. Participants will bring unfamiliar data,
ask terse ordinary-language questions and expect a correct, attractive desktop
dashboard that changes under follow-up questions. They may ask the system to
figure out a failure, but cannot be expected to debug. Mobile presentation is
out of scope for this phase; overflow, stale pages, wrong calculations,
fabricated citations and broken downloads remain failures.

The short overnight result and Antigravity fault summary was committed at
`docs/overnight-summary-antigravity-faults.md` in commit `c8684e5`.

The existing scientific-Algebra work in Heartwood/Totalrecall was inspected as
a possible small-model component. Adapter 9B-004d has strong frozen evidence on
its own v2.4 draft surface: 20/20 gold execution, 15/15 parser exactness and
97/100 unseen examples. The audit also found important limits for the present
use case. The v2.4 draft has typed `FILTER`, but general `GROUP` is explicitly
outside the released contract and arbitrary tabular joins are not supplied.
Earlier evidence also warns that byte-identical prompt layout and unique model
cache identities matter. The correct role for this LoRA is therefore a bounded
question-to-plan compiler, not a complete agent or webpage author.

The documented local compiler endpoints at ports 8001, 8007 and 8012 were
checked read-only and were unavailable. Totalrecall's repository instructions
explicitly forbid starting or restarting its shared model infrastructure, so no
service was changed and no live LoRA score is claimed. Cursor's `agent` CLI was
also present but unauthenticated; it was not made a dependency.

The initial design is now recorded in `docs/event-architecture-options.md` and
the development freeze in `benchmarks/event/`. It separates ingest, a validated
analysis plan, deterministic DuckDB execution, a provenance-bearing result and
a self-contained renderer. Observable validation/browser failures drive a
bounded fallback ladder. This makes it possible to test a 9B or 2B planner
without asking that model to install tools or author fragile JavaScript, and to
test a schema-only frontier styling call without disclosing real rows.

This is a design checkpoint, not a quality result. The next evidence must run
the restricted plan contract on the existing routine cases, render the actual
computed results, open and exercise every page, and compare the small planner,
27B planner, deterministic renderer and schema-only styling alternatives.

The first one-turn split-pipeline probes were deliberately retained as failed
development attempts. Qwen 3.8 27B inserted a templating string representing a
year selector into a typed integer filter; DuckDB rejected the conversion.
Qwen 3.5 9B unnecessarily grouped an already unique district-year table and
then tried to sort by the source column it had dropped. This demonstrated that
JSON-schema validity alone is insufficient: sequential column binding, value
type checks and execution must gate the page. The compiler instructions were
clarified to keep UI state out of the calculation plan, and the runner gained a
maximum two-repair loop whose failed attempts remain in the run evidence.

On the next smoke, Qwen 3.8 27B produced a valid first page in 22.99 seconds and
used the correct numerator and denominator. The offline page opened at 1440 by
1000 with no browser/console errors, no external requests or horizontal
overflow; the 2023 selector reduced six rows to three and the downloaded CSV
retained `year` and `source`. Human screenshot review found unnecessary numeric
filters, comma-formatted years, awkward percentage ticks and a sparse caution
panel. These deterministic renderer defects were fixed and rechecked rather
than attributed to the model.

Latency was variable. Qwen 3.5 9B medium returned no complete response within
the five-minute first-page budget and was stopped. In a fresh three-turn 27B
run, turn 1 took 96.402 seconds. Turn 2 used two attempts and 54.271 seconds,
but the accepted plan claimed in its note that the renderer would show only
2023 while retaining both 2022 and 2023 rows. That exposed a second validation
gap: successful execution does not prove that an explicit natural-language
filter was honored. A deterministic check for the benchmark's declared
`only YEAR` and `only YEAR to YEAR` forms was added. Turn 3 then returned no
complete response in five minutes and was stopped. This run is a development
failure, not evidence of multi-turn event readiness.

After the user authenticated Cursor CLI, it performed a read-only cross-repo
audit without editing files or changing services. It independently identified
the Heartwood typed validator/executor as reusable, the Idlisseus
`idli-result/1` envelope and visual renderers as useful provenance/drill-down
building blocks, and the same missing general relational surface: existing
`RELATE` is not an arbitrary table join and current follow-ups are bounded
actions rather than a general analyst state machine. Its recommendation was a
small compiler over deterministic DuckDB plus a separate renderer and bounded
escalation. This supports the working architecture but is design corroboration,
not new measured model evidence.

A Qwen 3.8 27B low-reasoning replay then completed all three smoke turns. Turn
1 took 30.461 seconds. Turn 2 first repeated the stale-year mistake; the new
semantic gate rejected it, and the repaired attempt added `year = 2023`. The
two attempts took 8.227 and 22.020 seconds. Turn 3 preserved the three-row state
and took 41.318 seconds. The computed result correctly identified Purnia at
76%, and all three pages passed load, console, offline-request, overflow, table
and download assertions.

That run still failed human visual review. Filtering the turn-1 time-series to
one year left three district points on one x position while the precomputed
change cards continued to show two-year changes. Turns 2 and 3 used a connected
line across unordered district names. The browser checks had missed these
semantic visual faults. The renderer was changed to compute insight cards from
currently visible rows and to turn a one-period multi-district trend into bars.
The plan validator now rejects categorical line axes and participant-facing
implementation jargon. A read-only Cursor review corroborated the stale-card
fault and also found that the schema advertised unimplemented chart types and
that formula-leading text was unsafe in spreadsheet downloads. The prototype
chart enum was narrowed to implemented modes and both CSV paths now neutralise
formula-leading strings. A new replay is required; the preserved low-reasoning
run remains a development failure.
