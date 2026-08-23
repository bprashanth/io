# 2026-08-23 14:00 — Should io carry an agent harness? Measured on an NGO-sector corpus

Question from the user: the repo's earlier experiments used the DeepSeek
Harness and Codex CLI (with a 27B). Harnesses are believed to "get better
over time by finding patterns and writing the right scripts". Is that true,
and should the io stack (laptop model, Ask + Build lanes, later sheltered)
include one — or not?

## 1. What a harness actually is, checked against the tools

- **Codex CLI 0.149**: an agent loop (shell + file tools) with a ~10k-token
  system prompt, `AGENTS.md` instructions, **skills** (`skill_search`
  stable: human-authored `SKILL.md` folders the agent loads on demand) and
  **memories** (`memories` feature: stable but *off* by default; the model
  writes notes from past threads into `~/.codex/memories_1.sqlite`). It does
  not learn by itself: a harness "matures" only through (a) instructions and
  tools people write for it, and (b) model-written memories if enabled. The
  0.149 CLI requires the Responses wire API (`wire_api = "chat"` is refused)
  and its bubblewrap sandbox cannot start on this DGX, so every run here was
  inside a throwaway Docker container (`io-codex-harness` image: python
  3.12, node 22, codex, pandas/duckdb/openpyxl/sqlglot/esprima).
- **DeepSeek Harness** (stage 1, `docs/harness-options.md`): a similar
  tool/plugin loop; its published Python composition is POSIX-only and
  `danger-full-access`, it read outside the staged workspace in the stage-1
  diagnostic, and the Web UI is a developer preview. Its stage-1 strength
  (89.0 mean vs Antigravity 52.2) was with a 27B and a human-written guardrail
  — again instructions, not self-improvement. It was not re-run; the Codex
  results below stand in for "a generic agent loop around the same model".

So the user's understanding is half right: harnesses improve through
*accumulated instructions and tools* (skills), which is exactly what io's
loader, plan contract and hints are — just without the model driving a shell.

## 2. The corpus (what NGO data actually looks like)

A delegated agent read the non-PII columns of the 31 survey responses, the
public pages of several of those organisations and typical Indian NGOs, and
the export formats of Zoho Books/CRM, Razorpay, KoboToolbox, WhatsApp, NRLM
SHG registers, 80G and UDID. Result: `benchmarks/t0/ngo-corpus/README.md`
(16 data shapes with their usual mess, sources cited) and 8 synthetic
organisations / 18 files / 40 cases (`cases.json`: 22 ask with pandas gold,
10 build, 8 page) — education register with a two-row merged header and
stacked baseline/endline blocks; SHG master + month-wide loan ledger + Zoho
Books invoices with "₹12,500.00"; Kobo ANC export with `hh/village` columns
and a 24-block camp register with title rows and Hinglish notes; UDID
beneficiary master (mixed date formats) + a running stock ledger; Zoho CRM
leads, Razorpay payments (amounts in paise, epoch times), 80G receipts;
expense vouchers with monthly totals and a pasted Budget-vs-Actual pivot,
staff attendance 1..31 wide, vehicle log; a 559-line WhatsApp field-group
export; a six-sheet MIS with headers that drift between months.

## 3. The loader had to grow to read it (all deterministic, all measured)

Stacked blocks (same header → one table with a `block` column carrying the
title above each; different headers → separate tables), two-row merged
headers, day-number/year header rows, footer/total rows, duplicate and blank
headers, "1,250"/"₹" numbers, GPS pairs, case/space variants of categories
merged, long digit-only identifiers kept as text (an 18-digit UDID had been
coerced to a float and JavaScript cannot hold it), dates typed, WhatsApp
exports parsed into a `messages` table (`sender`, `message`, `first_number`,
`media`), schema notes for month-wide layouts (blank = nothing, COALESCE,
UNPIVOT), running ledgers ("current stock = balance on the latest row"),
Razorpay paise/epoch, and sqlglot falling back to DuckDB's own statement
typing. Before these, the app scored 5/22 on the corpus; after, 20/22.

## 4. Results — 22 ask cases, same questions, same data

| leg | model | correct | mean time | mean input tokens | rows/PII the model saw |
|---|---|---|---|---|---|
| **io app (no harness)** | Qwen 3.5 9B | **20/22** | **2.5 s** | ~3k | 0 rows |
| io app | Qwen 3.8 27B | 20/22 | 1.6 s | ~3k | 0 rows |
| Codex, free (python) | 9B | 20/22 | 34 s | 103k | raw file reads in 21/22 runs; 635 PII-bearing lines |
| Codex, free | 27B | 21/22 | 33 s | 63k | raw reads 19/22; 114 lines |
| Codex + io tools skill | 9B | 19/22 | 24 s | 66k | 1 raw read; 81 lines (query outputs) |
| Codex + io tools skill | 27B | 22/22 | 20 s | 45k | 0 raw reads; 46 lines |

Grading: app answers by the value-set comparer; harness final messages by
the same comparer over lines with digit-group commas removed
(`GRADING.md`). The 9B only works in Codex with `model_reasoning_effort =
"none"` — with "low"/"minimal" it spends the turn in the reasoning channel,
makes one tool call and stops (0/22, twice). Residual 9B errors in the
harness are reasoning errors (deduplicated ANC women by name; read a monthly
column as "outstanding"), and the one it gets wrong everywhere without the
hint is Razorpay paise.

Build lane (10 cases) through the app with the 9B: 10/10 pages, 66/70
panels executable, 4–40 s, every page screenshotted; the device-inventory
dashboard got the current stock right via the ledger hint and its nonsense
"coverage %" cross-join was auto-flagged. Codex + io tools on four build
cases: pages produced, but 26–29 shell commands and 450k tokens for two of
them (140 s each) — the 9B thrashes when it has to drive a loop. Page lane:
the app produced 8/8 pages (lookup app verified by searching a UDID after
the identifier fix); Codex free produced 1/3.

## 5. Decision: no agent harness inside io for the laptop tier

- **Correctness**: equal or worse (9B: 20 → 20/19; only the 27B gains +2
  with io's tools, which is T1 territory).
- **Latency**: 10–15× slower on Ask (2.5 s → 24–34 s), 100 s+ on Build.
- **Cost**: 20–35× the tokens — on a local CPU that is minutes per question.
- **Privacy**: a free harness reads rows into the model in 21 of 22 runs.
  Sheltering a harness means intercepting every shell/file tool, which is
  the Antigravity-shield problem again (stage 3), not an easier one; in io
  the model never has a shell, so there is nothing to intercept.
- **"Gets better over time"**: the mechanism that actually works is the
  skill/instruction layer. io already *is* that layer, compiled into the
  loader (shapes), the schema notes (sector knowledge), the plan contract and
  the guards — and it improves the same way: each corpus case that fails adds
  a deterministic rule that every later user benefits from, with no model in
  the loop and no per-user drift.

What to keep from the harness idea: the **io tools skill**
(`benchmarks/t0/harness-skill/`: `AGENTS.md`, `io.py`, `plan_contract.md`)
is the right artefact for *T1/T2 agents* — a 27B or frontier agent given
`io.py` scores 22/22 here and never reads a row. That is how the higher dial
positions should be wired later: same loader, same receipts, the agent only
ever calls `io.py`.

## 6. UX for waiting

The app now shows what it is doing while a small model works: "Reading
files, finding header rows…", "Asking the model for a page plan", "Running
every panel's query on your laptop", "Found a syntax error; asking for a
fix", with elapsed seconds and "small local-tier model, thanks for waiting".
Screenshots: `benchmarks/runs/2026-08-23-harness-v1/ux-progress/`.

## Evidence

`benchmarks/runs/2026-08-23-harness-v1/` — `io-app-*` (app runs with full
answers), `cx-*` (Codex events, commands, final messages, workspace
listings, per-case `summary.txt`), `cx_run.sh`, `cx_batch.py`,
`cx_buildpage.py`, `GRADING.md`; `benchmarks/t0/ngo-corpus/` (generator,
README with sources, fixtures, cases); `benchmarks/t0/run_corpus_cases.py`;
`benchmarks/t0/harness-skill/`.
