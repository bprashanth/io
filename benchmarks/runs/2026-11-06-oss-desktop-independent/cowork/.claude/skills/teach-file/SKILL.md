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
- If `existing_skill` is set, load `file-skills/<existing_skill>/skill.json` and **extend** it. Keep its
  questions and checks, add the new question, and bump `version`.

## 2. Walk the user through it (always one confirmation round before writing anything)
Ask in one message, then wait for the reply:
1. "Your columns are:" then each header with its meaning and type (date in format X, amount, phone,
   email, category, free text). Ask them to confirm or correct.
2. Suggested checks: phone or email shape, dates that don't parse, amounts that aren't numbers,
   required fields, a category's allowed values.
3. Suggested clean-ups: spelling variants of one category, amounts written as "Rs. 1,200", mixed date formats.
4. How you read their question, e.g. "08/26 to 10/26 means 26 Aug to 26 Oct 2026; include all
   statuses or approved only?"

Skip anything already settled in an existing skill. Use their answers. If they say "you decide", pick
the sensible default and say what you chose. Don't write the skill until they've replied.

## 3. Write the file skill
Write `file-skills/<id>/skill.json`. The `<id>` is a slug of the file's title. It is data only, never Python:
```json
{
 "id": "tech_reimbursement_form", "title": "Tech reimbursement form", "version": 1,
 "headers": ["amount_inr", "category", "claim_date", "employee", "item", "status"],
 "sheet": "Claims",
 "summary": "Tech reimbursement claims: one row per claim with date, person, item, amount and status.",
 "columns": {"claim_date": {"type": "date", "format": "%d/%m/%Y", "meaning": "date of the claim"},
             "amount_inr": {"type": "number", "meaning": "claimed amount in rupees"}},
 "normalize": {"status": {"map": {"aproved": "Approved"}}, "village": {"case": "title"},
               "visit_date": {"type": "date", "formats": ["%d/%m/%Y", "%Y-%m-%d"]}},
 "validations": [{"column": "phone", "rule": "phone", "message": "not a 10-digit phone"},
                 {"column": "amount_inr", "rule": "number", "message": "amount is not a number"},
                 {"column": "status", "rule": "in_list", "arg": ["Approved", "Paid", "Pending", "Rejected"],
                  "message": "unknown status"}],
 "questions": [{"id": "total_between_dates",
                "ask": "Total amount and number of claims between two dates, optionally for one status",
                "params": {"start": {"type": "date", "description": "first day"},
                           "end": {"type": "date", "description": "last day"},
                           "status": {"type": "text", "optional": true, "description": "e.g. Approved"}},
                "sql": "SELECT count(*) AS claims, sum(amount_inr) AS total FROM {{table}} WHERE claim_date BETWEEN {{start}} AND {{end}} AND ({{status}} IS NULL OR status = {{status}})"}],
 "history": [{"version": 1, "taught": "add up reimbursements between two dates"}]
}
```
- `headers`: the slugged header set of the main sheet, which Idli uses to recognise the file. Copy it
  from `inspect`'s column keys, lower_snake_case.
- **Column names** in SQL are those slugs. In `{{table}}`, `date` columns are DATE and `number` columns
  are DOUBLE, after `normalize`. Unparseable values become NULL.
- **Rules:** `required`, `number`, `date` (`arg`: list of formats), `email`, `phone`, `in_list` (`arg`:
  values), `range` (`arg`: `[min, max]`), `regex` (`arg`: pattern). Each becomes an Excel formula
  column in Idli's "- checked" copy.
- **Questions:** generalise the user's question into parameters: dates, a status, a place. Write one
  query per question; it may return several columns or rows. Prefer a query that also shows its
  breakdown (e.g. per month) when that helps.

## 4. Test against the mock
- Copy the mock to `file-skills/<id>/mock.xlsx`.
- Write `file-skills/<id>/tests.json`:
  `[{"question": "total_between_dates", "params": {"start": "2026-08-26", "end": "2026-10-26"}, "expect": [[23, 80210.0]]}]`.
  Compute `expect` **independently** with pandas on the mock, not with your SQL.
- Run `.venv/bin/python -m lib.filekit test file-skills/<id>` until it prints `ALL PASSED`.

## 5. Hand back
- Write `teach/inbox/<id>/done.json`:
  `{"skill": "<id>", "version": N, "questions": ["..."], "summary": "<title> v<N> can answer: <ask>"}`.
  Idli's chat is told automatically.
- Tell the user in two lines what Idli can now check and answer, and that their Idli chat will continue.
