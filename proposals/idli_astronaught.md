ASTRONAUT MODE — next layer on the kernel. Go one level deeper on the harness
benchmarking: instead of a harness inside io, the big model
becomes a toggled skill-compiler ON TOP of the kernel - that can possibly run within a harness. 

FRAMING:
- io is the kernel: vault, guard, loader+hints, DuckDB, receipts manifest.
  Every UI or agent is a shell speaking io's tool interface. No shell ever
  runs inside the kernel; nothing in this task touches the guard or vault.
- A "skill" is a declarative, reviewable text artifact the kernel compiles
  deterministically: these are the things typically accepted by all harnesses. 

THE FEATURE (single toggle, off by default):
When astronaut is ON, the user gets two abilities:
1. COMPACT: a button that sends the local interaction log (questions, SQL,
   fixes, retries, escalations — no raw rows; log is already token-side) to
   the 27B (or frontier, per the reach dial) and gets back PROPOSED SKILLS
   as cards: name, when-it-applies, what-it-does, the artifact itself
   (hint/mapping/template). User edits inline, approves or discards.
   Approved skills compile into the kernel and affect subsequent answers
   immediately. 

This compaction itself is User-triggered only for now; leave a stub for auto-trigger
   (every ~100 questions or log-size threshold) but do not wire it. User triggered meaning a button, or user saying something like look at the usage and propose skills.. 

2. AUTHOR: an "add skill" wizard — plain-language guided form: when should
   this apply (example question), what should io do (hint / mapping /
   template), preview against a real file, save. Same card format as
   compaction output so editing is one code path. Trigger description is important. 

Additional featur: SEE WHY: parse/trigger transparency. Loader decisions and skill firings
   enter the receipts manifest and render as "io read this as: 3 tables,
   header at row 2, amounts in paise (skill: razorpay-signature fired)".
   Every interpretation is one-click correctable; a correction saves as a
   file-scoped skill. Ships with astronaut, visible in the demo.

No git/sync/sharing yet. Local skills dir, plain files, that's it. This is
a PoC to demo at the event.

TEST:
Replay the stage-4 story as an eval. Take the ngo-corpus logs from a
BARE kernel (no hand hints), run COMPACT, apply the machine-proposed
skills, re-run the 22 questions. Report:
- accuracy lift from compacted skills vs the 20/22 hand-hint ceiling
- how many proposals were correct / harmful / redundant (human-grade each)
- compaction cost+time on 27B vs frontier
- one iteration loop: does a second compact after more questions add
  anything or start proposing junk
Also negative-test: a proposed skill must never contain a real value from
the vault map — assert against the map like the egress guard does.

DONE = toggle in UI, compact->cards->edit->approve->takes effect, wizard
works end to end on one synthetic mirror, benchmark table in
benchmarks/astronaut/, chronology entry. Astronaut is additive behind the toggle so functionally speaking what's already decided on the the main demo of the event should continue work as well as it does against the io kernel. 

SKILL MODEL (locked — two layers, no sub-tiers):
- KERNEL (code): universal structure handling only. Domain claims are
  forbidden here; if a hint asserts anything about meaning (currency, which
  row is "the answer", what a column denotes), it cannot live in the kernel.
- SKILLS (one class): declarative claim + trigger text artifacts. A trigger
  can scope to a dir, a file/file-hash, or a described qualification
  ("matches Razorpay export signature", "FHIR-shaped health data", "our
  org's Kobo exports"). We are deliberately NOT creating sector/org/file
  sub-tiers — too early to be prescriptive. The requirement is only that
  the trigger is described precisely enough to fire correctly; the misfire
  suite is the enforcement.
- Skills never contain data values (assert every
  skill against the vault map, same mechanism as the egress guard).

EVENT FRAMING:
- Main io demo: the KERNEL on generic data. Universal structure handling
  lives in the loader as code — block splitting, multi-row/merged headers,
  header drift, long-numeric-IDs-stay-text. No domain claims, no triggers,
  no skills needed: this is what makes an unknown participant file work on
  first contact.
- Final segment: ASTRONAUT — how io extends itself. This is the only place
  the harness appears, and the only place skills are discussed.

A POSSIBLE EVENT DEMO (final segment, ~10 min): unknown file works via kernel alone →
a deliberately tricky file parses wrong → SEE WHY shows the misread →
one-click correction becomes a file-scoped skill → flip astronaut on, run
COMPACT on the day's accumulated log, show the consent popup, approve one
card → re-ask, watch the trigger receipt fire. Close on the line:
"io does not self-learn; it asks permission to remember."

ROLE OF HARNESS 

This is something we will need to evaluate. It feels like what we should do is start using a harness when the user switches to astronaut mode. This seems logical because of 1. Shell access could be useful in skills, like if a user says chunk up large files and process, it's fairly easy i would assume to use a shell even on windows. But it's possible that skills + llm itself is enough and that adding a harness just makes things more brittle. Not sure but I would suspect a harness like deepseek makes things better/more flexible not worse.

If the harness turns out to be useful, then what we'd want is to still apply the shield to the harness. While this doesn't need to work for the demo (it's just a poc) it seems possible in a few different ways I'll document here..

Extract the interceptor into a local OpenAI-compatible proxy (LiteLLM
  middleware or standalone). ALL model traffic from ALL shells (io UI,
  Antigravity plugin, harness) goes through it. One chokepoint, one
  egress log, one monitor. Like I said, this doesn't need to happen now, just outlining a later phase. 

If we don this, then astronaut mode is a time when the user just converses with the harness. And the harness respects the range setting per usual - if it's laptop only, it consults the local model straight otherwise it consults the relevant range. But FOR COMPACTION it requests an explicit consent from the user to choose one or the other model (either t4gc or frontier). 

This is why having a user trigger button for skill production (in either mode, author or compaction) helps.. it shows a consent popup:
   "A remote model will help write your skills. It will see your questions
   and queries — never your data values." Edit inline, approve or discard.
   Approved skills take effect immediately. 


A couple of questions that we probably need to figure out to guide this design 
1. Harness or not (and which, deepseek, Hermes, codex cli with remote url to model..etc.. you will probably find a Hermes container in this machine fyi so you don't need to reinvent there)
2. Current kernel - does it have anything not meant for kernel?
3. Telegram shell - that will be probably the most important shell to showcase so how can we test it out and use it for further evals?
4. Does telegram force the use of astronaut? (Meaning the telegram protocol istr - just handling chats etc - was pre built into harnesses like open claw and Hermes). Deep seek also seems possible via composio. 
