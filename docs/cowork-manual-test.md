# Co-work POC: manual test (owner)

About 30–45 minutes. You need:
- the laptop, with Paseo open and a Google account signed in to a workspace browser tab;
- the DGX agent ready, if you want it to watch.

Write down anything odd as you go, especially what you expected versus what happened. Each note is a
candidate for the DGX agent's first fix.

The paths below are short:
- `cowork/` means `~/src/github.com/bprashanth/io/benchmarks/runs/2026-11-06-oss-desktop-independent/cowork`.
- `~/idli-insights/cowork-real` is the "private data" folder. It holds a synthetic stand-in workbook.

## The Idli journey (current, 2026-11-09)

About 30 minutes, most of it reading Claude's questions. Uses your real cestrum workbook
(`field_vars_indicators.xlsx`); swap in any multi-tab sheet.

**0. Bring it up (laptop terminal)**
```sh
cd ~/src/github.com/bprashanth/io/benchmarks/runs/2026-11-06-oss-desktop-independent/cowork
git pull                                   # branch oss-desktop-eval
python3 desktop/setup-laptop.py            # adds matplotlib; idempotent
python3 desktop/idli-bootstrap.py          # rewrites Idli's CLAUDE.md and cowork.sites (google + files)
pkill -f lib/formserver.py                 # the form server restarts on Idli's next question
```
Start a **new** Idli chat after any pull (a chat keeps the tool code it started with).

**1. To teach from scratch:** in an Idli chat say "show me what you've learned" (or open the skills page), and
Delete the file's entry. It moves to `~/idli-insights/archive/skills`.

**2. Clean.** New Idli chat, type `hi`.
- [ ] A card: "Clean up a file / Analyse a file". Pick Clean. It asks which file; type a few words.
- [ ] If it lists several matches, pick the original. An "Idli working copy" is labelled as the cleaned version.
- [ ] Unknown file: a card says what goes to Claude (fake values, same columns) with "Yes, send and switch" and a
      Labels question (tick codes Claude may see as they are, e.g. species codes). The app switches to Claude.
- [ ] Claude asks one step at a time, on cards: what a row is per tab, checks (tick, add your own in Other),
      clean-ups, the words of the file, how it read your request. Then "Go back to Idli?". Yes switches back.
- [ ] Idli says teaching finished and asks "Mark them in a copy in your Drive?". Yes.
- [ ] Within ~30 s a tab opens on `<file> - Idli working copy <date time>` next to the original in Drive: red
      cells, an orange corner on the first cell of each kind of problem (hover: the comment), a comment count
      on each tab, a last tab "Idli checks". Fix a cell: its red goes away.
- [ ] Say "I'm ready". Idli re-checks the copy, says what you fixed, and asks how to start.

**3. Analyse.** In the same chat (or a new one: "I want to analyse <file>"; it offers the checked copy first).
- [ ] "I have a question": ask a few in a row, e.g. how many cestrum trees and what share; which plots have
      the most; compare transect 1 and 7. Each answer in 15-40 s, numbers from the form ("the form tab shows it").
- [ ] "Show me a graph of cestrum trees per transect": bars in the chat. "Cestrum share for each transect and
      plot": a grid. Both also in the dashboard's Charts.
- [ ] "Suggest analyses" (start card) or "ask Claude" after a chart: a card, then Claude suggests charts on fake
      data, draws the ones you tick in its chat, takes changes, and hands back. In Idli the charts appear drawn
      from the real data.

**4. Dashboard tab.**
- [ ] One line on top: "N problems in K kinds … View problems in Drive · Details". The link opens the working
      copy. Details opens the full list with suggested fixes.
- [ ] The answer card shows a small bar chart when there is a breakdown; the Charts card shows the file's charts
      (click one to enlarge).
- [ ] Known: in a narrow window the right edge can be cut off (Paseo P11); widen the window.

What to note: where you waited and for what, any card that didn't say enough, any answer that looked wrong.

## Older checks (before the journey was scoped)

### 0. Bring it up (laptop terminal)

```sh
cd ~/src/github.com/bprashanth/io/benchmarks/runs/2026-11-06-oss-desktop-independent/cowork
git pull                                   # branch oss-desktop-eval
python3 desktop/setup-laptop.py            # idempotent; skip if nothing changed
desktop/laptop-up.sh                       # tunnel for the DGX agent
.venv/bin/python run_tests.py sheets       # expect: [sheets] passed 5/5
```
If `laptop-up.sh` says Paseo has no DevTools port, quit Paseo and start it the way it prints.

- [ ] The tunnel is up, and the Paseo daemon, DevTools and Muse all say listening/reachable.

## 1. Co-work on a spreadsheet (private data path)

1. In Paseo, open the **cowork-real** workspace, or create one on `~/idli-insights/cowork-real`.
2. Start a new chat and pick **Co-work · T4GC (private data, no shell)**, model **T4GC model (Idli)**.
3. Ask: *"I've put our field visits spreadsheet in this folder. Which village had the most visits, and how
   many visits led to a referral? Then make me a dashboard of visits by village and by health worker."*
- [ ] It answers in about 2 minutes, using tools called `sheet_*`. Tool calls show in the chat.
- [ ] Correct answers: **Kirugavalu, 32 visits** (once "Kirugaval" is merged in) and **41 referrals out of 120**.
      Last time Muse said Halaguru.
- [ ] An **Open field_visits_….html** button appears under the reply. Click it.
- [ ] A new tab (127.0.0.1) appears next to the chat and shows the bar charts. Known bug: you have to click the tab yourself.
- [ ] Bars and numbers fit the window. Make the window narrow and check again.

## 2. Co-work on Gmail and Drive (your signed-in account)

In a new co-work chat, ask each of these:
- *"About a month ago AWS emailed me saying they hadn't received a payment. Which invoice was it, how much, and how do I pay it?"*
  - [ ] Expected: invoice 2856029173, 1360.08 INR, Billing console → Payments → Pay now.
- *"Find my Wildfires doc and correct its grammar. Just list the corrections, don't edit the doc."*
  - [ ] It lists corrections. The doc is **unchanged**; check it yourself.
- *"There's a sheet in my Google Drive comparing P/BV ratios of Indian, US and European banks. Which bank has the highest P/BV, and how do the Indian banks compare with the US ones on average?"*
  - [ ] Expected: Kotak Mahindra 4.21; India about 2.92 vs US about 0.70.
- *"Draft a reply to the most recent LinkedIn email saying I'm interested but busy until December."*
  - [ ] A draft appears in the Gmail tab, and nothing is **sent**. Discard it afterwards.

## 3. The gap loop (co-work can't, DIY builds it, co-work can)

1. In a new co-work chat, ask for something no tool covers. For example: *"Find the most recent email with a PDF
   attachment and tell me what the attachment says."* (or anything about Google Calendar).
   - [ ] It doesn't invent an answer. It shows a **CO-WORK GAP REPORT** block and tells you to paste it into DIY mode.
2. Copy the block and **remove any personal details** (names, subjects, IDs).
3. Open the workspace on the `cowork/` folder. Start a chat with **DIY · Claude** and paste the block.
   - [ ] It uses the `add-site` skill, explores with the browser and writes code under `sites/`.
   - [ ] If it needs test data, it tells you exactly what to create. For example: "email yourself a PDF".
   - [ ] It runs `run_tests.py` and reports a pass.
   - Takes 10–20 minutes; last time it took 13.
4. Back in the cowork-real workspace, start a **new** co-work chat and ask the question from step 1 again.
   - [ ] It now uses the new tool and answers.

## 4. Let the DGX agent take over

Paste the prompt below into the DGX agent:
```
Read docs/cowork-poc.md and follow "Verify before anything else". The tunnel from my laptop is up.
Report what passed and failed, then wait.
```
- [ ] It reports `ALL CHECKS PASSED`, or names each failure with a likely cause.
- [ ] It runs one co-work question on the laptop and shows you a screenshot of the answer in Paseo.
- [ ] Then give it one bug from your notes (or one from the "Known bugs" table in docs/cowork-poc.md) to fix as a check step.

## Afterwards

- `desktop/laptop-up.sh stop` closes the tunnel. While it's open, the DGX can see every tab, including real Gmail.
- Paseo keeps running. You can delete old test chats and workspaces in the sidebar.
