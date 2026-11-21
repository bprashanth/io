# Idli: handoff (read this first)

Last updated 2026-11-21, DGX. Overwrite the top section whenever the state changes. Keep `chronology/` and the
narratives in step with it.

This repo has a long history (event ladders, io, Codex, shield, Drivey, Teams). **Focus on the last two weeks:
Idli Desktop as sandboxes plus a command-line core.** The older material below is there to look things up, not to
start from.

## Checkpoint 2026-11-21: the scaffold core, hands-on (read in this order)

**Status:** items 1-6 below are built (2026-11-21). Measuring the smaller menu against the full one on the dev bank
(`benchmarks/runs/2026-11-21-menu-regression/`, blind graders running). The next agent starts from
`docs/handoff-prompt.md`.

### 1. What this phase is
The owner tests the scaffold (`desktop/idli`, a CLI over a DuckDB store per sandbox) by hand on test account
87profligate, and an agent fixes what breaks with general fixes only. Paseo and the app come later. A sibling
repo `../dune` will receive only the parts that are understood and tested; `../dune/.index.md` lists them.

### 2. Read first
1. `todos/idli-insights/p1/scaffold_core_round1.md`: the running list (bugs with evidence, decisions, proposals).
2. `chronology/2026-11-20T1400-scaffold-hands-on.md` and `chronology/2026-11-21T0000-search-defaults-agent-trial.md`.
3. `../dune/docs/cli.claude.md`: every term and command with an example (the owner copies it into `cli.md`).
4. `narrative/GOALS_V0.5.md` (written before hands-on testing; parts are design, not built), `CLI_CHOICES.md`,
   `EXAMPLES_V0.md`.

### 3. Evidence
- `benchmarks/runs/2026-11-21-heldout-rerun/`: frozen held-out, 9B 5 -> 10 correct, idli-remote 13 -> 13.
- `benchmarks/runs/2026-11-21-agent-trial/`: the agent asking like the owner; 20+ fixes; `owner-dev/` runs.
- `benchmarks/runs/2026-11-19-record-store/bank/tasks_owner_dev.json`: the owner's own questions, SQL-checked.
- `benchmarks/runs/2026-11-20-judge-models/`: Clef vs 9B vs Muse as judge.

### 4. State
- Code: `benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/lib/{recstore,idlicli}.py`, `desktop/idli`.
- Sandboxes on the DGX: `~/idli-sbx/t1`, `t2` (the owner's), `agent1`-`agent4` (the agent's). Test-account data;
  not in git.
- Models: the served 9B (Q5, port 8291) maps and words; `idli-9b-bf16` (port 8292) for `--mapper nine`;
  Clef-flash judges by default (OpenRouter, Cloudflare only; hosted, so test accounts only).
- Branch `oss-desktop-eval`, about 400 commits ahead, not pushed. Run `declaude origin/main` after committing;
  it rewrites hashes, so quote hashes only after it.

### 5. Being built now (owner's go, 2026-11-21), in this order
1. Embeddings for cards and page chunks, fused with literal search (quoted phrases stay literal); used by search,
   `summarise --search` and the menu.
2. A smaller menu: every sheet and view name, columns only for relevant sheets; every menu miss logged.
3. Kind chips (lookup / judgement / workflow, by Clef) and struggle signals with escalation offers, including a
   repeated question.
4. `idli explain` renamed `idli help` (users say "explain X").
5. A size cap on the 9B's instructions; fixes tagged code or prose.
6. Docs: GOALS, IDLI_DESKTOP, EXAMPLES, CLI_CHOICES brought up to date; this handoff and a handoff prompt.

### 6. Rules for this phase
- General fixes only; prefer code over prose (a sentence in the 9B's instructions). Measure on the dev bank and,
  for claims, on a new held-out set.
- Grinding goes to Cursor `agent` or `codex exec`; nothing under `~/.codex` is edited.
- Plain copy in anything a person reads. No "deepseek" in UI text: "idli-remote".

## Checkpoint 2026-11-20: where we are (read in this order)

### 1. The current thinking (read all of these first)
1. **[narrative/GOALS_V0.5.md](../narrative/GOALS_V0.5.md):** the core.
   - The scaffold (`idli` commands over a DuckDB store per sandbox).
   - The command design.
   - What crosses the masking line.
   - The benchmark results.
   - Why workflows need Minis (views, definitions, chains).
   - The journeys inside a sandbox, and the Builder's boundary.
   - Next steps.
2. **[narrative/EXAMPLES_V0.md](../narrative/EXAMPLES_V0.md):** concrete tables, commands and queries for Gmail,
   Drive, WhatsApp, calendar and leads.
3. **[narrative/CLI_CHOICES.md](../narrative/CLI_CHOICES.md):** the grammar and its references (kubectl, gh,
   clig.dev).
4. **[narrative/IDLI_DESKTOP.md](../narrative/IDLI_DESKTOP.md):** the product around the core.
   - Paseo.
   - The Builder outside, sandboxes inside.
   - Teams postponed.
   - Who sees what.
5. **[narrative/SANDBOXES.md](../narrative/SANDBOXES.md)** and
   **[narrative/ESCALATION_MODELS.md](../narrative/ESCALATION_MODELS.md):** how the app does it today. Covers
   routing, the Mini question chain, fork, the two consent questions, and transform blocks.
6. [narrative/GOALS_v0.md](../narrative/GOALS_v0.md): the goal (people extend Idli themselves) and the four layers.
   [narrative/UX.md](../narrative/UX.md): screen rules.

### 2. Evidence (READMEs, newest first)
- `benchmarks/runs/2026-11-19-record-store/`:
  - the scaffold's blind bench (80 tasks written blind, 27 held out, graders with SQL, blind testers);
  - the raw transcripts are kept out of git (they hold test-account mail).
- `benchmarks/runs/2026-11-19-capability-cli-mapping/`: menu vs commands vs manual pages vs grammar.
- `benchmarks/runs/2026-11-19-blind-tester/`: the first blind testers; a PDF masking leak found and fixed.
- `benchmarks/runs/2026-11-18-{sandboxes,builder-minis,transform-blocks,mini-escalation}/`: the app rounds on the
  laptop, with screenshots.
- `benchmarks/runs/2026-11-17-trusted-catalog/`, `2026-11-18-leads-routine/`, `2026-11-17-builder-journey/`.

### 3. Chronology
- `chronology/2026-11-18T0900-catalog-routines-sandboxes.md`:
  - sections 1 to 9: the app (catalog, OAuth, sandboxes, Minis, transform blocks, escalation chain, script_try
    consent);
  - sections 10 to 13: CLI benchmarks, the grammar, the blind testers, the scaffold.
- Earlier steps are one file each in `chronology/` (2026-11-13 onward).

### 4. State right now
- **Branch:**
  - `oss-desktop-eval`, about 378 commits ahead of `origin/main`, **not pushed**;
  - history was declauded on 2026-11-18 (backup branch `backup-before-declaude-2026-11-18`);
  - commits since carry no Claude lines.

  The owner reviews and pushes. Before any push: `bash -ic 'declaude origin/main'`, then
  `git push --force-with-lease`.
- **Alpha release prepared, not pushed:** `.github/workflows/idli-alpha.yml` and `docs/idli-alpha-release.md`.
  - Paseo 0.15.2 plus our patch, and the Idli kit, for Linux, Mac and Windows.
  - Only Linux arm64 was built for real. The Windows installer doesn't run yet.
- **Scaffold code** (`benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/`):
  - `lib/recstore.py`, `lib/idlicli.py`, `desktop/idli`;
  - try it with `IDLI_SANDBOX=<dir> desktop/idli --help`.
- **App code, same folder:**
  - the router's routing is `lib/modes.py`, served by the DGX's `muse-prefix-proxy.service`. It's a systemd user
    service: restart it after changing modes.py. Muse itself is untouched;
  - the Mini chain is `lib/minitalk.py` and `lib/miniscope.py`;
  - also `lib/minifork.py`, `lib/tries.py` (the two consent questions), `lib/blocks.py`, `lib/transforms.py`,
    `lib/google_api.py`, `lib/docmask.py`, `lib/privacy.py`;
  - the MCP tools are in `lib/idli_mcp.py`.
- **Google test accounts:**
  - 87profligate@gmail.com is "me" and 88profligate@gmail.com is "a lead". Sending between them is allowed;
    WhatsApp never sends;
  - OAuth uses Idli's own unverified app (GCP project `bitrot-in`), with scopes gmail.modify, calendar.events,
    calendar.freebusy, spreadsheets.readonly and drive.readonly;
  - tokens are in `~/.config/idlisseus/google-tokens/` on the laptop and on the DGX (DGX consent with
    `python -m lib.google_api start EMAIL`, then `finish EMAIL 'ADDRESS'`).
- **Laptop:**
  - synced to `aca76f65` (2026-11-19). The scaffold isn't on it, on purpose: test there once we know what ships;
  - the tunnel is often down: ask the owner to run `desktop/laptop-up.sh start`;
  - sync with `git fetch dgx` then `git reset --keep dgx/oss-desktop-eval`, after a backup branch, keeping its
    `file-skills/households` edits.
- **Owner to-dos:**
  - rotate silo's Access token (it leaked into a transcript on 2026-11-17);
  - `claude auth login` on the DGX before 26 to 29 Nov.

### 5. Rules for this phase (on top of "Rules that always hold" at the end)
- Run targeted tests for simple changes, and the full suite only for routing, masking or blocks. Fix on the DGX
  first, then the laptop.
- Benchmarks:
  - a blind task bank written before building;
  - held-out sets frozen by hash and run once on frozen code;
  - graders that check against data;
  - general fixes only, never per-question patches.
- Delegate grinding to subagents, Cursor `agent` or `codex exec`. Codex may run, but nothing under `~/.codex` may be
  edited.
- Plain copy in anything a person reads. No "deepseek" in the UI: say "idli-remote".
- Never print `catalog.source()`, the OAuth client file, tokens, or silo headers.

---

## Older checkpoints (look things up here as needed)

## Checkpoint 2026-11-17: team stacks (overnight)

New since the checkpoint below:
- **Read [narrative/TEAM_STACKS.md](../narrative/TEAM_STACKS.md)** after the three narratives listed below. A team
  can bring its own open-source tools:
  - the Builder writes `extensions/stack/` (pixi.toml, stack.json);
  - Idli installs it inside a wall that reaches only package and code hosts, after the person's yes;
  - every version is pinned;
  - the stack runs with no internet (and an optional door to the 9B).
  
  New capability kinds are **tool** (Analyst `team_run`) and **app** (a page, `app_open`). New team setup ends in
  the Builder (`setup-team` skill). The results of 2 development and 5 held-out requests are at the end of the
  narrative. The chronology is `chronology/2026-11-17T0200-team-stacks-overnight.md`.
- **Code:**
  - `cowork/lib/stackwall.py`;
  - `desktop/idli-stack-consent.py` (the PreToolUse hook);
  - `teamcaps` (tool, app, stack, ignores);
  - `idli_mcp` (`stack_install`, `stack_run`, `team_run`, `app_open`);
  - `builder.setup_prompt` and `open_setup`, `teams.setup_with_builder`, `/api/team-setup`;
  - `tests/test_stacks.py`.

  Local commits `ebb0a58c`..`536427a1` (plus this checkpoint) are on `oss-desktop-eval`. **Not pushed.**
- **Production changes on the DGX:**
  - the 9B (`idli-9b`) was recreated with `--mmproj .../mmproj-F16.gguf` (vision on, as the owner agreed on
    2026-11-16);
  - the old container is kept stopped as `idli-9b-novision` for rollback;
  - pixi 0.84.2 is in `~/idli-insights/platform/bin`;
  - Muse was untouched and gets no images.
- **Security fix:** the account's claude.ai connectors (Drive, Gmail and Calendar, all signed in on the DGX) loaded
  in the Analyst and the Builder, around masking. Both launchers now set `ENABLE_CLAUDEAI_MCP_SERVERS=false`. Check
  the laptop's account after the next sync.
- **Test teams on the DGX** (`~/idli-insights/teams/`), each with a stack and a test file from Wikimedia Commons or
  written by me:
  - event-media and event-media-mate (the teammate test);
  - field-notes, helpline, comms, leads, training and survey.

  Their Builder sessions are in tmux (`b1`, `b2`, `h1` to `h5`).
- **Laptop (04:10):** synced and tested as a person; see the chronology's "Laptop run". `git fetch dgx` still needs
  the owner's Tailscale browser check, so code went over the Paseo terminal in base64 chunks (md5 checked; the laptop
  commits "sync from DGX (...)"). The script is in the DGX scratchpad (`lapsync.sh FROM_DGX_REV MSG`); redo it as a
  plain `git pull dgx` once Tailscale is approved.
  - The test team "Field Media" is on the laptop (Builder `32f83373`, Analyst `a918b529`, chat `2b85cf8c`).
  - The DGX router (`muse-prefix-proxy`) was restarted twice, for `/idli/9b/props` and the mention fix. Muse was
    untouched.

## Checkpoint 2026-11-16: read this first, then the narratives

**Read the narratives before anything else.** Most of the sections further down describe the product as it was on
2026-11-11 (one file at a time, forms, cleaning, Mission control). They are still accurate about mechanisms such as
cards, UI as API, credentials and ops, but not about the product.
1. [narrative/IDLI_DESKTOP.md](../narrative/IDLI_DESKTOP.md) covers:
   - what we are doing: an operating layer for NGOs;
   - what a Team and a Mini are, and why data Minis and workflow Minis share one shape;
   - the building blocks, each marked built, tested or idea.
2. [narrative/DRIVEY_JOURNEY.md](../narrative/DRIVEY_JOURNEY.md): the journey step by step:
   - A: make a Mini with masked Claude;
   - B: use it with the 9B, the query service and escalation;
   - C: Start here, Privacy and Logins;
   - D: Teams.
3. [narrative/MODEL_TYPES.md](../narrative/MODEL_TYPES.md): the four kinds of model and the platform boundaries:
   - the **Assistant** (the 9B, on the left);
   - the **Consultant** (DeepSeek);
   - the **Analyst** (masked Claude, on the right);
   - the **Builder**, which extends a team in `<team>/extensions/` with tests and git versions.

   It covers where each runs, what it sees, its sandbox and what it can change.
4. `chronology/2026-11-13*` to `chronology/2026-11-16*`, oldest first: what was built, tried and fixed, step by
   step.

**The product now (on the laptop, Paseo build idli25).**
- **Start here:**
  - **Teams page:** cards with Open and Delete, and New team (six panels);
  - **Privacy:** the log of what was sent to Claude;
  - **Logins.**
- **Drivey:** the built-in team.
  - Each workspace is two halves: Idli on the left (the 9B chat, `@` Drive files, Mini cartridges) and the
    person's own Claude Code on the right, through the masking proxy (`lib/ccproxy.py`, `desktop/claude-masked.sh`)
    on masked copies.
  - Minis are saved from Claude's work and answered by the 9B mapping a question to a saved script.
  - When no saved question fits, the query service is offered with a yes; then Claude.
- **Teams made from the page:** exact clones of Drivey under a new heading (`~/idli-insights/teams/<name>/`).
- **WhatsAppy:** an empty plain Claude space. Owner rule: nothing is ever sent, by anyone.
- **Gone:** Canvay and the Teams chat. The bootstrap no longer recreates them.

**Code.**
- Everything is under `benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/`:
  - teams: `lib/teams.py` and `lib/teams_page.html`;
  - the page server and its routes: `lib/formserver.py`;
  - the Idli chat router: `lib/modes.py`;
  - Minis: `lib/minimap.py` and `lib/mini-card.html`;
  - the query service: `lib/minisql.py`;
  - sidebar setup: `desktop/idli-bootstrap.py`.
- **Paseo patches:** `desktop/paseo-idli-split.patch` (P13-P21). Each patch is listed in
  `todos/idli-insights/p1/paseo_patches.md`. Builds and patch copies are in `~/idli-builds/`. Rebuild before
  taking any Paseo update.
- **Tests:**
  - `/tmp/idli-journey-venv/bin/python -m pytest -q tests/ --ignore=tests/check_journey_browser.py`. The cowork
    `.venv` has no pytest; system python has no duckdb.
  - Headless page checks use system `python3` with Playwright.

**Git.**
- Branch `oss-desktop-eval`, last commits `bed5c05d` (Teams page, idli25) and the commit that wrote this
  checkpoint.
- **Not pushed.** Before any push: `bash -ic 'declaude origin/main'`, then `--force-with-lease`, with 0 Claude
  trailers.
- **Laptop:** at its own commit `7919ac9f` ("sync from DGX").
- **Code reaches the laptop as tarballs:** served from the session scratchpad at `http://100.82.28.38:8851/` and
  pulled by commands typed into the laptop's Paseo terminal. The app is driven over DevTools (port 49333) when the
  owner's tunnel is up. See "Ops" below.

**Laptop state (test Google account; the owner is about to test the new team flow).**
- **Backup:** Paseo's agents and projects were backed up first, to
  `~/idli-insights/archive/paseo-agents-projects-20261116-0918.tgz`.
- **What's left:**
  - Start here (Teams, Privacy, Logins);
  - Drivey (one empty workspace, five Minis);
  - WhatsAppy;
  - the Claude Code heading (no chats).
- **Archived:** test teams, Insights and Canvay are in `~/idli-insights/archive/`.

**Open, in rough priority.**
- **The Builder, on the laptop.** Built and tested on the DGX on 2026-11-16 (see MODEL_TYPES, "Built and tested").
  The laptop run is next:
  - the Builder tab opened by Paseo;
  - the left chat's Builder card on a real Drive photo;
  - Versions on a real team;
  - the labels in Paseo's terminals.

  The owner brings up the tunnel. The DGX test team is `~/idli-insights/teams/field-photos` (synthetic data only).
- **The owner's test of New team -> Open -> Delete:** reported working on 2026-11-16.
- **The Drivey split race.** It is repaired on display (P21), not prevented. The repair is in
  `utils/idli-side-pane.ts repairDriveySplit` in the Paseo checkout.
- **Small items:**
  - a reload strip shows above the Teams page;
  - the old chat-based team flow (`teams.route`, `modes.teams_chat_route`) is unused and can go.
- **Concepts, not built:**
  - a guided first Mini from a sample file at the end of making a team;
  - workflow Minis (see IDLI_DESKTOP section 3);
  - teams across computers.
- **Open questions:**
  - whether Claude's subscription terms allow the masking proxy (if not, use Codex on the right);
  - Google's terms for browser search (`lookup` is PoC only).

**Owner rules that came up in this run (on top of "Rules that always hold" below).**
- **Plain UI copy:** no flowery phrasing, few commas, no arrows or "·".
- **Who asks:** Idli asks, not Claude. Say "Idli" on screen.
- **No jargon:** NGO staff are not technical.
- **Testing:** default to the 9B; take screenshots.
- **The laptop:**
  - it is a test account and may be read for dev;
  - use its Paseo shell only for dev, never in front of the user;
  - back up and read git status before any reset.
- **WhatsAppy:** nothing is ever sent.
- **Muse:** client only; never restart it.

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

## Earlier checkpoint (2026-11-11 ~23:30 IST, history: see the 2026-11-16 checkpoint at the top)
Everything below is in git or on disk; nothing depends on a live session. Branch `oss-desktop-eval` (DGX, not
pushed to GitHub), last commit is the one that updated this page.

### 1. The product: the clean → analyse flow, verified in the app on the laptop
- **How a file goes from checks to analysis** (chronology: "2026-11-11 (night), DGX: cards back at every step into
  analysis"):
  1. `file_get` (a pasted link) → `file_open`. If the file has problems and no checked copy for its skill
     version, a card: "Upload a checked copy to your Drive so you can fix them?" → "Yes, upload a checked copy
     (Recommended)" / "No, analyse the original".
  2. On yes, `working_copy` puts the copy next to the original in Drive: red cells, a comment per kind of problem,
     counts on tab names, an "Idli checks" tab. Then a card: "Continue with analysis?" → "Continue with analysis" /
     "Not yet".
  3. On Continue, `working_copy_ready` downloads the copy from Drive again (the person's fixes) and says what was
     fixed and what's new ("you fixed 1; 1 new one appeared (Density row 3, …)").
  4. A file that already has a copy: "Use the checked copy (Recommended)" / "Use the original". A file re-taught
     since its copy: the upload is offered again (copies record `skill_version`).
- **Charts never drop or merge rows** (owner): chart code may not `drop_duplicates`, remove outliers or merge
  spellings (teach-file skill). `chart_show` draws rows with problems as they are and points at the checked copy.
- **Messy values** ("cancel" vs "Cancelled", "12 cm" in a number column) are flagged by the checks and fixed by the
  person in the copy. No special-casing in code (owner).
- **Commits** (newest last): `51392d9d`, `dabfad55`, `8a117e7f`, `05ea479d`, `dd54e801`. The laptop is on
  `dd54e801`.
- **Verified on the laptop:**
  - the cestrum original by link;
  - upload card → copy in Drive → Continue card;
  - a cell fixed in Drive was read back on Continue.
  - Screenshots and steps are in the chronology entry.
- **Known gaps:**
  - A copy lands in My Drive unless the original's folder is known (`file_get` doesn't record the parent
    folder).
  - Answers (`file_ask`) only say "rows that failed checks are included"; they don't point at the copy.
  - The new "fixed / new" wording hasn't been seen in the app yet.
- **Left on the laptop's test account:**
  - three cestrum working copies in Drive (9 Nov, 11 Nov 2248, 11 Nov 2257; D5 edited in the last);
  - old copy records backed up as `drive/field_vars_indicators.xlsx.source.json.bak-2026-11-11{,b}`.
- **The laptop's Google account is a test account** (owner): dev agents may read Idli's logs and Drive tabs there.
- **Other agents:** merge `oss-desktop-eval` before touching `file_open`, `working_copy`, `working_copy_ready`
  or `chart_show`.

### 1b. The model switch (2026-11-12): Muse / 9B / Steam powered
- Paseo's Idli model menu → DGX router (`dgx/muse_prefix_proxy.py`, user service `muse-prefix-proxy`) →
  `cowork/lib/modes.py`. The 9B: `dgx/idli-9b.sh up|down|status` (container `idli-9b`, port 8291), needed by the 9B
  and Steam modes. Chronology: "2026-11-12 (morning), DGX: Idli's model switch".
- **Laptop (2026-11-12 ~09:00):** pulled `1eda4efa`; the three models are in `~/.paseo/config.json` (backup
  `config.json.bak-modes`); Paseo lists them. In the app, cestrum original by link, "Use the checked copy" →
  start card → "trees per plot" (chart + list) → "share of trees that are cestrum, by transect" (17.4%, with the
  new %) → "ask Claude" → card:
  - **Steam powered:** all steps right; 5-7 s per question; "Not now" sent nothing (no new Claude chat).
  - **Idli 9B:** same answers, ~20 s per question; the "ask Claude" card appeared (3 min, mostly making the fake
    copy). Stopped there when the laptop closed: chat "9B: cestrum" sits on that card, nothing sent.
  - **Muse:** not run in the app yet (DGX-tested only).
  - Steps the product itself takes, in every mode: file_get ~40-60 s (browser download), the fake copy for Claude
    ~2 min.

### 2. Evals: E6, E7, E1, E2, E3 done and reported
- **Where:** branch `idli-pipeline-eval`, pushed at `b4e4361f` (declauded); worktree
  `.claude/worktrees/agent-aaf212a4b5f290bbe`; folder `benchmarks/runs/2026-11-10-idli-pipeline-eval/` (E).
  `E/REPORT.md` has every result, the owner decisions and "For the integrator". Not merged into
  `oss-desktop-eval` yet.
- **E1/E2:** the fake copy keeps 43/62 kinds of mistake (47 with `IDLI_MOCK_V2=1`). Teaching from it finds 85-90% vs
  81% from the real file: noise-level.
- **E3** (the trip to Claude and back):
  - It works: 0 wrong bounces in 27 chats; sent 23/24, back 22/23; about a minute and $0.15 a trip.
  - Chart code was exactly right on the real file in 12/24 trips, mostly because of split spellings and dropped
    repeated-ID rows. The no-drop rule above addresses the drops; the spellings are now flagged problems.
  - 6 of 9 expected answers were wrong and were corrected (`E/results/e3/refcheck.md`).
- **The local 9B is stopped** (`E/harness/serve9b.sh up` restarts it).
- **Owner decisions:**
  1. Charts use the form's reading: already true.
  2. No silent row drops: done.
  3. Hold `IDLI_MOCK_V2` for one more E2 run.
  4. Measures vs charts: open. Should Claude add a form measure for a number question, rather than a chart?
- **Round 2 done (2026-11-12):** E2b, E3b, E4, E5 on branch `exp/evals-1111` (local, `0b395e5a`), plus Codex's
  code/cards experiment on `exp/clef-form`. Results and what to do next: chronology "2026-11-12 (morning)".
- **Lessons:**
  - Run batches with `nohup` and wait with a background loop; hand code and log reading to Codex.
  - Check expected answers before trusting a score.
  - The 9B harness's `idli.setup()` chdirs into a temp home, so use absolute output paths.

### 3. Driving the laptop from the DGX (when the owner has the tunnel up)
- **CLI:** `cowork/desktop/paseo-remote.sh` (`ls`, `agent reload|send|logs <id>`, `workspace ls`).
- **A new chat runs new code;** an open one needs `agent reload <id>`.
- **Laptop terminal:** `terminal create --workspace <id>`, `terminal send-keys <id> "<cmd>" Enter`,
  `terminal capture -S <id>`.
- **The app window:** `desktop/drive.py shot|click|clickxy` (system `python3`). Click coordinates are CSS pixels,
  half the screenshot's. Chat tabs are titled "Analyse: <file>"; `drive.py click "<title>"` switches to one.
- **Drive/Sheets tabs:** screenshot or click them over DevTools with node, using the tab's `webSocketDebuggerUrl`
  from `http://127.0.0.1:49333/json/list`: `Page.captureScreenshot`, and `Input.dispatchMouseEvent` /
  `dispatchKeyEvent` to type.

### 4. Demo installers (not active)
Branch `idli-installers`. It works, but lacks our Paseo patches P1, P3 and P12. Gaps D1-D11 are in
`todos/idli-insights/p1/deployment_strategy.md`.

### 5. Session settings
`~/.claude/settings.json` sets `API_TIMEOUT_MS=1800000` and `CLAUDE_STREAM_FIRST_BYTE_TIMEOUT_MS=1200000`.
Headless teaching overrides it to 5 minutes per call.

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
- Read only, except the checked working copy in Drive, made after a yes on the upload card: always a new file next
  to the original, never an edit. Claude gets fake data only. Real data stays on the
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
