# Idli Desktop: an operating layer for NGOs

2026-11-19, updated 2026-11-20. Written after the move from Teams to sandboxes. It replaces the 2026-11-16 version, which was written
around Teams (still in git history: `git show 620f12e5:narrative/IDLI_DESKTOP.md`). Each claim is marked
**[built]** (in the code), **[tested]** (walked through in the app on the laptop's test accounts), **[idea]** or
**[untested]**.

**Update 2026-11-20:** the core engine under this product is now described in [GOALS_V0.5.md](GOALS_V0.5.md):
- a local record store per sandbox;
- one command language (`idli list`, `judge`, `ask`...);
- definitions, views and chains as what a Mini is made of;
- the blind benchmarks.

Read that first for where the thinking is. This page stays the product view: Paseo, the Builder, sandboxes, Minis,
masking.

Details live in:
- [GOALS_V0.5.md](GOALS_V0.5.md): the core (scaffold, commands, store, results, journeys);
- [SANDBOXES.md](SANDBOXES.md): the model, routing, blocks;
- [ESCALATION_MODELS.md](ESCALATION_MODELS.md): who decides what;
- [UX.md](UX.md): what the person sees;
- [PAGES_AND_TOOLS.md](PAGES_AND_TOOLS.md): the trusted catalog and pixi;
- the chronology `chronology/2026-11-18T0900-catalog-routines-sandboxes.md`.

---

## 1. What we are doing

People at NGOs run on spreadsheets, email, calendars, WhatsApp and Google Drive. AI agents can do much of that
work. NGO staff don't use them because:
- the data is about real people;
- they can't tell whether an answer is right;
- they're afraid the agent will break something;
- frontier models cost money.

**Idli Desktop is the layer between an NGO's people and AI.** The aim is to let an NGO use AI first, on its real
work, without giving up the privacy of the people it serves.

The method hasn't changed:
- **A large model learns once, on stand-ins:** masked data, fake files, test accounts.
- **A small private model and code do the daily work** on the real data, on the person's computer.
- **What the large model leaves behind is kept as a Mini.**

The shell is **Paseo**, a desktop app that hosts Claude Code and other agents, with Idli's patches (build idli26 on
the laptop). **[built]**

---

## 2. Teams are postponed, not dropped

Until 2026-11-17 the organising unit was the **Team**:
- a heading in the sidebar;
- a New team wizard with six questions;
- a per-team Builder and Analyst;
- a Teams page with an Installed tools line.

It worked, but it put too many ideas on screen at once. People had to understand teams, two Claudes per team,
stacks, tools and Minis before doing anything.

**Decision (owner, 2026-11-18):** be brutally simple for now. Strip the product down to the two things that have
to exist for anything else to work: **the Builder and the sandbox**. Teams are removed from the sidebar and the
wizard is gone. This is a postponement, not a conclusion. The reasons for teams still stand:
- what an NGO builds belongs to a group doing a job;
- rules like "never use the outside service" belong to the group, not the individual;
- Minis need a home where one person makes them and others run them.

Teams come back once the barebones are solid, probably as a layer over sandboxes: a team owns some sandboxes, their
Minis and their rules. Until then the "one person builds, the rest run" pattern is carried by the Mini and its
share code. **[idea]**

Drivey, the first hand-built team, stays exactly as it is. It is the regression check for every change.
**[tested, first and last in every round]**

---

## 3. The barebones: two places

There are two places, with a hard line between them.

### 3.1 The Builder: outside

- **What it is:** an ordinary Claude Code project in the sidebar. It defaults to Opus, like Antigravity. If Paseo
  has no Claude Code, it falls back to Idli 9B or 30B. **[built, tested]**
- **What it's for:** anything with public data: a dashboard from a public dataset, a script, a plan. The opening
  line says so: "Build with public data here. For private data or your own accounts, type /sandbox."
  **[built, tested]**
- **What it never sees:** the person's private files, accounts or what a sandbox finds. It sees each sandbox as a
  black box: its name, its blocks and its accounts. **[built]**
- **What it does for sandboxes:**
  1. **`/sandbox`:** it asks four questions, one at a time:
     - what you want to do;
     - whether the data has names, places or phone numbers;
     - whether Idli may ask an outside service (masked data only): ask each time, never, or always;
     - which accounts to use.
  2. **It maps the request to blocks** and makes a sandbox with exactly those. **[built, tested]**
  3. **It refuses a missing action** in plain words and records it as a request to our team. Instagram posting,
     and running on a schedule, were both refused. **[built, tested]**
  4. **It writes missing transforms** and adds them to a sandbox, after one approval card (section 4).
     **[built, tested]**

### 3.2 The sandbox: inside

- **What it is:** a sidebar heading named like a container (`merry-parrot-7ac1 leads`,
  `lucky-koel-7672 drivecharts`). It opens as a Drivey-style split. **[built, tested]**
- **Left, Idli:** the private 9B and code, on the real files and accounts.
  - Here the person asks questions, runs Minis, and sees every real result.
  - The 9B never chooses freely (section 5).
- **Right, Sandbox Claude:** Claude Code on masked data only.
  - Files reach it as masked copies. PDFs reach it as masked text.
  - Account content reaches it masked.
  - It can only use the blocks plugged into its sandbox. Its scripts get the same import check as blocks.
  - It never runs anything on real data itself. Idli runs its scripts, shows the real output on the left, and
    hands Claude the masked output. **[built, tested]**
- **Why the split:** inside, the person can do less, but it is safe. To extend what a sandbox can do, you go back
  outside to the Builder.

### 3.3 Who sees what

| | Real data | Masked data | Can change what a sandbox can do |
|---|---|---|---|
| **Builder** | Never | Never; only fake data and the trusted list | Yes: makes sandboxes, writes transforms |
| **Sandbox Claude** | Never | Yes | Only through Minis built from its blocks |
| **Idli (9B + code)** | Yes | — | No; it picks from fixed menus |
| **Outside service** | Never | The masked question and a short menu | No; it picks one item |

---

## 4. What a sandbox can do: three levels

| Level | Examples | Who builds it |
|---|---|---|
| **Actions** | Gmail drafts, Calendar bookings, anything that writes, sends or posts, a new website, a schedule | Our team only. The Builder refuses and sends a request |
| **Transforms** | Read PDFs, Word or tables; summarise; ask the 9B | The Builder writes them and adds them, within the trusted list |
| **Pages and servers** | Page servers, long-running tools | Undecided: on the person's computer or on silo |

### Actions: built by us [built, tested on 87 and 88]

- `drive_files`;
- `gmail_search`, `gmail_read` and `gmail_draft` (drafts only: the person presses Send);
- `calendar_freebusy`, `calendar_book` and `meetings`;
- `sheet_read`;
- `nine_b`, a judgement on real content with a fixed answer shape.

They run through Google's APIs with Idli's own OAuth app, with tokens per account on the person's computer. A
booking has a fixed key, so it is never made twice.

### Transforms: written by the Builder [built, tested]

- **What it checks:**
  - only trusted imports, baked into the build (plain-transform stdlib, pandas, numpy, openpyxl, pypdf,
    python-docx);
  - no network, no files outside the sandbox, no `eval`;
  - a test on fake data.
- **Cost:** the check takes about 0.1 s, once, when the block is added. Each run only compares a digest.
- **Approval:** the person sees one card: "Add block: Read PDFs. Uses pypdf. Reads PDFs you give it. Sends
  nothing."
- **Results on the laptop:**
  - the owner's "add PDF reading to drivecharts" took 43 s;
  - 18 PDFs were answered in 63 s, then 20 s for a follow-up;
  - a block that imports `requests` was refused with a plain reason.
- **The catch:** there is no wall (no bwrap) on any platform for now. The check is a guard, not a boundary. Walls
  come with the p1 `sandboxing_later` todo.

### The trusted catalog [built, tested; not yet wired into sandboxes]

Heavier tools (Whisper, Piper, NLLB, OCR, face blur and others, 14 in all) are vetted by us and served from silo.
They install with pixi on every platform, and installing them is the same on every OS. They fit the transforms
level once the catalog's tools are offered to the Builder as block dependencies. **[idea]**

---

## 5. Minis, and how a question is answered

A **Mini** is work Claude did once, saved so Idli can repeat it on the real data without Claude.
- **Data Minis** are scripts per saved question.
- **Workflow Minis** are scripts in **named steps**: read the leads, find replies, have the 9B read each one, and
  draft times. Each step can run on its own, in preview. **[built, tested]**

### The chain (owner, 2026-11-18) [built, tested]

The 9B never chooses freely. When it was allowed to, it made up a sheet link and gave empty answers. Each question
goes down this chain until something can answer it:

1. **The 9B, direct.** This covers only what maps cleanly to the open Mini:
   - its saved questions;
   - "run step 2";
   - explain;
   - a preview of the whole Mini;
   - run, turn on, or fork.
2. **Mapping, with consent.** The outside service gets the masked question and a short fixed menu: the Mini's
   steps and the sandbox's read blocks, or SQL for a data Mini. It picks one item. Idli runs it on the real data in
   preview and shows the output as the code wrote it. Write actions are never on the menu.
3. **The 9B maps instead** if the person says No. This is the person's quality call.
4. **Fork to Sandbox Claude** when nothing on the menu fits. Claude gets a copy of the Mini and the masked
   question. It splits a step, adds one, adds a chart or adds a file. Idli runs each try, and it saves as a new
   Mini. The original never changes.
5. **The Builder** for anything net new, such as a missing action.

A question asked with no Mini open goes straight to Sandbox Claude, masked, which builds a Mini for it.

**Why this matters:** in a team, one person makes the Minis with Claude and everyone else runs them. Nobody runs a
leads Mini they can't check piece by piece. So the person has to be able to:
- see each step's output;
- ask basic questions the blocks can answer even if the Mini doesn't name them, like "show me my meetings
  yesterday" or "which emails are new";
- get correct answers to those.

If that stage fails, people give up on the Mini. That is why the chain escalates for mapping instead of trusting
the 9B alone.

### Turning on and forking [built, tested]

- **Turn on:** "turn this on for my account" binds the Mini to an account from today. Running on a schedule is
  still a gap.
- **Fork:** a button on the Mini card. Sandbox Claude opens with the current flow and asks how to change it.

### Tested on the laptop (2026-11-18)

- **Leads**, in the merry-parrot sandbox:
  - "list of leads" took 9 s;
  - "meetings yesterday" took 8 s;
  - "which emails are new" took 18 s, with the 9B mapping it after a No;
  - "the draft for Asha" took 44 s;
  - "step 2" on a Mini with no steps went to a fork, which split it into 6 steps;
  - "which leads agreed but haven't picked a time" mapped to step 4 and took 94 s;
  - Instagram ended at the Builder.
- **Insights**, on a public survey with a report PDF and data CSV:
  - the PDF reached Claude masked;
  - a two-chart Mini was saved;
  - adding the 2025 data with the Mini open made a new, extended Mini.

---

## 6. Masking and accounts

- **What goes outside is masked:** names, places and numbers become codes. This covers Claude's requests through
  Idli's proxy, files, PDF text and account content. The person checks a privacy page before files go, and
  "<column> entirely withheld" is shown plainly. **[built, tested]**
- **Accounts:**
  - Google uses OAuth with Idli's own app, which is unverified (Advanced, then "Go to idli"), with a cap of 100
    users. Daily work uses the APIs, not the web pages.
  - Testing uses 87profligate (me) and 88profligate (a lead). Sending between them is allowed. WhatsApp never
    sends. **[built, tested]**
- **Gaps:**
  - account content is masked as text but not yet reviewed column by column the way files are;
  - connecting a real account with "start from today" has been tested only with 87 standing in. **[untested]**

---

## 7. Cost

| Who | Pays | When |
|---|---|---|
| The 9B on the person's computer | Nobody | Every day, most questions |
| Muse 30B on our hardware | Us | Heavier private work |
| The outside service (mapping, SQL) | Our key in the PoC | Questions a Mini can't place, with consent |
| Claude (Builder and Sandbox Claude) | The person's own subscription | Building, forking, new questions |

The expensive model stays at the edges. As Minis grow, Claude is needed less.

---

## 8. Open questions

- **When teams come back,** what do they own: sandboxes, Minis, rules, people? How do they work across computers?
- **Walls.** The transform check and the trusted list are a guard on every platform. A real boundary needs bwrap,
  WSL or containers (p1 `sandboxing_later`).
- **Pages and servers:** do they run on the laptop or on silo?
- **Schedules.** A workflow Mini that runs every morning is still a gap, and it's the most-requested action.
- **Speed.** Steps where the 9B reads every reply take 70 to 95 s, and the first masking of a long PDF takes 1 to
  3 min.
- **Subscription terms.** Can a person's Claude subscription go through a masking proxy?
- **The Builder's own guard.** The approval check sits in a folder the Builder can edit, and should move out.

---

## 9. What exists today

- **Sidebar:** Start here (Logins, Privacy), Drivey, the Builder, and one heading per sandbox. **[built, tested]**
- **Sandboxes on the laptop:**
  - `merry-parrot-7ac1 leads` (Lead replies, Lead replies in steps);
  - `quiet-tiger-0760 survey`;
  - `lucky-koel-7672 drivecharts` (Read PDFs);
  - the fixity insights Minis.
- **Alpha release, prepared and not pushed:**
  - `.github/workflows/idli-alpha.yml` builds patched Paseo plus the Idli kit for Linux, Mac and Windows;
  - only the Linux arm64 build has been made for real;
  - the Windows installer doesn't run yet;
  - the apps are unsigned;
  - each tester needs the DGX and a silo token.

  Steps are in `docs/idli-alpha-release.md`.
- **Tests:** 356 passed and 5 skipped on the laptop. 11 failures are older than this work, in `lib/test_chat.py`
  and `lib/test_home.py`.
- **Evidence:** `benchmarks/runs/2026-11-18-*` (sandboxes, builder-minis, transform-blocks, mini-escalation), each
  with a README and screenshots.
- **The core, headless (2026-11-19 to 20):**
  - `cowork/desktop/idli`, a command line over a DuckDB store per sandbox, synced read-only from Google;
  - definitions judged by the 9B;
  - `idli ask`, where idli-remote or the 9B maps words to commands, Idli runs them, and the 9B words the reply.

  On blind held-out asks, trust questions and people's own definitions mostly work; multi-step workflows don't yet,
  because there were no Minis to fix the meaning of words like "lead". See [GOALS_V0.5.md](GOALS_V0.5.md) and
  `benchmarks/runs/2026-11-19-record-store/`. Not wired into the app yet.
