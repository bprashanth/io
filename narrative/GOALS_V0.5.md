# Goals v0.5: the core of Idli Desktop, as of 2026-11-20

**Superseded by [GOALS_V0.6.md](GOALS_V0.6.md) (2026-11-21): the scaffold as built and tested.** Kept as written.

This is the current thinking. Read it first. It builds on [GOALS_v0.md](GOALS_v0.md) (the goal and the four
layers) and [EXAMPLES_V0.md](EXAMPLES_V0.md) (worked examples), and adds what the scaffold and the benchmarks have
shown since.

Other documents:
- [IDLI_DESKTOP.md](IDLI_DESKTOP.md) describes the product around this core: Paseo, the Builder, sandboxes,
  Minis, masking.
- [CLI_CHOICES.md](CLI_CHOICES.md) explains the command design and its references.

---

## 0. In one paragraph

Idli lets people at NGOs use AI on their real accounts and files without handing that data to an AI company. The
data stays on their computer, in a **sandbox**: a folder holding a small local database of their emails, events,
files and sheets. Questions are answered by a **small private model** (the 9B) and plain code, on the real data. A
**larger outside model** helps, but only ever sees masked text, where names and emails are replaced by codes. That's
either **idli-remote**, a cheap model that picks commands, or **Sandbox Claude**, which writes new workflows. Work
that is worth keeping is saved as a **Mini**: a named, checked recipe the small model can rerun and answer questions
about. Everything inside a sandbox is expressed as a small set of commands (`idli list`, `idli judge` and so on). That
is what makes it possible to check, explain, extend and trust.

---

## 1. Words used here (no jargon without this table)

| Word | Plain meaning |
|---|---|
| **Sandbox** | A folder on the person's computer for one area of work (for example "leads", "survey"). It holds the store, the Minis and the settings. It only reaches the accounts and tools it was set up with. |
| **Store** | One DuckDB database file in the sandbox (`store.duckdb`). DuckDB is a small database that lives in a single file, like SQLite but built for counting and filtering ([duckdb.org](https://duckdb.org/docs/)). |
| **Record** | One natural item: one email, one calendar event, one Drive file, one spreadsheet row, later one WhatsApp message. One row in the store. |
| **Connector** | The code that copies records from a place (Gmail, Drive, later WhatsApp) into the store. Read only. Command: `idli sync`. |
| **Definition** | A category the person invents, which only a model can apply: "about conservation", "urgent", "has an animal in it". It is a question with fixed answers (`yes,no`, or `bird,mammal,none`). |
| **Label** | The answer a definition gave for one record, kept so it is computed once. Command: `idli judge`. |
| **View** | A **saved, named list**: "my leads" means the Name and Email columns of the leads sheet; "replies" means emails from a lead, minus calendar notices. It pins down what a word means in this person's work, once, so every later question uses the same meaning. Technically it is a saved SQL query you can list like a table ([what a database view is](https://duckdb.org/docs/sql/statements/create_view)). |
| **Step** | One command, for example `idli list replies --since 7d`. |
| **Chain** | Steps in order, each able to use the one before. "Find replies, judge which agreed, draft three times". |
| **Mini** | A saved workflow: its views, its definitions and its chain, plus a short description. You can run it, run one step, ask about it, or fork it. Data Minis (charts over a spreadsheet) and workflow Minis (leads follow-up) are the same shape. |
| **Mapper** | Whatever turns a person's words into commands. It is the 9B, or idli-remote with the person's consent. It only ever sees masked text and the command descriptions. |
| **9B** | Qwen 3.5 9B running on the DGX for the PoC (on the person's computer later). Private. It does three jobs: picks values for commands, applies definitions, and words short replies. |
| **idli-remote** | A cheap outside model (today DeepSeek through OpenRouter) that maps masked questions to commands. It is named generically so we can swap it. |
| **Sandbox Claude** | Claude Code on the right side of a sandbox. It sees masked data only, and builds or changes Minis. Idli runs everything it writes on the real data. |
| **Builder** | Claude Code outside any sandbox. It never sees private data. It decides what a sandbox can reach, and adds new connectors and tools. |
| **Masking** | Replacing private values (names, emails, places, numbers) with codes like `NAME_007` before anything leaves the computer, and putting them back in replies. |

---

## 2. The scaffold: the core running without the app

To test the model quickly and cheaply, it runs as a plain command line on the DGX, on the real test accounts
(87profligate is "me", 88profligate is "a lead"). The app (section 8) will later put a UI over the same thing.

Code is in `benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/`:
- `lib/recstore.py`: the store and the Google connectors;
- `lib/idlicli.py`: the commands and `ask`;
- `desktop/idli`: the entry point.

Try it with `IDLI_SANDBOX=<dir> desktop/idli --help`.

```
idli sync [mail|events|files|sheets|all]        copy your Google account into this sandbox's store (read only)
idli list RESOURCE [--where ..] [--since ..]    rows: mail, threads, events, files, folders, photos, sheets,
                                                rows --sheet NAME, labels, definitions, or a view
idli count RESOURCE [...] [--by FIELD]          how many, optionally grouped
idli get RESOURCE ID|NAME                       one item in full
idli explain [RESOURCE]                         its fields, with examples using real dates (the manual page)
idli describe file|sheet NAME                   what's inside: pages, columns, value ranges
idli read file NAME / summarise file NAME       a PDF's text / the 9B's summary
idli define NAME --on mail|event|file|photo --ask ".." --answers yes,no
idli judge RESOURCE --def NAME [--where ..]     the 9B labels each row once per definition version
idli query "SELECT ..."                         any read-only SQL over the store
idli view NAME --sql "SELECT ..."               save a query as a named list
idli date "next monday"                         what a date phrase means (dates are worked out in code)
idli draft mail --reply-to THREAD --ask ".."    a draft, previewed only; nothing is saved or sent
idli ask "question"                             your own words -> commands -> run -> a short reply
```

**How `idli ask` works:**
1. The question, the command descriptions and the store's columns are masked once.
2. The mapper returns commands.
3. Idli runs them on the real store:
   - one repair round if a command fails;
   - up to two "continue" rounds, where the mapper sees results before writing the next commands (this stops it
     inventing ids).
4. The 9B writes one to three sentences that answer what the person just said, above the rows. Every number in its
   wording must appear in the result, otherwise the wording is dropped and only the rows are shown.

**Store bounds:**
- mail is the last 60 days, events ±60 days;
- email bodies are capped at 8 KB and file text at 60 KB;
- one sync of 87 (188 emails, 10 events, 191 files, 23 sheets) took about 2 minutes, and the store was 13 MB after
  judging. Extracted file text is most of it.

---

## 3. Command design

Full reasoning, references and the open choices are in [CLI_CHOICES.md](CLI_CHOICES.md). The short version:

- **One shape:** `idli VERB RESOURCE [NAME] [flags]`, like kubectl and gh, because models have seen those patterns a
  great deal and one learned pattern covers every resource.
- **Verbs split by effect:**
  - reading verbs (`list`, `count`, `get`, `explain`, `describe`, `read`, `summarise`, `judge`, `query`);
  - writing verbs (`draft`, later `book`, `send`, `move`).

  Writing verbs only preview unless given `--apply`, and they are never on the mapper's menu. So the mapper cannot
  change anything in the world.
- **The same flags everywhere:**
  - `--since`, `--until`, `--on` for dates;
  - `--where` for conditions on fields;
  - `--limit`, `--as` for which account;
  - `-o` for the output format.

  A model that learned `--since` on mail uses it on events too.
- **`explain` is the manual page:** fields plus two or three examples with real dates. The benchmark showed examples
  matter most for the 9B. Placeholder dates get copied literally, so use real ones.
- **Dates are worked out in code,** never by the model ("since Monday" was the 9B's last repeated mistake).
- **Who may add what:**
  - Sandbox Claude adds flags, views and definitions inside a sandbox;
  - the Builder adds resources, connectors and verbs;
  - our team adds writing verbs.

  Adding is add-only: no removed flags or changed defaults (p1 todo `todos/idli-insights/p1/capability_versions.md`).

---

## 4. The store and sandboxes

- **One store per sandbox,** not per Mini or per question. All Minis in a sandbox share its records.
- **Who writes what into the store:**
  - `idli sync` (the connector) creates and fills the record tables, read only, for the window the sandbox's
    Minis need;
  - `idli judge` writes labels into one shared labels table, keyed by record, definition and its version. So
    "conservation" is judged once per email, and every question or Mini reuses it. A new version of a definition
    re-judges;
  - views and definitions are small saved entries, kept with the Mini that made them, or with the sandbox if
    shared.
- **Questions create nothing.** A question is a query, and its answer isn't stored.
- **The store is a cache of the source, kept rather than temporary:**
  - labels cost 9B time to recompute;
  - the next sync only fetches what's new.

  It is bounded (a window, capped bodies, evicted thumbnails) and deleted with the sandbox. It holds real content
  on the person's computer, like Drivey's downloads already do. Encryption at rest is an option.
- **What crosses the line:**

  | | idli-remote | Sandbox Claude |
  |---|---|---|
  | The question | masked | masked |
  | Table and column names, command descriptions | yes | yes |
  | Sample values | a few, masked | masked sample rows while building |
  | Records, email bodies, images | never | never: Idli runs its code and it gets masked output after the person's yes |

Worked examples with tables, commands and queries for Gmail ("conservation correspondence"), Drive ("pictures with
animals"), WhatsApp ("funder chats with a blue tick or a heart"), calendar and leads are in
[EXAMPLES_V0.md](EXAMPLES_V0.md).

---

## 5. What the benchmarks showed

Five rounds, 2026-11-19 to 20. Details and numbers are in each folder's README under `benchmarks/runs/`.

1. **Commands with descriptions beat a flat menu** (`2026-11-19-capability-cli-mapping`). For mapping a partial
   question to the right command and values:
   - the 9B went from 78% to 97%;
   - idli-remote went from 81% to 94%;
   - the kubectl-style grammar matched manual pages with shorter, faster prompts.
2. **Blind testers on the app's own flows** (`2026-11-19-blind-tester`):
   - **Leak found:** masking leaked 9 author names from a PDF whose text came out one word per line. Fixed; one
     name ("Kari May") still slips.
   - **Where trust broke:** at "one person at a time" and at "explain this step".
3. **The scaffold, blind** (`2026-11-19-record-store`):
   - **Task bank:** 80 asks written by an outside agent that never saw the commands. 53 for development; 27 held
     out and run once on frozen code.
   - **Grading:** by a separate agent that checks each answer with read-only SQL.

   Held-out results:

   | Kind of ask | idli-remote | 9B as mapper |
   |---|---|---|
   | Trust ("is Gmail connected", "meetings yesterday", "how many files in this folder") | 4 of 5 | 2 of 5 |
   | Own definition ("my conservation emails", "photos with people") | 9 of 10 (+1 partial) | 3 of 10 |
   | Own workflow ("for each lead, who needs a follow-up") | 0 correct, 3 partial of 7 | 0 of 7 |
   | Other sites (WhatsApp, Slack, Canva...) | correctly said "needs a connector" | 4 of 5 |
   | Reply quality (fit / takes in corrections / not repetitive, out of 5) | 4.5 / 4.8 / 4.6 | 3.6 / 3.6 / 4.2 |

   - **Coverage:** every trust and own-definition ask can be expressed with the existing pieces. Other sites need
     a connector; move, rename and post need writing verbs. The only design miss was "every Monday" (a schedule).
   - **Speed:** a normal turn takes about 4.5 s. Judging a new definition across all Drive files took 5 to 7 minutes
     the first time, because it reads each PDF once.
   - **Blind testers:** simple checks held in 5 of 6 sessions, and a few steps in 4. Every session that reached a
     full workflow broke there.

**Conclusions:**
- Trust questions and people's own definitions work today, with no per-question code: define, judge once, list by
  label.
- Letting the 9B word replies around checked numbers works well. Pure templates are not needed.
- The 9B should pick values and judge. It should not plan open requests.
- Multi-step workflows fail when the mapper has to invent them (next section).

**Known gaps:**
- masking misses surnames in account text and one PDF author;
- "fixity from" was over-masked;
- the number check always lets 1, 2 and 3 through ("1 document" for a count of 0);
- "mail from people" counted sent mail;
- a reply called the mail count "connection ID 188".

---

## 6. Why workflows failed, and what a Mini fixes

In the scaffold benchmark the sandbox was **blank: no Minis**. The blind writer's asks were sorted into three kinds:
- **trust:** one read from one source;
- **own definition:** one category to apply;
- **own workflow:** several sources joined, plus words that only mean something in this person's work: *lead*,
  *reply*, *follow-up*.

**What happened on a workflow ask** ("For each lead, check the latest email and tell me who needs a follow-up"):
1. idli-remote wrote one large query in a single turn. It invented the meanings:
   - "lead" became the union of two test sheets it found;
   - "reply" became any email to or from that address, so a calendar "Declined:" notice counted as a reply;
   - "needs a follow-up" became "declined".
2. The tester narrowed it ("only the ones with no reply since our last note"). idli-remote wrote a different query
   with different meanings and named six other people.

Each answer was plausible, and each defined the words differently. That is why it scored partial or wrong, and why
a person would stop trusting it.

**The fix is not a better mapper. It is giving those words a fixed meaning once, in a Mini:**
- **views:**
  - `leads` = Name and Email from the leads sheet;
  - `replies` = incoming mail from a lead's address, minus calendar notices;
  - `needs_followup` = leads whose last email from you is newer than their last email to you;
- **a definition:** `intent` on replies, with answers agreed, picked a time, or other;
- **a chain:** list replies, judge intent, draft three times for "agreed", book for "picked a time".

Sandbox Claude writes these once, on masked samples, and the person checks each step on the real data. After that,
"who needs a follow-up?" is `idli list needs_followup`, and "only Ravi" adds `--where name~Ravi`. The mapper only
fills in values, which is what it is good at (94 to 97% in the first benchmark).

So:
- **Inside a Mini,** a trust question is a variation on an existing step ("show me today's meetings", "only the last
  two days"), and the mapper handles it.
- **A new workflow** ("WhatsApp all my meeting attendees", "who needs a follow-up" with no leads Mini) is a request
  to make a Mini, and goes to Sandbox Claude.

Today's app Minis hold these meanings inside Python scripts (the sheet id, the "skip calendar notices" rule). Moving
them into named views and definitions is what lets the 9B and idli-remote reuse them for new questions.

---

## 7. Journeys inside a sandbox

### 7.1 I have a Mini. I want to trust it, ask it things, and stretch it

1. **Open it.** Idli says what it reads and lists its steps ("reads the leads sheet, reads your email, sees your
   calendar; 5 steps").
2. **Simple checks.** "Is it connected?", "show me my leads", "yesterday's meetings".
   - The 9B answers directly when the question matches a step or view.
   - Otherwise the mapper picks a step or view with values. It is idli-remote after a one-line consent card ("I
     want to call idli-remote with this question: ... Your account data stays on this computer. Can I proceed?"),
     or the 9B if the person says no.
   - Idli runs it on the real data and shows the rows.
3. **Step by step.** "Run step 2", "what would step 4 draft for Asha?". Writing steps only preview: "Would draft
   (not saved)".
4. **Stretch without Claude:**
   - new filters on the Mini's views ("only replies this week", "only Ravi");
   - new categories on its records ("which replies sound urgent?" becomes `define` plus `judge`);
   - counts and groupings.

   These use the same pieces and need no new code.
5. **Turn it on** for the person's own account, starting today. Running on a schedule is not built yet.
6. **When it can't answer** (no step, view or definition fits), Idli says so and offers to fork.

### 7.2 I want a new Mini

1. In a sandbox, the person asks for something no Mini does ("follow up with my leads", "chart attendance by ward").
2. Idli shows the masked question and asks to send it to Sandbox Claude.
3. Sandbox Claude, on masked samples, proposes the views, any definitions and the chain, one step at a time.
4. For each step, it asks Idli to run it. There are two consent questions on the left:
   - **"Run it here?"**
   - after the real output is shown, **"Send this masked version to Claude?"**

   The person sees every real result. Claude sees only masked output.
5. When every step looks right, it is saved as a Mini. The person then uses 7.1 to build trust.

### 7.3 I fork a Mini

1. The Fork button copies the Mini to Sandbox Claude with the current flow laid out.
2. The person says what to change ("only replies from the last two days", "add a chart", "add this new spreadsheet").
3. Claude changes the smallest thing: a flag, a view, a step.
4. Each try runs through Idli, with the same two consent questions.
5. It is saved as a new Mini. The original never changes.

### 7.4 Insights over files (a data Mini), the same pattern

Spreadsheets and PDFs become records too:
- every sheet is a table;
- a PDF has pages and text.

Simple questions ("how many columns", "summarise this report") are answered directly. "Help me analyse" goes to
Sandbox Claude on masked copies. Its charts and queries run in Idli on the real files, and are saved as a Mini that
others can ask.

### 7.5 Others in the team use a Mini (later)

One person makes Minis with Claude. Others only run them and ask (7.1). That is why 7.1 must work well with only
the 9B and idli-remote: if people can't check a Mini piece by piece, they won't use it.

---

## 8. Outside the sandbox: the Builder (boundary clear, details to be decided)

What a sandbox cannot do on its own, and who adds it:

| Need | Who | Status |
|---|---|---|
| A new place to read (WhatsApp, Slack, Mattermost, Canva, LinkedIn, Amazon, a funder portal) | The Builder writes a read connector from trusted libraries and sources. Sites with no API go through the browser on a test account first. | to be decided |
| New fields or a new resource on an existing place | Builder | to be decided |
| A new reading verb or a file reader (Word, scanned images) | Builder, within the trusted import list (built for transform blocks, see SANDBOXES.md) | partly built in the app |
| Any writing verb (send, book, post, move, rename) | Our team only. The Builder asks for it. | built for Gmail drafts and Calendar bookings in the app |
| Which accounts, connectors and tools a sandbox may use | Builder, at `/sandbox` | built in the app |
| Running on a schedule | not decided | gap |

The Builder never sees the person's data. It sees each sandbox only as a list of what it can reach. How Builder
work plugs into the scaffold (a connector contract, `explain` pages generated from it, versioning across sandboxes)
is the next design step after workflows.

---

## 9. How this fits the rest of the work

This document is the core engine. Around it:

- **The app is Paseo** (a desktop app that hosts Claude Code and other agents), patched by us (build idli26). See
  [IDLI_DESKTOP.md](IDLI_DESKTOP.md) and `paseo/ui/README.md`.
  - **The left pane of a sandbox** is Idli's chat. It will become a UI over `idli ask`.
  - **The right pane** is Sandbox Claude.
  - **The sidebar** has Start here (logins, privacy), Drivey, the Builder and one entry per sandbox.
- **Today's app already has earlier versions of these ideas:**
  - fixed "blocks" (`lib/blocks.py`);
  - the Mini question chain (`lib/minitalk.py`, `lib/miniscope.py`, routed by `lib/modes.py` in the DGX router);
  - fork (`lib/minifork.py`);
  - the two consent questions for Claude's tries (`lib/tries.py`);
  - transform blocks the Builder writes (`lib/transforms.py`).

  The scaffold replaces blocks with connectors and commands, and the Mini's buried script logic with views,
  definitions and chains. Moving the app onto the scaffold is a later step, after workflows work headless.
- **Masking** is the production code (`lib/privacy.py`, `mask_account_text`, `lib/docmask.py` for PDFs), used by
  the scaffold unchanged.
- **Accounts:** Google through Idli's own OAuth app, which is unverified (people click Advanced, then Go to idli).
  Tokens are kept per account, on the laptop and, for tests, on the DGX.
- **Drivey,** the original insights flow over Drive spreadsheets, stays as it is. It is the regression check for
  the app.
- **Tools** (speech, OCR, translation, face blur) come from a vetted catalog on silo installed with pixi
  ([PAGES_AND_TOOLS.md](PAGES_AND_TOOLS.md)). They are not yet part of the scaffold.
- **Teams** are postponed, not dropped ([IDLI_DESKTOP.md](IDLI_DESKTOP.md) section 2).
- **Proper walls** around code (bwrap, WSL and so on) come later (p1 todo `sandboxing_later.md`).

---

## 10. Next steps (proposed)

1. **Workflows the right way:**
   - Sandbox Claude builds the leads Mini (views, a definition, a chain) from the person's ask, on masked samples,
     in the scaffold;
   - then the blind testers ask their workflow and partial questions against it;
   - score with the same frozen held-out tasks, plus new held-out tasks written blind for "with a Mini".
2. **Small general fixes:** the number check (1, 2, 3), "mail from people" excluding sent mail, reply wording slips,
   surname masking.
3. **Narrow before judging,** and show progress on long judging.
4. **The connector contract and the Builder's role** (section 8), then one non-Google connector chosen by the task
   bank.
5. **Only then,** move the app's left pane onto `idli ask` and test once on the laptop.

## 11. Where to look

- **Chronology:** `chronology/2026-11-18T0900-catalog-routines-sandboxes.md`. Sections 1 to 9 cover the app work
  (catalog, routines, sandboxes, Minis, transform blocks, the escalation chain); sections 10 to 13 cover the CLI
  benchmarks, the grammar, the blind testers and the scaffold.
- **Benchmarks** (each has a README):
  - the scaffold and its blind bench: `benchmarks/runs/2026-11-19-record-store/`;
  - the grammar: `benchmarks/runs/2026-11-19-capability-cli-mapping/`;
  - the first blind tester: `benchmarks/runs/2026-11-19-blind-tester/`;
  - the app rounds: `benchmarks/runs/2026-11-18-{sandboxes,builder-minis,transform-blocks,mini-escalation}/`.
- **Design documents:** [GOALS_v0.md](GOALS_v0.md), [EXAMPLES_V0.md](EXAMPLES_V0.md), [CLI_CHOICES.md](CLI_CHOICES.md),
  [SANDBOXES.md](SANDBOXES.md), [ESCALATION_MODELS.md](ESCALATION_MODELS.md), [UX.md](UX.md).
- **Handoff for agents:** `docs/idli-handoff.md`.
