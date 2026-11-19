# The question chain for Minis: no free 9B (2026-11-18)

The owner's round after "ok lets simplify this". Design: [SANDBOXES.md](../../../narrative/SANDBOXES.md) "Routing in
a sandbox", [ESCALATION_MODELS.md](../../../narrative/ESCALATION_MODELS.md) "The chain". Driven on the laptop over
CDP as a person, in the leads sandbox `merry-parrot-7ac1 leads` with the test accounts 87profligate@gmail.com ("me")
and 88profligate@gmail.com ("a lead"). Gallery: `shots/index.html`.

## The two finds from the owner's explorations

1. **The sheet link in the raw sandbox chat** (`show my list of leads`, no Mini open): the 9B had the account tools
   and no Mini, and made up a link, `1BxiMVs0XRA5nFMdKvBdBZjGMUUqptlbs74OgvE2upms`. That is Google's sample sheet
   from the Sheets API docs, so it got a 404. The leads sheet is only in the Mini's script. Fixed by the rule: a
   question with no Mini open goes to Sandbox Claude (masked), never to the 9B with tools.
2. **"Here is what it found." with nothing under it** (`show me the list of leads`, Mini open): the 9B sorted it as
   a preview, the whole Mini ran, and the 9B's summary of the output came back empty, so the reply had only its lead
   line and footer. Fixed: "see data" questions are mapped (below), and every output is shown as code wrote it,
   never through a 9B summary. The answer is now the sheet's 5 rows (shot 18).

## Results

The sandbox's outside setting was Never; it was set to Ask each time for this round (test sandbox).

| # | Question or action | Route | Result | Time | Shots |
|---|---|---|---|---|---|
| 1 | Drivey, Household debt by ward: "which ward owes the most?" | Mini, as before | Pass, ward table and chart | 9 s | 02, 03 |
| 2 | Leads, no Mini: "which meetings do I have this week?" | Card, then Sandbox Claude (masked) | Pass. Claude wrote a 3-step script with `blocks.meetings`, the person approved `script_try`, the real meetings showed on the left. Claude saw codes. It also spotted 5 back-to-back "Meeting with Asha Verma" bookings on Fri 20 Nov from earlier test runs | card 12 s, answer about 60 s | 09 to 11 |
| 3 | "yes, save it as a Mini" | Claude, `idli_draft_mini`, Save | Pass, "My meetings this week" with its 3 steps | 15 s | 12, 13 |
| 4 | Lead replies: "how are leads picked?" | 9B direct (explain) | Pass (thin, as before: sheet and the 2-week window) | 9 s | 16 |
| 5 | "show me the list of leads" | Mapping card, Yes: the outside service picked the sheet | Pass, 5 rows | card 6 s, answer 9 s | 17, 18 |
| 6 | "show me all my meetings from yesterday" | Card, Yes: the calendar for Tue 17 Nov | Pass, "No meetings" (correct) | 8 s | 19 |
| 7 | "which emails are new since yesterday?" | Card, "No, Idli picks": the 9B mapped it to a Gmail search | Pass, 19 emails with dates in IST | 18 s after the card | 20 |
| 8 | "show me the draft you would write for Asha" | 9B direct (whole preview) | Pass: the full draft; it also showed the Mini's bug, "would book" a "Declined: Meeting with Asha Verma" notice | 44 s | 21 |
| 9 | "what would step 2 produce?" (old Mini, no steps) | Plain command, no step 2 | Pass: "runs as one piece", Fork card | 3 s | 22 |
| 10 | Fork it | Sandbox Claude with the masked question | Pass: it laid out 6 steps, proposed splitting the script | 18 s | 23 |
| 11 | In the fork: "do that, and skip calendar notices" | Claude edits, `script_try` step 2 | Pass: step 2 alone on the left, the Declined notice skipped, 10 replies listed | 1 min 45 s | 24, 25 |
| 12 | Save as "Lead replies in steps" | Save on the card | Pass: a new Mini with 6 step titles, `forked_from` the original | about 2 min (the save check runs the whole Mini) | 26, 27 |
| 13 | New Mini: "run step 1" | Plain command | Pass, 5 leads | 3 s | 29 |
| 14 | "run step 3" | Plain command | Pass, the 9B's reading of 10 replies | 71 s | 30 |
| 15 | "which leads agreed but have not picked a time yet?" | Card, Yes: the service picked step 4 | Pass, the one draft in full | 94 s | 31 |
| 16 | "also post each booked meeting to our Instagram page" | 9B: change, Fork card, Fork | Pass on the chain: Claude said only the Builder can add an Instagram block. **Bug found:** it then opened the old per-team Builder beside itself; interrupted before it wrote anything. Fixed: no `builder_open` for Sandbox Claude in a sandbox | 32 s | 32 to 34 |

The laptop link dropped at about 21:45 IST; the owner reopened it and the rest ran at 23:00 to 23:55.

### Insights: a report PDF and data in one folder, then a second year

The Dryad set the owner named needs a login now, so this uses a public one with a report and data from two years:
the NDSA Fixity Survey (Zenodo, CC BY 4.0). The files were put in a folder "NDSA fixity study" in 87's Drive through
87's Chrome profile, and the Drive index was rebuilt. Sandbox: `lucky-koel-7672 drivecharts` (outside service: ask).

| # | Question or action | Route | Result | Time | Shots |
|---|---|---|---|---|---|
| 17 | `@NDSA fixity study` "help me analyse this study: how often do organisations check fixity, and what charts would show it?" | drive_fetch: the CSV for review, the PDF as masked text | Pass: "using NDSA 2021 Fixity Survey Data.csv. Also the text of 1 PDF ... with names, places and numbers as codes." Privacy page as before | 230 s the first time (most of it masking 96 pages), 83 s later | 36, 37, 39 |
| 18 | Switch to Claude | Handoff with the docs note | **Bug found:** the first try lost the PDF note after the privacy review. Fixed (c4225579). Second try: Claude got "Also the text of 1 PDF, masked by Idli: docs/NDSA 2021 Fixity Survey Report.txt", read it, and checked its counts against the report's | 1 min | 38, 40 |
| 19 | The PDF reached Claude masked | Claude's folder and the wire log | Pass: the cover's 11 authors are NAME_049 to NAME_057 (one partial, "NAME_057'homme"); no author name in the text Claude has | n/a | n/a |
| 20 | "make A and B, show them on the left, save as a Mini Fixity checks 2021" | Claude, idli_show, idli_draft_mini | Pass: two charts on the left (intervals; checks after events), saved as "Fixity checks 2021" with 2 questions. Its charts list is empty: the pins didn't reach the draft | about 4 min | 41 to 45 |
| 21 | Open the Mini: "how often do organisations check fixity on stored files?" | 9B maps to the Mini's question | Pass | 7 s | 47 |
| 22 | With the Mini open, `@2025 data` `@2025 report` "redo the check interval chart with 2025 next to 2021" | Masked handoff with the Mini as context (6dbab66e) | Pass: Claude got the 2025 CSV, the 2025 report's masked text (11 names coded) and "Mini context: Fixity checks 2021", and drew 2021 vs 2025 as shares | fetch 115 s (masking the 2025 report), Claude 2.5 min | 48 to 50 |
| 23 | "do the same for checks after events, save as a new Mini Fixity checks 2021 and 2025" | Save card: Add to the Mini, or Save as a new Mini | Pass: "Save as a new Mini" made "Fixity checks 2021 and 2025" with 2 comparison questions; the 2021 Mini is unchanged | 1.5 min | 51, 52 |
| 24 | Drivey last: "which ward owes the most?" | Mini, as before | Pass, the ward table. (A misclick first opened "Invasive plants"; its out-of-scope card was the same as before) | 16 s | 53, 54 |

Laptop suite: 356 passed, 5 skipped, the same 11 known failures.

- **PDF masking, measured on the DGX first** on the 2021 report: 96 pages, the first 150,000 characters masked in
  53 s. The name scanner on whole pages left all 11 authors' names on the cover (its confidence drops with length);
  line by line, in parallel, they were coded.

## Built (commits)

- b46249da: the chain (`lib/miniscope.py`, `lib/minitalk.py`, `lib/modes.py`), `blocks.run_steps`,
  `blocks.meetings`, `lib/docmask.py`, the fork carries the question, steps kept in mini.json.
- c90c5cc2: the masked preview needs no workspace; a chat without Claude says to press Start Claude.
- 44f65e15: no `builder_open` for Sandbox Claude in a sandbox; opening a workflow Mini lists what it sees and its
  steps.
- ed3d7708: PDF text masked line by line, in parallel, kept per file version.
- c4225579: the PDF note survives the privacy review.
- 6dbab66e: files added while a data Mini is open go to Claude with that Mini as context.
- Tests: `tests/test_mini_escalation.py` (16). Suites: DGX 355 passed, laptop 356 passed, 5 skipped each, the same
  11 known failures.

## Rough edges

- **Masking a long PDF is slow the first time** (1 to 3 min for a 100-page report); kept afterwards.
- **Pinned charts didn't reach the first Mini draft**; the saved Mini has its questions but no pinned charts.
- **The 2021 and 2025 Mini lists only the 2025 file** as its files (its scripts read both).

- **Slow late steps:** a step after "read each reply" takes 70 to 95 s, because the 9B reads every reply on every
  run. Keep step results for a few minutes, or keep the 9B's reading per message.
- **The menu is long on the card** (the whole list shows). Fold it under "What it gets".
- **Times in step output are UTC ISO** when the Mini's own script prints them (`2026-11-18T11:11`); the blocks'
  own reads are local.
- **New chats from Paseo's plain "New workspace" form** have no Idli label, so Claude can't be found for them
  ("Press Start Claude"). The sidebar's + is fine.
- **The sandbox start card** says "Ask about your Drive files" in a leads sandbox.
- **Mini saves run the whole Mini** as a check (about 2 min for the leads one).
- **Test data:** 5 duplicate "Meeting with Asha Verma" events on Fri 20 Nov in 87's calendar from earlier runs.
- **"My meetings this week" was saved by the old page server**, so its steps were copied from its draft by hand;
  page servers were restarted and the next save ("Lead replies in steps") kept them on its own.

## Round 2026-11-19: script_try asks in the left chat; searches fit the question

Owner's asks:
- Claude Code's prompt for `script_try` ("Script Try Tool", "Rule ... overrides auto mode") was unreadable.
- "show me this morning's lead replies" got a LinkedIn notice and a calendar decline.

Code: `lib/tries.py`, `lib/idli_mcp.script_try`, `lib/modes.py` (Try cards), `lib/miniscope.py` (from_sheet).

| # | What | Result | Shots |
|---|---|---|---|
| 1 | Lead replies Mini: "show me this mornings lead replies" | The idli-remote card, Yes. The search was scoped to the people on the leads sheet, with calendar notices left out. "No emails match" is correct: 88's last reply was yesterday 4:41 PM | 56, 57 |
| 2 | "show me all emails from today" | A broad search, `newer_than:1d`, as asked. LinkedIn, the decline (marked "a calendar notice") and 88's reply | 58 |
| 3 | Sandbox Claude: "write a script that lists my leads, run it with script_try" | No Claude Code prompt; the right pane only showed "Calling idli". The left chat showed gate 1: "Claude wants Idli to read more from your accounts: List my leads. Nothing is written." | 59 |
| 4 | Gate 1 Yes | The real list ran on the left. Gate 2 showed "Claude would get this, with private values as codes" with the masked sample | 60 |
| 5 | Gate 2 Yes | "Sent to Claude". Claude got the masked output and described it | 61 |
| 6 | "add each lead's email and run it again", gate 1 Yes, gate 2 **No** | "Not sent". Claude said it can't check the results itself, and asked the person whether the list on the left looks right | 62, 63 |

Found by gate 2, as it should be:
- The masked sample showed `NAME_001 Verma`. A surname stays unmasked in account text when only the first name is a
  known value.
- Before this round that line went to Claude unseen. Now the person sees it and can say No.
- Masking account text needs the full-name rule that files have (open item, not fixed here).

Also: "today" maps to `newer_than:1d`, which is the last 24 hours, so it includes yesterday evening.
