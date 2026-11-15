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

## 3. Marketplace
- **Flow:** Start here, then sign in to Google and Claude, then the marketplace. Each app is a card with
  Install.
- **Drivey-app:** a copy of Drivey for testing the install flow. Plain Drivey stays as it is.
- **Install:** creates the workspace (the 9B on the left and Claude on the right). Idli asks to scan Drive
  files on this computer. The scan draws the graph in the left pane, with suggested questions and "Make Minis
  for these files?" below it. The + button still opens the usual flow.
- **An app is a description:** name, skills and tools to copy, the left-pane opening and a first-run step.
  Later apps (a search Mini) are one more card.
