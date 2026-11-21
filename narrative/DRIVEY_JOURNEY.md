# Drivey: the journey

Drivey is how someone at an NGO, who is not technical, analyses their own Google Drive files with Claude without
handing Claude their private data, and leaves behind a **Mini**: a small, reusable analysis that colleagues can open
and ask questions of with a private local model.

Two panes, always:
- **Left:** Idli, a chat with the person. It is where a journey starts and where Minis live. The small local model
  (the 9B) works here **only inside a Mini**. Everything else on the left is written by code.
- **Right:** the person's own **Claude Code CLI**, the same tool they learned in the Claude Code workspace. Its
  requests pass through Idli's masking proxy, so Claude sees codes for private values and the person sees real ones.

Style for every word on screen: plain labels and short sentences, no jargon, no poetic or flowery phrasing ("A little
care, before sharing" -> "Privacy review"; "Your question, as Claude sees it" -> "Example masked question:"), avoid
commas where a shorter sentence works, no arrows (write "->" or "up"/"down"), no "·" (use ":" or " - "). Never make
the person feel they did something wrong.

## A. Making a Mini (no local model at all)

1. **Start.** The person clicks "+" on the Drivey heading. A new workspace opens split in two:
   - left: an empty chat box (model: Idli 9B), with the Mini cartridges underneath;
   - right: Claude Code, ready.
2. **Cartridges** sit under the empty chat box: one slim line each, a bold name, a short heading, and the date and
   author on the right. Choosing one starts Part B.
3. **Or they ask a question.** They type a question and pick files with `@` (files or whole folders from their
   Drive, by path, Tab to choose, as in Claude Code), and press Enter.
4. **Idli downloads the files** (showing which ones, with a short progress line), then asks on a card:
   *"Before Claude sees these files, do you want to check what will be hidden, or accept Idli's choices?"*
   - "Check each file" -> step 5
   - "Accept Idli's choices" -> step 6
   (There is no "always" setting yet: Idli asks every time until people are used to it.)
5. **The privacy review appears in the chat**, not in another tab: each file's columns, what Idli will hide and why,
   a few real values next to what Claude will see, a switch per column, and the question as Claude will read it.
   "Done" when they are happy.
6. **A card:** *"Ready. Claude will get your question and these files, with private values replaced by codes. Switch
   to Claude?"* Yes -> Claude's pane gets the masked files and the question, and takes focus.
7. **Claude takes over** on the right. It works in small steps and checks in with the person ("Shall I break this
   down by ward?"). It offers a chart when one would help.
8. **A chart** appears in the left chat (the "binder"), in order, under the line "Chart from Claude: <title>". It is
   live: hover, click a part for "Where did this come from?", right-click "Copy to Claude" to bring that part and its
   sources into Claude's prompt. **Enlarge** shows it in a large window over the app.
9. **Pin.** Every chart has a Pin button. Pinned charts go into the Mini; unpinned ones don't.
10. **Making the Mini.** After about ten exchanges Claude offers, or the person types `/mini` at any time. Claude
    builds the questions, runs every one, and puts the **draft in the left chat**, under the charts. The draft is the
    Mini exactly as colleagues will see it when they open it (one page, `lib/mini-card.html`), not a form:
    - the title, the source file, then the author's text and the pinned charts in one column;
    - "You can ask": the questions, each with its options in italics (ward, months, ...), tested on the current files.
    The author arranges it like a short document:
    - click any text to change it (simple Markdown: `### heading`, `- list`, `**bold**`); click the title or a
      question to reword it;
    - **Add text** adds their own explanation; text and charts can be dragged up or down by **Move** (or moved with
      the arrow keys on Move);
    - **Remove** takes out a chart, a text or a question, with **Undo**;
    - **Enlarge** opens the same draft in a large window. Changes are kept as they are made, so the large copy and
      the one in the chat stay the same;
    - **Save Mini** (or **Add to <Mini>** when it grew out of one). Options themselves (choices, defaults) are not
      edited here.
11. **A new cartridge** appears under the chat box. It carries everything: the page as arranged, the charts, the code,
    the questions and their options. This is the Mini's "API".

## B. Using a Mini (the only place the local model works)

1. **Opening.** The person clicks a cartridge. The left chat shows the Mini's page: the same page the author arranged
   and saved, with live charts, read only. No model has run yet.
2. **Asking.** The person asks in their own words. Now the local model maps the question to one of the Mini's
   questions and options, shows which one it chose, and the Mini's own code answers. A question maps only when it is
   the same question: "where does Cestrum grow?" is not "where are Cestrum's big trees?" (the saved question counts
   trees above a DBH cut-off only).
3. **Out of scope: the query service, with consent.** If no question fits, Idli first shows a card with exactly what
   an external query service would get: the question with private values as codes, and the first lines of the
   column list (sheet and column names, types, number ranges, and for short text columns the list of their values,
   as codes when private), columns that list their values first. Never rows. Yes or No:
   - **Yes**: the service writes one read-only query, which runs on this computer. It may ask back which of two or
     three exact questions was meant (which sheet, what counts as big); picking one sends that one. That card also
     offers Claude.
   - **No**: nothing is sent.
   Limits: a short reply, a capped column list and 200 questions a day per computer; past that, only Claude is
   offered.
4. **Claude.** *"This Mini can't answer that. Claude can work on the Mini's files with private values as codes.
   Masked question: <the masked question>."* Switch to Claude -> the same Claude flow as Part A, with the Mini's files
   and code as context.
5. **Growing the Mini.** At the end, Claude offers to **add** what they found to this Mini, or **save a new Mini**.

## C. Start here: what was sent

Under the Start here heading are two entries, so neither gets lost the way a tab can:
- **Logins**: the setup chat (Google and Claude sign-in checks), with the Minis tab.
- **Privacy**: the "Sent to Claude" log, shown in the chat. Everything Idli's privacy guard sent to Claude in the last
  7 days, newest first, labelled by app (Drivey, ...). Private values show as codes. Type a name or a word to search:
  for a private name it says which code it went as (for example "Ramtekdi is private. It went to Claude only as
  PLACE_005"). Requests the guard stopped show only the codes that stopped them. Paseo lists the two entries by most
  recent use, so Privacy can sit above Logins.

## D. Making a team (chat built 2026-11-15; a page since 2026-11-16. PoC: the Insights team)

A **team** is a heading in the sidebar for one kind of work, made by answering a few questions in Start here. The
PoC makes one kind of team: what comes out is exactly today's Drivey (same flow, panes, tools and pages) under the
team's name, with its own folder and its own Minis. Drivey itself stays as it is. **Idli asks, not Claude**: the
questions are written by code. Nothing here goes to Claude.

1. **Start here > Teams** is a page (`lib/teams_page.html`), not a chat: a card per team and a **New team** card.
   Drivey has a card too (Open only: it is built in).
2. **New team** opens one question per panel, with Back, Cancel and "Step 2 of 6":
   - **"What's your team called?"** Typed, with an **Insights** shortcut ("Insights is fine for a try-out").
     "call it Field M&E" gives Field M&E. A name already in the sidebar, or not a name ("hello", "test"), asks again.
   - **"What does Insights work towards?"** Typed, one line, with **Use an example** (Lower household debt in 12
     villages). Lead-ins ("ok so we help...") are dropped. It can be left blank.
   - **Where does the team keep its data?** Google Drive / On this computer / Somewhere else (one click each; the
     plan then says to put a copy in Drive).
   - **Who will use Insights?** Just me / A few of us / The whole team.
   - **Do the files have names, places or phone numbers?** Yes / No / Not sure. Codes stay on whatever the answer.
   - **When a Mini can't answer a question, may Idli ask an outside service?** Yes / Ask me each time (both: "Only
     masked data is sent") / No. Yes skips the card in the Mini. Shown with a
     "What is this?" line. No leaves the team without the query service (its Minis offer Claude instead).
3. **"Set up Insights?"** The plan: its own heading (ask on the left, Claude helps on the right); files come from
   Google Drive and stay on this computer; names, places and phone numbers go to Claude as codes; Minis answer on
   this computer, new questions go to the outside service only if you say yes; for you for now, or for your team.
4. **Set it up** goes back to the cards, with the new team's card marked New: "Insights is ready. Click Open to
   start."
5. **Open** goes to the team's latest workspace, or makes its first one in two halves exactly like Drivey's New chat
   row: Idli on the left with the team's own (empty) Minis, Claude on the right in the team's own masked folder.
   **Delete** asks "Delete Insights and its chats?" (Delete / Keep): the heading, its workspaces and chats go from
   Paseo; the folder and Claude's masked copies move to `~/idli-insights/archive/teams/` (nothing is lost).
6. Next: type @ to pick a sheet and ask a question; a good answer becomes the team's first Mini. (Concept for later:
   end team creation with a guided first Mini from a sample file.)

The chat version (2026-11-15, `lib/teams.py route`, with typed answers read by rules and the local 9B) is still in
the code but no chat uses it: buttons leave far fewer odd answers than typing did.

**Where things live.** `~/idli-insights/teams/<name>/` holds `team.json` (the answers), Drivey's instructions and
tool list, and the team's downloads, Minis and privacy codes. Claude's masked copies go in
`~/idli-insights/claude-masked-<name>`. The team's page server takes the next free port after 8797 (Paseo trusts
8797-8819); Drivey's server lists a team's Minis for Paseo (`/api/minis-public?dir=`). The Privacy log labels the
team's requests with its name.

## E. When the team can't do something: the Builder (2026-11-16)

The four kinds of model and their boundaries are in [MODEL_TYPES.md](MODEL_TYPES.md). In the journey:
1. **A file the team can't read.** The person picks a file with @, for example a photo, and the team has nothing
   that reads photos. Idli's card says: "Insights can't read images yet. The Builder can add that to Insights.
   Build it with the Builder?" The options are Build it and Not now. Typed questions such as "can you read photos
   of our registers?" get the same card. Typing "open the Builder" opens it directly.
2. **Build it.** A Builder tab opens on the right with the request, masked, as its first message. It is the
   person's own Claude Code with an amber BUILDER label. It never sees the team's files.
3. **The Builder works.** It says in a sentence what it will add, and chooses the cheapest option itself
   (Tesseract on this computer for photos). It tests on fake samples it makes, and saves a version. On the next
   message the team reads that kind of file. The person picks the photo again with @, and the usual flow follows:
   the privacy review, then the Analyst.
4. **Inside a Mini** a question the Mini can't answer still goes to the outside service, then to the Analyst
   (extending a Mini is the Analyst's job). The Analyst offers the Builder only for things outside the team's
   tested capabilities.
5. **Versions** on the team card lists what was added. Go back undoes it. Files and Minis are not affected.

## What runs where
- Left chat: Paseo's chat. Its replies outside a Mini are written by code; inside a Mini, the 9B only picks a
  question and options, and the Mini's script writes the answer.
- Right: Claude Code CLI, launched through Idli's masking proxy, with Idli's tool server (charts, Minis) and Idli's
  instructions.
- Idli's local server serves the pages shown inside the chats and panes: privacy review, charts, the Mini page (draft
  and saved), the Sent to Claude log. Paseo shows them inside a chat (patch P19, build idli22).
- The query service: any OpenAI-compatible endpoint (today DeepSeek through OpenRouter, providers that keep no data).
  It gets only what the consent card shows.
