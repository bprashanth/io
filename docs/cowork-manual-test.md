# Co-work POC: manual test (owner)

About 30–45 minutes. You need:
- the laptop, with Paseo open and a Google account signed in to a workspace browser tab;
- the DGX agent ready, if you want it to watch.

Write down anything odd as you go, especially what you expected versus what happened. Each note is a
candidate for the DGX agent's first fix.

The paths below are short:
- `cowork/` means `~/src/github.com/bprashanth/io/benchmarks/runs/2026-11-06-oss-desktop-independent/cowork`.
- `~/idli-insights/cowork-real` is the "private data" folder. It holds a synthetic stand-in workbook.

## 0. Bring it up (laptop terminal)

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
