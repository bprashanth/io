# Idli Desktop: an operating layer for NGOs

2026-11-16. Written after Teams became a page. It replaces the strategy brief of 2026-11-13 (still in git history:
`git show 459eed69:narrative/IDLI_DESKTOP.md`). Each claim is marked **[built]** (in the code), **[tested]** (walked
through in the app on the laptop's test account), **[idea]** or **[untested]**. How a person moves through Drivey and
Teams, step by step, is in [DRIVEY_JOURNEY.md](DRIVEY_JOURNEY.md). The design reasoning is in
[docs/idli-design.md](../docs/idli-design.md). Where the work stands is in
[docs/idli-handoff.md](../docs/idli-handoff.md).

---

## 1. What we are doing

People at NGOs run on spreadsheets, WhatsApp groups, email, funder portals and Google Drive. AI agents such as
Claude Code can now do much of that work, but NGO staff stop using them for four reasons:
- the data is about real people and can't be pasted into a chat;
- every task means switching between tools;
- they can't tell if an answer is right;
- they're afraid the agent will break something.

On top of that, frontier models cost money that a programme budget doesn't have.

**Idli Desktop is meant to be the operating layer between an NGO's people and AI.** The goal is that an NGO can use
AI first, for its real work, at a cost it can manage and without giving up the privacy of the people it serves. It
should be able to keep what it builds this way, and pass it on to the rest of the team.

It works by splitting each job between two kinds of model:
- **A large model learns once, on stand-ins.** It sees fake or masked copies of the data, or test accounts. It
  writes code, scripts and an explanation.
- **A small model runs that work every day.** It runs on the real data, on the person's own computer, as the
  person. It makes only small choices; code does the arithmetic and the actions.

The person sees each hand-off between the two and says yes to it. What the large model leaves behind is kept as a
**Mini**, and Minis are kept and shared inside a **Team**.

The shell is **Paseo**, a desktop app that hosts agent CLIs (Claude Code, Codex, a local model) and a browser with
the person's own logins. We patch it (build idli25 today), and the person never sees a terminal they didn't ask
for. **[built]**

---

## 2. What a Team is

**A Team is a collection of Minis, the people who use them, and the rules they share, organised around one kind of
work.** Examples are "Insights" (household survey analysis), "Field M&E" or "Livelihoods Wardha". In the sidebar a
team is a heading. Under it are the team's workspaces. Each workspace is the two halves: Idli on the left and the
person's own Claude on the right.

A team holds:
- **Its Minis.** Each team has its own list, separate from other teams.
- **Its folder.** `~/idli-insights/teams/<name>/` holds the answers given at setup (`team.json`), the instructions
  and tools, downloads, and the privacy codes. Claude's masked copies sit beside it in `claude-masked-<name>`.
- **Its rules, set by answering the setup questions:**
  - where the data lives;
  - who uses it;
  - whether the files hold names, places or phone numbers (masking stays on whatever the answer);
  - whether a Mini may ask an outside service when it can't answer.
- **Its own trail.** The Privacy log labels every request with the team's name.

A manager makes a team on the **Teams page** under Start here: New team, six questions with one panel each, then
Set it up. The new team's card then has **Open** and **Delete**. Delete removes the team's chats and moves its
folder to an archive, so a mistake loses nothing. **[built, tested 2026-11-16]**

**Why a team and not an app:** what an NGO builds belongs to a group of people doing a job, not to one person's
chat history. The team is where a Mini made by one person becomes something everyone else can use. It is also where
rules belong that individuals shouldn't have to decide each time, such as "this team never uses the outside
service". Drivey is the first team. It was built by hand, and the PoC's "make a team" produces exact copies of it
under new names.

**Not built yet [idea]:**
- membership across computers (a team today lives on one machine; its Minis travel by share code);
- roles (who may make Minis and who only uses them);
- team-wide settings beyond the four questions;
- a team whose Minis are workflows rather than data (see section 3).

---

## 3. What a Mini is, and whether the two kinds are the same thing

A Mini is **a piece of work the large model learned once, saved so a small model and code can repeat it on demand,
and shared with the team.**

### The two kinds as they look today

**The data Mini (Drivey) [built, tested]**
- **Data:** one or more Drive files. These are fetched fresh as the person every time the Mini opens, so the numbers
  are always current.
- **Scripts:** one per saved question. Each has its options (ward, months, species).
- **A narrative:** the author's own text and the pinned charts, arranged like a short document.
- **Follow-up questions:**
  1. The small model maps the person's words to one saved question and its options, and the script answers.
  2. If nothing fits, the person can say yes to the outside query service.
  3. If that doesn't work, the question goes to Claude, on masked copies.
  4. Whatever Claude finds can be added back to the Mini.

**The workflow Mini [idea; WhatsAppy is an empty space for it]**
An example: log in to email, find emails with leads, add them to the Excel sheet, and schedule a call on the
calendar. It has:
- logins in the app's browser (email, Drive, calendar);
- a sequence of steps, where each step is code that reads or writes one page, like a small API for that site;
- a narrative of what the workflow does and when;
- small decisions along the way: is this email a lead, which row is it, which free slot to pick.

### Are these two patterns the same?

**They have the same shape. What differs is the effects they have on the world.** Lay both Minis side by side and
they have the same parts:

| Part | Data Mini | Workflow Mini |
|---|---|---|
| **What it is bound to** | Drive files, read as the person | Logged-in sites, used as the person |
| **What the large model learned on** | A fake or masked copy of the file | Test accounts, or recorded pages with fake data |
| **Entry points** | Saved questions with options | Named actions with parameters ("find leads since Monday") |
| **Code behind each entry point** | A script that reads the file | Step code that reads or writes pages |
| **What the small model does** | Picks the question and options | Picks the action, and makes the small judgements in between (is this a lead?) |
| **Narrative** | The author's page and charts | What it does, when, and what it will change |
| **When it can't do something** | Query service with a yes, then Claude on masked copies | Same: ask, then send it to Claude on stand-ins, with a yes |
| **How it grows** | Claude adds a question | Claude adds a step or an action |

The data Mini is the read-only special case of the workflow Mini. One of its steps is "fetch the file" and the rest
are "answer". **The building blocks are therefore shared** (section 4), and the team, the Minis list, the share code
and the consent cards should serve both kinds.

The differences are real, and all of them come from the workflow Mini being able to change things:
- **Writes need a yes each time,** at least at first. A data Mini can't hurt anything. A workflow Mini sends emails
  and books meetings. The rule already used for Drive applies: never overwrite, never delete, and a card before every
  write. (On WhatsAppy the owner's rule today is that nothing is sent at all, by anyone, including the private 30B.)
- **It runs over time.** It needs triggers ("every morning") and a log of what it did. A data Mini just answers when
  asked.
- **It is more fragile.** Sites change their pages, so step code breaks. The fix is in the same loop: the small model
  notices that a step failed, and the large model re-learns that step on the test account.
- **It needs more trust.** A shared Mini that acts in someone's browser is more dangerous than a shared dashboard.
  It needs to show who made it and what it can change, before anyone says yes to it.

There is a third kind, an **org kit Mini** **[idea]**: brand colours, templates and "how we make the newsletter in
Canva". It has no small model and no data, only instructions and assets for the person's own Claude. It fits the
same table with most rows empty. That is why the Mini, not the dashboard, is the right unit.

---

## 4. The building blocks

Each block is one piece of the operating layer. Most were built for Drivey and are meant to be reused by every team
and every kind of Mini.

### 4.1 Small models
- A **local 9B** (Qwen 3.5 9B) runs on the person's computer, free. **Muse 30B** runs on our own hardware for
  heavier private work. Evals compare against Muse 30B on held-out sets. **[built]**
- **What they do:** choose, not compose. They map a question to a saved script, choose its options, and decide which
  card to show next. Code computes every number and writes every sentence that carries a number. When the 9B wrote
  answers in its own words, it dropped a number in 13 of 53 turns; when code wrote them, none were dropped. Mapping
  questions to a Mini's scripts with the 9B scored 84 of 85, including 20 of 20 correct "no match" answers.
  **[tested]**
- **Why it matters for cost:** the expensive model is used once to learn. The cheap model is used every day.

### 4.2 Redaction (masking)
- **What leaves the computer is masked:**
  - the person's own Claude Code reaches Anthropic through Idli's masking proxy (`lib/ccproxy.py`);
  - names, places, phone numbers and other private values become codes (`NAME_007`, `PLACE_005`) in every request;
  - the replies are turned back into real values for the person. **[built, tested]**
- **Claude works on masked copies of the files**, not the real ones, inside its own sandbox (it can't read Idli's
  private folder). An earlier version showed why this matters: Claude found real species names by running scripts on
  the real file. **[built, tested]**
- **The person checks what will be hidden before anything leaves.** The privacy review shows a switch per column,
  with real values next to their codes. **[built, tested]**
- **Start here > Privacy** lists everything sent in the last 7 days, as codes, and can be searched by a real name.
  **[built, tested]**
- **Wire audits on the laptop found no real values in what was sent.** One example: 16 requests, 0 real names,
  250 place codes. **[tested]**
- **How it detects private values:** a vault of known values, close matches, regex rules, and a local name scanner
  (GLiNER). **[built]**

### 4.3 Large and small models working together
- **Teacher and worker:** Claude teaches on stand-ins, and what it leaves behind is code (scripts, chart code, a
  Mini). The private model drives that code on the real data. **[built]**
- **The two halves on screen:** Idli (the small model and code) on the left, the person's own Claude on the right.
  A bright border shows which side is in control, so a hand-off looks like the focus moving. The split now repairs
  itself if Paseo loses it. **[built, tested]**
- **Charts travel between them:** Claude's charts appear in Idli's chat, and a click on a bar can send that bar back
  to Claude as a question. **[built, tested]**
- **No new subscription:** Claude is the person's own Claude Code subscription. Idli doesn't resell it. (Open
  question: the subscription terms may rule out a proxy that rewrites prompts. If so, the right side switches to
  Codex.) **[open]**

### 4.4 Escalation to larger models while the work runs, with consent
Most questions never leave the computer. When a piece of the work is beyond the small model, that one piece goes up
the ladder, and every step up has a yes or no card that shows exactly what will be sent:
1. **The Mini's own scripts** answer, on this computer. **[built]**
2. **The outside query service** comes next. It gets the masked question and the column list, never rows, and writes
   one read-only query that runs locally. It may ask back which of two or three questions was meant. It is capped at
   200 questions a day per computer. A team can turn it off at setup. **[built, tested]**
3. **Claude on masked copies** is next. The person switches to the right half and Claude works there. **[built,
   tested]**
4. **Inside Claude:**
   - `unmask` can reveal a contextual value (a place, a species), never a personal one. It needs two consents and
     is limited to 3 reveals per workspace.
   - `lookup` searches the web from this computer with the real value, and the results are masked before Claude
     sees them. **[built, tested]**

The rule throughout: **escalate the piece, not the whole job, and only with a yes.**

### 4.5 Logins and the browser ("UI as API")
- **No OAuth apps and no API keys for Google:**
  - the person signs in once in Paseo's browser;
  - Idli reads Drive with that session, and the cookies go only to Google;
  - a shared Mini fetches its file with the receiver's own Google account. **[built, tested]**
- **Site plugins:** narrow tools that read a page like an API. The large model writes them on a test account, and
  the small model uses them on the real account. Only Google is built; it was first built for Gmail, Drive and
  Sheets. **[built for Google]**
- **Start here > Logins** checks Google, Claude and the private model, and helps the person sign in.
  **[built, tested]**
- **Open problems:**
  - reading the session through DevTools needs a proper Paseo change before shipping;
  - many sites' terms forbid automation;
  - funder portals rarely have test accounts. **[open]**

### 4.6 Sharing Minis
- **How it works:**
  - a Mini has a share code (`IDLI-XXXX-XXXX`);
  - the receiver says yes, and the Mini appears in their list;
  - the code carries the workflow and which file it points at, never data rows;
  - the code bundle is stored at silo.idli.cc. **[built, tested on one account]**
- **Not tested yet:** two different Google accounts.
- **Not built:**
  - updates to a shared Mini (a share is a frozen copy today);
  - cloning a Mini onto a different file of the same kind;
  - signing, so people can see who made a Mini. **[idea]**

### 4.7 Organising Minis and workflows
- **Today:**
  - Teams are headings, and each team has its own Minis;
  - Start here holds the Teams page, Privacy and Logins;
  - in a workspace, Minis show as slim cartridges under the chat box. **[built, tested]**
- **Next [idea]:**
  - a team's Minis page that lists data and workflow Minis together;
  - a Mini's entry points, as an index the small model can search across Minis;
  - a library of common Minis (a funder's report format, a standard survey) that NGOs clone rather than share.

---

## 5. Cost

| Who does the work | Who pays | How often |
|---|---|---|
| The small model (9B) on the person's computer | Nobody | Every day, most questions |
| Muse 30B on our hardware | Us (could be a paid tier) | Heavier private work |
| The outside query service (DeepSeek through OpenRouter) | Our OpenRouter key in the PoC; short replies, capped at 200 questions a day | Questions the Mini can't answer |
| Claude | The person's own subscription | Learning, and new questions, with a yes |

The design keeps the expensive model at the edges, for learning and for new questions, and the cheap model in the
middle, for the daily work. As a team's Minis grow, it needs Claude less.

---

## 6. Open questions

- **Subscription terms.** Can a person's Claude subscription go through a proxy that rewrites prompts? If not, the
  right half becomes Codex.
- **Workflow Minis that write.** How much approval is enough, how is a Mini made safe to share, and which sites can
  be automated through the browser at all?
- **Teams across computers.** A team is on one machine today. A real team needs shared membership, and a way to keep
  Minis in step without a server that holds data.
- **The first Mini.** A guided first Mini from a sample file, at the end of making a team, is still a concept.
- **Is this a product or a wedge?** If the CLI makers add their own desktop apps, what stays ours: privacy,
  cheap daily runs, and Minis organised by team for NGOs.

---

## 7. What exists today

- **Paseo build idli25:**
  - Start here: the Teams page, Privacy, Logins;
  - Drivey: Idli on the left, the person's masked Claude on the right, Minis, and the query service;
  - team headings made from the Teams page, as Drivey clones;
  - WhatsAppy: an empty Claude space with no sending.
- **Evidence:**
  - tests, synthetic fixtures and evals against Muse 30B;
  - laptop walk-throughs on a test Google account (chronology under `chronology/2026-11-1*`).
- **Not built:**
  - workflow Minis;
  - org kit Minis;
  - teams across computers;
  - Mini updates, clones and signing;
  - the guided first Mini.
