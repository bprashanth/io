# Plan: evaluate the fake-twin flow end to end (2026-11-10)

The 9B benchmark (branch `idli-9b-bench`, `benchmarks/runs/2026-11-10-idli-9b/REPORT.md`) tested only the
private side: a chat model answering questions from forms that already existed. The forms were written by a
script in the shape Claude produces. Claude's side (learning a file from a fake copy, writing checks, extending
the form, drawing charts) was not tested there. This plan tests the whole loop, starting with the simple
version below, before anything cleverer (Claude planning on redacted questions comes last, step 7).

## The flow being tested

1. **Fake copy (code, no model).** `filekit.mock_column` turns the real sheet into a copy with fake values:
   same tabs, columns and row count. It keeps the kinds (number, date, category, ID, email, phone, long text), number
   and date ranges, blank cells, junk such as "n/a" or a second date format, ID shapes ("R-2025-0412"), and the
   same fake for the same real value across tabs, so joins still work. Category labels become "Village A", "Village B"
   unless the user ticks them as not private (statuses, item types). Coordinates move to (0, 0).
2. **Claude learns the file on the fake copy, with the user.** Cards in the Claude chat: what a row is, checks,
   clean-ups, the file's words and measures. Output: a skill (the form's dials, checks, fixes).
3. **Cleaning runs on the real file (code, no model).** The checks run locally. After a yes, `working_copy` puts a
   copy next to the original with red cells (conditional formatting from the same checks) and one Drive comment
   per kind of problem. The comment text is a code template.
4. **Questions go to the private model (9B, Muse, ...).** Three calls per question: the chat model passes the
   question in full words to the file-question tool (`file_ask`); inside it, a second call sets the form's dials;
   code computes; the chat model writes the reply. Tested in the 9B benchmark: 9B alone 79-81% on fresh chats
   (held3), Muse 83%.
5. **Bounce back to Claude when the form can't answer.** Two routes:
   - a chart the form can't draw, or "suggest analyses": a new fake copy plus the question, as typed, goes to
     Claude (`chart_request`). Claude writes chart code on the fake copy; Idli reruns it on the real data inside
     bubblewrap and shows it (`chart_show`).
   - a question with no measure or filter for it: the question plus what was missing goes to Claude
     (`teach_file` with `missing`). Claude extends the form; the user comes back and asks again.
   For this POC the question goes to Claude unredacted. Only the data is fake.

## What hasn't been measured yet

- **How faithful the fake copy is.** Number columns are drawn at random inside the real range, so the shape of
  the distribution and the relationships between columns are lost (density = tree count per plot; DBH 2 only
  when DBH 1). A check Claude writes for such a relationship either fires on every fake row or can't be seen at
  all. Outliers survive only as the column's min and max.
- **How good Claude's skill is when judged on the real file.** Do its checks find the real problems without
  flooding false alarms? Do its measures compute on real values?
- **The bounce loop from start to finish.** The 9B benchmark only checked that the 9B shows the right card and
  sends the request. It never checked that Claude extends the form, that the user comes back, or that the
  re-asked question is then answered.
- **Charts from fake to real.** Does code written on fake values run, and look right, on the real values?

## Evals, in order

### E1. Fake-copy fidelity (code only, cheap)
For each test file (the 12 benchmark fixtures with planted mistakes, plus the real cestrum workbook on the
DGX/laptop only), compare real against fake:
- per column: the kind, the share of blanks, the share of junk values, the min and max, and the number of categories;
- relationships Claude has needed so far: a column blank when another is filled, a count matching rows in
  another tab, an ID unique, a value present in a key tab;
- planted mistakes: is each kind still present in the fake copy (same kind, not the same cell)?
Output: a table per file, which lists what survives and what is lost. Fix in `mock_column` only where a real
check needs it (for example, keep "blank when the other is blank" patterns and keys that exist in a lookup tab).

### E2. Teaching quality, judged on the real file
Run the real teach flow headless: Claude Code with the teach-file skill on the fake copy. A scripted user
(Haiku or Codex, given the file's documentation, never its data) answers the cards. Then run the skill on the
real file and score:
- the checks: the share of planted mistakes found, and false alarms per 100 rows;
- the measures: they compute, and they match a hand-built reference (the `harness/make_skills.py` skills);
- the minutes it takes and the number of cards.
Run twice: once on today's fake copy, once on the E1-improved copy. This is the number that says whether the
twin is representative enough.

### E3. The bounce loop
Scripted chats where the question needs a measure the form doesn't have (e.g. "cestrum share by girth class",
"average delay between visit and payment"):
the 9B routes to `teach_file` → Claude extends the form on the fake copy → the user returns → the same question
is answered from the form. Score each hop, and the final number against the reference. Also count wrong bounces:
questions the form could answer but which went to Claude anyway.

### E4. Charts from fake to real
For 10 chart requests, Claude writes code on the fake copy, and it is run on the real data in the wall. Score:
it runs, it shows what was asked (judged), and no value on it is invented (every number on the chart traces to
the data). Note when code that works on fake data breaks on real data (labels longer than the fakes, more
categories, odd dates).

### E5. How answers are worded
Today the form's answer is a code template ("Average Height (m); Fragment is Karian Shola; Native or alien is
Native. 15.57."), and the chat model rewords it. That rewording drops totals and sometimes paraphrases numbers.
Compare on the benchmark chats:
- A. the template is shown as is, in its own block, and the model adds at most one line (a follow-up offer);
- B. today's rewording;
- C. a friendlier template (code): "Native trees in Karian Shola average 15.57 m tall (67 trees)."
Score: numbers lost, numbers invented, UX grade. Expect A or C to win on accuracy; keep B only if the UX
grade clearly drops without it.

### E6. Benchmark fixes found on the way
- held3 r03 steps 3-4 ask for paid hardware claims, but the fixture has none: every model fails them, Muse included.
  Fix the fixture or the question.
- The scorer fails a reply that drops the "All" total even when every number given is right: score totals
  separately.
- Most of the remaining 9B failures were a card shown where the user should type. Add a guard for it, and remeasure.

### E7. Later: Claude plans on a redacted question (no fake copy for every question)
Replace GLiNER's guessing with redaction driven by the data:
- During teaching, Claude marks the personal columns (name, phone, email, address, PAN, Aadhaar, household ID,
  free-text notes) on the fake copy, and the user confirms them on a card.
- Locally, every real value in those columns gets a token named for its column and position (`beneficiary_name_14`).
  In the question, replace any match: whole words, small misspellings allowed. Remove phones, emails, PANs and
  Aadhaar numbers with patterns. Leave everything else alone (villages, seasons, species, items).
- As a backstop, GLiNER looks for person names only, with a strict threshold, to catch a name that isn't in the
  file.
- Rerun the Claude-plans variants (Haiku and Sonnet, with shape-only backtrack) on the same chats. Before:
  75-77% on held3, with only a fifth of questions leaving unredacted.

## Who does what
- **Codex / cursor-agent:** write the E1 comparison script, the E3 and E4 scripted chats and their reference
  answers, and the E6 fixture fix.
- **Benchmark agent:** run E2-E5 and judge them.
- **Real data:** only on the DGX or laptop. Claude only ever sees fake copies and, in E7, the redacted question.

## Not doing
- No new small skills written to max the benchmark. Fix things in the flow, not per question.
- No dense 27B models for the free tier.
