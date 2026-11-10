# Can a 9B do Muse 30B's job in Idli? (2026-11-10)

Verdict: a local Qwen3.5-9B with general guards matches Muse on start, find, open, clean, teach-switch, skills,
Start here and index summaries. On long follow-up chats (fresh held3) it stays 10-16 points behind, all in turning
a follow-up question into a form spec. Spend intelligence there: a 35B-A3B-class model for that step only (83% on
held3 = Muse; 89% spec accuracy vs the 9B's 73%) or a stronger stateful spec builder. The algebra LoRA (9B-004d)
does worse than the raw 9B (51/60% vs 65/86%): backtracking guards mattered more than fine-tuning.

## Per segment (% of conversation spans passed)

| Segment | Muse 30B | 9B raw | 9B + guards | Verdict |
|---|---|---|---|---|
| Start card | 100 | 25 | 100 | 9B ok |
| Find a file | 95 | 89 | 100 | 9B ok |
| Open (file cards) | 70 | 60 | 100 | 9B ok |
| Ask, tuned conversations | 80 | 64 | 79 | 9B ok |
| Ask, fresh long follow-ups (held3) | 76 | 52 | 53 | 9B 13-23 behind |
| Charts | 96 | 46 | 62 | partial |
| Teach-switch | 94 | 62 | 92 | 9B ok |
| Clean (working copy) | 67 | 33 | 100 | 9B ok |
| Skills (learned / delete) | 33 | 33 | 100 | ok (tool fix helps Muse too) |
| Start here (indexing chat) | not run | 100 | - | 9B ok |
| Index summaries (top-1 of 15) | 10, 79 s/batch | 12, 4.6 s | - | 9B better |
| All, dev + held + held2 | 85 | 65 | 86 | 9B ok |
| All, held3 (never tuned on) | 83 | 65 | 67-73 | 10-16 behind |
| Real Claude Code CLI | 78 (partial) | 70 | 76 | 9B ok |
| UX, blind rubric (of 5) | 3.2 | 2.6 | 2.7 | 9B less polished |

## Results (lean harness; % of conversation spans passed)
dev+held+held2 (n≈190 spans per config, 2 repeats): Muse 85 | 9B raw 65 | 9B+thinking 72 | 9B+guards 86 |
9B+guards2 84 | 9B+guards3 86 | 9B local Q5 66 -> 85 with guards | LoRA 004d 51 -> 60 | 35B-A3B 76 -> 90 (guards3) |
Granite 8B 69 -> 85 (6-8% made-up numbers) | Ministral 8B 54 -> 69 | gpt-oss-20b 32 -> 45.
held3 (fresh, 10 long chats, never tuned on): Muse 83 | 9B 65 / 67 / 69 / 70 (base/guards/guards2/guards3) |
9B+thinking 70-73 | 35B-A3B 74 -> 83 (guards3). Gap is in ask: spec 57 vs Muse 77.
Real Claude Code CLI (cards answered as Paseo does): Muse 78 (partial) | 9B 70 -> 76 with guards.
Start here chat: 9B 100, 35B-A3B 94. Index summaries (top-1 of 15): names only 7, Muse 10 (79 s/batch),
9B 12 (4.6 s), Gemma 12B 13. Spec building alone (44 items): 9B 73% (JSON-schema enums 70%: it doesn't invent
ids), 35B-A3B 89%, LoRA 52%, Ministral 43/61%.
UX (blind rubric, Codex first pass, out of 5): Muse 3.21 (44% >=4) | 9B 2.55 | 9B+guards 2.73 | local 9B 3.00 |
LoRA 2.59. 9B flags: repeats (text then card under the guard), unneeded questions.

## Where each model fails (Codex tally, results/lean-v1/failures.md)
Muse: wrong card / misroute ~20 of 29 failing spans; skipped the delete confirmation.
9B raw: card written as text 17, wrong card 23, misroute 28, wrong spec 22. With guards: card as text 1;
misroute 15, wrong spec 18, incomplete relay 10, asked instead 10 remain.

## Scaffolding (general; patches/ apply cleanly to cowork/)
- 0001 drive_find(goal): find|clean|analyse; opens the spreadsheet itself when clear.
- 0002 skill_delete shows its card before deleting.
- 0003 skills_delete honours IDLI_HOME.
- 0004 Stop hook: one nudge per turn for an unshown card or a number no tool gave (tested on a real transcript).

Variants measured: guards2 (key aliases, labels->ids, unknown keys are errors, small counts come with their rows),
guards3 (stateful form: file_ask refine=true).

Proposed, not yet patched:
- file_ask: `"presets"` is silently ignored today (business rules drop without an error); accept labels where ids
  are expected.
- The host renders tool cards itself (a Paseo patch, or MCP elicitation): removes card-as-text and the repeats.
- Stop repeating the "say 'ask Claude'" line after every chart.
- A follow-up spec model for the ask step (35B-A3B class or better).

## Caveats
- The scripted user first typed into "which file?" cards instead of clicking the obvious file; fixed, and the 203
  affected transcripts were rerun.
- Muse's Claude Code number is partial (67 spans); Muse's spec-building run was stopped to free Muse, so no spec
  score for Muse.
- guards2 fixes were partly motivated by held-out sets; held3 was written fresh and kept as the judge.
- An early harness bug wrote archived skill copies into ~/idli-insights/archive on the DGX; removed and fixed.
- No idli9b-* containers left running; Muse was never restarted.

## Method
Idli's real tools on a fake Drive: 12 spreadsheets (taught-skill mocks, totalrecall synthetic livelihoods tables,
public Valparai road-kill and tree-plot data cut to NGO-sheet columns, with a few planted mistakes), 6 documents,
a real DuckDB index. 40 scripted chats in the owner's voice: dev 14, held 8, held2 8, held3 10 (Codex-authored,
references checked against the engine), plus 2 Start here chats. Two harnesses: a lean loop (same prompt for every
model) and the real Claude Code CLI through the Agent SDK. Scoring: right tool and args; answer numbers match a
reference spec run on the engine; no made-up numbers; no loops. UX judged separately.

Workers: Codex (held2/held3 authoring, failure tally, first-pass UX grading); benchmark agent (design, harness,
scaffolding, judging).
