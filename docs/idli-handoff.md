# Idli: handoff (read this first)

Last updated 2026-11-10 (~20:30 IST), DGX. Overwrite this page whenever the state changes, and keep the chronology
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
   - `2026-11-10-one-file-at-a-time-field-note.md`: what a 9B can do, the three-call shape of a question, and the
     decision to drop the up-front index.
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

## State right now (checkpoint 2026-11-11 ~08:40 IST): read this to resume
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

### 2. Evals (checkpoint 2026-11-11 ~08:40 IST): E6, E7, E1, E2 done; E3 needs one bug fixed
- **Where:**
  - branch `idli-pipeline-eval`, pushed at `848d7c7f` (declauded, 0 trailers);
  - worktree `.claude/worktrees/agent-aaf212a4b5f290bbe`;
  - folder `benchmarks/runs/2026-11-10-idli-pipeline-eval/` (E). `E/PLAN.md` is the plan.
  - `E/REPORT.md` covers E6 and E7 only: E1-E3 still have to be added to it.
- **E6 and E7:** see `E/REPORT.md`. The local 9B with the split, 12 tools, soft phases: 86% on held3, the same as
  Muse.
- **E1 (done, `E/results/e1/`):**
  - 43 of 62 kinds of mistake survive today's fake copy; 47 of 62 with Codex's fixes, which sit in
    `cowork/lib/filekit.py` behind `IDLI_MOCK_V2=1`, off by default.
  - Still lost: spacer and notes rows, merged headers, and info blocks.
  - The tax "end before start" result was random luck, not a regression (`E/results/e1/tax_end_before_start.md`).
    It exposed two real gaps: "12-Mar-22" dates aren't recognised, and the order between start and end date
    columns isn't kept.
- **E2 (done, `E/results/e2-logs/table.txt`):** mistakes found, counting per the owner's decisions:

  | Claude learned from | Mistakes found | False alarms |
  |---|---|---|
  | today's fake copy (2 runs) | 88% / 85% | 20 / 17 |
  | the fixed fake copy | 90% | 35 |
  | the real (synthetic) file | 81% | 16 |

  - Of the 35 false alarms with the fixed copy, 14 are in the tax file.
  - Info blocks: 0 of 6 found ("not readable yet").
  - So, with one repeat each, learning from the fake copy is not worse than from the real file. The differences
    are about the size of run-to-run noise (2-4 mistakes per file).
- **E3 (the trip to Claude and back): needs one fix.**
  - Built by cursor-agent:
    - 9 chats in `E/scenarios/e3.json`;
    - the runner `E/harness/e3_bounce.py` (args: `--model --scenario scenarios/e3.json --conv <id> --out <file.json>`);
    - the table `E/harness/e3_table.py`;
    - the spec `E/generators/E3_SPEC.md`.
  - My batch script `E/harness/e3_all.sh` ran all 27 chats (the 9B twice, Muse once) on 2026-11-11, 07:06-08:01.
  - **The bounces happened**: Claude's teaching folders are in `E/results/e3-logs/<model>/<chat>/teach/`.
  - **Bug:** apart from the first chat (`E/results/e3/local-qwen35-9b-r0/`), **no per-chat result JSON was
    written**, and the logs are empty (exit code 0).
    - A single rerun reproduced it: `--out results/e3/dbg/x.json` wrote nothing, with exit 0.
    - So `run()` in e3_bounce.py, or `convo.run` in `../2026-11-10-idli-9b/harness/convo.py`, returns or exits
      before `json.dump`. Debug it with prints, or `python -X faulthandler`.
  - **Next:** fix the bug, delete `E/results/e3-logs/*-r0`, `*-r1` and `E/results/e3/*-r*`, rerun
    `nohup E/harness/e3_all.sh > E/results/e3-logs/all.log &` (about an hour), then
    `E/harness/e3_table.py`. The local 9B server is on port 8291 (`E/harness/serve9b.sh`). Stop it when done.
- **Then:**
  - Add E1, E2 and E3 to `E/REPORT.md`, ending with a "For the integrator" section and answers to PLAN.md's four
    questions (where to invest; whether it works end to end; more models where; newer designs).
  - Put the chronology line in `docs/cowork-poc.md`.
  - E4 (answer wording) and E5 (charts) come after.
- **New todos to add:** keep start-before-end order in the fake copy; parse "12-Mar-22" dates; a last teaching
  step where Claude ticks off each rule the owner stated (E6 misses: counts across tabs, totals, duplicate IDs).
- **Lessons on running this:**
  - Background agents kept stalling: the system stops one after 10 minutes with no output, and it happened even
    before any work.
  - It's more reliable to run the batch scripts directly (`nohup ... &`, then check the log) and use Codex or
    cursor-agent for code changes.
  - Very long sessions got slow; start fresh from this page.

### 3. Demo installers (not active)
Branch `idli-installers`. It works but lacks our Paseo patches P1, P3 and P12. Gaps D1-D11 are in
`todos/idli-insights/p1/deployment_strategy.md`.

### 4. Session settings
`~/.claude/settings.json` now sets `API_TIMEOUT_MS=1800000` and `CLAUDE_STREAM_FIRST_BYTE_TIMEOUT_MS=1200000`,
because very long sessions were hitting "No response from API".

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
- Read only, except the working copy in Drive after a yes. Claude gets fake data only. Real data stays on the
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
