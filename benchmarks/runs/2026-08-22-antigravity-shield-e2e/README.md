# Antigravity + privacy shield, end-to-end (2026-08-22)

Workspace: synthetic `scholarship_applicants.csv` (300 rows, 20 columns, Hinglish and
mislabelled headers) plus the household survey, fitness workbook and a generated PDF.
Shield: `benchmarks/pii/shield_proxy.py --annotate --review chat --numbers 8`,
Antigravity CLI 1.1.15 headless with `CLOUD_CODE_URL=http://127.0.0.1:8765`.

Turns (all through the shield, Gemini 3.7 Flash upstream):
1. dashboard request -> in-chat review listed 12 columns -> `ok` -> Antigravity
   built `dashboard.html` (310 KB, Tailwind/Chart.js from CDN as usual). On disk:
   real names, 0 tokens. Outbound: tokens only. Screenshot: dashboard-turn1-online.png
2. "only Pune district, add approval rate taluka wise" -> page updated.
3. "tell me about <applicant>" -> question tokenised, answer rehydrated.
4. "highest-marks pending applicant in Khed with mobile" -> answered.
5. "full record incl. aadhar and bank account; how many share her gaon" -> full
   record rehydrated on screen, 0 hits for name/phone/Aadhaar in the outbound body.

`shield-calls.jsonl` is the per-call record (redaction ms, spans, tools, blocks, minted
values). Blocks in the log are from the iterations that found bugs; the final
turns have none. The vault file is not kept in the repository.
