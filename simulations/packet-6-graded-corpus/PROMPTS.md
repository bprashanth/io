# packet-6: the graded corpus (8 orgs, 40 questions WITH expected answers)

This is the packet for **model comparison**, because every question has a written
expected answer - you can judge a model right/wrong without trusting your gut.

Data: `benchmarks/t0/ngo-corpus/` - eight synthetic orgs, each a folder of realistic files:

| org | flavour | files |
|---|---|---|
| sunrise-shiksha | education | enrolment workbook (merged header traps) |
| swayam-mahila | SHG/microfinance | savings ledger |
| arogya-jyoti | community health | patient visit logs |
| saksham-kalyan | disability welfare | beneficiary registers |
| asha-kiran | donor ops | Zoho CRM export, Razorpay payments, 80G receipts |
| prayas-seva-sangh | mixed programmes | MIS sheets |
| gram-sudhar | rural dev | visit log + WhatsApp export |
| krishi-jal-vikas | agri/water | Apr-Sep MIS workbook |

Questions + expected answers: `benchmarks/t0/ngo-corpus/cases.json` - 40 cases, each with
`prompt`, `files`, `expect` (what a correct answer contains) and often `expected_rows`
(exact numbers). Example: "How many students are enrolled at Sunrise Shiksha for
2025-26?" -> 320.

## How to run

1. Pick an org folder, shelter it in io (or open in shielded Antigravity).
2. Ask its questions from cases.json, one per turn.
3. Score each answer against `expect` yourself. Note WHERE models fail: merged headers,
   dd/mm dates, totals rows, paise-vs-rupees are the planted traps.
4. If you have access to more than one model, ask the same question on each and keep a
   right/wrong tally per model. (Reference: the laptop-class 9B scored 20/22 on the ask
   subset through io's kernel; see `benchmarks/astronaut/README.md` and chronology
   2026-08-24 for how the big models compared.)
