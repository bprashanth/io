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

Not run on the laptop: the laptop link (Paseo daemon tunnel and CDP) dropped at about 21:45 IST, before the
insights round and the final Drivey check.

- **Insights folder:** not run. The Dryad set the owner named needs a login now, so I picked a public one with a
  report and data from two years: the NDSA Fixity Survey (Zenodo, CC BY 4.0), 2021 report PDF and data CSV, then
  the 2025 data to add. Both are downloaded on the DGX. The upload to 87's Drive is scripted (87's Chrome profile,
  Shift+F for the folder, Shift+U with the file chooser answered over CDP) but did not run.
- **PDF masking, run on the DGX on the 2021 report:** 96 pages, the first 150,000 characters masked in 53 s. The
  first run (the name scanner on whole pages) left all 11 authors' names on the cover; the scanner's confidence
  drops with length. Line by line, in parallel, all were coded (NAME_001 to NAME_008 on the cover, one partial).
- **Drivey last:** not run.

## Built (commits)

- b46249da: the chain (`lib/miniscope.py`, `lib/minitalk.py`, `lib/modes.py`), `blocks.run_steps`,
  `blocks.meetings`, `lib/docmask.py`, the fork carries the question, steps kept in mini.json.
- c90c5cc2: the masked preview needs no workspace; a chat without Claude says to press Start Claude.
- 44f65e15: no `builder_open` for Sandbox Claude in a sandbox; opening a workflow Mini lists what it sees and its
  steps.
- ed3d7708: PDF text masked line by line, in parallel, kept per file version.
- Tests: `tests/test_mini_escalation.py` (15). DGX suite: 355 passed, 5 skipped, the same 11 known failures.

## Rough edges

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
