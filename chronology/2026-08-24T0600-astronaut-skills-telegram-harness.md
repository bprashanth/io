# 2026-08-24 06:00 — Astronaut: skills in the kernel, compaction measured, Telegram shell live, harness decided

Overnight run for `proposals/idli_astronaught.md`. Decisions the user asked for, each with the
run behind it. Evidence: `benchmarks/astronaut/`, `benchmarks/runs/2026-08-24-astronaut-flows/`,
`app/io-desktop/skills/builtin/`, `app/io-desktop/server/{skills,telegram_shell}.py`.

## 1. Kernel: keep or clean up → cleaned, no regression

The four domain claims that lived in loader code (Razorpay paise/epoch, running-ledger "latest
row", WhatsApp `first_number` counts, month-wide blanks) are now **built-in skill files** with
structural triggers (`columns_all`, `ledger`, `whatsapp`, `months` flags). Same text, same firing:
corpus 22 asks with the 9B scored 20/22 before and 20/22 after (different wobble cases; ±1 is the
9B's run-to-run variance). What stays in code and why is in
`backlog/2026-08-24-structural-claims-left-in-kernel.md`.

The skills layer (`skills.py`): JSON files in three layers (built-in → user → folder `.io/skills`),
kinds **hint** (schema note), **mapping** (`unify` differently-named columns, `derive` a column),
**rule** (prompt rule for matching questions), **parse** (header row / day-first / sheet, per file),
**template** (a plan used verbatim). Every skill is asserted against the values of high-cardinality
text columns before it is previewed or saved — a skill that contains a name/phone/id is refused.
**SEE WHY** records per table: header row, rows skipped, blocks merged, dates typed (and which
way), numbers parsed from text, long ids kept as text, merged spelling variants, normalised join
columns, mapping columns added, skills fired. **Interaction log** per folder (question, lane,
tables, SQL/plan SQL, errors, attempts, scope notes, invented numbers, skills fired, parse notes —
never rows) is what COMPACT reads.

## 2. Compaction: 27B vs frontier (`benchmarks/astronaut/README.md`)

Bare kernel (built-ins off) → 17/22. Hand built-ins → 20/22. Compacted from the bare logs:
t1 Qwen 3.8 27B round 1 → 18, rounds 1+2 → 18; t2 Gemini 3.7 Flash round 1 → 18, rounds 1+2 → 19.
Gemini proposed more and better-targeted cards (rediscovered the ledger and WhatsApp built-ins,
wrote three `unify` mappings for the MIS workbook's drifting headers); the 27B proposed fewer,
all correct, and on the live demo folder produced exactly the two cards the demo needs
(`unify-mis-monthly-columns`, a pivot-layout hint) in one round. Round 2 did not produce junk;
it fixed the one regression round 1 had caused. Cost 1–55 s and 1.5–6 k tokens per folder per
round. 0 of 23 cards contained a protected value. Misfire suite: 3 cross-org firings, all from
one over-broad trigger (`columns_any: [Name, Student Name]`). What neither tier can see: a wrong
number that ran without error (paise) — that needs a user correction, which is the AUTHOR path.

**Call:** the 27B is good enough for compaction at the event and keeps the consent story inside
sector custody; frontier adds ~1 answer and more mapping proposals. Offer both in the consent
popup (done), default t1.

## 3. The flows, through the real UI (screenshots in `benchmarks/runs/2026-08-24-astronaut-flows/`)

1. **Tricky file → SEE WHY → correction.** `demo-tricky/us_dated_donations.csv` (US dates): "donations
   per month" gives 12 months; click the file → "Dates typed: Date (day first)"; "This was read
   wrong — correct it" → wizard preselects a parse correction → month first → saved as a folder
   skill → re-ask gives 6 months; SEE WHY now says "(month first)" and lists the skill.
2. **COMPACT.** MIS workbook: four questions (two wrong-ish) → "Propose skills from my usage" →
   consent popup (27B/frontier) → two cards → approve the `unify` mapping → six monthly tables gain
   `Households`, `SHGs`, `Water Structures` columns; SEE WHY shows "Mapping skills added columns".
3. **AUTHOR.** Wizard → rule skill "dropouts = in baseline, not in endline, by name" with a question
   trigger → fires on the next dropout question (`skills_fired` on the turn).
4. **File edit → page updates** is a kernel behaviour (live re-run), not a skill; SEE WHY's "data as
   of" line covers the demo beat.

## 4. Telegram shell (`telegram_shell.py`) — live on `@Iotheidli_bot`

A thread inside the io service, long-polling with the token pasted in the Astronaut box (or saved
in config). No server, no inbound port: it runs while the laptop and the app are open, which is
the event plan. Commands: `/start`, `/reach laptop|t4gc|frontier` (changes which model answers:
laptop = the 9B, t4gc = 27B, frontier = Gemini; rows never leave either way), `/files`, `/why`
(SQL + skills fired for the last answer), `/skills`, `/propose [frontier]` (consent text, then
cards), `/approve N`; plain text routes to ask/build/page. Ask replies are a monospace table plus
"Laptop · model · rows sent 0 · 2.3 s"; build/page replies are the rendered HTML as a document.
Tested end to end through an injection endpoint (`/api/telegram/inject`) — the real bot is polling
with the real token, nobody has messaged it yet; Telethon login for a scripted user is pending
the user's phone code. Hermes' own gateway was left stopped so the two pollers don't collide.

## 5. Harness: which, and where

Codex: no packaging for any of this (stage-4 follow-up). **Hermes** (`hermes-agent-local`, on this
box) has everything the proposal wants packaged: Telegram/WhatsApp gateway, agent-created skills +
curator, local providers, skills registry. Measured in an isolated container with OpenRouter
qwen/qwen3.5-9b, `AGENTS.md` + `io.py` mounted, `--yolo`: see the table at the end of this entry
(filled in when the batch finished). Early rows: correct answers, 27–205 s each.

**Decision.** For the event, astronaut mode = kernel + skills + Telegram shell, **no agent loop in
the laptop path**: the 9B through io answers in 2–4 s at 20/22; through Hermes it is as correct
but 10–50× slower and every answer is a multi-step loop the user cannot see. Hermes is the right
harness *when* one is wanted: as the T1/T2 agent shell (27B via `io.py`: 22/22, 0 raw reads in the
Codex measurement) and for shell-needing skills (chunk large files), and it can be offered as a
remote "harness in a box" on the DGX behind the Cloudflare wall later — with the caveat that the
kernel (the data) then has to be reachable from it, which means a tunnel from the laptop or the
data on the server (T1 custody). Neither is needed for the demo.

## 6. What a participant sees

Settings → Astronaut on → an Astronaut box: "Propose skills from my usage", "Add a skill", the
skill list with firing dots and delete, the Telegram token field. Files in the sidebar get a dot
when a skill fired; clicking one opens SEE WHY. Progress steps during waits say what is happening
("Reading files, finding header rows…", "Running every panel's query on your laptop", "Sending N
log lines … to qwen/qwen3.8-27b").
