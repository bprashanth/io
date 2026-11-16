# 2026-11-17 02:00: Team stacks: a team brings its own tools from GitHub, conda-forge and PyPI (overnight run)

**Asked (2026-11-16, late):** "When a user clicks new team, I want them to brainstorm with the builder claude first."
After the fixed cards, send the bundle of answers to the Builder, which:
1. works out how models, privacy filtering, consultation, logins and UI skills fit together;
2. talks through the team's central goals and workflows (the leads example: an email comes in, a call goes on the
   calendar, the sheet gets hot or cold).

The Builder then gets the GitHub projects and tools those workflows need, and runs them safely on Mac, Windows and
Linux. Teammates duplicate the stack. "Enable such free-wheeling innovation rather than get in the way, but in an
easy manner that is not insecure." Then: "Go for it. Would you be able to figure out with an overnight run? Don't
overfit. You can assume that someone would say I want a voice chatbot or I want hindi translations etc also."

**Agreed in the brainstorm:**
- the platform owns models, masking, consent and logins; the team owns a pixi-locked stack inside Idli's wall;
- Linux everywhere (WSL2 on Windows, a light VM on Mac);
- every tool's output is files or tables that go through the privacy review;
- RapidOCR and the 9B's vision (from the image comparison) are agreed, and Muse stays off images.

**Built:** see [TEAM_STACKS.md](../narrative/TEAM_STACKS.md).
- `lib/stackwall.py`:
  - the install wall: bubblewrap with no network, plus one door to an egress proxy on a unix socket (HTTPS to
    package and code hosts only, every host logged);
  - the run wall: no network, plus an optional door to the 9B's chat endpoint only;
  - pages served from the wall through an inward door;
  - pinning: pixi.lock, plus stack-lock.json for repo commits and download sha256;
  - consent by item set.
- Team capabilities gain kinds **tool** (runs on originals, writes to `outputs/`, called by the Analyst with
  `team_run`) and **app** (a page, opened with `app_open`), and `"stack": true` for readers and tests.
- **Builder:**
  - new tools `stack_install` and `stack_run`;
  - a PreToolUse hook makes Claude Code ask the person, with Idli's own summary of the stack (from a settings file
    outside `extensions/`);
  - asks again only when something new is added;
  - new skill `setup-team`, and a rewritten `CLAUDE-builder.md` (cheapest first, but a purpose-built model over a
    home-made rule for judgement).
- **Onboarding:** Set it up makes the team, opens it, and starts the Builder with the answers (`/api/team-setup`).
- **Found on the way and fixed:** the account's claude.ai connectors (Google Drive, Gmail and Calendar, signed in on
  the DGX) loaded in both the Analyst and the Builder, which bypasses masking. Both launchers now set
  `ENABLE_CLAUDEAI_MCP_SERVERS=false`.
- **Platform:** pixi 0.84.2 in `~/idli-insights/platform/bin`. The production 9B (`idli-9b`) was recreated with
  `--mmproj` (vision on, as agreed). The old container was kept stopped as `idli-9b-novision` for rollback. Muse
  was untouched.

**Method.** Two development requests (D1 video, D2 voice notes). Then the code was frozen (commit 50a33a05) and five
held-out requests were written before any code (`benchmarks/runs/2026-11-17-team-stacks/requests.md`). Each ran
through the real Builder (Claude Code in tmux), with me answering as a non-technical person. Then I checked each
result on files the Builder never made: public recordings from Wikimedia Commons, or documents I wrote.

**Results:** see TEAM_STACKS.md, "Results".

**Fixes after the freeze (bugs, not tuning), each found by a held-out run:**
- the page door kept a 10 s read timeout;
- installed stacks were committed to team git (up to 2.2 GB);
- a stale git lock was left behind;
- the capability menu still said the private model can't read images.
