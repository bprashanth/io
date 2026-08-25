# Working with this NGO's data

The folder holds this organisation's spreadsheets and exports. They contain beneficiaries' personal
details (names, phone numbers, Aadhaar, bank details). Rules:

1. NEVER print, cat, head or open the data files directly. Do not read rows.
2. Use the io tool instead. First run `python3 io.py schema` — it lists every table, its columns
   and types, and notes about tricky shapes (stacked blocks, running ledgers, amounts in paise,
   WhatsApp exports, month-wide layouts, spelling-normalised join columns).
3. Answer questions with ONE read-only DuckDB query at a time: `python3 io.py query "SELECT ..."`.
   The tool prints the result. If it prints QUERY ERROR, fix the query and run again.
4. For a dashboard or report, write a plan JSON (see plan_contract.md) and run
   `python3 io.py page plan.json`; the laptop renders it. Never write HTML with numbers in it.
5. Your final message must contain the answer as a small table or sentence with the numbers that
   came from the query output. Never guess or compute numbers in your head.
