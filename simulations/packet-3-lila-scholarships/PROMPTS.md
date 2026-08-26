# lila-scholarships: what to run and what we saw

Scholarship foundation (survey rows 24-26: "automatically reconciling applicant lists across multiple Excel files to flag missing/duplicates"). Data: 2025 and 2026 applicant workbooks (phones, emails, family income; exactly 30 planted cross-year duplicates with case differences), disbursements.

## The three questions (type them exactly, one after another, in one conversation)

1. Can you make me a dashboard for this year's scholarship applicants and payments?
2. Please flag likely duplicate applicants across 2025 and 2026, even when their name uses different capital letters.
3. Add a clear disbursement-status view showing who is fully paid, partly paid or not yet paid, plus totals by installment.

## What we measured when we ran this (2026-08-26)

All 3 turns completed in both surfaces. io: scan 3 s, answers 5-31 s, 643 rows as codes, disbursement view built, share fetched (122 KB). This packet also caught a real bug (share links from different folders overwriting each other) - fixed and verified.

## What to check, each time

- **In Antigravity without the shield**: pick a name/phone from the data, ask a question that
  uses it, and know that everything left as-is. (Do this first so the contrast lands.)
- **In Antigravity with the shield on**: after the answer, open the shield menu -> status
  page. `calls` moved, `vault_entries` matches roughly the people in your files. Open
  "last request" and ctrl+F a real name and a real phone from the data: **zero hits** is a
  pass; codes like NAME_012 are what you should see instead. The file the agent wrote on
  disk should have the real values.
- **In io**: the review sheet shows the same columns highlighted; Preview shows the exact
  tokenised payload; after asking, the meta line under the answer says how many rows left
  as codes; built pages get "share on your network" - open the link from your phone.
- The duplicate turn is the correctness check: the model only sees codes, yet duplicate flagging still works because the same person always gets the same code. Count how many of the 30 it finds.
