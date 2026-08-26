# asha-kiran

## Survey Question

How do we reconcile donor records across our CRM, payment gateway, and receipts, and report to the board?

## Data

`data/`

This folder has a donor CRM export, Razorpay payment records, and 80G receipts. Amounts in the payment file are in paise.

## Suggested Questions

1. How many leads in the donor CRM are marked Converted?
2. What was the total amount raised for the WinterDrive2025 campaign?
3. Which donors gave twice or more?
4. Build a donor funnel dashboard: lead status breakdown, monthly collections, top campaigns.
5. Build a board report: total raised, unique donors, receipts issued.

## Answers

Written expected answers for these questions are in `../../benchmarks/t0/ngo-corpus/cases.json` (org: asha-kiran). The planted traps: amounts stored in paise, failed payments that must be excluded, and payments without a matching receipt.

## Results

Existing comparison results are available in:

- `../../benchmarks/runs/2026-08-22-t0-ask-v1/`
- `../../benchmarks/astronaut/README.md`

## Verification

1. Try it in Antigravity.
2. Try it in Antigravity with the shield. Press `Ctrl+Shift+P`, verify the vault, and check the last request.
3. Try it in io. Open the generated page on the local network and keep it ready for the next session.
