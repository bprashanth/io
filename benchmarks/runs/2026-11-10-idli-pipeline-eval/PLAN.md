# Idli pipeline eval: plan (2026-11-10)

Status: plan written, waiting for the owner's go. Follows the 9B benchmark (branch `idli-9b-bench`,
`benchmarks/runs/2026-11-10-idli-9b/REPORT.md`), which tested only the private model answering from forms
that already existed. This eval tests the whole journey for one file at a time, with no upfront Drive index
(see `todos/idli-insights/p1/file_by_file_index.md`).

## What it should tell us
1. **Where to invest:** in better fake data (code), in more ways to make fake data, in a model for wording
   answers, in a model for setting the form's dials, or in nothing yet.
2. **Whether the architecture works end to end:** fake copy → Claude learns → checks run on the real file →
   working copy → questions → bounce to Claude → charts.
3. **Whether more models are needed, and where:** the chat, setting the dials, wording answers, fake data.
4. **Whether to try newer designs:** Claude planning on a redacted question, without a fake copy for every
   question.

## Method
- **Plant the mess and keep a manifest.** Generate files that start clean, inject known kinds of mess, and
  record every injected cell and rule in a manifest. Every score is then recall and false alarms per kind of
  mess, with no hand labelling. Generators: totalrecall's synthetic tables, and Codex / cursor-agent writing
  sheets in the style of the owner's real ones (the cestrum field-vars workbook and the files the owner adds).
  Kinds of mess:
  - **Layout:** sections stacked under each other with repeated headers, sub-heading rows, totals rows, merged
    cells, notes in data cells, empty spacer rows and columns, several tables on one tab.
  - **Values:** units in cells ("12 cm", "approx 12"), "n/a" and "pending", mixed date formats, typos of codes,
    team codes not in the key (UKS1, Fern), wrong casing, numbers outside a plausible range, duplicate IDs.
  - **Between columns and tabs:** DBH 2 filled without DBH 1, a density tab not matching the tree count, a key
    tab missing a species, a total that doesn't add up.
- **Teach on the real file as well as the fake copy.** Synthetic files have no privacy issue, so Claude can learn
  each one twice, once from its fake copy and once from the real (synthetic) file. The difference is the exact
  cost of faking, and it says whether to invest in fake data (question 1).
- **Give each stage the perfect input (an oracle).** Run each stage with the correct output of the stage before
  it, for example correct dials into `file_ask` or the correct skill into cleaning. Errors that remain belong to
  that stage. This answers question 3 without guessing.
- **Real data stays local.** The owner's real files run only on the DGX or laptop, and Claude only ever sees fake
  copies, as in the product.
- **Workers:** Codex and cursor-agent build generators, manifests, scripted users and reference answers. A
  benchmark subagent runs and judges. The main session only reviews and reports.

## Evals (run order: E6, E7, then E1-E3, then the rest)

### E6. Cleaning output on messy data
Run the planted-mess files through teaching (the skill), then the checks on the real file, then `working_copy`.
Score:
- red cells against the manifest (recall, false alarms);
- one comment per kind of problem, with correct and readable wording, on a cell that really has that problem;
- red cells clear once fixed;
- skipped rows (repeated headers, totals) are skipped and not flagged.
No model runs in this step: the checks are code Claude wrote while teaching, and the comment wording is a code
template. Comments are written per kind of problem, not one per bad cell. Layout problems (stacked sections)
are handled in the skill, which Claude writes while teaching, and are covered here only as "rows skipped
correctly".
Also fix the benchmark itself:
- held3 r03 steps 3-4 ask for paid hardware claims that the fixture doesn't have, so every model fails them;
- a reply that drops the "All" total is failed even when every number given is right; score totals separately;
- add a guard against cards shown where the person should type.

### E7. Fewer tools, by phase
Today the 9B chooses from 29 tools. Scope Idli to conversations about Drive spreadsheets and offer only what
the current phase needs:

| Phase | Tools |
|---|---|
| Get the file (link or upload) | `start`, `file_get`, `file_open`, card |
| Learn (Claude) | `teach_file`; the card's yes sends the file |
| Clean | `working_copy`; the card "I've fixed it, go on" continues |
| Analyse | `file_ask`, `chart_request`, `chart_show`, `teach_file` (bounce), card |

Gone: Gmail, live Drive search, indexing, doc and Google Sheet readers, list tabs, progress, gap reports,
dashboard, and the learned-files tools (they have their own page now).
Steps that only follow a click (send to Claude, make the working copy, ready) run from the card itself, so the
model doesn't have to remember to call them.
Two versions:
- **(a) Hard phases:** only that phase's tools are listed.
- **(b) Soft phases:** the same small set throughout, with the server answering "not now: <what to do>" when a
  tool is used in the wrong phase.
Both keep an exit from every phase ("skip cleaning, just ask"; "clean it after all"). Score: held3 and the other
chats, cards shown where the person should type, steps per chat, seconds. Check whether Claude Code picks up
a changed tool list in the middle of a chat (MCP `tools/list_changed`). If it doesn't, only (b) works in the
product.

### E1. How realistic is the fake copy
Compare each planted-mess file with its fake copy (`filekit.mock_column`), per kind of mess in the manifest:
does it survive as the same kind, though not in the same cell? Check per column: kind, share of blanks, junk
values, range, number of categories. Check per relationship: which-blank-when, counts between tabs, keys present,
unique IDs. Known losses: numbers are drawn at random inside the range, so links between columns and the shape
of the distribution disappear. Fix only what a real check needs, in code, and rerun E2.

### E2. Teaching from the fake copy, judged on the real file
Run the teach flow headless (Claude Code with the teach-file skill). A scripted user answers the cards from the
file's documentation, never from its data. Teach each file twice, once on the fake copy and once on the real
(synthetic) file. Score each skill on the real file:
- the checks: recall per kind of mess, and false alarms per 100 rows;
- the measures: they compute and match the reference;
- the layout: handled;
- the cost: minutes and number of cards.
The gap between the fake-taught and the real-taught skill is the number that matters.

### E3. Bounce to Claude, end to end
Scripted chats with questions the form can't answer (a new measure or filter) and charts it can't draw. Score
every hop:
- the 9B routes to Claude;
- Claude extends the form on the fake copy;
- the person comes back;
- the same question is answered correctly from the form.
Also count wrong bounces (the form could have answered), bounces that don't come back, and the minutes taken.

### E4. Wording the answer
Today the form's answer is a code template, and the chat model rewords it (losing totals in about a third of
relays under Claude Code). Compare:
- A. the template shown as is, plus at most one line from the model;
- B. today's rewording;
- C. a friendlier code template ("Native trees in Karian Shola average 15.57 m tall (67 trees).").
Score: numbers lost, numbers invented, UX grade. Use the oracle dials, so that only the wording varies.

### E5. Charts from fake to real
For 10 chart requests, Claude writes code on the fake copy, and it runs on the real data inside the wall. Score:
it runs, it shows what was asked, every number traces to the data. Note code that breaks only on real data
(longer labels, more categories, odd dates).

### E8. Finding files from learned files only
After E2 has taught 10-15 files, search their context cards ("the cestrum file", "last year's household
survey", "which files have plot-level counts") with plain code. Score: right file first, and in the top three.
Answers whether finding needs a model (the 30B, or any) once the index is only learned files.

### E9. Help with setting the dials (only if E7 leaves dial errors)
- Restrict the model's output to valid ids and values (llama.cpp JSON schema built from the form).
- Match names in code first (question words → filter values), so the model only picks the measure and
  breakdown.
- Score: dial accuracy on the 44 single questions, and held3.

### E10. Later: Claude plans on a question redacted using the data
Personal columns are marked while teaching. Their real values become tokens (`beneficiary_name_14`), phones,
emails and IDs are removed by patterns, and GLiNER looks only for person names, at a strict threshold. Compare
with the GLiNER-only version (75-77% held3).

## Models in each eval
The chat and dial-setting models: the 9B alone (the free tier, fully local), Muse 30B (the baseline), and
9B + Ling-3.0-flash. Inkling-Small (276B total / 12B active) is kept open as a hosted option for setting the dials.
Teaching and charts use Claude (Opus or Sonnet as in the product). The scripted user is Haiku.

## Outputs
`REPORT.md` here, with one table per eval and a closing section that answers questions 1-4 directly. The
chronology gets a line per finding, and a field note follows once the evals have run.
