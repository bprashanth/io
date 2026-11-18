# Idli's UX: the Builder outside, sandboxes inside

The owner's model, set 2026-11-18. It replaces Teams as the way an org gets to its workflows. Drivey stays exactly as
it is. Related: [ESCALATION_MODELS.md](ESCALATION_MODELS.md), [SANDBOXES.md](SANDBOXES.md) (being written with the
build), [BUILDER_JOURNEY.md](BUILDER_JOURNEY.md) (the earlier, team-based version) and
[DRIVEY_JOURNEY.md](DRIVEY_JOURNEY.md).

## The idea

There are two places, with a hard line between them.

- **Outside: the Builder.** An ordinary Claude Code project. The person can do anything there: build a dashboard,
  write a script, plan. It never touches their private accounts or real files. To extend what the org can do
  safely, you come out here.
- **Inside: sandboxes.** Each one is like a small VM. It has only the building blocks it was created with, works
  on the real accounts and files, and keeps Claude to redacted data. Inside, the person can do less, but it is
  safe.

All of an org's workflows are sandboxes: insights over Drive files, and actions like leads follow-up. An insights
workflow is just a workflow.

## The sidebar

- **Start here:** sign-ins and setup, as today. The Teams page and the New team wizard are gone from it.
- **Drivey:** unchanged.
- **Builder:** the outside Claude Code project.
- **Sandboxes:** one item each, named like a Docker container, with the workflow at the end, for example
  `wobbly-heron-3f2a leads` or `brisk-otter-91c0 insights`.

Nothing else. No Analyst and Builder double tabs, no Teams cards, no Installed tools page. The Teams page's one
line of tool usage goes away with it.

## The journey

1. **The person works in the Builder.** It's ordinary Claude Code work, unrelated to private data.
2. **They want a workflow that touches private accounts or files.** They type `/sandbox`.
3. **The Builder asks what the old Teams cards asked:**
   - what you want to do;
   - whether the data has names, places or phone numbers;
   - whether Idli may ask an outside service (masked data only) when it can't answer;
   - which accounts to use.
4. **The Builder breaks the request into building blocks**, from a fixed list:
   - Drive files and Minis (insights, as in Drivey);
   - Gmail: search, read, draft;
   - Calendar: free times, book;
   - Sheets: read;
   - the 9B: a judgement with an answer shape;
   - catalog tools (speech, OCR, translation, face blur and so on).
5. **Gap or sandbox:**
   - **If a needed block is missing,** the Builder says so plainly ("There's no block for posting to Instagram
     yet") and does not create the sandbox. The gap is recorded as a platform request.
   - **Otherwise** it creates the sandbox with exactly those blocks.
6. **The sandbox opens as a Drivey-style split.**
   - **Left: Idli,** the private 9B chat. `@` files, Minis, and escalation to an outside service, as Drivey does.
   - **Right: Sandbox Claude** (the Analyst, renamed). It sees only redacted data: files as today, and account
     data (senders, email bodies, calendar titles) redacted the same way.
7. **The person assembles the workflow step by step in the left chat.** They see each step work before adding the
   next.
   - **Insights:** `@ attendance.xlsx`, "which ward dropped most?", then save as a Mini. This is what Drivey does
     today.
   - **Leads:**
     - "Read my emails from foo@bar.com". It shows them.
     - "Offer them three free times". A draft appears in Gmail and the person sends it.
     - They reply. "Book the time they picked". The 9B reads the reply, and the event lands on both calendars.
     - Save the whole thing as a Mini. Running the Mini again doesn't double anything.
8. **Sandbox Claude helps design** when the left chat can't do a step on its own. It writes the script on redacted
   data. For action workflows the script calls the 9B for judgement on real content (escalation model A). For
   insights the 9B picks the Mini, and escalates when it can't answer (model B).

We build the blocks, not each team's workflow. The person learns to test step by step, and the saved Mini is their
workflow.

## Accounts

- Google access is by OAuth with Idli's own app. Sign-in happens once per account in a real browser (Google forbids
  embedded browsers). People click Advanced, then "Go to idli (unsafe)", because the app is unverified. The cap is
  100 users.
- Daily work uses Google's APIs, not the web pages: faster, and no page quirks.
- Testing uses the two test accounts, 87profligate@gmail.com ("me") and 88profligate@gmail.com ("a lead").
  Sending email between them is allowed. WhatsApp: never send.

## Copy rules

- Plain words, few commas, no arrows or "·".
- Names: "Builder", "Sandbox Claude", "Idli".
- A gap is stated, never worked around.

## What changed from Teams (2026-11-17)

| Teams (before) | Sandboxes (now) |
|---|---|
| New team wizard with cards | `/sandbox` in the Builder asks the same questions |
| A Builder per team, inside the team | One Builder, outside |
| The Builder writes each team's workflow and rehearses it | We build blocks. The person assembles and tests the workflow in the left chat |
| Analyst | Sandbox Claude |
| Teams page, Installed tools | Gone |
| Test accounts in Chrome profiles for the Builder to click through | OAuth plus the APIs. Chrome profiles only for sites with no API |
