# Goals v0: a system people extend themselves

2026-11-19. Written after the CLI benchmark and the first blind tests. Related:
- [IDLI_DESKTOP.md](IDLI_DESKTOP.md): the Builder and the sandbox;
- [CLI_CHOICES.md](CLI_CHOICES.md): the grammar;
- [SANDBOXES.md](SANDBOXES.md);
- [ESCALATION_MODELS.md](ESCALATION_MODELS.md);
- [EXAMPLES_V0.md](EXAMPLES_V0.md): the four layers on concrete examples.

Each part is marked **[have]**, **[partial]** or **[new]**.

---

## 1. The goal

People should build their own workflows on their own data, without us building each one, and trust them enough to
use them. What they will want is open-ended:

1. **Other sites:** Canva, WhatsApp, LinkedIn, Slack or Mattermost, Amazon, a funder's portal.
2. **Their own definitions on a site we already have:**
   - "last week's emails about conservation";
   - "all my Drive photos with animals in them";
   - "a lead", "a reply", "an urgent request".
3. **Their own workflows:** "my funder WhatsApp chats where a message I sent last week got a blue tick or a heart".

**What we must not do is fix these one at a time.** We added a flag to limit an email search to a sheet's people,
because one test needed it. Then the blind tester asked for one lead at a time. Chasing each such ask overfits a
system to the few tests we have. The system has to be built so that each of the three kinds above is something a
person, with Sandbox Claude's help, can add within rules we already have.

---

## 2. What the benchmark concluded

Read narrowly, it is about mapping: does the question reach the right command with the right values?

- **A structured surface with schemas and short examples maps partial questions well.**
  - The 9B went from 78% to 97%, and idli-remote from 81% to 94% (32 questions; held-out agreed).
  - The kubectl-style grammar matched man pages on accuracy (idli-remote 96%) with shorter, faster prompts.
- **What carries the gain:**
  - for idli-remote, the schema;
  - for the 9B, examples with real dates;
  - the 9B's last misses were dates ("since Monday"), which should be worked out in code.
- **The mapping layer is good enough to build on.** The blind testers' remaining breaks were not mapping errors.
  The surface was missing things:
  - one person at a time;
  - "explain just this step";
  - summarising a spreadsheet;
  - consent as a card.

**The limits, stated plainly:**
- 54 questions, mostly from one leads sandbox and one Drive account, and many derived from the owner's own
  explorations.
- Hand-written command schemas.
- One mapper model each.

It shows the *shape* works. It does not show the system covers what people will ask. The next measure has to be
coverage on tasks we didn't write (section 6).

---

## 3. The answer to "get lead NAME and --where lead="

Neither should be a new feature. Both fall out of two general parts:
- **Views.** A Mini can name a view over what its commands read: `leads` is the rows of the leads sheet, and
  `replies` is mail from leads, minus calendar notices. Sandbox Claude defines views inside a Mini, because a view
  only combines commands the sandbox already has.
- **One selector for everything.** `--where` is a filter over the fields that `explain` lists for any resource,
  never a per-resource flag. `get lead Ravi` is then `list leads --where name~Ravi`, and the replies for one lead
  are `list replies --where lead=Ravi`.

So yes, Sandbox Claude can add these, and nothing lead-specific is built. The general rule is that Sandbox Claude
defines views and filters, while the Builder adds new sources and commands.

---

## 4. The architecture that extends

Four layers. Each grows by a rule, not by a fix.

### 4.1 Connectors: getting records out of a place [partial]

- **What it is:** a connector reads one place and returns **records with fields**:
  - emails (sender, to, date, subject, body, labels);
  - messages (chat, sender, direction, time, ticks, reactions);
  - files (folder, type, size, modified);
  - events (title, time, guests, response).
- **Commands:** every connector answers the same `list RESOURCE --since --until --limit --as` and `explain
  RESOURCE`, so the grammar stays the same across sites.
- **How a connector reaches its place:**
  - **An API where there is one** [have for Google]: Gmail, Drive, Sheets, Calendar. Slack and Mattermost
    have good APIs.
  - **The browser where there isn't** [partial]: WhatsApp Web, Canva, LinkedIn and Amazon, driven in a Chrome profile
    on a test account first (UI as API). These are fragile, and some sites' terms forbid automation. Pick sites
    case by case.
- **Who builds them:** the Builder writes read connectors from trusted libraries and sources. Our team writes any
  connector that writes.

### 4.2 A local record store: DuckDB per sandbox [new; DuckDB is already used for data Minis]

- **What it holds:** everything a connector reads lands as rows in a DuckDB file inside the sandbox, synced since the
  last run, with each record's id, source and fetch time. Files already go through DuckDB in data Minis, and
  idli-remote already writes SQL over a masked schema there (minisql).
- **Why it matters:** it is the single general answer to "different definitions" and "different workflows".
  - Instead of a flag per filter, a question becomes SQL over the fields `explain` lists.
  - "Messages I sent last week that got a heart" is a filter on direction, time and reactions.
  - "Which leads haven't replied" is a join between two views.
- **It also unifies the two sides:** insights and workflows become the same thing, queries over records, and only
  the last step differs (a chart or an action).
- **What crosses the boundary:** idli-remote sees the masked schema and a few masked sample values, never rows.
  That's the same rule as today.

### 4.3 Definitions: fuzzy labels people make [new]

- **The problem:** "conservation-related", "a photo with an animal", "a funder", "urgent" are not fields. They are
  labels that only a model can apply.
- **What a definition is:** a named, versioned prompt with an answer shape and a few examples the person gives.
- **How it runs:** `judge` runs it per record and writes a new column, cached by record id and definition version.
  - The 9B handles text, and its vision handles images (live since 2026-11-17).
  - Catalog tools handle sound and speech.
  - Cheap filters (SQL, keywords, dates) run first, so the model sees fewer rows.
- **How trust is built:**
  - the person checks a sample: "show me 10 it called conservation, and 10 it didn't";
  - they mark the wrong ones, and the agreement is shown;
  - the marked examples go into the definition.

  This is the same incremental pattern the blind testers needed, made general.
- **Who writes them:** Sandbox Claude writes definitions on masked samples, and Idli runs them on the real records.

### 4.4 Chains: workflows [partial]

- **What a Mini is:** a chain.
  1. Sync records.
  2. Apply definitions.
  3. Query.
  4. Act, previewed unless `--apply`, or chart.

  Each step can be run alone, and its output shown.
- **Who handles a Mini:**
  - idli-remote and the 9B fill in the values: dates, names, which view;
  - Sandbox Claude composes new chains and views on masked data;
  - the Builder adds connectors;
  - our team adds write actions.

---

## 5. Do we have enough?

| Need | Today |
|---|---|
| Google reads, Gmail drafts, Calendar bookings | **[have]** through the APIs, with OAuth on the laptop and on the DGX |
| Files: spreadsheets, PDFs, Word | **[have]** Drivey, transform blocks, PDF masking |
| A grammar that maps partial questions | **[have]**, benchmarked |
| Consent and masking both ways, two gates | **[have]**; known gaps: surnames in account text, one author name in a PDF, over-masking ("fixity from") |
| Views, and one `--where` over `explain` fields | **[new]**, small |
| A record store per sandbox (DuckDB) with sync | **[new]**; DuckDB is used for files today |
| Definitions (judge plus check-a-sample) | **[partial]** `nine_b` exists; versioning, caching, sampling and agreement are new |
| Images (animals in photos) | **[partial]** the 9B has vision; Drive image listing and thumbnails are new |
| Non-Google sites | **[partial]** Chrome profiles and site tools exist; no connector follows the record contract yet |
| Dates worked out in code | **[new]**, small, and fixes the 9B's last mapping misses |
| Running on a schedule | **[new]**, still the most-asked gap |
| Walls around code | **[later]** p1 `sandboxing_later` |

---

## 6. How we avoid overfitting

- **A task bank we didn't write.** A separate agent writes 50 to 100 DIY workflow asks, in people's own words,
  across sites, definitions and workflows (including the three examples in section 1). It writes them before we
  build anything for them. A third are frozen as held-out.
- **Two scores, kept apart:**
  - *Coverage:* can the system express the task with its existing layers (connector, view, definition, query,
    chain)? Or does it need a new connector or a new write action?
  - *Correctness:* does it give the right answer on real test accounts?

  A task that needs a new flag on one command counts as a design miss, not a to-do.
- **Blind testers stay blind:**
  - walled off with only `./ask`;
  - personas, not scripts;
  - simple first, then a few steps, then the workflow;
  - they stop at the first failure.
- **Fixes must be general.** A fix is allowed if it adds or improves a layer (a connector, a selector, the store, the
  definition loop). A fix that makes one question pass gets written down and refused.

---

## 7. Order of work (proposed)

1. **Small, general fixes:**
   - views plus one `--where` over `explain` fields;
   - dates worked out in code;
   - "Would draft (not saved)" in the app's own footer;
   - consent always as a card.
2. **The record store:** Gmail, Calendar, Sheets and Drive sync into DuckDB per sandbox. idli-remote writes SQL over
   the masked schema for workflow questions too.
3. **Definitions:** judge with versioning, caching and the check-a-sample loop. Test on "conservation emails"
   (text) and "photos with animals" (the 9B's vision on Drive images).
4. **The task bank and coverage score,** written blind, before step 5.
5. **One non-Google connector,** chosen by the task bank. Slack or Mattermost has an API; WhatsApp would go through
   the browser, read-only, never sending.
6. **Then** building new workflows end to end: how a person, with Sandbox Claude, gets from an ask to the right
   chain.

## 8. Open questions

- **Browser connectors:** how much fragility and terms-of-service risk do we accept, and for which sites?
- **The store's privacy:** it holds real content on the person's computer. It needs the same deletion rules as the
  rest of the sandbox, and none of it may ever leave.
- **Judging many rows with the 9B:** how much cost and delay is acceptable? Cheap filters go first, but some
  definitions will need every row.
- **When a definition drifts** (the person's idea of "urgent" changes), do older results change?
- **Capabilities shared across sandboxes:** see p1 `capability_versions`.


Worked examples (Gmail, Drive, WhatsApp, calendar and leads: connector calls, tables, queries, the 9B's role):
[EXAMPLES_V0.md](EXAMPLES_V0.md).
