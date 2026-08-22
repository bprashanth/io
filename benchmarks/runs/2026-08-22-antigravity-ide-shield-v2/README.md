# Privacy shield 0.2.3 verified inside the real Antigravity IDE (2026-08-22, DGX arm64, Antigravity 1.107.0)

Verification of the laptop handoff (0.2.2) by driving the real IDE under Xvfb with
CDP/Playwright (`ide.py`, `turn.py`, `scenario.py`), cold-installing the packaged
`.vsix`, and acting as a participant: status-bar picker, Enable, the relaunch modal,
the in-chat column review, `ok`, dashboards and follow-ups, Disable, relaunch.

Workspace: the synthetic corpus files a participant might bring — the 300-row
scholarship CSV (Hinglish/mislabelled headers), the child-fitness workbook (two
sheets), a WhatsApp export and a generated PDF report.

| # | Screenshot | What it shows |
|---|---|---|
| 01 | status-bar picker (off) | click the status bar → "Enable Privacy Shield" |
| 02 | relaunch modal | Enable → daemon up → one relaunch |
| 03 | review prompt | 12 columns proposed, kept list, reply grammar |
| 04 | dashboard | built through the shield; 300/103/61/136/67.2 % all correct; real values on disk; 0 wire hits |
| 05 | follow-up | top 3 in Khed with school + mobile, rehydrated |
| 06 | workbook | Baseline→Endline sit-up gains (verified with pandas), coaches and parent phones rehydrated |
| 07 | WhatsApp export | 12 senders (correct), most-mentioned beneficiary + number; 0 wire hits |
| 08 | PDF report | coordinator, follow-up name + number; 0 wire hits |
| 09 | disable modal | two-step picker, no stray Antigravity error toasts |
| 10 | unshielded chat | after Disable + relaunch the IDE works normally, account stays signed in |
| 11 | cold start | fresh install of 0.2.3: Enable → Relaunch → shielded answer, `signedIn`, 0 ECONNREFUSED |

`shield-calls-final-session.jsonl` is the daemon's per-call record for the last
session. Wire probes were run with `/shield/last-request` after every turn.

Defects found during this verification and fixed in 0.2.3 are listed in
`chronology/2026-08-22T2130-shield-0.2.3-verification.md`.
