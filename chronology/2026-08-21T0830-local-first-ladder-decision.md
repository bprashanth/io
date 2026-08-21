# The local-first ladder passed as a routed system, not as a laptop model

We finished the bounded quantization search and the first executable event
prototype. The result is more useful than a single-model winner, but it needs
careful wording.

Qwen 3.8 27B passed all 30 questions in the final accounted OpenRouter run. It
took 225.027 seconds, used 14,845 tokens and cost USD 0.02673396. This qualifies
it as the trusted data-query fallback. It does not yet prove local DGX behavior;
the same frozen run must be replayed against the locally served model.

Arctic-Text2SQL-R1-7B BF16 passed 26/30, and later passed the separate 15/15
holdout. Its full run took 1,060.113 seconds. The laptop quantizations did not
improve monotonically with size:

- Q4_K_M: 25/30, 434.925 seconds, 4,683,074,144-byte weights;
- Q5_K_M: 24/30, 484.796 seconds, 5,444,831,840-byte weights;
- Q8_0: 24/30, 575.617 seconds, 8,098,525,792-byte weights and about 7,952 MiB
  observed GPU memory.

Q8 was the last bounded quantization check. We stopped there. XiYan 3B and 7B
had already scored 11/30 and 19/30 respectively. The existing trained 2B/9B
Algebra models were not silently repurposed: their documented place/scientific
dialect lacks the generic table grouping and join contract needed here.

Q4 missed the agreed 85% standalone gate by one answer, so it cannot be called
the answer engine. A generic routing replay changed the system conclusion. The
router checked requested grouping, ranking direction, percentage arithmetic,
named-category separation and whether named comparison periods survived into
the result. It accepted 21 Q4 answers, all correct; escalated nine, including
all five Q4 mistakes and four conservative false positives; and accepted zero
wrong answers. Substituting the separately qualified Qwen answers gives a
30/30 routed replay and a 30% fallback rate. This is the current event design:
Q4 tries locally, Qwen 27B repairs rejected work, and local DuckDB remains the
calculator.

We then ran the actual three-turn agriculture journey through this shell. Q4
handled the simple 2024 ranking. It was correctly rejected when it mislabeled a
tonnes-per-hectare difference as percentage points, and again when it returned
only the change while omitting the 2023 and 2024 endpoint measures. Qwen
produced the retained-period results. The final page showed Bhojpur and Wardha,
0.1 and 0.2 t/ha change, both endpoints and source. Its browser check passed:
one SVG, expected two rows, working download, no console/page error, no external
request and no desktop overflow.

Four more final pages covered a merged-heading Excel table, a digital PDF with
page/table provenance, a two-file budget join and two ecology indicators. They
all passed the same browser checks. Human screenshot inspection caught things
the SQL gate did not: the first Q4 agriculture page displayed a unit error; the
renderer mistook `nitrate` for the word `rate`; dense line labels collided; and
a small 0.1/0.2 chart initially used a 0–1 scale. The fixes tokenize unit names,
reduce dense labels and scale small non-percent values to their data.

The frontier boundary also became stricter. The raw user question was removed
because it can contain participant data such as district names copied from a
sheet. The optional layout request now contains only value-free intent enums,
source/download booleans, result column name/type/role and a fixed layout
contract. Five final journey leak scans found no row values, categories,
aggregates, filenames, hashes, screenshots or HTML. The deterministic renderer
did not need a frontier call.

The new Antigravity agriculture evidence is the most direct product comparison.
Antigravity 1.1.15 resolved to Gemini 3.7 Flash (High). Repetition one failed at
turn two and never ran turn three. Repetition two returned good chat analysis
for all three turns, but every result had `status: ERROR`, and the webpage hash
never changed after turn one. The final page was still the 2024 all-block
ranking, not the requested two-block comparison. Its first online page looked
more decorative than ours, but depended on four CDN families; offline it raised
`Chart is not defined`. The local shell completed the durable journey and works
without the network. This is a measured win on this journey, not universal
Antigravity equivalence.

What remains is operational: package the prototype for representative Windows
laptops, serve and replay Qwen locally on the DGX, test a realistic 20-user
burst, and add scanned PDF, arbitrary workbook-region correction and official
data discovery journeys. Until then the pitch is “a credible checked
local-first prototype with a trusted fallback,” not “finished replacement.”

## Evidence

- [aggregate decision](../benchmarks/results/v2-local-first-ladder-2026-08-21.json)
- [architecture decision](../docs/v2-local-first-event-decision.md)
- [frozen query suite](../benchmarks/v2/query-suite-v2.json)
- [Q4 strict run and router replay](../benchmarks/runs/2026-08-21-v2-query-gate-v2/arctic-text2sql-r1-7b-q4km/rep-01-full-final)
- [Q8 final bounded run](../benchmarks/runs/2026-08-21-v2-query-gate-v2/arctic-text2sql-r1-7b-q8/rep-01-full-final)
- [Qwen accounted run](../benchmarks/runs/2026-08-21-v2-query-gate-v2/qwen38-27b-openrouter/rep-04-full-final-accounted/result.json)
- [final routed agriculture journey](../benchmarks/runs/2026-08-21-local-first-cli/agriculture-q4/rep-05-final)
- [Antigravity repetition one](../benchmarks/runs/2026-08-21-v2-dashboard-journey/agriculture/antigravity-default/rep-01/agent/antigravity-summary.json)
- [Antigravity repetition two](../benchmarks/runs/2026-08-21-v2-dashboard-journey/agriculture/antigravity-default/rep-02/agent/antigravity-summary.json)
