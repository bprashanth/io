# Record store scaffold: blind task bank, graded rounds, blind testers

2026-11-19 to 2026-11-20. Tests the model in `narrative/GOALS_v0.md` and `narrative/EXAMPLES_V0.md` headless, on
the real test accounts. The model has four layers: connectors, a DuckDB record store per sandbox, definitions
judged by the 9B, and chains. The plan, frozen before building, is in [PLAN.md](PLAN.md).

## What was built

`cowork/lib/recstore.py`, `cowork/lib/idlicli.py`, `cowork/desktop/idli`. Try it with
`IDLI_SANDBOX=<dir> desktop/idli --help`.

```
idli sync [mail|events|files|sheets|all]       Gmail, Calendar, Drive, every spreadsheet (read only, the APIs)
idli list|count RESOURCE [--where ..] [--on yesterday] [--since 7d] [--in FOLDER] [--search ..] [--label DEF=VAL] [--by FIELD]
idli get mail|thread|event|file REF ; idli describe file|sheet REF ; idli read|summarise file REF
idli define NAME --on mail|event|file|photo --ask ".." --answers yes,no   ; idli judge RESOURCE --def NAME
idli query "SELECT .." ; idli view NAME --sql ".." ; idli date "next monday" ; idli draft mail ... (preview only)
idli ask "question"                            the left chat: mapper -> commands -> run -> 9B reply
```

- **The store:**
  - **Rows:** one per email, event, Drive file and sheet. Every spreadsheet is its own table.
  - **Labels:** one table, keyed by kind, record, definition and version.
  - **Bounds:** email bodies capped at 8 KB, file text at 60 KB; mail is the last 60 days, events ±60 days.
- **Dates are worked out in code:** `day_range`, plus a `dates_note` given to the mapper.
- **`ask`:**
  - **Mapping:** the mapper returns idli commands. It is idli-remote (DeepSeek through OpenRouter, given the
    whole prompt masked once by production `mask_account_text`) or the local 9B.
  - **Running them:** Idli runs the commands. There is one repair round with the error, and up to two
    `continue` rounds, in which the mapper sees results before writing the rest. A placeholder like
    `<thread_id>` triggers one.
  - **The reply:** the 9B writes 1 to 3 sentences answering what was just said, above the rows. A number that
    isn't in the result throws the wording away.

## How it was tested

- **Task bank:**
  - **Written blind:** Cursor `agent` in the bwrap wall saw only a person-level brief and GOALS_v0 section 1.
  - **Size:** 80 tasks. Dev has 53 (10 trust, 20 own definition, 13 own workflow, 10 other site); held-out has
    27, frozen by hash.
  - **Held-out** was run once, on frozen code (commit 11844101).
- **Grader:** a separate Cursor `agent` session per run, in the wall. Its only tool is read-only SQL on that run's
  store, so it checks answers against the data. It grades coverage, correctness, fit, acknowledgement and
  repetition (`grader/RUBRIC.md`).
  - Held-out was graded by fresh sessions that never saw dev.
  - Graders differ between rounds, so differences of 1 to 3 tasks are noise.
- **Blind testers:** Cursor `agent` personas in the wall with only `./ask`, on a fresh copy of the store, going
  simple first, then a few steps, then the workflow, and stopping at the first failure.

## Results

**Coverage** (does the design express the ask?), dev and held-out alike:
- **Expressible with the existing layers:** 39 to 40 of 53 dev tasks, and 19 of 27 held-out. That is every
  trust and own-definition task.
- **New connector:** all other-site tasks (WhatsApp, Slack, Canva, LinkedIn, Amazon, funder portal), and a Slack
  draft.
- **New write action:** move, rename, post.
- **Design miss:** only "every Monday" (a schedule) in round 1.

**Correctness, dev, idli-remote** (round 1, then 2, then 3, with general fixes between):

| kind | r1 correct | r2 correct | r3 correct + partial | r3 wrong or failed |
|---|---|---|---|---|
| trust (10) | 8 | 9 | 9 + 1 | 0 |
| own definition (20) | 19 | 18 | 12 + 8 | 0 |
| own workflow (13) | 3 (6 failed) | 1 + 3 partial | 2 + 6 (3 refused ok, 2 refused wrong) | 0 |
| other site (10) | 10 refused ok | 10 refused ok | 10 refused ok | 0 |

**Correctness, dev, the 9B mapper:**
- **Round 3:** trust 6 of 10, definitions 11 of 20 (+6 partial), workflows 2 of 13 (4 wrong, 4 failed).
- **Round 1:** 19 of 53 correct.

**Held-out** (27 tasks, frozen code, separate graders):

| mapper | correct | partial | wrong | refused ok | refused wrong | failed |
|---|---|---|---|---|---|---|
| idli-remote | 13 | 4 | 1 | 8 | 0 | 1 |
| 9B | 5 | 6 | 6 | 8 | 1 | 1 |

Held-out by kind for idli-remote:
- trust: 4 of 5 correct;
- own definition: 9 of 10 correct, plus 1 partial;
- own workflow: 3 partial, 3 correct refusals, 1 failed;
- other site: 5 of 5 correct refusals.

Its one wrong answer (T55) said "1 document" for a count of 0. The number check always allows 1, 2 and 3, a
loophole to close. Its fit was 4.5, acknowledgement 4.8 and repetition 4.6.

**Reply quality**, scored 1 to 5 by the grader:
- **idli-remote, dev round 3:** fit 4.2, acknowledges corrections 4.6, not repetitive 4.1.
- **9B, held-out:** 3.6, 3.6 and 4.2.
- **Round 1** had "Would you like..." at the end of most replies and talked about "rows" and seconds. The style
  rules fixed that for idli-remote's turns. The 9B mapper still sometimes tells people to run commands.

**Speed:**
- **A turn without judging:** median 4.2 to 4.4 s (idli-remote) and 5.0 to 7.5 s (the 9B). Turns were 25 to 47 s
  when four sessions shared the 9B.
- **First judging of a category over all Drive files:** 5 to 7 minutes, because it reads each PDF once. Repeat
  questions are cached.
- **9B judging per dev run:** 4 to 20 minutes in all.

**Store size:**
- **Contents:** 13 MB for 188 emails, 10 events, 191 files, 23 sheets (five of 1,876 rows), 120 extracted file
  texts and about 1,000 labels.
- **The sync** of 87's account took about 2 minutes, with retries for Gmail's per-minute quota.

## Blind testers (frozen or near-final code)

| session | world, persona, mapper | stage 1 (simple) | stage 2 (few steps) | stage 3 (workflow) | where trust broke |
|---|---|---|---|---|---|
| L1 | leads, coordinator, remote | trusted (after "hi" and "what can you read" were refused; since fixed) | trusted after one rephrase ("who hasn't replied") | broke | draft to a lead with no thread went to another address (fixed: draft must match one conversation or `--to`) |
| L2 | leads, programme lead, 9B | trusted | trusted | broke | the five-lead summary left one lead out; on rephrase it was still vague with no message content |
| I1 | insights, researcher, remote | trusted | broke, then recovered | — | a 96-page PDF summary outran the tester's patience; the late answers were right (fixed: parts in parallel) |
| I2 | insights, researcher, remote | trusted (folders, kinds, 116 columns, PDF gist) | trusted (top answers per question, 2021 and 2025) | broke | the cross-year trend said the 2025 data was missing, contradicting earlier answers |
| D1 | own categories, finance, remote | broke | — | — | refused "what day is next monday" after its help showed that date (fixed: `idli date`) |
| D2 | own categories, finance, remote | trusted | partial | — | first "needs attention" took 150 s; "mail from people" counted my own sent mail; it noted that saving a category is stored state, not a pure preview |

No tester read files or explored. The only other tool calls were the agent polling its own long-running `./ask`.

## What it says about the goals

1. **The record store plus definitions carries the "own definition" kind well.** Coverage was 100%, and with
   idli-remote no answer was wrong or failed on dev round 3: 12 of 20 fully correct, 8 partial. Define, then judge
   (once per item, cached), then list with `--label` was general enough for urgent, conservation, caste, GRE prep,
   people in photos, workshop notes, funder meetings and newsletters. No per-question code was added.
2. **Trust questions work.** Folder counts, sheet columns, dates and meetings are 9 to 10 of 10 with idli-remote.
   Dates worked out in code removed the old date misses.
3. **Own workflows are the weak layer.** Joins across leads, mail and calendar, "who needs a follow-up", and
   multi-source analysis are only partial even with idli-remote. They fail with the 9B. The mapper can write the
   SQL, but a request phrased about people ("my leads") needs a definition of those people.
   - That is exactly a Mini's views, `leads` and `replies` (EXAMPLES_V0), which this blank sandbox didn't have.
   - Testers broke at this stage every time.
   - The next layer to build is Sandbox Claude writing views and chains, then the mapper filling in values. The
     mapper alone should not compose workflows from scratch.
4. **Other sites are cleanly "new connector",** and the refusal now says what would make it possible.
5. **The 9B as mapper is not enough for open asks.** It's fine for trust questions, weak for definitions and poor
   for workflows. As earlier, it should fill values in a known chain, not plan.
6. **Costs:**
   - the store is small (13 MB);
   - first-time judging of a whole Drive is minutes;
   - per-turn latency is about 5 s.

   The cost to design around is judging, which needs narrowing filters first, and progress shown to the person.

## Not done

- Laptop: not synced. Nothing here is wired into the app, and the workflow layer isn't ready.
- No Sandbox Claude step: analysis across sources went only as far as the mapper could compose.
- Grader noise: a single grade per run.
