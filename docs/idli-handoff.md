# Idli: handoff (read this first)

Last updated 2026-11-10 (evening), DGX. Overwrite this page whenever the state changes, and keep the chronology
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

## State right now (2026-11-10 evening)
- **Product (on `oss-desktop-eval`):**
  - No Drive index and no file search. Idli asks for a link.
  - Start here has its own folder (`~/idli-insights/setup`) and only checks Google, Claude and Muse.
  - Mission control holds only What Idli has learned.
  - The Idli chat gets 12 tools instead of 34.
  - Verified on the DGX: the tool lists, the Claude and Muse checks, the unit tests.
  - Still to verify on the laptop: the pull, the bootstrap, the screenshot, and one run from a link.
  - Known gap: without the index, a working copy lands in My Drive instead of the original's folder
    (`working_copy` used the index to find the folder).
- **Evals:** a background agent is running E6 (cleaning output on files with planted mess) and E7 (fewer tools
  by phase) on branch `idli-pipeline-eval`, and stops for a report before E1-E5. E8 (file search) and E10
  (redaction) are skipped on the owner's word. Messy example files include the two hollow templates the owner
  attached: a germination protocol, and a tax questionnaire that is private, so only its structure is used.
- **Demo:** the installers work but lack our Paseo patches (P1, P3, P12). See D1-D11.

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
