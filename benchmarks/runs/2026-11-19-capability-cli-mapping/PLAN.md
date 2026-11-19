# Do CLI capabilities with man pages map partial questions better? (plan, written before any run)

2026-11-19. The owner's question: if each capability were a command with arguments and a short man page, would
idli-remote and the 9B map partial questions about a Mini better than today's menu? This is a small check before the
refactor. No production code changes.

## Questions

`questions.json` has 32 questions over the three Minis in the leads sandbox `merry-parrot-7ac1`:
- **Lead replies in steps:** 6 named steps;
- **Lead replies:** no steps;
- **My meetings this week:** 3 steps.

16 questions come from the owner's own chats on 2026-11-18 and 19. The other 16 are variations:
- narrow and broad versions ("lead replies" against "all emails");
- dates ("since Monday", "next week", "yesterday", "tomorrow");
- one lead;
- one step;
- 6 things the Mini can't do, where the gold answer is none.

The questions are masked as the mapper sees them: `EMAIL_001` and `NAME_001` for the lead, and `SHEET_1` for the
sheet.

**Gold:**
- **The answer:** the item or command plus its argument values, or none. Each question has acceptable alternatives
  for today's menu (`gold1`) and for the CLI (`gold23`).
- **The date:** fixed at Thursday 2026-11-19, IST.
- **`cli_only` questions:** 4 questions (q14, q16, q23, q31) need something only the CLI has:
  - the full email (`mail read`);
  - a new judgement (`nine-b judge`);
  - a guest or sheet filter on meetings.

  For condition 1 their gold is the best that menu can do, or none. They're reported separately, so the comparison
  "same capabilities, different format" stays clean.

**Not covered:**
- **Insights data Minis.** Their production path already uses saved questions with options (minimap, 84 of 85
  earlier) and SQL from idli-remote. Their shape is already the CLI shape.

## Split

- **Held out:** 11 questions, chosen by hash before any run (`split.json`): q03, q11, q12, q20, q22, q23, q24, q25,
  q26, q28, q30.
- **Hash:** sha256 of the held-out questions and their gold is `6afc844f10b725e4...` (in full in `split.json`).
- **Tuning** of the man pages and system prompts happens on the 21 dev questions only. The held-out set is scored
  once, at the end.

## Conditions

1. **Today's menu:** production's `lib/miniscope.menu_text` and `MAP_SYSTEM`, with the Mini's real steps, the
   sandbox's blocks and the fixed date. It includes `from_sheet`.
2. **CLI schemas only:**
   - the Mini written as a chain of commands, with the arguments each step may change;
   - the commands, each with its synopsis and arguments: step, whole, sheet rows, mail search, mail read, calendar
     meetings, calendar free, and nine-b judge;
   - a system prompt that mirrors `MAP_SYSTEM`'s rules.
3. **Condition 2 plus a short man page:** one line on what each command does, and 1 to 3 examples. The examples
   must not copy any benchmark question.

The menus are in `menus.py` (run `python menus.py steps` to print all three).

## Mappers

- **idli-remote:** the same model, endpoint, temperature 0 and JSON mode as `miniscope.map_service`.
- **The local 9B:** the same endpoint and call as `miniscope.map_local` (`routines.judge`, with the JSON schema).

Each question runs once per mapper and condition. Noise is estimated with a repeat of 8 dev questions × 3 runs.

## Scoring

- **Exact:** the right item or command (or none), and every specified argument right. Dates are compared as days.
  Gmail query words in condition 1 are parsed:
  - `from:` becomes from;
  - `after:` and `newer_than:Nd` become since;
  - `before:` becomes until;
  - any other words become text.

  A "null" argument must be absent. One item may be enough even if two are given: the first matching item counts,
  if the other doesn't contradict it.
- **Partial:** the right item with wrong arguments.
- **Also counted:** accuracy on the none questions, latency per call, and prompt size.

## Decision rule

- **Worth the refactor:** if condition 3 beats condition 1 by 3 or more points on dev and held-out together, outside
  the `cli_only` questions, for the 9B or for idli-remote.
- **Not worth it:** if they're within noise, the gain is only the capabilities (the `cli_only` questions). That can
  be had by adding arguments to today's menu.
- **Examples:** if condition 3 beats condition 2, the man pages earn their keep.

A handful of chosen commands are run end to end on the 87 and 88 accounts, read-only, to check the outputs fit the
questions.

## Changes during the run (recorded as they happened)

- **Harness:** idli-remote sometimes returns no content. The model reasons, and with production's `max_tokens` 400
  the reasoning can use up the whole budget. The benchmark retries once and counts these. It's a production finding
  in its own right (`miniscope.map_service`).
- **Gold fixes** after the first dev run, before any held-out run (applied to every condition and mapper, recorded
  in `questions.json` "gold_fixes", new held-out hash in `split.json`):
  - in the meetings Mini, step 2 with start/end overrides is a valid CLI answer (q29, q30, q31);
  - step 2 with a text override is valid for q15;
  - "this week" may mean the last 7 days (q10, q27).
- **Dev tuning of condition 3:**
  - The 9B copied `<today>` and `<2 days ago>` from the examples into its answers. The examples now use real dates
    for 2026-11-19, which code would fill in at run time.
  - Example wording was kept away from benchmark questions.
- **Added variant `d`** (conditions 1d and 3d): one line of worked-out dates ("This week: Monday 2026-11-16 to
  Sunday 2026-11-22. Yesterday..."). Code could compute it at run time. It's tested on its own, because it helps any
  menu, not just the CLI.
- **Follow-up condition (owner, via the coordinator):** a uniform kubectl/gh-style grammar (`verb resource
  --flags`: get, list and describe plus a few domain verbs, common flags such as --since, --limit, --as and -o,
  selectors, and Mini-defined resources such as "leads" and "replies").
  - It will be a 4th condition in this harness: a menu builder in `menus.prompt`, a `FAMILY` entry in `bench.py`,
    and a translation of its answers into the canonical items.
  - Gold stays canonical, so the frozen held-out set is reused as is, scored once per condition.
