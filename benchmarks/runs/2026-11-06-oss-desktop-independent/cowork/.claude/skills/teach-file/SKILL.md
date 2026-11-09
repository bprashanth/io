---
name: teach-file
description: Teach Idli (the private model) how to read a spreadsheet and answer a question about it, or design a chart for a file Idli knows, by writing a file skill from a mock with fake data. Use when a message mentions teach/inbox or an Idli teaching request, when an Excel file has a hidden `_idli_teach` sheet, or when the user shares a mock spreadsheet and asks to "teach Idli" this file.
---

# Teach Idli a file

Idli runs a small private model on the user's real spreadsheets. It never computes numbers itself:
it runs **file skills**, which you write here. You only ever see a **mock**: same sheets, headers,
formats, blanks and messiness as the real file, with every value replaced by junk. Never ask for or
look for the real file.

## 1. Read the request
- A request folder is `teach/inbox/<id>/` with `mock.xlsx` and `request.json` (title, the user's
  question with names removed, `existing_skill`, column kinds). Run
  `.venv/bin/python -m lib.filekit inspect teach/inbox/<id>/mock.xlsx` for columns, types and messiness.
- A mock the user dropped in without a request: check for the hidden `_idli_teach` sheet with `inspect`.
  With no watermark, treat it as a mock if the user says so, and make the request folder yourself.
- If `existing_skill` is set, load `file-skills/<existing_skill>/skill.json` and **extend** it: the file's
  layout changed, or the form couldn't answer a question. Keep what still applies, update `headers` for
  a changed layout, add what's missing, and bump `version`. A version-1 skill (keys at the top level, no
  `tabs`) still works; convert it to `tabs` when you change it.

### A request with `missing` (Idli has a form; it couldn't do one thing)
Only that gap is open. Skip the mainline below except what the gap touches: say in one line what you'll add
(e.g. "I'll add sheet row numbers to the tree listings"), confirm it with one card ("Yes, add that
(Recommended)" / "Let's discuss"), extend the skill, test, and hand back. Ways to close common gaps:
- **Row numbers in listings:** set `"row_numbers": true` on the tab; listings then start with "Sheet row"
  (the spreadsheet row, as the checks number them).
- **A question the form's dropdowns can't express:** a taught query in `questions` (section 3).

## 2. Walk the user through it, one small step at a time
People can't weigh five topics in one message. Keep a running list of what you still need (the mainline below),
ask about **one step at a time**, and come back to the list after every answer or side discussion. Start each
step with where they are, e.g. "Step 2 of 5: checks". Skip steps that don't apply or are settled in an existing
skill. Don't write the skill until every step is answered.

Use a card (AskUserQuestion) when the answer is a choice: put your suggestion first as "(Recommended)" and say in
it what you'd do; the card's "Other…" box is where they write their own. Use plain chat when it needs talking
through: say "I'd like to discuss <topic>", go back and forth until it's agreed, then say what you settled and
move on to the next step. A card holds up to 4 questions, shown one at a time, and up to 4 options each.

The mainline:
1. **What a row is, per tab.** One question per tab (up to 4 per card): "Tab Visits: I think one row is one
   field visit. Columns: visit_date (date, dd/mm/yyyy), officer (name), amount (rupees), status (Done /
   Follow-up / Cancelled). Right?" Options "Yes, that's right (Recommended)" and "Not quite". On "Not quite"
   or a note in Other, talk it through in chat, then carry on.
   **Layout, if `request.json` has `layout`** (rows that aren't records: `repeated_header` rows that repeat the
   column names, e.g. a sheet made of sections pasted one under another; `subheading` rows with one label like
   "Transect 2"; `total` rows). Idli skips repeated headings by default and lists the others as problems. Say
   what you see and discuss it in chat, briefly: (a) keep the layout and skip those rows (set `"skip_rows":
   ["repeated_header", "subheading", "total"]` as fits), or (b) if a cleaner layout would help them (one table
   with a Transect column instead of sections, codes explained in their own tab), describe it as a suggestion
   for their next version of the sheet. Idli never changes their file; they decide. Don't push (b) on a sheet
   that works for them.
2. **Checks.** One card, multiSelect: "Which checks should I add? Tick all you want." Options are your
   suggestions (phone/email shape, dates that don't parse or are in the future, amounts that aren't numbers,
   required fields, allowed values, keys that must exist in another tab), at most 4 per question; use a second
   question in the same card for more. Then ask in one line whether they want to add any of their own; keep
   taking them, one per message, until they say that's all. For a code list (species, villages) checked against
   another tab: codes that recur but aren't in the list (e.g. "UKS1" for an unidentified species) are probably
   the team's own conventions; ask whether to accept them (add to `normalize` maps or the check's list) rather
   than flag every one. Every problem Idli finds gets a suggested fix or a note in the dashboard, which the
   person accepts or rejects; you don't need to write fixes.
3. **Clean-ups.** Same shape: a multiSelect card of what you'd tidy (spelling variants of one category, "Rs. 1,200"
   amounts, mixed date formats, header rows repeated mid-sheet), then "any others?".
4. **The words of this file.** One card question per decision that has clear options: what they add up or count
   (measures, with their names for them), which date is "the date", rules like "does 'paid out' mean Approved and
   Paid?", "leave out Rejected by default?", how tabs connect. Anything open-ended goes to chat.
5. **How you read their question.** Usually chat: "I'd like to discuss how I read your question: …". Agree it,
   then confirm in one line.

If they say "you decide" at any point, take your suggestions for that step and every step left, say in a short
list what you chose, and go on to writing the skill.

## 3. Write the file skill
Idli turns the skill into a **form** for the file: per tab, a list of measures, ways to break them
down, filters with the values in the data, date ranges and the rules you name. A person picks from
dropdowns, or Idli fills the same form from a typed question. So describe the file once, generally;
don't write one query per question. Every number column already gets Total and Average, every category
column a breakdown and filter, every date column month/quarter/year and a date range. You add what the
data can't tell: labels, the measures people actually use, rules, checks, lookups.

Write `file-skills/<id>/skill.json`. The `<id>` is a slug of the file's title. It is data only, never Python:
```json
{
 "id": "field_programme_tracker", "title": "Field programme tracker", "version": 1, "format": 2,
 "tabs": {
  "Visits": {
   "headers": ["amount_disbursed", "field_officer", "households_visited", "notes", "status", "village", "visit_date"],
   "summary": "One row per field visit.", "row_noun": "visits",
   "columns": {"visit_date": {"type": "date", "formats": ["%d/%m/%Y", "%Y-%m-%d"], "label": "Visit date"},
               "amount_disbursed": {"type": "number", "label": "Amount disbursed (Rs)"},
               "status": {"type": "category", "label": "Status", "values": ["Done", "Follow-up", "Cancelled"]}},
   "normalize": {"status": {"case": "title", "map": {"complete": "Done"}}, "village": {"case": "title"}},
   "validations": [{"column": "visit_date", "rule": "not_future", "arg": ["%d/%m/%Y", "%Y-%m-%d"], "message": "date in the future"},
                   {"column": "amount_disbursed", "rule": "number", "message": "amount is not a number"}],
   "measures": [{"id": "disbursed", "label": "Amount disbursed (Rs)", "sql": "sum(amount_disbursed)", "format": "inr"},
                {"id": "households", "label": "Households visited", "sql": "sum(households_visited)", "format": "count"}],
   "presets": [{"id": "completed", "label": "Completed visits", "filters": {"status": ["Done"]}},
               {"id": "not_cancelled", "label": "Leave out cancelled", "filters": {"status": {"not": ["Cancelled"]}}}],
   "date_columns": ["visit_date"],
   "lookups": [{"tab": "Officers", "on": {"field_officer": "name"}, "columns": ["district"], "prefix": "officer_",
                "labels": {"district": "Officer's district"}}],
   "hidden": ["notes"]
  },
  "Officers": {"headers": ["district", "email", "name", "phone"], "row_noun": "officers",
               "validations": [{"column": "phone", "rule": "phone", "message": "not a 10-digit phone"}]}
 },
 "history": [{"version": 1, "taught": "disbursement by district, completed visits, date ranges"}]
}
```
- **Tabs:** one entry per tab that matters, keyed by the tab name. A one-sheet file has one tab (a CSV's
  tab is called "csv"; give it the file's title as the key). `headers` is the slugged header set
  (copy it from `inspect`'s column keys); Idli recognises the file and each tab by it, even renamed.
- **Column names** are those slugs. After `normalize`, `date` columns are DATE and `number` columns are
  DOUBLE; unparseable values become NULL. `values` lists a category's known values: a new value later is
  reported to the user as a change in the file.
- **Measures:** `sql` is one aggregate over the tab's columns (`sum`, `count(*)`, `avg`, `count(*) FILTER
  (WHERE ...)`, `count(DISTINCT x)`), nothing else. Labels are what the user calls it.
- **Presets** are the business rules, as filters: `{column: [values]}`, `{column: {"not": [values]}}`,
  `{column: {"min": n, "max": n}}`.
- **Lookups** add another tab's columns to this one (`on` = {this tab's column: other tab's column},
  matched ignoring case). A key missing from the other tab is reported as a problem automatically.
- **group_by** (optional) adds groupings the defaults can't, e.g.
  `{"id": "size", "label": "Household size", "sql": "CASE WHEN members > 5 THEN 'Large' ELSE 'Small' END"}`.
- **Rules:** `required`, `number`, `date` (`arg`: list of formats), `email`, `phone`, `in_list` (`arg`:
  values), `range` (`arg`: `[min, max]`), `regex` (`arg`: pattern), `not_future` (`arg`: date formats).
  If no rule fits, you may add a *generic* rule to `RULES` and `excel_formula` in `lib/filekit.py`, with a
  test. Tell the user plainly, because the change affects every file skill. Each rule becomes an Excel
  formula column in Idli's "- checked" copy.
- Only if the question truly can't be a form spec (it needs two separate aggregates combined, a join
  the lookups can't express, a running total), add a taught query to top-level `questions`:
  `{"id", "ask", "tab", "params": {...}, "sql": "... FROM {{table}} WHERE x BETWEEN {{start}} AND {{end}}"}`.

## 4. Test against the mock
- Copy the mock to `file-skills/<id>/mock.xlsx`.
- Write `file-skills/<id>/tests.json` with the user's question as a form spec, plus one or two more:
  `[{"tab": "Visits", "spec": {"measures": ["disbursed"], "group_by": ["officer_district"], "preset": ["completed"],
  "date": {"from": "2026-07-01", "to": "2026-09-30"}}, "expect": [["District A", 21950.0], ["District B", 14075.0]]}]`.
  Each expected row lists the breakdown values then the measures, in order. Spec keys: `measures`,
  `group_by` (ids, up to 2), `filters`, `preset`, `date` (`column` with `from`/`to` or a `period` such as
  `last_month`, `this_financial_year`), `sort` `{by, dir}`, `limit`. Compute `expect` **independently**
  with pandas on the mock (apply the same clean-ups), not with Idli's code.
- Run `.venv/bin/python -m lib.filekit test file-skills/<id>` until it prints `ALL PASSED`. It also
  checks the mock is recognised, the contract test passes and every tab's form builds.

## 5. Hand back
- Write `teach/inbox/<id>/done.json`:
  `{"skill": "<id>", "version": N, "summary": "<title> v<N>: <what the form can now answer>"}`.
  Idli's chat is told automatically.
- Tell the user in two lines what Idli's form for this file now offers, and that their Idli chat will
  continue.
- Then ask with a card (AskUserQuestion), header "Idli", question "Teaching is done. Go back to Idli to see
  your answer?", options "Yes, back to Idli" and "Stay here". If they pick yes, create the empty file
  `teach/inbox/<id>/go_back` (`touch` it). Idli's watcher outside this chat sees it and switches the app; don't
  try to switch it yourself (this chat can't reach the app). Then say "Switching you back to Idli."

## Chart requests (`request.json` has `chart`)
Idli already has a form for this file (`existing_skill`). The person wants a picture: `chart` is what they asked
for, or empty when they want you to **suggest** analyses. You design the chart on the mock; Idli runs your code on
the real data on their computer and shows it in their chat and dashboard. Don't change the skill unless the chart
needs it (then bump `version` and run the tests as usual).
1. Load the skill and look at the mock through Idli's own cleaned tables:
   `.venv/bin/python -c "import json; from lib import chartkit; s=json.load(open('file-skills/<skill>/skill.json')); s['_dir']='file-skills/<skill>'; t=chartkit.tables('teach/inbox/<id>/mock.xlsx', s); [print(k, list(v.columns), len(v)) for k, v in t.items()]"`
2. **Agree what it shows, one card.** For a question: "Here's how I'd draw it: <chart type> of <measure> by
   <breakdown>, <filter>, <sorted/top N>. OK?" options "Yes, draw that (Recommended)" / "Let's discuss". For a
   suggestion request: a multiSelect card of 3-4 analyses that fit this data (what it would show and why it's
   useful, e.g. "Cestrum share of trees per plot: where the invasion is densest"); they tick what they want.
3. **Write each chart** as `file-skills/<skill>/charts/<chart-id>.py`:
   ```python
   TITLE = "Cestrum share of trees, by plot"      # says what and in what unit
   QUESTION = "where is cestrum densest"          # what it answers, in their words
   def make(tables, plt):
       df = tables["Raw 10x10m Data"]             # the form's cleaned table: slug columns, skipped rows left out
       ...
       fig, ax = plt.subplots(figsize=(9, 5))
       ...
       return fig
   ```
   Only pandas, numpy, matplotlib (and math, re, datetime, collections, textwrap, itertools, statistics) may be
   imported; no files, no savefig, no network: data comes only from `tables`. Use the column names Idli gives, never
   values you saw in the mock (they're fake): filter by codes and rules from the skill (presets, `Read me` lookups),
   and handle any number of categories (top N plus "Others"), blanks and empty results (draw "No data" text).
   Aesthetics: one message per chart; horizontal bars for categories, sorted; lines only for time; label axes with
   units; value labels when there are few bars; no pies, 3D or dual axes; Idli's style (colour-blind-safe palette,
   no top/right spines) is applied for you, so don't set colours unless they carry meaning.
4. **Render it on the mock** and show it in this chat: `.venv/bin/python -m lib.chartkit try file-skills/<skill>
   <chart-id>` prints a markdown image line; write that line so they see the picture (with fake values: say so).
   Card: "This is the chart on fake data. Looks right?" options "Yes, use it (Recommended)" / "Change something".
   Iterate on changes (style, colours, labels, what's counted) until they're happy; after every change, render
   again and show the new picture in the chat before asking again (they judge what they see, not a description).
5. **Hand back:** `done.json` with `{"skill": "<skill>", "version": N, "charts": ["<chart-id>", ...], "summary":
   "<one line: the charts and what they show>"}`, then the same "Go back to Idli?" card as in section 5. Idli
   draws the charts from the real data when they get back.
