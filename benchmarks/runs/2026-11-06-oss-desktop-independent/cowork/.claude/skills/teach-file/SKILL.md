---
name: teach-file
description: Teach Idli (the private model) how to read a spreadsheet and answer a question about it, by writing a file skill from a mock with fake data. Use when a message mentions teach/inbox or an Idli teaching request, when an Excel file has a hidden `_idli_teach` sheet, or when the user shares a mock spreadsheet and asks to "teach Idli" this file.
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

## 2. Walk the user through it (always one confirmation round before writing anything)
Ask in one message, then wait for the reply:
1. What one row is in each tab ("one row per claim"), and for each tab "Your columns are:" with each
   header's meaning and type (date in format X, amount, phone, email, category, free text). Ask them to
   confirm or correct.
2. Suggested checks: phone or email shape, dates that don't parse or are in the future, amounts that
   aren't numbers, required fields, a category's allowed values, keys that must exist in another tab.
3. Suggested clean-ups: spelling variants of one category, amounts written as "Rs. 1,200", mixed date formats.
4. **The words of this file**: what they add up or count (measures, with names they'd use), which date
   is "the date", and business rules, e.g. "does 'paid out' mean Approved and Paid?", "leave out
   Rejected by default?". With several tabs: how they connect (Visits.Officer = Officers.Name).
5. How you read their question, e.g. "08/26 to 10/26 means 26 Aug to 26 Oct 2026".

Skip anything already settled in an existing skill. Use their answers. If they say "you decide", pick
the sensible default and say what you chose. Don't write the skill until they've replied.

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
  your answer?", options "Yes, back to Idli" and "Stay here". If they pick yes, run
  `.venv/bin/python -m lib.uiswitch agent <caller_agent>` with `caller_agent` from request.json (skip the
  card if it's empty).
