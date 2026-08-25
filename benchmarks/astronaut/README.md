# Astronaut compaction eval (2026-08-24)

Corpus: `benchmarks/t0/ngo-corpus` (8 orgs, 22 ask cases). Model answering: Qwen 3.5 9B (T0).
Kernel: built-in skills OFF (`IO_DISABLE_BUILTIN=1`) so the only domain knowledge comes from compaction.
Compactors: t1 = Qwen 3.8 27B, t2 = Gemini 3.7 Flash (reasoning low). Each folder's interaction log is
sent (questions, SQL, errors, retries, parse notes — no rows) and cards come back as skill JSON.

| run | ask correct /22 | notes |
|---|---|---|
| bare kernel | 17 | no hint skills at all |
| + hand built-ins (4 skills) | 20 | ledger, WhatsApp, paise, month-blanks (`app/io-desktop/skills/builtin`) |
| + compacted t1 round 1 (3 cards) | 18 | quoting hint, month-filter rule, attendance 'A' hint |
| + compacted t2 round 1 (8 cards) | 18 | incl. ledger and WhatsApp rediscovered, 3 MIS header-drift unify mappings |
| + t1 rounds 1+2 (6+3 cards) | 18 | |
| + t2 rounds 1+2 (8+4 cards) | 19 | round 2 fixed the round-1 regression it caused (month column rule) |

Cost: 1–20 s per folder per round, 1.5–6k prompt tokens (logs are tiny: 2–4 questions per folder).
Leak assertion: 0 cards contained protected values. Misfire suite (`misfire-t2.json`): 11 firings,
3 cross-org — all from one over-broad trigger (`unify-student-name-columns`, `columns_any: [Name, Student Name]`).
What compaction cannot see: a wrong number that ran without error (paise) — needs a user correction.
Per-run records under `runs/`, cards under `skills/` and `skills-r2/`.
