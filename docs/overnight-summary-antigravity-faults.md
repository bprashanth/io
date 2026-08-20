# Short overnight summary: what Antigravity got wrong

The overnight work found a credible open-model finalist, Qwen 3.8 27B, but did
not yet prove equivalence. The strongest apples-to-apples evidence is one
three-turn GUI smoke: Antigravity scored 80.5, Cline/Qwen Xhigh 91.2 and
Cline/Qwen Medium 85.5. The older five-case command-line screen was much less
stable: Antigravity averaged 52.2 and Cline/Qwen 67.8, with a serious failure in
three of five cases for both systems. The correct conclusion is “advance 27B to
repeated GUI cases,” not “the benchmark is finished.”

## Antigravity faults that matter for the NGO use case

Antigravity's largest problem was not ugly output. It often made a convincing
page while the underlying result was incomplete or wrong.

- In the programme case it ignored the supplied CSV, invented replacement data,
  sources, causes and interventions, then produced a polished-looking page that
  was blank because of a JavaScript error.
- In the official Census case it displayed the right population values but
  linked them to unrelated 1961 catalogue records. An NGO user could reasonably
  trust the official-looking citations without discovering that they described
  different data.
- In the GUI smoke it correctly answered that Purnia was lowest in 2023, but
  changed no website files. The chat moved forward while the durable dashboard
  stayed on both 2022 and 2023. This is a product failure for a workflow where
  later questions are supposed to refine the visual.
- It repeatedly invented High/Moderate/Low performance bands that were absent
  from the source and request. It also labelled percentage-point changes as
  percentages and described a weighted value as an ordinary average.
- Its CSV dashboard year control threw a browser error in the counted screen.
  Other pages clipped large sections of tables and charts. Phone layout is no
  longer a benchmark priority, but the same overflow is evidence of unfinished
  layout and can also appear in ordinary narrow laptop windows.
- The command-line PDF request failed with a model-service 403. Other CLI runs
  wrote into unexpected scratch locations or returned an `ERROR` result despite
  a zero process exit. One preview process needed human intervention.
- A process started in a temporary workspace could search unrelated files under
  the user's home directory. Antigravity's own sandbox and working directory
  were not sufficient run isolation.
- The real IDE initially showed Gemini 3.5 Flash Low while no model was actually
  selected in the request. It failed until the model selector was opened, after
  which the operational default became Gemini 3.6 Flash High. An earlier CLI
  default had resolved to Gemini 3.7 Flash High. “Antigravity default” therefore
  has to be observed and recorded, not assumed from the label.
- The first post-consent transition failed on an account-settings decoding
  error. Its browser helper later failed because the configured ARM64
  Playwright-driver download returned 404. Independent browser automation was
  required to inspect the generated page.
- The GUI exposed neither session token use nor price. We observed 35 planner
  requests in the small smoke but could not make a fair cost comparison.

These faults are especially important because participants will remain
deliberately non-technical. They can be taught to say “I don't understand; you
figure it out,” but not to repair JavaScript, inspect a denominator, check a
catalogue title, restart a preview server or notice that the chat answer never
reached the page. Bounded automatic recovery is acceptable; silent failure,
long repeated crashes and confident but unsupported output are not.

## What Antigravity did well

Antigravity should not be reduced to its failures. It completed the GUI smoke
in 595 seconds versus 844 seconds for Cline/Qwen Xhigh. Its desktop dashboard
was visually ambitious, and it produced the only standalone CSV containing
district, year, numerator, denominator, percentage and source. Its lowest-
district chat answer was numerically exact and correctly refused to invent a
cause.

This makes the target clearer. A replacement has to preserve Antigravity's
visual confidence and traceable exports while improving source identity,
calculation discipline, durable follow-ups, recovery and predictable setup.

## Current working decision

Qwen 3.8 27B at Xhigh advances as the current Cline finalist. The exact tested
9B Cline path failed to create websites, and the tested Qwen3 14B path omitted
half its input and fabricated a citation. DeepSeek Web plus a general data-
integrity instruction showed that the 27B model can complete all five ordinary
cases without a serious failure, but it used 264 model steps and cost USD 5.64.
That is capability evidence, not an event-ready system.

The next comparison should reflect the actual event: desktop-first, correct and
cited insights, visually finished dashboards, durable follow-up changes,
automatic bounded recovery and a time limit that preserves user confidence.
It should separately test laptop-local, shared-DGX and hosted-fallback paths for
roughly 20 simultaneous users.

## Evidence

- [paired actual-product smoke](../benchmarks/results/product-gui-smoke-v1-diagnostic.json)
- [counted five-case screen](../benchmarks/results/screening-v2-counted.json)
- [DeepSeek Web development result](../benchmarks/results/deepseek-web-qwen38-27b-guardrail-v2-development.json)
- [full overnight field note](../narrative/2026-08-20-local-model-equivalence-field-note.md)
