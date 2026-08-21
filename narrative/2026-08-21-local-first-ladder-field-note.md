# A small model can open the door, but it should not decide what is true

We were trying to replace the useful part of Antigravity for a room of about 20
NGO staff: give it an unfamiliar file, ask a short question, see a good desktop
dashboard, then ask another question without debugging anything.

The design that survived is a ladder, not one clever model. A roughly 4.7 GB
Arctic Text2SQL model tries the query on the participant's machine. Ordinary
code checks whether the query kept the requested groups, periods, units,
ranking and source. If it did, DuckDB calculates the numbers locally. If not,
Qwen 3.8 27B tries again on the trusted DGX. A fixed renderer turns the checked
result into a self-contained webpage. A frontier model is optional and can only
suggest a layout from a value-free outline.

The distinction matters. The small Q4 model got 25 of 30 strict questions
right, which is below our 85% standalone line. We did not round that up. The
router accepted 21 answers, all correct, and sent nine to Qwen. It caught all
five observed Q4 errors and was cautious on four correct answers. Qwen got
30/30 in the final hosted run. Put together, the saved replay ends at 30/30,
with 30% of this hard suite going to the bigger model.

Making the quantization larger did not rescue it. Q5 and Q8 both scored 24/30;
Q8 took longer and used about 8 GB of GPU memory. The BF16 Arctic model crossed
the line at 26/30 and passed a later 15/15 holdout, but it belongs on a strong
machine, not in the mid-grade laptop pitch. XiYan 3B and 7B were much weaker.
The existing 2B/9B Algebra LoRAs remain an interesting compiler design, but
their present language is too tied to place/scientific operations for arbitrary
workbooks.

Opening the pages changed the work. One agriculture query was numerically close
but called a tonnes-per-hectare difference “percentage points.” One renderer
check saw the letters `rate` at the end of `nitrate` and put percent signs on an
ecology chart. Another clean page downloaded only the change and dropped the
two values being compared. These would all look plausible to a nontechnical
participant. The fixes are generic: tokenize units, retain named comparison
periods, keep dense labels out of each other's way, and reject a result before
rendering when its semantic shape does not match the question.

We opened final pages for a CSV journey, merged-heading Excel, digital PDF,
two-file join and ecology averages. They had no external request, error or
desktop overflow, and their downloads retained provenance. They look clean and
finished. Antigravity's best first page still had more visual flourish.

Only the CSV journey is a final Q4-to-Qwen product run. The other four used Q5
while quantization testing was still in progress, so they prove the shell can
ingest, calculate and render those shapes, not that Q5 or Q4 is independently
qualified on each one.

But the Antigravity comparison showed why polish is not the whole product. In
two repetitions of the same agriculture journey, one stopped at turn two. The
other answered all three turns in chat, yet its webpage never changed after the
first turn because every write reported an artifact-path error. The final page
showed the old all-block ranking, not the requested Bhojpur/Wardha comparison.
It also depended on online chart and style CDNs and broke when they were
blocked. Our local page completed the follow-up and stayed offline.

So the honest event pitch is now strong but bounded: this is a checked
local-first insight prototype that can beat the observed Antigravity journey on
durability, privacy and offline reliability while staying close enough on
visual finish. It is not yet a general Antigravity replacement. We still need a
Windows package, local Qwen replay, a 20-user burst, scanned-PDF handling,
workbook-region correction and official-source citation journeys.

The privacy boundary is simpler than before. The frontier does not receive the
raw question because a sentence like “only Bhojpur and Wardha” already carries
data. It sees only an enum like `change` or `comparison`, result column roles
and a fixed layout standard. Real rows, categories, aggregates, files and
screenshots stay with the local/DGX side. The current renderer did not need the
frontier at all.

Full measurements and replay paths are in
[`docs/v2-local-first-event-decision.md`](../docs/v2-local-first-event-decision.md)
and the
[`aggregate result`](../benchmarks/results/v2-local-first-ladder-2026-08-21.json).
