# Idli: handoff (read this first)

Last updated 2026-11-11 (~14:00 IST), DGX. Overwrite this page whenever the state changes, and keep the chronology
(`docs/cowork-poc.md`, "What changed") and the latest field note in step with it.

## What we are building now
**Idli is a Drive helper for people at NGOs who keep their data in spreadsheets.** It helps them clean a file and
then ask questions of it, with charts, without their data leaving their computer. Its scope today is one file at
a time, which the person pastes as a link:

1. **Learn the file (Claude, on fake data).** Idli makes a copy of the file with fake values, using plain code
   (`lib/filekit.py`, `mock_column`). Claude sees only that copy. With the person answering cards, Claude writes a
   "skill" for the file: what a row is, checks, clean-ups, the file's words, and the "form" (the measures,
   breakdowns and filters that can be asked of it).
2. **Clean (code, on the real file).** The checks run locally. After the person says yes, Idli puts a working copy
   next to the original in their Drive, with red cells and one comment per kind of problem. This is the only write
   Idli ever makes, and the comments come from code, not a model. The person fixes things there and says "ready",
   and from then on Idli answers from the copy.
3. **Analyse (the private model).** Questions go to the private model, which answers only by filling the form
   (`file_ask`). Code computes every number; the model never adds up. A chart the form can't draw, or a question
   it has no measure for, bounces back to Claude with a fresh fake copy and the question. Claude writes chart code
   or extends the form. Idli runs the chart code on the real data inside a sandbox (bubblewrap).
4. **What Idli has learned** grows one file at a time. It's a page in Mission control. The plan is to turn it into
   the index and a graph of files, places, species and plots
   ([todo](../todos/idli-insights/p1/file_by_file_index.md)).

The models:
- **Muse 30B** is the private model today (dense 28B, llama.cpp on the DGX, reached through `silo.idli.cc` behind
  Cloudflare Access).
- **A 9B** is being tested as the free tier. Muse is the baseline it's measured against.
- **Claude** only ever sees fake copies and the person's question.

The app:
- **Paseo** (a desktop app that runs Claude Code chats) is the shell. Idli is a Claude Code chat whose model is
  the private one, plus our MCP server (`cowork_mcp.py`) and its tools.
- The sidebar shows **Start here** (a check that everything is signed in), **Mission control** (What Idli has
  learned), **Idli** (the work; a "New chat" is always waiting on the start card) and **Claude** (teaching).

### The core design: Claude learns from stand-ins, writes code, and the private model runs it on the real thing
Claude (the frontier model) never touches the person's real accounts or real data. It learns from two kinds of
stand-in, and what it hands back is always **code**, which runs locally with the private model.

| To learn... | Claude works on... | It writes back... | Which then runs on... |
|---|---|---|---|
| **A new app or website** (Gmail, Drive, Sheets, a portal) | **Test accounts** signed in to Paseo's browser (`~/idli-insights/config/accounts.json`), in the Claude (DIY) workspace | A **site plugin**: narrow tools that read the page like an API (`cowork/sites/<site>/tools.py`), with tests, via the `add-site` skill | the person's real, signed-in account, used by the private model |
| **A new file** (a spreadsheet's layout, words, checks) | **A fake copy** of the file (same shape, fake values; `lib/filekit.py`), made locally | A **file skill**: the form (measures, breakdowns, filters), checks and clean-ups, via the `teach-file` skill | the real file on the person's machine, through the form engine |
| **A chart or analysis** the form can't do | **A fresh fake copy** plus the person's question | **Chart or analysis code** (pandas, numpy, matplotlib only) | the real data, inside the sandbox (bubblewrap: no network, read-only) |

So:
- **Test accounts teach Claude the app. Fake data teaches Claude the data.** Neither carries the person's
  information.
- **Claude's output is code** (plugins, skills, chart code), never answers about real data. The private model
  (Muse, or the 9B for the free tier) only uses that code and relays what it computes. It never adds up numbers
  itself.
- **The weak points are the stand-ins themselves.** A fake copy that loses the file's mess means Claude writes
  weaker checks (measured in E1 and E2). A test account that differs from the real one breaks a plugin (caught by
  each plugin's tests).
- Everything below (the cards, UI as API, the bounce, the evals) serves this split.

### This is a big turn from the rest of the repo
`io` started as an event experience for local-first models (the stage ladder, sheltered mode with GLiNER
redaction, the Antigravity comparisons, io-codex, sandboxing). Read `README.md` and `docs/stages/` only as
background. The work since 2026-11-06 (the "oss-desktop" line, then "co-work", then "Idli") is the live product.
Don't revive older designs (free SQL over sheets, site plugins for every website, a Drive index built up front,
gap reports pasted by hand) unless the owner asks.

## Read in this order
1. **This page.**
2. **`docs/cowork-poc.md`.** The "What changed" section, newest first, is the chronology for this line of work.
   Read the 2026-11-09 and 2026-11-10 entries in full.
3. **Field notes** in `narrative/`:
   - `2026-11-07-cowork-ui-as-api-field-note.md`: Paseo as the UI, and a 30B model driving it.
   - `2026-11-09-one-journey-field-note.md`: the journey (clean, then talk to a file) on the real cestrum workbook.
   - `2026-11-08-oobe-field-note.md`: the first run on a new laptop (setup, indexing, timings).
   - `2026-11-10-one-file-at-a-time-field-note.md`: what a 9B can do, the three-call shape of a question, and the
     decision to drop the up-front index.
   - On branch `idli-9b-bench` only: `narrative/2026-11-10-idli-9b-field-note.md` (read it with
     `git show origin/idli-9b-bench:narrative/2026-11-10-idli-9b-field-note.md`).
4. **How the machines work together:**
   - `docs/laptop-dgx-sync.md` and `docs/driving-desktop.md`: the owner's laptop runs Paseo; the DGX drives it over
     an ssh tunnel (`desktop/paseo-remote.sh`, DevTools on 49333).
   - Code moves with `git pull dgx oss-desktop-eval` on the laptop.
5. **Testing by hand:** `docs/cowork-manual-test.md`, section "The Idli journey".
6. **Todos, by priority:** `todos/idli-insights/README.md` (p1 = the demo and the architecture evals).
7. **Evidence:**
   - `benchmarks/runs/2026-11-08-oobe/`: first-run timings, and the search eval for the old index.
   - `benchmarks/runs/2026-11-08-form-fill-eval/`: small models filling forms.
   - Branch `idli-9b-bench`, `benchmarks/runs/2026-11-10-idli-9b/REPORT.md`:
     - the 9B vs Muse;
     - the "split" (a separate call that sets the form's dials, inside `file_ask`): 9B 79-81% vs Muse 83% on fresh
       chats;
     - Claude planning on GLiNER-redacted questions: 75-77%.
   - `benchmarks/runs/2026-11-10-idli-pipeline-eval/PLAN.md`: the evals now running (E1-E7, with E9 if needed). The
     results go to branch `idli-pipeline-eval`.
   - Branch `idli-installers`: one-click installers for Mac, Windows and Linux (official Paseo plus bundled
     tools). The demo gaps D1-D11 are in `todos/idli-insights/p1/deployment_strategy.md`.

## Cards: how the person steers, and how work bounces between Idli and Claude
A **card** is a clickable question in the chat (Claude Code's `AskUserQuestion`). Cards are the backbone of the
product. Design rules, all learned the hard way:
- **Tools hand the model the card.** A tool returns `card` (the exact questions and options) and `then` (what to
  do next). The model's job is to show that card as is, with nothing written before it.
  - A small model follows a card it's handed. It skips one it was told to ask *after* writing text.
  - So a card that must happen comes first and carries the text. Optional follow-ups are one line in the chat,
    not a card.
- **Only show a card a tool provided.** The 9B's main failure in E7 was putting up its own card where the person
  should just type. A guard now allows a card only when a tool handed one over. Questions about the data get
  typed answers, not cards.
- **One question at a time,** with a recommended option first. "None (Recommended)" on the labels question means
  the person can click through. Typing in "Other" is answered, and then the card is asked again.
- **Every switch between Idli and Claude goes through a card with a yes.** It says where they're going, what goes
  with them (always the fake copy, shown first in a "Fake copy for Claude" tab), and that a card brings them back.
  Nothing is sent before the yes.
- **The bounce, step by step:**
  1. Idli (the private model) hits something the form can't do: `teach_file`, with `missing` for a question, or
     `chart_request` for a chart.
  2. A card asks: send the fake copy to Claude?
  3. On yes (`teach_send`), the Claude chat opens with the request.
  4. Claude teaches through its own card sequence (the teach-file skill): what a row is, checks (multi-select),
     clean-ups, the file's words, how it read the request. Each step is a card the person answers.
  5. Claude's last card asks "Go back to Idli?".
  6. A small watcher outside Claude's sandbox (`lib/teachwatch.py`) sees the yes, switches the app back, and
     tells Idli that teaching finished.
  7. Idli reruns the question or shows the chart.

  E3 measures this trip. The person is always the one who says go.
- **The start of a chat is a card too:** "Clean up a file" or "Analyse a file", then the link. A first message
  that already says what it wants skips the card.
- **Cleaning uses cards at its two decision points:** "Mark them in a Drive copy?" (the only write) and "I've
  fixed it, go on".
- **Soft phases:** all 12 tools are always listed, so a wrong guess about which step the chat is in costs
  nothing. Hard phases lost questions in E7.
- **Why it matters for privacy:** the person sees and approves every hand-off. Real data stays with the private
  model, and Claude only gets what the card said it would.

## How Idli reaches Google: "UI as API" (an important pattern)
Idli has **no Google OAuth and no Google API keys.** It works through the person's own signed-in browser tabs
inside Paseo.
- **The mechanism:** Paseo's built-in browser tools (snapshot, evaluate, navigate). These are wrapped by thin
  "site plugins", one per site: `cowork/sites/google/tools.py` for Gmail, Drive, Docs and Sheets, and
  `sites/files` for downloaded spreadsheets. Each plugin treats the page as an API: it knows where Drive's file
  list or a sheet's cells sit on the page and returns only those, never a whole page. Plugins can't send, edit
  or delete.
- **Why:**
  - Whole pages were 8-11k tokens each, and a model with a shell went browsing the home folder. Narrow tools fixed
    both: tasks that failed finished in 1-2.5 minutes.
  - No OAuth app or Google verification is needed, and the person's data never leaves their machine except to
    the private model.
- **How the plugins were made:** Claude, in the "Claude" (DIY) workspace, wrote and repaired them with the
  `add-site` skill (`cowork/.claude/skills/add-site/`). It used Paseo's browser signed in to **test accounts**
  (`~/idli-insights/config/accounts.json` on the laptop), with tests in `run_tests.py` and each site's
  `tests.json`. The private model then uses them on the real account. This split is the pattern to reuse for new
  sites: Claude builds the tool on test accounts, Idli uses it on real ones.
- **Read:** `narrative/2026-11-07-cowork-ui-as-api-field-note.md`,
  `chronology/2026-11-07T1750-laptop-cowork-diy-poc.md`, and `cowork/README.md`.
- **The cost:** a site changing its pages breaks a plugin. The tests catch it, and `add-site` repairs it.
- **Uploads:** the working copy is dropped into Drive through Paseo's DevTools (P9 in
  `todos/idli-insights/p1/paseo_patches.md`), not through an API.

## Logins a person needs (what Start here checks with `setup_check`)
1. **Google:** sign in to Google in Paseo's browser (the Drive tab in Start here). That's all. There's no OAuth
   screen and no token file.
2. **Claude**, for teaching: the Claude Code CLI signed in to the person's account (`claude auth status` shows
   `loggedIn`). If the CLI isn't there, install it: `curl -fsSL https://claude.ai/install.sh | bash` on
   Mac/Linux (the installers on branch `idli-installers` bundle this), then `claude` and sign in through the
   browser. The Claude workspace uses this login.
3. **Idli's private model (Muse today):** a Cloudflare Access service token for `https://silo.idli.cc`. The owner
   makes one per person and gives them a code (`desktop/muse-code.py` on `idli-installers` makes the `idli1.`
   code). `desktop/muse-connect.py <token file>` checks it and writes `~/idli-insights/config/muse-access.json`.
   It also points Idli's Claude Code provider at silo: `ANTHROPIC_BASE_URL` plus the Access headers in
   `~/idli-insights/config/claude-t4gc/settings.json`. Without it, Idli can't think; Paseo becomes just a browser.

## Where credentials live (never print, paste or commit them)
| What | Where | Notes |
|---|---|---|
| OpenRouter API key | `~/.config/idlisseus/openrouter.json` (DGX) | The benchmarks' `models.json` points at it (`key_file`). OpenRouter isn't private: fake data only. |
| Silo (Muse) service token, the owner's | `~/.config/idlisseus/silo.json` (DGX) | `client_id` and `client_secret` for Cloudflare Access. |
| Silo token, on the laptop | `~/idli-insights/config/muse-access.json` | Written by `muse-connect.py`. |
| Idli's Claude Code provider settings | `~/idli-insights/config/claude-t4gc/settings.json` (laptop) | Holds the Access headers. |
| Claude CLI login | the CLI's own store (`claude auth status`) | The owner's subscription. Agents use it as is. |
| Google test accounts, for plugin work | `~/idli-insights/config/accounts.json` (laptop) | The only file under `~/idli-insights` the DIY workspace may read. |
| Other services (HF, GitHub, eBird, Telegram, ...) | `~/.config/idlisseus/*.json` (DGX) | Not used by Idli. |
| Codex login | `~/.codex` | **Never touch it**, not even to read. |

## Ops: the laptop tunnel (ask the owner; the DGX can't start it)
The owner's laptop runs Paseo. The DGX drives it only while the owner has the tunnel up
(`docs/laptop-dgx-sync.md` has the details).
1. **On the laptop,** Paseo starts with its DevTools port:
   `setsid /opt/Paseo/Paseo --remote-debugging-port=9333 >/dev/null 2>&1 &` (or the edited launcher in
   `docs/driving-desktop.md`).
2. **On the laptop,** from `.../cowork`: run `desktop/laptop-up.sh`. It also takes `status` and `stop`.
   - It opens an ssh connection to the DGX (`beeps@gx10-0a47.tail5ef239.ts.net`) that carries the Paseo daemon
     (`-R 46767`) and DevTools (`-R 49333`). It forwards Muse (`-L 8181`) only when silo isn't set up.
   - Tailscale SSH sometimes asks for a browser check: the owner runs `ssh beeps@gx10-0a47.tail5ef239.ts.net true`
     by hand once.
3. **On the DGX, check it's up:** `cowork/desktop/paseo-remote.sh ls --global --json`. A list means it's up.
   "Connection refused" or `DAEMON_NOT_RUNNING` means it's down or the laptop is asleep.
4. **If it's down,** ask the owner: "Please rerun `desktop/laptop-up.sh` on the laptop (and keep it awake)."
   Don't type secrets through the laptop's terminal, and don't copy tokens over the tunnel. The owner moves
   tokens themselves.
5. **When done,** the owner runs `laptop-up.sh stop`. While the tunnel is up, the DGX can read every tab in the
   workspace browser, including real Gmail and Drive. Use it only for the task at hand.

## Save your own tokens: delegate the grinding
The owner's standing instruction: **don't spend your own context on grinding work.** You plan, decide, review and
report. Hand the rest to:
- **Codex** (`codex exec "<task>"`) or **cursor-agent** (`agent -p "<task>"`). Use them for writing scripts and
  generators, bulk edits, fixing a failing harness, data generation, and reading through big logs.
  - Give each one a short written spec, a file path to put its work, and what "done" looks like.
  - Never give them real data, credentials or the owner's private files. Never touch `~/.codex`.
- **A smaller subagent** (Sonnet or Haiku) for searches and routine runs.
- **Plain background jobs** for anything long: `nohup <script> > <log> 2>&1 &`, then check the log with short
  commands. Never sit in one long foreground command or a long silent stretch: background agents get stopped
  after 10 minutes with no output.

Check their work (run it, read the diff) before you commit it. Their results become facts only after that.

## Filling your own gaps (before saying "that wasn't recorded")
Most things were recorded somewhere. Look in this order:
1. **The chronology for this line of work:** `docs/cowork-poc.md`, "What changed", newest first, back to
   2026-11-06. Search it: `grep -n -i "<word>" docs/cowork-poc.md`.
2. **Older session entries** in `chronology/`, one file per session:
   - `2026-11-06T2030-dgx-oss-desktop-independent-research.md` (why Paseo);
   - `2026-11-06T2330-dgx-paseo-aionui-behavioural.md`;
   - `2026-11-07T1615-laptop-desktop-ux-and-cowork.md`;
   - `2026-11-07T1750-laptop-cowork-diy-poc.md`;
   - `2026-11-07T1830-laptop-cowork-handoff-to-dgx.md`;
   - `2026-11-07T1950-laptop-idli-insights-and-latency.md`;
   - `2026-11-06-oss-desktop-*.md`.
3. **Field notes** in `narrative/` (above), which give the lessons, not just the events.
4. **Benchmark folders,** each with a README, REPORT or PLAN:
   - `benchmarks/runs/2026-11-06-oss-desktop*/`: the app comparison;
   - `benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/`: the product code itself, with its `README.md`;
   - `benchmarks/runs/2026-11-07-cowork-event-eval/`;
   - `benchmarks/runs/2026-11-08-oobe/`;
   - `benchmarks/runs/2026-11-08-form-fill-eval/`;
   - `benchmarks/runs/2026-11-10-idli-pipeline-eval/`;
   - on branches: `git show origin/idli-9b-bench:benchmarks/runs/2026-11-10-idli-9b/REPORT.md`, and
     `git ls-tree -r --name-only origin/<branch>` to list a branch's files.
5. **Todos and design notes:** `todos/idli-insights/` (p1-p3, Paseo patches, deployment gaps, optimizations),
   `docs/distribution.md`, `docs/cowork-manual-test.md`.
6. **Git history:**
   - `git log --oneline oss-desktop-eval -- <path>`: why a file changed. Commit messages are detailed.
   - `git log --all --oneline --grep "<word>"`: search every branch.
   - Branches: `oss-desktop-eval` (main work), `idli-9b-bench`, `idli-pipeline-eval`, `idli-installers`.
7. **Agent memory:** `~/.claude/projects/-home-beeps-src-github-com-bprashanth-io/memory/`, one fact per file;
   `MEMORY.md` is the index.
8. **The last resort: past session transcripts.**
   - Files: `~/.claude/projects/-home-beeps-src-github-com-bprashanth-io/*.jsonl`, one per session. They're very
     large, so never read one whole.
   - Search: `grep -l "<word>" ~/.claude/projects/-home-beeps-src-github-com-bprashanth-io/*.jsonl`, then
     `grep -o ".\{200\}<word>.\{300\}" <file> | head`.
   - The long session behind most of this page is `89b0f21c-c677-4103-ad2f-cc63bbc75af6.jsonl`.
   - What you find there is a lead, not a fact: check it against the code or results before relying on it.
   - Then write what you learned into the chronology, so the next agent doesn't have to dig.

If something truly isn't anywhere, say what you searched, and ask the owner.

## Where the code is
Everything lives under `benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/`:

**The MCP server**
- `cowork_mcp.py`: loads the sites listed in `cowork.sites`, then keeps only the tools in `cowork.tools`. Both
  files are per folder and written by the bootstrap.

**Tools**
- `sites/files/tools.py`: Idli's tools.
  - Get and open the file: `start`, `file_get`, `file_open`.
  - Ask and chart: `file_ask`, `chart_request`, `chart_show`.
  - Teach: `teach_file`, `teach_send`.
  - Clean: `working_copy`, `working_copy_ready`.
  - Learned files: `show_skills`, `skills_list`, `skill_delete`.
- `sites/google/tools.py`: `setup_check` (Start here) and `gsheet_read` (the fallback). Also the Drive index and
  search, and Gmail, which are no longer offered to any chat.

**Libraries (`lib/`)**
- `filekit.py`: reading files, and the fake copy.
- `formkit.py`: the form engine, and `answer_text` (the code template for answers).
- `fixkit.py`: suggested fixes.
- `workcopy.py`: the marked working copy.
- `formserver.py`: the dashboard and pages.
- `chartkit.py`: charts and the sandbox.
- `muse.py`: where Muse is, and its Access headers.
- `driveindex.py`: no longer used in the journey.

**Instructions**
- `idli/CLAUDE.md`: Idli's instructions.
- `idli/START-HERE.md`: Start here, the sign-in check.
- `idli/LEARNED.md`: Mission control.
- `.claude/skills/teach-file/`: how Claude teaches a file.

**Laptop setup**
- `desktop/idli-bootstrap.py`: the sidebar layout, the per-chat tool lists, and the tabs.
- `desktop/setup-laptop.py`: Paseo providers.
- `desktop/muse-connect.py`: points Idli at silo.

## State right now (checkpoint 2026-11-11 ~14:00 IST): read this to resume
If the session that wrote this hung, everything below is in git or on disk. Nothing needs it to be alive.

### 1. Product change: done, almost verified
- **Commits on `oss-desktop-eval`** (DGX; not pushed to GitHub):
  - `94570b4`: no Drive index or file search (link first). Start here only checks sign-ins (`setup_check`) in
    its own folder `~/idli-insights/setup`. Mission control is only What Idli has learned (`idli/LEARNED.md`).
    Tool lists per chat (`cowork.tools`: Idli 12 tools, Start here 1, Mission control 3).
  - `2da8988`: `setup_check` waits for Muse longer and says busy, refused or not set up. Google errors carry
    their message.
- **Laptop:** pulled to `2da8988` (`git pull dgx oss-desktop-eval`). The bootstrap was run, which:
  - archived the old Start here workspace;
  - made a new "Start here" chat (in `~/idli-insights/setup`);
  - replaced the stale "New chat" (it had the old 34 tools) with a fresh one.
- **Verified:**
  - On the DGX: tool lists (`COWORK_DATA_DIR=<folder> .venv/bin/python cowork_mcp.py --list`), the Claude and
    Muse checks, and the formkit and fixkit tests (`PYTHONPATH=. .venv/bin/python lib/test_formkit.py`).
  - On the laptop: Start here's first check said Claude ✓, Muse ✗ and Google ✗ ("couldn't check
    (RuntimeError)"). From a laptop shell, Muse answered 200 through silo. The check took 44 s, so Muse was
    likely slow or busy. `2da8988` makes the reason visible.
- **Still to do:**
  1. In Start here, send "check again". The chat must be reloaded or new to load the new code
     (`paseo agent reload <id>`, then `paseo agent send <id> "check again"`). If Google still fails, read the
     message it now gives. The cause is likely the browser tools from a workspace that isn't on screen.
  2. Screenshot the sidebar (`python3 desktop/drive.py shot sidebar`). Expect Start here, Mission control (What
     Idli has learned), Idli and Claude.
  3. Run one journey from a pasted link in the new "New chat": start card, Analyse, paste the cestrum file's
     link, then one question.
  4. Known gap: a working copy now lands in My Drive (it used the index to find the original's folder).
     Fix: have `file_get` record the parent folder.
- **Driving the laptop from the DGX:**
  - CLI: `cowork/desktop/paseo-remote.sh` (tunnel port 46767).
  - Laptop terminal: `paseo-remote.sh terminal create --workspace <full Claude workspace id>`, then
    `terminal send-keys <id> "<cmd>" Enter` and `terminal capture -S <id>`. Use `-S`: without it, capture can
    come back empty.
  - The daemon sometimes times out ("Liveness check timed out"). Retry, or ask the owner to rerun
    `desktop/laptop-up.sh`.

### 1b. Checked copy after every teach; charts never drop rows (2026-11-11 afternoon): waiting for the owner
- **Read:** the chronology entries "2026-11-11 (late afternoon), DGX: the checked copy is made after every teach"
  and "2026-11-11 (afternoon), DGX: charts never drop rows; messy rows go to the checked copy" in
  `docs/cowork-poc.md`. It has the design, the rule change (the checked copy is now also made without a
  card), how it was verified, the owner's decisions 1-4, and a correction to the E3 report.
- **Commits:** `51392d9d`, `dabfad55`, `8a117e7f` on `oss-desktop-eval` (`file_open` and `chart_show` in
  sites/files/tools.py, `chartkit.tabs_used`, the teach-file skill). The laptop has pulled them.
- **Other agents (e.g. `exp/answer-mock`):** merge `oss-desktop-eval` before touching `chart_show`. It may now
  call `working_copy` itself and returns `messy_rows`, `working_copy` and `then`.
- **Waiting for the owner before:** rerunning E3 (which needs a scripted "fixed" step), E4/E5. To try it in the app,
  open a file by its Drive link in a new Idli chat (older files have no Drive id recorded).

### 2. Evals (checkpoint 2026-11-11 ~12:00 IST): E6, E7, E1, E2, E3 done and reported
- **Where:** branch `idli-pipeline-eval`, pushed at `4dbc4c22` (declauded, 0 trailers); worktree
  `.claude/worktrees/agent-aaf212a4b5f290bbe`; folder `benchmarks/runs/2026-11-10-idli-pipeline-eval/` (E).
  `E/REPORT.md` covers E6, E7, E1, E2, E3, the owner decisions, answers to PLAN.md's four questions, and
  "For the integrator". The branch is not merged into `oss-desktop-eval` yet.
- **E1/E2:** the fake copy keeps 43/62 kinds of mistake (47 with `IDLI_MOCK_V2=1`). Teaching from it finds 85-90% vs
  81% from the real file: noise-level, so better fake data isn't the next investment.
- **E3:** the trip to Claude and back works (0 wrong bounces in 27 chats, sent 23/24, back 22/23, about a minute and
  $0.15 a trip). But Claude's chart code was exactly right on the real file in only 12 of 24 trips: it splits
  readable spellings and drops repeated-ID rows (p1 todo `chart_code_reading.md`).
  - The expected answers were checked by Codex: 6 of 9 corrected (`E/results/e3/refcheck.md`).
  - Scoring: `E/harness/e3_rescore.py` reruns chart code on the real fixture.
  - Harness fixes: `--out` made absolute (`idli.setup()` chdirs); headless teaching caps API calls at 5 min.
- **Machine state:** the local 9B is stopped (`E/harness/serve9b.sh up` restarts it). Muse untouched.
- **Owner decisions pending (E1-E3, in `E/REPORT.md`):**
  1. chart code uses the form's reading (recommended);
  2. no silent row drops (recommended);
  3. hold `IDLI_MOCK_V2` for one more E2 run;
  4. share questions as form measures instead of charts?
- **Next, one of:** E4 (answer wording) and E5 (charts; E3 already covers much of it); the chart-code fix
  (p1); subtables (p1); the laptop check of Start here (section 1 above).
- **Lessons on running this:**
  - Run batch scripts directly (`nohup ... &`) and wait with a background `until` loop; hand code and log reading
    to Codex (`codex exec`), which did the rescorer and the reference check well.
  - Check expected answers before trusting a score: most of E3's were wrong.

### 3. Demo installers (not active)
Branch `idli-installers`. It works but lacks our Paseo patches P1, P3 and P12. Gaps D1-D11 are in
`todos/idli-insights/p1/deployment_strategy.md`.

### 4. Session settings
`~/.claude/settings.json` now sets `API_TIMEOUT_MS=1800000` and `CLAUDE_STREAM_FIRST_BYTE_TIMEOUT_MS=1200000`,
because very long sessions were hitting "No response from API".

## todos/ and proposals/: how work is queued and how agents agree on designs
- **`todos/idli-insights/`** is the work queue, by priority:
  - `p1/`: the demo and the architecture evals;
  - `p2/`: measured, worth doing next;
  - `p3/`: later.
  
  Each todo is one file saying the decision behind it, what to build and how to test it. The `README.md` there is
  the index. When something ships, record it in the chronology and **delete** the todo. When results change a
  priority, move the file and say why, as the capacity todo did when it moved from p1 to p2. Raise and demote
  freely, but leave a line in the file saying why.
- **`proposals/`** is for designs not yet built and decisions that aren't an agent's to make (see
  `docs/agent-handoff.md`).
  - **Writing one:** write the options with a recommendation as `proposals/<topic>.md`, and stop. Don't build it
    until the owner decides.
  - **Syncing between agents** (Claude on the DGX, the laptop agent, Codex, cursor-agent): a proposal is the
    shared place to agree on a design. One agent writes it, others add their notes under a dated heading with
    their name ("codex, 2026-11-11: ..."), and the owner's decision goes at the top. Then the work becomes a todo.
  - **Idli-related proposals so far:** `demo_and_flow.md`, `pii_idli.md`, `hive_mind.md`,
    `idli_astronaught.md`, `oss-desktop-open-private-agent-handoff.md`, `model-training.md`. Read the relevant
    one before designing something nearby.
- **Field notes and the chronology are history; todos and proposals are the future.** Keep them apart.

## Owner decisions (2026-11-10, after E6/E7)
1. **Inconsistent but readable values** ("Rs. 1,200", "approx 12", casing, "n/a"): Idli reads them quietly and
   flags them only when they would confuse the 9B, for example two spellings that split a count. Fewer flags are
   less intimidating. A strict mode that flags everything comes later
   ([p3 todo](../todos/idli-insights/p3/strict_mode.md)).
2. **Template instruction rows** (descriptions, MANDATORY/OPTIONAL) stay unchanged in the fake copy.
3. **Every table on a tab** must be read: subtables and info blocks. Today Idli reads one table per tab, so
   this is new work ([p1 todo](../todos/idli-insights/p1/subtables.md)). When a layout would confuse the 9B,
   Claude suggests a simpler one while teaching, and the working copy carries a comment.
4. **Tools:** soft phases. All 12 tools are always listed, and the server says "not now" when one is used too
   early. This is how it ships.

## Running experiments in parallel (any agent: Claude, Codex, cursor-agent)
Do the simplest thing: **one git worktree and one branch per experiment, one benchmark folder of its own, and
no changes to shared code unless they're behind a switch.** At the end everything merges into
`oss-desktop-eval`, which goes to `main` as a PR.

1. **Start** from the main checkout (`~/src/github.com/bprashanth/io`, branch `oss-desktop-eval`):
   ```sh
   git worktree add ../io-<name> -b exp/<name> oss-desktop-eval
   cd ../io-<name>
   ```
   This gives a full copy of the repo on its own branch, sharing git history. Don't work in the main checkout,
   and don't copy the folder by hand.
2. **Your results** go only in `benchmarks/runs/<date>-<name>/`: PLAN.md, scripts, results, REPORT.md. Reuse
   other harnesses by importing them or copying them into your folder; don't edit them in place.
3. **Changing product code** (`cowork/lib`, `cowork/sites`, `idli/*.md`): only behind an environment switch that
   is off by default (like `IDLI_MOCK_V2=1`), and in its own small commit, so it merges cleanly and is easy to
   review or revert. Never change behaviour that another experiment relies on.
4. **Machine state:**
   - **Idli's data:** never use the real `~/idli-insights`. Set `IDLI_HOME` (and `COWORK_DATA_DIR`) to a folder
     inside your benchmark directory.
   - **GPU:** follow `../GPU_COORDINATION.md`. Use a memory cap, check free memory first, and stop your own
     servers when done.
   - **Muse:** a client only. Never stop or restart it.
   - **Ports:** pick unused ones. Name containers `exp-<name>-*` and remove only your own.
   - **Processes:** no `pkill -f`; use a `/proc` scan.
   - **The laptop:** it's shared, so drive it only if the owner says so.
5. **Shared files** (`docs/cowork-poc.md`, this page, `todos/`, `narrative/`): don't edit them on your branch.
   They conflict. Put the one-line chronology entry, and any todo changes, at the end of your REPORT.md under
   "For the integrator".
6. **Commit** often. Commits end with the attribution lines. **Push** your branch only after
   `bash -ic 'declaude origin/main'` and a check that 0 `Co-Authored-By`/`Claude-Session` lines remain:
   `git push --force-with-lease origin exp/<name>`.
7. **Report back:** a REPORT.md in your folder, in plain language, with tables, surprises, what wasn't
   measured, cost and time, and decisions for the owner. Then tell the owner the branch and commit.
8. **Merging** (the integrating agent, in the main checkout):
   ```sh
   git merge exp/<name>
   ```
   Then copy the "For the integrator" lines into the chronology and todos, update "State right now" above,
   commit, and remove the worktree (`git worktree remove ../io-<name>`). Once everything is merged,
   `declaude`, push `oss-desktop-eval`, and open the PR against `main`.

## Rules that always hold
- Read only, except the checked working copy in Drive, which Idli makes without asking after each teach (or from
  `chart_show`): always a new file next to the original, never an edit. Claude gets fake data only. Real data stays on the
  DGX or the laptop.
- Never print or commit credentials: the silo token (`~/.config/idlisseus/silo.json`,
  `~/idli-insights/config/muse-access.json`) and the OpenRouter key. Never touch `~/.codex` or `docs/sandbox.md`.
- Before any push, run `declaude origin/main` (a bash function, so use `bash -ic`), then
  `git push --force-with-lease`. Check that there are 0 Claude trailers.
- On the DGX, use no `pkill -f` (scan `/proc` instead). Follow `../GPU_COORDINATION.md`. Muse (container
  `idli-muse`) may be stopped only briefly, with `docker stop`, and must be brought back.
- Benchmarks: no small per-question scripts to max a score. Fix the flow. Fresh test sets (held3) are the judge.
- Write plainly for the owner: no invented jargon, or explain it in brackets.

## How to keep this current
After each step: one line in `docs/cowork-poc.md` "What changed", an update to "State right now" above, and a
field note when a set of results adds up to a lesson. Long, grinding work goes to subagents, Codex
(`codex exec`) or cursor-agent (`agent`), to keep each session's context small. Very long sessions start
hitting API timeouts.
