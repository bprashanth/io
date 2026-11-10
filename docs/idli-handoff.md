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

## State right now (2026-11-10, ~20:30 IST): read this to resume
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

### 2. Evals: E6 and E7 done (report: `benchmarks/runs/2026-11-10-idli-pipeline-eval/REPORT.md` on branch `idli-pipeline-eval`, pushed at a16edeb0)
**Result:** the local 9B with the split, on the 12 shipped tools with soft phases, scored 86% on held3, the same as
Muse (question steps 78% vs 85%). Hard phases scored 79%. E6: 72% of planted mistakes found, few false alarms.
**Now running (started 2026-11-10 late night):** E1-E3 in a new background agent, same worktree and branch, from
a16edeb0. It uses defaults until the owner answers: soft phases; E1 measures template instruction rows both kept
and made fake; marking and info blocks unchanged. It hands generator and script writing to Codex and
cursor-agent. If it hangs, check the branch's commits and running jobs (`/proc` scan), then restart it with:
"continue E1-E3 from PLAN.md and REPORT.md on idli-pipeline-eval". **After that:** E4 and E5. Waiting on the owner's four decisions (listed in the report). The background
agent has finished. To continue, start a new agent on branch `idli-pipeline-eval` (worktree
`.claude/worktrees/agent-aaf212a4b5f290bbe`), or SendMessage the old one. Restart the local 9B with
`harness/serve9b.sh up`.

Details from when it was running:
- **Plan:** `benchmarks/runs/2026-11-10-idli-pipeline-eval/PLAN.md`.
- **Scope:**
  - Run order: E6 (cleaning output on planted-mess files), E7 (fewer tools by phase), then stop for a report.
    After that: E1 (fake copy fidelity), E2 (teaching from the fake copy, judged on the real file), E3 (bounce to
    Claude), E4 (answer wording), E5 (charts).
  - Skipped by the owner: E8 (file search) and E10 (redaction). E9 (constrained dial setting) runs only if E7
    leaves dial errors.
  - The subject is the 9B (the free tier). Muse 30B is only the baseline.
- **Where it works:**
  - Branch `idli-pipeline-eval`, in worktree `.claude/worktrees/agent-aaf212a4b5f290bbe`. It is not pushed. Push
    only with declaude.
  - It merged `origin/idli-9b-bench`, which carries the harness and fixtures, and `oss-desktop-eval` (`687b8c2`).
- **Done so far:**

| Commit | What |
|---|---|
| `c0d92d9` | Planted-mess generator with manifests: 5 files, 209 known problems, written with Codex. Includes fake-filled versions of the owner's two templates: the germination protocol, and the tax questionnaire under a neutral name (private, structure only). Also: headless teach runner (Claude Code with the teach-file skill on Idli's fake copy, Haiku as the file owner), the E6 scorer, link-first chats, the E7 phase variants and a `list_changed` probe. Harness fixes: totals scored separately, a guard against Idli's own card where the user should type, card clicks as steps. |
| `dcd5e17` | Partial E7 results (runs cut short) |
| `bea46f4` | E7 variants from the merged product: e7-product = the 12 shipped tools; e7-p12 = the 12 tools plus the separate dial-setting call. The partial runs from before the merge are set aside. |

- **E7 runs only the meaningful setups** (owner, 2026-11-10):
  - **The local 9B (Q5) with the split** (a separate dial-setting call to itself inside `file_ask`), on the 12
    shipped tools: (a) hard phases and (b) soft phases, two repeats each. The container is `idli9b-raw` on the
    DGX; it showed "unhealthy" once, so check it.
  - **Muse,** as the baseline only and as a client. Don't stop it.
  - **"Before" (29 tools):** last round's local 9B split runs, rescored with the fixed scorer. Not rerun.
  - **Why only these:** last round, the local 9B with the split scored 81% on held3 and 80% on the other chats,
    against Muse's 83% and 85%. Bigger dial-setters (Ling, gpt-oss, 122B, 35B-A3B) moved results only by noise.
  - **Dropped:** those bigger dial-setters (they don't fit beside Muse, and Ling only fits with Muse stopped),
    the 9B with no split, and OpenRouter 9B runs.
- **If the agent hangs:** it stalled once already (10 minutes with no output; the system stops a background agent
  after that).
  1. Check for runs still going with a `/proc` scan for `run.py` (no `pkill -f`), and look at
     `git -C <worktree> log` and `git status`.
  2. Commit any results.
  3. Restart it, or start a new agent with: "continue the pipeline eval from PLAN.md and the commits on
     idli-pipeline-eval; E6 and E7 first, then report".
- **Results go to:** `benchmarks/runs/2026-11-10-idli-pipeline-eval/REPORT.md` on that branch, with one line per
  finding in `docs/cowork-poc.md`.

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
