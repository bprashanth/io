# Idli pipeline eval: report (E6, E7, E1, E2, E3; 2026-11-10/11)

Plan: [PLAN.md](PLAN.md). The subject is the free tier: a local 9B (Q5 on the DGX) with the split (a separate
call to itself that sets the form's dials, inside `file_ask`). Muse 30B is the baseline only. E8 and E10 were
skipped on the owner's word; E4 and E5 come next.

**In one line:** on new messy files, learn → check → working copy worked end to end with no person in the loop
(about 72% of planted mistakes found, very few false alarms). On fresh chats, the local 9B with the split matched
Muse with soft phases (86% vs 86%). Hard phases cost 7 points.

**E1-E3 in one line:** learning from the fake copy is as good as learning from the real file (85-90% vs 81% of
mistakes found, within run-to-run noise), so better fake data is not where the money goes. The trip to Claude and
back works mechanically (sent 23 of 24 times, back 22 of 23, in about a minute, about $0.15 each, no wrong
bounces), but Claude's chart code gave exactly the right numbers on the real file only about half the time. The
misses come from how the chart code reads the data, not from the 9B.

## E6: cleaning output on messy files

### Setup
- **Files:** a generator (written by Codex) builds 5 invented spreadsheets clean, plants 209 known mistakes, and
  records each in a manifest (`generators/`, `manifests/`). Two of the files follow the owner's attached
  templates:
  - the germination protocol;
  - a fake of the tax questionnaire. It uses only the tab names and header wording. The original, its file name
    and its contact cells were never copied, committed or sent to Codex.
- **Notes per file:** half a page, written the way a team lead would explain the file.
- **Pipeline:** the product's real one, run headless (`harness/teach_run.py`).
  1. Idli makes its fake copy.
  2. Claude Code (Sonnet) learns the file from it with the teach-file skill. Haiku plays the file's owner and
     answers the cards from the notes only, never from the data.
  3. The checks Claude wrote run on the real (synthetic) file.
  4. `working_copy` builds the marked copy: red cells and one comment per kind of problem.
  5. The scorer (`harness/e6_score.py`) sets every planted cell to its right value and checks again.
- **Repeats:** each file was taught twice.

### Results

| File | Mistakes found (run 1 / run 2) | Layout rows skipped | False alarms |
|---|---|---|---|
| Tree plots (stacked transects, 4 tabs) | 23/36 · 24/36 | 19/19 | 3 · 0 |
| Germination protocol (owner's template) | 21/36 · 21/36 | 7/9 | 0 · 3 |
| Household survey | 28/33 · 25/33 | – | 15 · 12 |
| Tax questionnaire fake | 31/35 · 27/35 | 8/10 | 2 · 2 |
| Field visits | 15/21 · 18/21 | 4/4 | 0 · 0 |
| **All** | **118/161 (73%) · 115/161 (71%)** | **38/42** | **20 · 17, in 3,378 rows** |

- **Found by whether the notes mentioned them:** 79% of rules the notes stated; about 57% of mistakes no note
  mentioned.
- **Cost:** 2-11 minutes and 3-6 cards per file. About $3 of API-equivalent cost per run of all five files.
- **The working copy:**
  - The marks are live: conditional formatting clears a cell's red once it's fixed (11 static cells in all).
  - Comments are about one per kind of problem.
  - After every planted cell was fixed, all marks cleared in 9 of 10 runs.
- **The household false alarms** are knock-on effects, e.g. both copies of a duplicated ID get flagged.

### Caught every time
Out of range, blanks in required fields, future or impossible dates, text in number columns, codes missing from
the key, a key missing a species, end date before start, and every layout row: repeated headers, sub-headings,
totals, spacers, merged headers.

### Misses, in three groups
1. **Read correctly instead of marked.** "Rs. 1,200", "approx 12", mixed date formats and casing are turned into
   the right values by Idli's reader, so nothing is marked. "n/a" is treated as a blank. Whether these should also
   be marked is the owner's call.
2. **Checks Claude didn't write:**
   - counts across tabs (density vs tree rows): found 4 of 7 times, even though the notes said it outright;
   - totals that don't add up: 7 of 10;
   - duplicate IDs: 6 of 9.

   A last step where Claude ticks off each rule the owner stated would probably close most of these.
3. **The fake copy (E1 showing up early):**
   - **Germination instruction rows:** the template's description row and its MANDATORY/OPTIONAL row became junk
     in the fake copy ("approx 500", "SCIENTIFIC NAME (BOTANICAL) 2"), so Claude couldn't recognise them. Idli
     then read them as data and commented on them ("No.: 'OPTIONAL' isn't a number").
   - **The contact block above the table is never checked:** Idli reads only one table per tab.
   - **Team codes:** UKS1 and Fern were accepted in one run and flagged in the other. The household casing went
     the opposite way between runs.

### Fixes to the benchmark
- **held3 r03:** it asked about paid hardware claims, which the file doesn't have; it now asks about approved
  ones (6 rows).
- **Totals:** the "All" total is now scored on its own.
- **Invented cards:** a guard allows a card only when a tool handed one over. It fired 4 times.

## E7: fewer tools (local 9B with the split, on the 12 shipped tools)

### Setup
- **The product as shipped:** `oss-desktop-eval` (94570b4, 2da8988) was merged first, so this is link first with
  no file search.
- **Chats:** 6 of the 40 were find-only, learned-files or Start here chats, and were dropped. 34 remain, each
  first request carrying the file's link.
- **Versions:**
  - **(a) Soft:** all 12 tools listed all the time; a tool used at the wrong moment answers "not now".
  - **(b) Hard:** only the current step's tools are listed (get the file, learn it, clean it, analyse it).
- **Runs:** 2 repeats of each version, 136 chats. The 9B ran fully local, 4 at a time. Muse ran only as the
  baseline.

| Setup | Fresh chats (held3) | Other chats | Question steps right, held3 / other | Seconds per step |
|---|---|---|---|---|
| Before: local 9B + split, old 29 tools (rescored with the fixed scorer, 1 repeat) | 85% | 83% | 74% / 70% | 12-19 |
| **Soft, 12 tools** | **86%** | **80%** | **78% / 77%** | 18-20 |
| Hard, 12 tools | 79% | 77% | 67% / 69% | 19 |
| Muse, shipped product | 86% | 86% (last round, rescored) | 85% / 83% | 29-46 |

The r03 steps 3-4 are left out of every row, so all rows count the same steps.

- **Soft phases** are as good as before or a little better on questions. On fresh chats they match Muse overall
  and are 7 points behind on questions, at about twice Muse's speed.
- **Hard phases cost 7 points.** The 9B sometimes picks "clean" when the person wants answers. In the clean step
  the question tool isn't listed, so it re-opens the file to switch, which shows another card, and the question
  gets lost. With soft phases a wrong guess costs nothing.
- **Claude Code can change the tool list mid-chat.** A probe with the real CLI (2.1.321) showed it re-reads the
  list when the server changes it (MCP `tools/list_changed`), and the model can call a new tool in the same chat.
  Hard phases are buildable; they just score worse.
- **The 9B's remaining failures are mostly on questions:** wrong dials or a reworded answer (about 22 steps), and
  no question asked after a card (about 17).
- **No made-up numbers** in any run.

### Set aside
- **Ling and the OpenRouter 9B:** not free-tier options. They were stopped mid-way, and the 13 chats that
  finished are kept in `results/ling-not-free-tier`.
- **9B with no split, a 9-tool variant, Muse with the split:** in `results/dropped`.

## E1: how realistic is the fake copy

### Setup
- **What's compared:** each of the 5 planted-mess files against the fake copy Idli makes of it
  (`filekit.make_mock`), kind of mistake by kind of mistake (`harness/e1_fidelity.py`, written by Codex).
- **The question per kind:** does the fake copy still contain that kind of mistake somewhere, so that Claude can
  see it and write a check for it? (Not the same cell; the fake values are drawn fresh.)
- **Two versions:** today's fake copy, and a fixed one with small code changes from Codex
  (`cowork/lib/filekit.py` behind `IDLI_MOCK_V2=1`, off by default). The fixes keep count mismatches between
  tabs, duplicate IDs, "n/a" placeholders, and template instruction rows (MANDATORY/OPTIONAL).

### Results (a "kind" counts once per file: 62 in all, 27 distinct kinds)

| File | Today | Fixed |
|---|---|---|
| Tree plots | 12/17 | 15/17 |
| Germination protocol | 5/12 | 7/12 |
| Household survey | 11/11 | 11/11 |
| Field visits | 7/9 | 7/9 |
| Tax questionnaire fake | 8/13 | 7/13 |
| **All** | **43/62 (69%)** | **47/62 (76%)** |

- **Still lost in both:** spacer rows, notes rows, merged headers, and info blocks (the contact block above a
  table). These are layout, and the fake copy rebuilds a plain table.
- **The tax "end before start" drop (8 → 7) is luck, not a regression**
  ([note](results/e1/tax_end_before_start.md)). The sale date ("12-Mar-22") isn't recognised as a date, and the
  fake copy doesn't keep start before end, so whether the mistake survives is a coin toss in both versions.
  Those are two real gaps (todos below).
- The fixed version's code changes pass the formkit, fixkit and new mock tests (`results/e1/*.log`).

## E2: teaching from the fake copy, judged on the real file

### Setup
- Same pipeline as E6 (Claude Sonnet teaches headless with the teach-file skill, Haiku answers the cards from the
  file's notes only). Every skill's checks are then run on the real (synthetic) file and scored against the
  manifest.
- **Three things Claude learned from:** today's fake copy (the two E6 runs), the fixed fake copy (one run), and
  the real file itself (one run; allowed only because these files are invented). Real-file teaching is the upper
  bound: what we'd get if faking cost nothing.
- **Counting follows the owner's decisions of 2026-11-10:** values Idli reads correctly anyway ("Rs. 1,200",
  casing, "n/a") and info blocks are counted in their own rows, not as misses.

### Results ([table](results/e2-logs/table.txt))

| Claude learned from | Mistakes found | Read correctly anyway (flag optional) | Info blocks | False alarms (3,378 rows) |
|---|---|---|---|---|
| Today's fake copy, run 1 | 91/104 (88%) | 27/51 | 0/6 | 20 |
| Today's fake copy, run 2 | 88/104 (85%) | 27/51 | 0/6 | 17 |
| Fixed fake copy | 94/104 (90%) | 23/51 | 0/6 | 35 |
| The real file | 84/104 (81%) | 18/51 | 0/6 | 16 |

- **Learning from the fake copy is not worse than learning from the real file.** With one or two runs each, the
  differences (2-4 mistakes per file) are the size of run-to-run noise. The real-file run happened to score lowest.
- **The fixed fake copy found the most, but doubled the false alarms,** 14 of the 35 in the tax file (Claude
  wrote stricter checks there). One run only; not enough to ship it on.
- **By kind:** out of range, codes not in the key, future dates, text in number columns, and keys missing a
  species are caught every time from every source. Duplicate IDs went from 6/18 (today) to 9/9 (fixed): that
  fix works. Counts across tabs and totals stay the weak spots in every version, including the real file: those
  are checks Claude doesn't write, not things the fake copy hides.
- **Info blocks: 0 of 6 everywhere,** because Idli reads one table per tab (the subtables todo).
- **Cost:** 2-11 minutes and 3-6 cards per file, as in E6.

## E3: the trip to Claude and back

### Setup
- **Chats:** 9 chats on 4 of the planted-mess files (`scenarios/e3.json`, written by cursor-agent). Each one
  opens the file by link, asks one question the form can answer (the control), then one it can't (a share, or a
  chart), says yes to the card, and asks the same question again after Claude is done.
- **The pipeline:** the shipped tools (soft phases, 12 tools). When Idli sends the request, the harness runs
  Claude Code (Sonnet) headless with the teach-file skill on Idli's fake copy, Haiku answering the cards from the
  file's notes (`harness/teach_run.py`). Then it puts the extended skill or chart code back in Idli's folder, as
  the product's watcher does.
- **Runs:** the local 9B twice and Muse once: 27 chats.
- **Strict scoring (`harness/e3_rescore.py`, written by Codex):** for a chart, the harness reruns Claude's chart
  code on the real file and reads the plotted values off the figure. Then they're compared with the expected
  answer.
- **The expected answers were checked one by one (`results/e3/refcheck.md`, Codex).** 6 of the 9 that cursor-agent
  wrote were wrong for what Idli should say: a "Total" row counted as a visit, casing not merged, wrong size-class
  edges, and unreadable values in the denominator. They were recomputed from Idli's own cleaned tables. Where a
  question was truly ambiguous ("clear 70%": ≥ or >), either reading counts.
- **One chat is left out:** "chart of disbursement by officer district" is something the form *can* draw. Both
  models drew it from the form, which is right. So it counts only towards wrong bounces.

### Results (8 chats per run that need Claude)

| Hop | 9B run 1 | 9B run 2 | Muse |
|---|---|---|---|
| Control question answered from the form, no bounce (9 chats) | 9/9 | 9/9 | 9/9 |
| Sent to Claude (the 9B called `chart_request`, card yes) | 8/8 | 7/8 | 8/8 |
| Claude finished teaching | 8/8 | 7/7 | 8/8 |
| Came back and showed the result | 7/8 | 7/7 | 8/8 |
| **Right numbers on the real file** | **4/8** | **4/8** | **4/8** |
| Right numbers, but one readable value shown as its own bar | +1 | +2 | +2 |
| Minutes in Claude per trip (median) | 0.7 | 0.5 | 0.6 |
| Claude cost per trip | $0.16 | $0.13 | $0.15 |

- **The trip works.**
  - Wrong bounces: 0 of 27.
  - Claude finished every time it was asked.
  - Most trips took under a minute. One took 18 minutes, and that chat's turn timed out.
- **Every "can't answer" question went as a chart request.** That includes plain share questions; no chat used
  `teach_file` with `missing`. The answer then comes back as a chart (with the numbers on the bars), not as a new
  measure in the form. So the same question goes to the saved chart next time, not to the form.
- **The 9B's two dropped trips:**
  - It said in text "I can create a chart, would you like that?" instead of calling `chart_request`, so no card
    appeared. This is the E7 failure again.
  - Claude took 18 minutes and the chat turn timed out.
- **Why the numbers were wrong (the same with the 9B and Muse, because Claude writes the code):**
  1. **Readable values split.** "cancel" and "Cancelled" are drawn as separate bars (0.4% and 33.2%). The
     owner's decision is to read them as one: 33.6%. The chart reads Idli's cleaned tables, and the skill has no
     rule merging status spellings. The form's own lookups do this; chart code doesn't get them.
  2. **Rows deleted.** In 4 of 6 household charts, Claude's code removed rows with a repeated ID before counting,
     which changed the ward and village shares. Nobody asked for that, and the person isn't told.
  3. **Wrong shape.** In one run Claude drew canopy by plot when the question was the overall share.
  4. Small: "12 cm" in a number column is blank in the chart's tables (the form reads it as 12). That's 0.3
     points on one bar.
- **Not measured:** extending the form (no chat took that path); the Claude Code harness (the lean harness was
  used, as in E7); a person judging whether the charts look right.

### Harness bugs fixed on the way
- **Results not written:** the runner wrote nothing and exited 0, because the 9B harness's `idli.setup()` changes
  into a temporary folder and `--out` was relative. Fixed in `harness/e3_bounce.py`.
- **API stalls:** a stalled Claude API call waited 30 minutes, which timed out 4 chats. Headless teaching now
  caps each call at 5 minutes, and those 4 chats were rerun.

## Surprises
- **Teaching with nobody in the loop** worked first time on all 5 files.
- **Run-to-run noise:** the same file taught twice gives results 1-4 mistakes apart, and team-code handling
  flipped between runs.
- **Hard phases lost:** a hard wall turned a wrong guess into a lost question.
- **The fake copy wasn't the weak point.** Claude found as many mistakes from the fake copy as from the real file
  (E2). In E3 too, the wrong numbers came from choices in the chart code (merging spellings, dropping repeated
  IDs), not from anything the fake copy hid.
- **Most of the expected answers were wrong:** 6 of 9 needed fixing, all in the same ways as the chart code
  (totals rows, casing, unreadable values). Writing the right answer for messy data is hard even for an agent
  with the real file.

## Not measured yet
- **Answers and charts:** E4 (wording) and E5 (charts). E3 already says a lot about E5: charts come back and run,
  but the reading of the data inside them is the weak spot.
- **Extending the form after a bounce:** no E3 chat took that path.
- **Repeats:** E2's fixed fake copy and real-file teaching ran once each.
- **The Claude Code harness:** E7 ran in the lean harness only.
- **Muse on the other chats:** it ran on held3 only this round. Its other-chats number is last round's run,
  rescored.

## Cost
- About 5 hours wall clock, including a session restart.
- About $6.70 of API-equivalent Claude cost for teaching, plus cents for Haiku. The 9B was local.
- Muse was lightly used (10 chats). Codex wrote the generator (about 57k tokens).
- **E1-E3 (2026-11-11):** E3 about 2.5 hours of wall clock over two attempts; about $3.50 of Claude for the 23
  trips. Codex wrote the E1 fixes, the E3 rescorer and the expected-answer check (about
  40k tokens each).

## Paths
Everything is under `benchmarks/runs/2026-11-10-idli-pipeline-eval/`:
- `generators/`, `manifests/`, `fixtures/` (with the files' notes);
- `harness/`: `teach_run.py`, `e6_score.py`, `e6_table.py`, `linkfirst.py`, `e7_*`, `serve9b.sh`;
- `variants/e7-*`;
- `results/e6`, `results/e7-local12`, `results/e7-muse`, `results/before`;
- E1: `harness/e1_fidelity.py`, `results/e1/` (`today/`, `fixed/` summaries);
- E2: `results/e2-logs/table.txt`;
- E3: `scenarios/e3.json`, `harness/e3_bounce.py`, `e3_all.sh`, `e3_rescore.py`, `e3_refcheck.py`;
  `results/e3/<run>/`, `results/e3/rescore.txt`, `results/e3/refcheck.md`; Claude's teaching per trip in
  `results/e3-logs/<run>/<chat>/teach/`.

The local 9B server is stopped; `harness/serve9b.sh up` restarts it.

## For the owner to decide (E6/E7: decided 2026-11-10, see the handoff)
1. **Mark or read silently:** mark units in cells, casing and "n/a", or keep reading them quietly as now?
2. **Instruction rows:** keep a template's instruction rows (descriptions, MANDATORY/OPTIONAL) unchanged in the
   fake copy, the way repeated headers already are? Recommended: yes.
3. **Info blocks:** read key/value blocks above a table, such as the contact details?
4. **Phases:** ship soft phases? Recommended: yes.

## For the owner to decide (E1-E3)
1. **Should Claude's chart code use Idli's reading of the file?** That means the same merged spellings,
   units and lookups as the form. Recommended: yes. It's the biggest cause of wrong numbers in E3.
2. **Should chart code be allowed to drop rows** (repeated IDs, outliers)? Recommended: no, unless the person agreed
   on a card. The chart then says how many rows it used.
3. **Ship the fixed fake copy (`IDLI_MOCK_V2=1`)?** It found the most mistakes (90%) but had twice the false
   alarms in one run. Recommended: not yet; one more run of E2 on it first.
4. **When a share question can't be answered,** should Claude add a measure to the form (answers in words, reusable
   by the 9B) instead of a chart? Today the models always ask for a chart.

## Answers to PLAN.md's four questions
1. **Where to invest:**
   - Not in better fake data first: learning from it is as good as learning from the real file today (E2).
   - The cheap fixes worth keeping are date order and dd-mmm-yy dates (E1).
   - Invest in **how Claude's code reads the real file:** chart code should use the form's reading of values, and
     must not drop rows on its own (E3).
   - Then in **teaching:** a last step that ticks off every rule the owner stated (E6/E2 misses: counts across
     tabs, totals).
   - Not in a model for setting dials or wording yet (E7 and E4 decide that).
2. **Does it work end to end?** Yes, mechanically, with the 9B:
   - fake copy → Claude learns → checks on the real file → working copy (E6);
   - questions (E7);
   - bounce → Claude → back → chart on the real data (E3: 22 of 24 trips came back).
   The weak links are the correctness of Claude's chart code on real data (about half exactly right) and the
   9B's occasional question in text where a tool call belonged.
3. **More models, and where?** Not for the chat: the 9B routed as well as Muse (control 18/18, sent 15/16) and
   wrong numbers came from Claude's code, not the chat model. Not for fake data. The open one is dial setting
   (E9), only if E4/E7 leave dial errors.
4. **Newer designs (Claude planning on a redacted question, without a fake copy per question)?** Not yet. Each
   trip already costs under a minute and about $0.15 with the fake copy, and the errors weren't caused by the
   fake copy. A redacted-question design wouldn't fix them.

## For the integrator
- **Chronology line (`docs/cowork-poc.md`):** 2026-11-11, DGX: E1-E3 results. The fake copy keeps 43 of 62 kinds
  of mistake (47 with the fixes behind `IDLI_MOCK_V2=1`). Claude taught from it finds 85-90% of mistakes vs 81%
  from the real file (noise-level). The trip to Claude and back works with the 9B (sent 15/16, back 14/15, 0
  wrong bounces, about a minute and $0.15 a trip), but the chart code gave exactly right numbers on the real file
  in 12 of 24 trips. The rest split readable spellings or dropped repeated-ID rows. E3 runner bug fixed (chdir into
  a temp home swallowed the results).
- **New todos:**
  - p1: chart code reads the file as the form does, and never drops rows silently (`chart_code_reading.md`);
  - p2: fake copy date order and dd-mmm-yy dates (`fake_copy_dates.md`);
  - p2: teaching ticks off every stated rule (`teach_rule_tickoff.md`);
  - p3: share questions become form measures rather than charts (in `chart_code_reading.md`, decision 4).
- **Product code touched on this branch:** only `cowork/lib/filekit.py` behind `IDLI_MOCK_V2=1` (E1, off by
  default), and the 9B harness's fixtures override (`IDLI9B_FIXTURES`).
