# Mini page, Privacy entry in Start here, consent before the query service (2026-11-15 evening)

## Owner feedback (after trying the binder)
1. The Mini draft in the chat should look exactly like the Mini when its cartridge is clicked. The author arranges it
   like a Markdown document (their own explanations, charts dragged up and down). An enlarged view is fine. Not a form.
2. The "Sent to Claude" tab should be a chat of its own so it can't get lost: Start here > Logins, Privacy.
3. Clicking into a Mini and asking an unmatched question went to the query service with no consent. Show the actual
   query going out and a sample of the data first.
4. Confusion about "cestrum" and "big trees" (answered: the saved question counts only trees above a DBH cut-off, so
   "where does Cestrum grow?" is a different question; not matching it was right).

## Built
- **One Mini page** (`lib/mini-card.html`) for the draft and the saved Mini. It replaces the form editor
  (`mini-editor.html` deleted; `/mini-editor` serves the same page). Title, source, then text and charts in one
  column, then "You can ask". In a draft: click text to edit (simple Markdown), click the title or a question to
  reword it, Add text, Move (drag, or arrow keys), Remove with Undo. Edits are kept as they are made
  (`/api/mini-card-edit`, stored as `edits` in the draft) and copies of the page tell each other
  (BroadcastChannel), so the enlarged copy and the one in the chat agree. Saved Minis keep `blocks` (text and chart
  order); older Minis read as story then charts. Charts inside a Mini hide Pin (`pin=0`).
- `mini_open` shows that page (`/mini-card?mini=<id>&embed=1`) instead of writing Markdown.
- **Query service consent.** An unmatched question first calls `mini_ask` with `preview: true`:
  `minisql.preview` builds exactly what would be sent (masked question, first 14 lines of the column list, how many
  more) without calling the service or counting against the daily limit. Card: Send / Ask Claude / Not yet. Send
  calls the service with the same text (`minisql.prepare` is shared).
- **Privacy entry.** Start here now has two workspaces: Logins (the old Start here workspace, renamed) and Privacy.
  The Privacy chat is written by code (`modes.privacy_chat_route`, first message "Show what Idli sent to Claude"):
  it calls `wire_page` and shows `/wire?embed=1` from Drivey's page server; anything typed searches the log. The
  Sent to Claude tab is closed by the bootstrap.
- **Paseo idli22** (P19): `/wire` added to the pages shown inside a chat; the Mini page gets Enlarge.

## Laptop test (test account, real field_vars_indicators file)
- idli22 installed and loaded by reloading the window. Bootstrap renamed Start here to Logins and created Privacy.
- Privacy: the log shows inside the chat; typing "Ramtekdi" answered "Ramtekdi is private. It went to Claude only as
  PLACE_005." with 25 matching requests. Fixed: "Show all" appeared on short cards (the frame was still sizing).
- Mini page: a copy of the Big trees draft posted into its workspace's left chat. In a ~200 px left pane the question
  list broke to one letter per line (space kept for the edit buttons); fixed by floating the buttons, with a 220 px
  check added. Edited text, Enlarge showed the edit, a chart moved in the large view and the chat copy followed,
  Save from the large view turned both copies to saved.
- New Drivey chat: the cartridge opened the same page, read only. "how many plots does each transect have?" showed
  the consent card (masked question, column lines, "...and 40 more lines"); Send; the service asked which sheet;
  "10x10m trees" gave 6 plots for transects 1 and 4, 5 for the rest.
- The test copy Mini was deleted afterwards. One more Drivey workspace was created.

## Known
- Paseo orders entries by recent use, so Privacy can show above Logins.
- The consent card shows the first lines of the column list. For field_vars_indicators those are mostly number
  columns, so the example values (codes) are further down.
- The Privacy chat shows "Used 1 other tool" above each reply (Paseo's tool line).
- In a narrow left pane, chart labels can be cut on the right; Enlarge shows them in full.

## Commits
cb306de5, 8044597e (DGX, not pushed); laptop 91414371, fd9f1d91. Tests: 172 passed, 2 skipped; `lib/test_chat.py`
still has its 10 old failures.
