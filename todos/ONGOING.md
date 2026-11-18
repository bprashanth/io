# Ongoing

Big buckets we are thinking about. Not todos yet. Each may become a todo or a feature as things develop.
Noted 2026-11-15.

## 1. Search
- **Lookup today:** Google News RSS and Wikipedia, run from the person's computer with the real value. Claude
  sees only masked results.
- **Tried and failed:** SearXNG on the DGX, DuckDuckGo from a script, headless Chrome to Google. Details in
  `idli-insights/p2/scouting_for_data.md`.
- **Works (2026-11-15):** search through the Paseo browser on the laptop (signed in, home connection), read
  over DevTools. 11 Google searches, Bing and DuckDuckGo all returned results with no CAPTCHA, including 6 Google
  searches 3 s apart. Reading a result page worked (ncf-india.org, 11,700 characters). Google's terms do not
  allow automated searches, so this is PoC only.
- **Lesson from idlisseus:** connectors to known sources beat general search (GBIF, Zenodo, CKAN, OpenAlex).
  For India: ward and village directories, data.gov.in, OpenStreetMap.
- **Idea:** a search Mini that searches, reads the pages found, fills a sheet and drafts an email. It drafts.
  The person sends.

## 2. Data graph and relationships
- **Index:** a local scan of Drive files with no AI. Header row, row counts, column types, ranges and blanks.
- **Privacy:** patterns, header words and the GLiNER name scanner. For the PoC the scanner runs on the laptop.
- **Links between files:** code, not a model. Find text columns whose values repeat (ward, species,
  organisation, scheme) and measure how many values one column shares with a column in another file. Spelling
  variants are paired by edit distance and confirmed by the person. Unique columns are IDs.
- **GLiNER's part:** label what a link is (place, species, organisation), pull names from free text (notes,
  PDFs, docs) and privacy.
- **Findings:** code computes and ranks them. The 9B only words them as questions. Code checks every number
  in the 9B's sentence.
- **Graph:** reuse the chat.idli.cc Atlas (`idlisseus/.../visualAtlas.js`, data format `idli-graph/1`).
  Nodes are files, tabs, measures and shared things. Recorded links solid, inferred links dashed. See step 5 of
  `idli-insights/p1/file_by_file_index.md`.
- **Open:** the 2026-11-10 decision dropped the upfront Drive index because it picked the wrong file. An
  opt-in index that only draws a map and suggests Minis is a different job.

- **Query service for Minis (built 2026-11-15):** unmatched questions go to an external service for one SQL query
  from the masked question and column list; it can ask back with specific questions. Next: "Keep this question"
  so good answers become Mini questions.

## 3. Marketplace
- **Flow:** Start here, then sign in to Google and Claude, then the marketplace. Each app is a card with
  Install.
- **Drivey-app:** a copy of Drivey for testing the install flow. Plain Drivey stays as it is.
- **Install:** creates the workspace (the 9B on the left and Claude on the right). Idli asks to scan Drive
  files on this computer. The scan draws the graph in the left pane, with suggested questions and "Make Minis
  for these files?" below it. The + button still opens the usual flow.
- **An app is a description:** name, skills and tools to copy, the left-pane opening and a first-run step.
  Later apps (a search Mini) are one more card.
- **2026-11-18:** the sandbox model ([narrative/UX.md](../narrative/UX.md)) may replace the marketplace. Installing
  an app would mean `/sandbox` in the Builder picking its blocks. Decide once sandboxes are tested.

## 4. Builder outside, sandboxes inside (2026-11-18, being built)
- **Model:** [narrative/UX.md](../narrative/UX.md). The Builder is an ordinary Claude Code project. `/sandbox`
  asks the old Teams questions, maps the request to building blocks, and refuses with a named gap when a block is
  missing.
- **A sandbox is a small VM:** only its blocks. A Drivey-style split, with Idli on the left and Sandbox Claude
  (renamed from Analyst) on the right, on redacted data. The person assembles the workflow step by step in the left
  chat and saves it as a Mini.
- **Blocks today:**
  - Drive files and Minis;
  - Gmail search, read, draft;
  - Calendar free times, book;
  - Sheets read;
  - the 9B judge;
  - catalog tools.

  Google through OAuth (Idli's own unverified app, project bitrot-in) and the APIs.
- **Escalation:** [narrative/ESCALATION_MODELS.md](../narrative/ESCALATION_MODELS.md). A for action workflows
  (Claude's script calls the 9B), B for insights (the 9B picks the Mini, as Drivey), C later (a stronger model picks
  scripts on redacted questions).
- **Removed:** Teams page, New team wizard, per-team Builder, Installed tools page.
- **Unchanged:** Drivey, Start here.
- **Tested:** Drivey regression, Builder `/sandbox` for insights and leads, a gap case
  (`benchmarks/runs/2026-11-18-sandboxes/`).
- **Owner round, 2026-11-18 afternoon** (`benchmarks/runs/2026-11-18-builder-minis/`):
  - the Builder is Claude Code first (one pane, Opus by default, Idli 9B and 30B only without Claude Code, a
    /sandbox hint). Careful and Auto are off the menu;
  - @ a folder works, and a folder with no spreadsheets gets a plain gap;
  - the privacy page says "<column> entirely withheld";
  - an action Mini can be asked (the 9B explains from its code), previewed on the real accounts with nothing
    written, run, turned on for an account from today, or forked into Sandbox Claude. A fork's runs show on the
    left and it saves as a new Mini.
  - all checked on the laptop (preview with the full draft, turn on, Fork to a new Mini, Drivey unchanged).
- **Transform blocks** (`benchmarks/runs/2026-11-18-transform-blocks/`, design in SANDBOXES.md "Three levels"):
  - three levels: actions (ours), transforms (the Builder writes them), pages and servers (undecided);
  - the trusted imports are baked in; Idli checks a block once (about 0.1 s) and the person approves one card;
  - `block_run` is in every sandbox; the first block is `read_pdfs`;
  - Mini scripts get the same scan;
  - checked on the laptop: 18 PDFs answered in 63 s, then 20 s; actions and a bad import refused; Drivey and the
    leads Mini unchanged.
- **Open:**
  - Paseo's approval card shows JSON, not the hook's words (a Paseo patch);
  - the Builder's hook lives in its own folder (move it outside);
  - a block's cached Drive download ignores later edits to the file;
  - pages and servers: local or on silo;
  - redaction for account data (email bodies, senders, calendar titles) at the same standard as files;
  - escalating a Mini question the 9B can't place (masked, to an outside model) is not built; the 9B places
    every question today;
  - running a turned-on Mini on a schedule (a gap: no block);
  - connecting the person's real account (turn on binds an account from today; test accounts only so far);
  - where the earlier work fits: team stacks, the trusted catalog, test-account Chrome profiles. These become
    blocks, or the Builder's tools, not team features.
