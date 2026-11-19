# CLI capabilities with man pages against today's menu: mapping partial questions (2026-11-19)

The plan was written before any run: [PLAN.md](PLAN.md), with what changed during the run recorded at its end.

- **Questions:** 32 partial questions over the three Minis of the leads sandbox. 16 are the owner's own, from the
  chats. 21 are dev and 11 held out.
- **Mappers:**
  - idli-remote: the production path, with model and settings as in `miniscope.map_service`;
  - the local 9B: as in `miniscope.map_local`.
- **Runs:** three of every condition, at temperature 0.
- **Not run:** the read-only end-to-end check on the laptop (`e2e.py`). The laptop's Paseo link was down for the
  whole run.

## Result

Exact match: the right command or item, and every argument right. Three runs each.
- **same-cap:** the 28 questions both menus can express.
- **cli-only:** the 4 questions that need `mail read`, `nine-b judge` or a meetings guest or sheet filter. For
  condition 1 their gold is the best that menu can do.
- **exact of valid:** leaves out idli-remote's empty or cut-off replies (see "Failure kinds").

| mapper | condition | dev | held-out | all | same-cap | cli-only | none | failed calls | exact of valid | median s | prompt chars |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 9B | 1 today's menu | 71% | 91% | 78% | 76% | 92% | 100% | 0/96 | 78% | 2.6 | 3.0k |
| 9B | 2 CLI schemas | 83% | 97% | 88% | 89% | 75% | 100% | 0/96 | 88% | 3.3 | 3.9k |
| 9B | **3 CLI + man pages** | **95%** | **100%** | **97%** | **96%** | **100%** | 100% | 0/96 | 97% | 3.5 | 6.0k |
| 9B | 1d menu + dates line | 62% | 85% | 70% | 69% | 75% | 100% | 0/96 | 70% | 2.5 | 3.2k |
| 9B | 3d man pages + dates line | 89% | 100% | 93% | 92% | 100% | 100% | 0/96 | 93% | 3.8 | 6.2k |
| idli-remote | 1 today's menu | 83% | 79% | 81% | 87% | 42% | 67% | 7/96 | 88% | 1.7 | 3.0k |
| idli-remote | 2 CLI schemas | 92% | 85% | 90% | 90% | 83% | 87% | 10/96 | 100% | 1.6 | 3.9k |
| idli-remote | **3 CLI + man pages** | **95%** | **91%** | **94%** | **93%** | **100%** | 87% | 6/96 | **100%** | 1.3 | 6.0k |
| idli-remote | 1d menu + dates line | 75% | 73% | 74% | 79% | 42% | 61% | 13/96 | 86% | 1.5 | 3.2k |
| idli-remote | 3d man pages + dates line | 97% | 91% | 95% | 94% | 100% | 80% | 5/96 | 100% | 1.3 | 6.2k |

Noise: for idli-remote, one run varied by up to 3 questions on dev at temperature 0 (16 to 19 of 21 in condition
1). The 9B in condition 3 got the same score in all three runs (20 of 21). The held-out set agrees with dev in
direction. Raw answers are in `results/` and the table is in `results/summary.txt`.

## What it means

- **Do the refactor.** Against today's menu, commands with man pages help both mappers:
  - **the 9B:** from 76% to 96% on same-capability questions, and from 78% to 97% over all;
  - **idli-remote:** from 87% to 93% on same-capability questions; on the replies it actually returned, from 88% to
    100%.

  That clears the plan's bar (3 points outside `cli_only`) for both.
- **Schemas carry most of idli-remote's gain. Examples carry the 9B's.**
  - Moving to commands with arguments (condition 2) fixed idli-remote's mapping. All of its valid answers were
    right.
  - The 9B gained another 7 to 9 points from the man pages: 88% to 97% over all.
  - The examples must use real dates. In the first version, the 9B copied the placeholders `<today>` and
    `<2 days ago>` into its answers.
- **The capabilities matter on their own.** idli-remote got 42% on the `cli_only` questions with today's menu and
  100% with the CLI (full email, a judgement over a step, meetings with a guest).
- **Don't add a worked-out dates line.** It made both mappers worse (3 to 8 points). The 9B still put "since
  Monday" on the 17th with the line in front of it.
- **Cost:** the prompt roughly doubles (3.0k to 6.0k characters). The 9B's median rises by about 0.9 s (2.6 s to
  3.5 s). idli-remote stays at about 1.3 s.

## Failure kinds

**The 9B with today's menu:**
- it answers "none" to broad questions ("all emails from today", "which emails are new since yesterday") because
  the menu reads as the Mini's own scope (q02, q05);
- it puts `from:SHEET_1` in the Gmail query beside `from_sheet` (q01, q09, q25), which would match nothing;
- it picks step 2 unchanged for "the last 2 days", because steps can't be narrowed (q21);
- it says "none" for "meetings this month" because the Mini covers this week (q31).

All of these go away with commands, where steps take overrides and commands are general tools.

**The 9B, still with CLI:**
- "since Monday" became 2026-11-17 in every run (q09), a date-arithmetic slip;
- "since yesterday" was occasionally read as today.

**idli-remote, all conditions:**
- **Empty or cut-off replies:** 5 to 14% of calls. The model reasons, and production's `max_tokens` 400 runs out
  before or during the JSON, so `map_service` crashes on `None` or can't parse the reply. **This is a production
  bug today.** Raise `max_tokens` (about 1000), or turn off reasoning for this call.
- "Which leads have not replied at all" (q24) fails mostly through those empties.
- "Yesterday" is read as two days (q25).

**Gold fixes during the run** (in PLAN.md) were applied to every condition, before the held-out run.

## Caveats

- 32 questions, one sandbox, and 3 Minis.
- The CLI commands and their gold were written by the same person (me). The held-out set limits how far that can
  tilt the result, but doesn't remove it.
- Condition 1 is production as it is. Its `from_sheet` argument and rules were added yesterday for exactly the
  q01 kind.
- Not covered: insights data Minis (saved questions with options and SQL), which already have this shape.

## Follow-up

A 4th condition will be a uniform kubectl/gh-style grammar (owner, via the coordinator). It reuses this harness
(`menus.prompt`, `FAMILY` in `bench.py`) and the frozen held-out set, scored once per condition.
