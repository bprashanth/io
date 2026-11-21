# One file at a time: an index (and a graph) built as files are learned

Decided 2026-11-10. Drop the upfront Drive index and the Start here / reindex chat for now. Idli works on one
file at a time, from a link the person pastes or a file they upload. Learning that file (with Claude, on a fake
copy), cleaning it and analysing it produce everything an index entry needs. Each entry is stored as it's
made, so the index grows only with files the person actually uses.

## Why
- When the upfront index surfaces the wrong file, the journey starts wrong. Building it also needs Muse to write
  summaries, a minute or two of reindexing, and a chat that exists only for that.
- One file at a time keeps Idli focused on learn → clean and standardise → analyse, which is the journey that
  matters.
- Everything the index needs (what a row is, the columns, measures, words, checks, which tabs link to which,
  personal columns) is already worked out while teaching. Today it is thrown away once the skill is written.

## What each file adds (its "context card")
- Kept only locally: the real name, the Drive id and link, the folder, the owner, the dates seen and cleaned,
  and the working copy's link.
- From the skill: what a row is, tabs, columns with their kinds and meanings, measures, checks, and which
  columns are personal.
- Links: a column that matches a column in another learned file (same village, plot, species, household or
  officer codes, checked on the real values, locally). These links become the edges of the graph.
- Usage: questions asked and the charts saved (titles only).

## Search
"The cestrum file", "last year's household survey": search the cards with plain code (names, folders, column
meanings, measures). There are tens of files, not thousands, so no model is needed. A model joins in only for
goal-based questions across files ("which files have plot-level tree counts?").

## The graph
A Data view like idlisseus's site-pack graph (`~/src/github.com/bprashanth/idlisseus`,
`chatbots/odysseus/static/js/visual/visualAtlas.js`, contract `idli-graph/1`, fixtures in
`dss/contracts/fixtures/graph/`). Nodes: files, tabs, measures, and shared entities (places, plots, species,
programmes). Edges: "has tab", "measures", "shares column with", "working copy of". Show recorded links as solid
lines and inferred links (matched values) as dashed lines. It should be searchable and expand a node's
neighbourhood. It grows as files are learned. Its first use is to show the person what Idli knows. Its second
use is to answer questions across files.

## Steps
1. Write a card when teaching finishes (from the skill plus local metadata), and update it on clean, ready, ask
   and chart. Keep it next to the skill.
2. Make `drive_find` search the cards. A paste or upload goes straight to `file_get`.
3. Remove the upfront index from the default journey (bootstrap, Start here, `drive_index*`). Keep the code
   for later.
4. Find links between learned files (matching values, locally) and write them as edges.
5. Build the graph page in Mission control, next to "What Idli has learned", reusing the visualAtlas design.

## Open questions
- Uploads: where does an uploaded file live, and does a working copy still go to Drive?
- Can a card's description be written by Claude from the fake copy, or does it have to be written locally (it
  may mention real names)? Start with local code templates.
- Does finding links need Muse, or are value matches enough? Measure this once there are 5 or more learned files.
