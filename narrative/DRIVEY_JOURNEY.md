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
8. **A chart** opens on the right, beside Claude, as a live chart: hover, zoom, click a part for "Where did this come
   from?", right-click "Copy to Claude" to bring that part and its sources into Claude's prompt. They switch back to
   Claude or keep typing to it.
9. **Pin.** Every chart has a Pin button. Pinned charts go into the Mini; unpinned ones don't.
10. **Saving a Mini.** After about ten exchanges Claude offers, or the person types `/mini` at any time. Claude
    writes the Mini and opens it on the right as an editable page:
    - a title and a short story of what was found (their "essay");
    - the pinned charts;
    - the questions the Mini can answer, each with its options (ward, months, ...), tested on the current files;
    - where the code and data live.
    The person can edit any text, remove a question or a chart, then press **Save**.
11. **A new cartridge** appears under the chat box. It carries everything: the story, the charts, the code, the
    questions and their options. This is the Mini's "API".

## B. Using a Mini (the only place the local model works)

1. **Opening.** The person clicks a cartridge. The left chat becomes that Mini and shows exactly what the author
   left: the story, the live charts, the questions it answers and their options. No model has run yet.
2. **Asking.** The person asks in their own words. Now the local model maps the question to one of the Mini's
   questions and options, shows which one it chose, and the Mini's own code answers.
3. **Out of scope.** If no question fits, Idli says so and offers a card: *"This Mini can't answer that. Send your
   question to Claude, with the Mini's files masked? Claude will see: <the masked question>."* Yes -> the same Claude
   flow as Part A, with the Mini's files and code as context.
4. **Growing the Mini.** At the end, Claude offers to **add** what they found to this Mini, or **save a new Mini**.

## What runs where
- Left chat: Paseo's chat. Its replies outside a Mini are written by code; inside a Mini, the 9B only picks a
  question and options, and the Mini's script writes the answer.
- Right: Claude Code CLI, launched through Idli's masking proxy, with Idli's tool server (charts, Minis) and Idli's
  instructions.
- Idli's local server serves the pages shown inside the panes: privacy review, charts, the Mini editor.
