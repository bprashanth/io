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

## D. Making a team (planned, PoC: the Insights team)

A **team** is a heading in the sidebar (its "office space") made from a short talk with Claude. The PoC models one
case: a manager makes an **Insights** team, and what comes out is exactly today's Drivey (same flow, same panes, same
tools), named Insights. Drivey itself stays as it is.

1. **Start here > Teams > New team.** Idli asks "What's your team called?" -> Insights. Claude opens on the right:
   "I'll ask a few questions about your team's work, then suggest how to set up Insights." Claude sees this talk
   through the masking proxy like everything else.
2. **Claude asks about the work**, one question at a time, stopping when it has enough:

   | Claude asks | What it sets |
   |---|---|
   | What does your team work towards? | The outcome, shown on the heading and on each Mini |
   | How do you know it's going well? What do you count or track? | The first Mini suggestions |
   | Where is that kept? | Sources: Drive sheets mean tables, so DuckDB and SQL |
   | Who needs the answers? Who makes the sheets? | Makers get the two panes with Claude; others use Minis only |
   | Does it have names, villages, phone numbers? | How strict the codes are (codes stay on in the PoC) |
   | When someone asks something new, can the question and column names go to an outside service, as codes? | Query service on or off, asks each time, daily limit |

3. **Pick one file you use often** (optional). Claude sees the masked copy and makes the Mini suggestions concrete.
   If the file has names the manager said it wouldn't, Idli says so and keeps codes on.
4. **The proposal card: "Your office space: Insights".** Plain lines, each backed by a part of Drivey: the heading;
   ask on the left and Claude helps on the right; names become codes before Claude sees them; files are read from
   Drive when picked and stay on this computer; everyday questions are answered on this computer (the 9B picks a
   saved Mini question); new questions can go to the query service, asking each time; a maker can ask Claude to build
   a new Mini; three Minis to start. **Set it up** or **Change something** (back to Claude).
5. **Setup.** A short progress list, then the Insights heading appears and its first chat offers the suggested Minis.
   A "Map your Drive?" card is offered later, once the Drive scan exists.

Under the hood Claude fills a team description through one tool (`propose_team`): name, outcome, sources, data
shape, layout, privacy, query service, roles, suggested Minis. Idli checks it, draws the card from it and installs
from it with the same steps the bootstrap uses for Drivey. Claude never edits setup files itself. For a class there
is also "Use an example team", which fills in Insights with the sample households file.

## What runs where
- Left chat: Paseo's chat. Its replies outside a Mini are written by code; inside a Mini, the 9B only picks a
  question and options, and the Mini's script writes the answer.
- Right: Claude Code CLI, launched through Idli's masking proxy, with Idli's tool server (charts, Minis) and Idli's
  instructions.
- Idli's local server serves the pages shown inside the chats and panes: privacy review, charts, the Mini page (draft
  and saved), the Sent to Claude log. Paseo shows them inside a chat (patch P19, build idli22).
- The query service: any OpenAI-compatible endpoint (today DeepSeek through OpenRouter, providers that keep no data).
  It gets only what the consent card shows.
