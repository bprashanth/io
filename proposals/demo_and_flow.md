1. Privacy flow: are participants comfortable using a frontier model with redaction? 
2. Ask, Build, Deploy (deploy is descoped for now but mentioned for completeness): for a number of reasons 
    - cost 
    - privacy
    - correctness 
users may still require a kind of lane based ask, build flow. 
This means they ingest some data and ask questions for which they would expect correct and high quality answers. This can happen across many shells, the io ui itself being one such shell. 
The io kernel is designed in such a way that it prevents nonsense building (answers from memory, phantom trends etc) even from frontier models, but this becomes all the more important in smaller models. 
what this ask mode does is transform your data into a db and then ask a model (based on the range setting) for sql queries to run against this. This will produce some custom dataset that you can verify. 
Realistically speaking, one way to even get here is to visually inspect the data, which means "build me a dashboard" will probably be the first question. 
The flow or lane switching should be explicit based on user and not implicit based on their phrasing. Build me a dashboard above can happen in the ask flow too as they are trying to ask the right question basis this dashboard. If they want to see what this dashboard looks like without duckdb etc in the flow - they can manually siwtch to build mode - and it will do the query and building without actually relying on duck db. If they want to try and build an app with ask model also they can, they will get poor results as it is constrained to user query. 

Let us first test out 1 and 2. Give me a shell i can use that implements this. 
I can use this to test out the real range x lane combos.
3. Skills: this is how the system extends itself

So as far as role harness goes, there are a few differnt possibilities
(measured 2026-08-24, `chronology/2026-08-24T0600-…` and the Telegram field test):

1. **Redoing or retrying queries.** The kernel already retries 3× feeding the DuckDB error back —
   that catches syntax errors and misses conceptual ones (the real-user "map of farmers" turn
   failed the same way 3×: missing GROUP BY every time). The agentic promise is real here, but the
   measured price of a full loop with the 9B is 83 s/answer and discipline loss (it read a raw
   file and answered "80G" as "Rs 80,000" when confused). The plan: **structured replan, not a
   loop** — on final failure, one extra call that gets the error + candidate columns' distinct
   values (tokens only) + permission to change table/strategy; plus the dial's consented
   escalation one tier up. Two calls max.
2. **Skill creation/compaction/invocation.** Measured: a single call to a smart model over the
   interaction log (27B or frontier both work; 27B default). Invocation is deterministic triggers
   in the kernel — no model chooses skills, so a harness's context management adds nothing here.
3. **Smarter selection / request-response handling (astronaut conversation).** The field test
   showed the gaps are conversational, not SQL: provenance questions ("who put this data in?"),
   capability questions (map, slider), scope questions, off-domain chit-chat — each got forced
   into a SQL answer. Fixes are a describe/refuse lane, explicit lane labels, and reach-aware
   lane relaxation — one call or deterministic each, no agent loop. A true conversational
   astronaut (smart model managing the session — Hermes is the packaging if we want it) is
   **blocked on the vault**: user questions and SQL literals carry PII, so they must be tokenised
   before any remote model sees them, live and in the log. Descoped until the vault is in the
   kernel.

## Phase 1 demo: the clean transition (antigravity → antigravity+shield → io)

Same folder, same kind of terse request, three surfaces: stock Antigravity (frontier agent, sees
everything) → Antigravity + privacy plugin (same agent, sees tokens) → **io open lane**: as free
as Antigravity — point at a folder, ask anything, the model writes whatever page it wants. No
DuckDB, no plan contract, no receipts; the ONLY io in the path is the privacy filter: files are
tokenised through the vault before they leave, the page comes back and is rehydrated on the
laptop. People will compare head-to-head with Antigravity, so the open lane must be benchmarked
against the recorded Antigravity results (stage 3: scholarship dashboard 300/103/61/136/67.2 %,
`benchmarks/runs/2026-08-22-antigravity-ide-shield-v2/04-…png`; frontier = Gemini 3.7 Flash as in
`benchmarks/runs/2026-08-21-remote-dashboard/`). Whether the open lane needs a harness (an agent
computing with pandas over a redacted copy of the folder) or a one-shot frontier call is an
empirical question — run both, screenshot both, compare numbers against gold; pick the cheapest
thing that matches Antigravity. Lane switching stays explicit: open is a mode the user chooses,
and the ask/build lanes are the upgrade story (receipts), not a constraint imposed on this phase.
