

Done. Computed from `zoho_books_invoices_export.csv` (260 invoices; `shg_master.csv` and `loan_ledger.xlsx` are unrelated to invoicing). Definition: **Due Date < today (2026-08-23) AND Balance > 0**.

**Result**: 109 invoices are overdue with a balance pending, totaling **₹830,176.60**. Status mix: 40 "Sent", 35 "Overdue", 18 "Partially Paid", 16 "Draft". (All 151 paid invoices are past due but fully settled, so excluded.)

Largest outstanding balances (of 109):

| Invoice | Customer | Due Date | Balance (INR) |
|---|---|---|---:|
| INV-2025-00072 | Divya Mahila Bachat Gat 143 | 30/07/2025 | 23,372.06 |
| INV-2025-00107 | Radha Mahila Bachat Gat 4 | 18/08/2025 | 21,645.62 |
| INV-2025-00237 | Vandana Mahila Bachat Gat 157 | 04/10/2025 | 21,002.99 |
| INV-2025-00246 | Kajal Mahila Bachat Gat 2 | 18/07/2025 | 18,754.11 |
| INV-2025-00007 | Vandana Mahila Bachat Gat 92 | 20/07/2025 | 17,861.58 |
| INV-2025-00230 | Asha Mahila Bachat Gat 93 | 25/09/2025 | 16,374.29 |
| INV-2025-00011 | Kalpana Mahila Bachat Gat 120 | 12/07/2025 | 16,111.31 |
| INV-2025-00240 | Pooja Mahila Bachat Gat 180 | 05/07/2025 | 15,920.62 |
| INV-2025-00113 | Simran Mahila Bachat Gat 88 | 08/10/2025 | 15,721.44 |
| INV-2025-00162 | Deepa Mahila Bachat Gat 6 | 11/07/2025 | 15,359.54 |

Want me to export the full list of 109 to a CSV, or filter differently (e.g., only status "Overdue", or a minimum balance)?