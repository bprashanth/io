# Idli pipeline eval: report (E6, E7; 2026-11-10)

Plan: [PLAN.md](PLAN.md). The subject is the free tier: a local 9B (Q5 on the DGX) with the split (a separate
call to itself that sets the form's dials, inside `file_ask`). Muse 30B is the baseline only. E8 and E10 were
skipped on the owner's word; E1-E5 come next.

**In one line:** on new messy files, learn → check → working copy worked end to end with no person in the loop
(about 72% of planted mistakes found, very few false alarms). On fresh chats, the local 9B with the split matched
Muse with soft phases (86% vs 86%). Hard phases cost 7 points.

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

## Surprises
- **Teaching with nobody in the loop** worked first time on all 5 files.
- **Run-to-run noise:** the same file taught twice gives results 1-4 mistakes apart, and team-code handling
  flipped between runs.
- **Hard phases lost:** a hard wall turned a wrong guess into a lost question.

## Not measured yet
- **Claude's side:** E1 (fake-copy fidelity), E2 (including teaching on the real file as the upper bound) and
  E3 (the bounce to Claude).
- **Answers and charts:** E4 (wording) and E5 (charts).
- **The Claude Code harness:** E7 ran in the lean harness only.
- **Muse on the other chats:** it ran on held3 only this round. Its other-chats number is last round's run,
  rescored.

## Cost
- About 5 hours wall clock, including a session restart.
- About $6.70 of API-equivalent Claude cost for teaching, plus cents for Haiku. The 9B was local.
- Muse was lightly used (10 chats). Codex wrote the generator (about 57k tokens).

## For the owner to decide
1. **Mark or read silently:** mark units in cells, casing and "n/a", or keep reading them quietly as now?
2. **Instruction rows:** keep a template's instruction rows (descriptions, MANDATORY/OPTIONAL) unchanged in the
   fake copy, the way repeated headers already are? Recommended: yes.
3. **Info blocks:** read key/value blocks above a table, such as the contact details?
4. **Phases:** ship soft phases? Recommended: yes.

## Paths
Everything is under `benchmarks/runs/2026-11-10-idli-pipeline-eval/`:
- `generators/`, `manifests/`, `fixtures/` (with the files' notes);
- `harness/`: `teach_run.py`, `e6_score.py`, `e6_table.py`, `linkfirst.py`, `e7_*`, `serve9b.sh`;
- `variants/e7-*`;
- `results/e6`, `results/e7-local12`, `results/e7-muse`, `results/before`.

The local 9B server is stopped; `harness/serve9b.sh up` restarts it.
