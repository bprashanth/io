# One journey: clean a file, then talk to it

Idli had grown many paths: site plugins, gap reports, free SQL over sheets, dashboards. On 2026-11-09 the owner
scoped it back to one journey and asked for it to work well before anything else. Index the Drive in Start here.
Then, in Idli, pick one file, clean it with Claude's help, and have a conversation with it, charts included.
[Chronology](../docs/cowork-poc.md), test steps in [the manual test](../docs/cowork-manual-test.md).

We played it end to end on the owner's real cestrum experiment workbook (four tabs: a 1,876-row tree sheet made
of sections pasted under each other, a density sheet, a seedlings sheet, a species key), driving the app on the
laptop like a person: clicking cards on screen, typing replies, taking screenshots.

What the journey looks like now:
- **Idli asks first.** A new chat opens with a card, "Clean up a file" or "Analyse a file", then "which file?". A
  message that already says what it wants skips the card.
- **Claude learns the file from fake data, one question at a time.** The teaching ran as five steps of cards:
  what a row is (one question per tab), checks (multi-select, plus the person's own; "if DBH 2 is filled DBH 1
  must be too" became "stems recorded in order" for all 15), clean-ups, the words of the file (measures such as
  cestrum share and basal area; "is cestrum always cesaur?"), and how it read the request. 13 minutes, most of
  it the person reading. Claude extended the engine where the rules ran out: checks across tabs (density
  matches the tree count per plot) and a team's own codes (UKS1, Fern) accepted by pattern.
- **Mistakes land in the person's Drive, as a copy.** After a yes, Idli puts a working copy next to the
  original: red cells that turn white once fixed (conditional formatting built from the same checks), and one
  real Google comment per kind of problem on its first cell. 195 problems became about ten comments. One said
  "neosco appears 75 times but isn't in the species key": a species missing from the key, not a typo.
- **"I'm ready" moves to analysis.** Idli downloads the copy, checks it again, and from then on answers from it.
  Opening the original later offers the checked copy first.
- **Questions go through the form.** "How many cestrum trees, and what share?" "Which plots have the most?"
  "Compare transect 1 and 7." Each answer is a form query; the model never adds up. 13 to 40 seconds each.
- **Graphs come two ways.** A breakdown the form can express is drawn straight from its answer and shown in the
  chat (bars for one breakdown, a grid for two; cestrum share by transect and plot showed T1-P1 at 60%). For
  anything else, or "suggest analyses", Idli sends Claude the fake copy; Claude proposed four analyses, drew the
  two picked on fake data in its own chat, took a change ("most of our trees are small: use <5, 5-10 ... cm"),
  and handed back code. Idli ran it on the real data: 62% of cestrum trees are under 5 cm against 40% of other
  species, a young invasion that is still spreading.

What we learnt:
- **The model invents tools you leave lying around.** Asked for a graph, Muse reached for an old free-SQL chart
  tool and wrote a query that failed. Removing that site from Idli did more than any instruction.
- **Muse follows cards, not afterthoughts.** A card asked for *after* writing text was skipped every time. Cards
  that must happen go first and carry the text; optional follow-ups became one line in the chat.
- **Arguments land in the wrong place.** Muse put `chart: true` inside the spec. Tools now accept it either way.
- **Contradictions cost a minute.** The earlier 60 s turns were mostly Muse deliberating between two rules; with
  them removed, a link to a card takes about 35 s, a question 15 to 40 s.
- **Code Claude writes runs inside a wall.** Chart code only gets the form's cleaned tables, may import only
  pandas, numpy and matplotlib, and runs under bubblewrap (the same wall io's Codex used): no network, the file
  system read-only, the home folder hidden. Claude only ever saw fake values.
- **Paseo shows some browser tabs wider than their pane** in a narrow window, cropping the dashboard. That's a
  Paseo fix (P11), not a page fix.

Left open: working copies pile up in Drive; the index doesn't know copies made after it was built; a stale
dashboard tab after a server restart; a chat keeps the tool code it started with.
