# Blind tester on real data: building trust in a Mini step by step (2026-11-19)

The owner asked for a blind tester who builds trust the way a new user would: simple checks first, then a few steps,
then the whole workflow, failing fast and saying why. It was not to be told about the commands or the code, and not
to cheat. This was run on the real test accounts (87profligate is "me", 88profligate is a lead), read-only and
preview-only. Nothing was drafted, booked, sent or changed in Drive.

## Setup

- **The app's left chat:** `harness.py` plays it for one sandbox.
  - **Leads:** the "Lead replies in steps" Mini.
  - **Insights:** 87's Drive, with no Mini open.

  A question goes the production way, with the grammar of [narrative/CLI_CHOICES.md](../../../narrative/CLI_CHOICES.md)
  (condition 4b):
  1. idli-remote gets the question and menu masked by production's `privacy.mask_account_text`. The local 9B gets
     them as they are, as `miniscope.map_local` does.
  2. The mapper picks one or two `idli` commands.
  3. Codes are put back (`home.rehydrate`), and Idli runs the commands on the real data.
  4. The reply is the output as the code wrote it.
- **Escalation (insights):** when no command fits, a consent turn names the masked question and the files.
  - On yes, Sandbox Claude (headless `claude -p`, no tools) gets the masked material:
    - spreadsheets as masked copies (`privacy.suggest` with Idli's choices, then `maskcopy.build`);
    - PDFs as masked text (`docmask`).
  - Claude writes a script. Idli puts the real values back (`maskcopy.rehydrate_script`), runs it on the real
    files, shows the real output, and gives Claude the output masked. Claude's explanation is unmasked for the
    person.
- **Wire log:** every payload to idli-remote or Claude goes to `wire.jsonl`, checked against the vault's real
  values (`privacy.known_leaks`), the leads' names and emails, and by eye.
- **The tester:** Cursor's `agent` (`wall.sh`) in a bwrap wall. It sees an empty folder holding `./ask`, a
  throwaway home with its sign-in, its own install and the system read-only. It doesn't see the repo, this folder,
  or `~/.config/idlisseus`. A check from inside the wall listed `/home/beeps` as only `.local` (the agent's own
  install).
- **Personas** (`prompts/`): an office coordinator, a programme lead, a sceptical finance head, an M&E officer and a
  sceptical researcher. Each prompt describes only the job and the trust-building rules: simple, then a few steps,
  then the whole thing; at most one rephrase; stop and explain; a trust report at the end.
- **Cheating check:** `analyze.py` lists every tool call that isn't `./ask`.
  - **Flagged but benign:** the agent waiting for, or reading the saved output of, its own long `./ask` calls. In I3
    it also wrapped `./ask` in a small pty script to type "yes" into it.
  - No session read files or explored the machine.
- **Raw transcripts stay out of git.** They hold the test accounts' mail and the names of folders shared into 87's
  Drive. They're in the session scratchpad; this README summarises them.

The harness changed between rounds as the testers found faults in it. Each change is listed below, with whether
the fault was in the harness or in the product.

## Results, per stage

C = correct, P = partial, W = wrong, R = refused correctly. "First failure" is the first answer that wasn't C.

### Leads

| Session | Mapper, persona, harness | Stage 1 (simple) | Stage 2 (few steps) | Stage 3 (whole) | First failure, and where trust broke |
|---|---|---|---|---|---|
| L1 r1 | remote, coordinator, v1 | "which sheet and columns": P (rows, no headers), then W (refused) | not reached | not reached | Stage 1: questions about the Mini itself had no `explain` |
| L2 r1 | remote, programme, v1 | one W (idli-remote returned no JSON) | `run mini`: P (drafted for already answered threads, a harness bug) | not reached | Stage 2 |
| L3 r1 | remote, finance, v1 | sheet: C; "date range": W ×2 (a dump of replies, no range) | not reached | not reached | Stage 1: no `explain` |
| L1 r2 | remote, coordinator, v2 | explain: C; leads: C | per-lead replies: W (one sender's threads, no "no reply from" line) | not reached | Stage 2: no per-person view |
| L2 r2 | remote, programme, v2 | `run mini`: C | Asha: W (Gmail quota, from parallel sessions); then no JSON | not reached | Stage 2, harness |
| L3 r2 | remote, finance, v2 | preview: P ("Nothing was drafted" under draft text; booking time didn't match, a harness bug) | not reached | not reached | Stage 1: wording |
| L4 r2 | 9B, coordinator, v2 | explain, leads, replies: C ×3 | classify the newest per lead: W ×2 (Gmail quota) | not reached | Stage 2, harness |
| **L5 r3** | remote, coordinator, v3 | steps: C; "what wouldn't change": P (answered with the whole preview) | classify: P (every thread, answered ones too); one row per lead: W (refused) | not reached | **Stage 2: no per-person view** |
| **L6 r3** | remote, finance, v3 | date range: C; sheet and fields: C | decide rules: C; agreed, no time: C (step 4) | picked-time event: C (already booked, so it would skip); full preview: C | **None. "Yes, with caution"; it wants a per-lead preview** |
| **L7 r3** | 9B, programme, v3 | "who would it follow up with": W (refused); four branch questions: P (the whole explain page each time) | draft: C; Asha: P (the whole preview, not her part) | Ravi: W (all replies, the filter ignored); Ravi only: W (refused; right answer: he hasn't replied, so nothing happens) | **Stage 1 refusal; trust broke on one person, one next step** |

Round 3 (v3, the final harness) is the fair reading:
- idli-remote passed the sceptical finance head end to end.
- Both other personas broke at stage 2 or 3 on the same missing thing: **one person at a time**.

### Insights (87's real Drive: "NDSA fixity study", "Strategy Classics")

| Session | Mapper, persona, harness | Stage 1 (simple) | Stage 2 (few steps) | Stage 3 (analysis) | First failure, and where trust broke |
|---|---|---|---|---|---|
| I1 r1 | remote, M&E, v1 | folder contents: C ×2; columns (26; 116): C ×2; PDF summary: C (94% and 96% checked in the report) | top 5 takeaways: C; 2021 against 2025 through Claude: P (first output raw comments), then C (counts per year, Q1/Q3/Q5) | synthesis: P (said the 2025 summary extraction was empty) | Stage 3: the PDF's executive summary didn't extract; "not yet" |
| I2 r2 | 9B, researcher, v2 | folder, columns, PDF summary: C ×3 | Strategy Classics, workbook columns, themes, 2021 summary: C ×4 | compare reports: W (the harness sent Claude the wrong files; the consent card listed them and the tester caught it) | Stage 3, harness |
| I3 r2 | remote, M&E, v2 | folder, columns ×2: C ×3; compare two workbooks: escalated (fine) | "what does it record, what are the DBH columns": consent to Claude ×3, never sent | inconclusive | Stage 2: interpreting a spreadsheet needed Claude, and consent as text confused the tester |

### Leaks and masking (wire check)

- **No real email address, IP address or lead name** reached idli-remote or Claude in any session.
  - The leads' names were coded in questions ("show me NAME_001's latest email").
  - The survey CSVs' IP address and recipient columns were coded or empty.
- **A real leak, found and fixed.**
  - The 2025 NDSA report's text came out of pypdf one word per line, so production's line-by-line name scanner
    missed 9 author names, and they reached Claude.
  - Fixed in `lib/docmask.py`: join the word runs, scan long lines in 70-character windows and each comma piece
    (commits a3832691, 3daeae35, tests in `tests/test_docmask.py`).
  - Left: "Kari May" ("May" reads as a month).
  - I1 ran between the two fixes and also sent "Krista Oldham".
- **Over-masking:** "fixity from" in a question became `VALUE_070` (a cell value learned from the CSV), and "Texas
  A&M" became "Texas PLACE_001&M". The `A` "leaks" in the wire log are false positives from that one-letter vault
  value.

## What it means

1. **The grammar can't yet do "one person at a time", and that's where trust broke.** Every persona who got past
   stage 1 asked about one lead: "what happens next for Ravi", "one row per lead", "who would it follow up with
   today". The Mini's steps are per thread, and no command filters by person or joins the sheet to the replies.
   - Add `get lead NAME`: their row, newest reply, its class and the next action, or "no reply, nothing happens".
   - Add `--where lead=NAME` on `run step` and `run mini`.
2. **`explain` is what stage 1 rests on.** Without it (rounds 1 and 2), "which sheet, which columns, what date
   range" got data dumps or refusals. With it, every such question was right in round 3. It should answer the one
   step or rule asked about; the 9B returned the whole page each time.
3. **Previews must say "would".** "Nothing was drafted" under draft text read as a contradiction. "Would draft (not
   saved to Gmail)" and "A preview: nothing was saved or sent" didn't draw a complaint. Production's footer says
   "Nothing was drafted, booked or sent" and should change the same way.
4. **Two definitions of "replies" confuse people.** Step 2 drops answered threads, but the `replies` view and
   `judge replies` didn't. Make the view match the Mini's step, and mark "(already answered)" where both appear.
5. **Insights stage 1 and 2 hold up**, for both mappers: folder contents, columns, PDF summaries and themes.
   - `summarise` should cover spreadsheets too, with the 9B reading the columns and a few rows here. Otherwise
     "what does this dataset record" needs Claude.
   - Same-named folders must be called out (two "Strategy Classics").
6. **Escalation works, and the consent card is the safeguard.**
   - Claude's analysis ran on masked copies and its script ran on the real files.
   - The comparison between years was right and specific.
   - When the harness picked the wrong files, the tester caught it from the card's file list.
   - Consent has to be a card with buttons, as in production. Typed "yes or no" confused one tester.
7. **The 9B and idli-remote differ the same way as in the benchmark.** idli-remote filled filters and dates better.
   The 9B was faster but refused more ("who would it follow up with today").
8. **Harness lessons:**
   - Run sessions on one account one at a time (parallel runs hit Gmail's per-user quota).
   - Production's `_label_id` creates the `Idli/handled` label if it's missing. The harness looks it up read-only.

## Files

- `harness.py`: the app's chat on the real accounts (`serve`, or `ask` for a one-off).
- `wall.sh`: the bwrap wall around Cursor's `agent`.
- `session.sh`: one session (harness plus tester).
- `prompts/`: personas and the common rules.
- `analyze.py`: per-session summary, cheating flags and wire leaks. Its output holds real values, so it stays out of
  git.
