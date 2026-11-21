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

**Laptop run (03:00-, test account), "verify like a real human":**
- **Sync.** `git fetch dgx` still needs the owner's Tailscale browser check. Instead, the changed cowork files went
  to the laptop through its Paseo terminal, in base64 chunks (md5 checked). The laptop's copies were first checked
  to equal the last synced versions. Committed on the laptop as `9e3b4c10 sync from DGX (team stacks)`. pixi 0.84.2
  (x86_64) is in `~/idli-insights/platform/bin`.
- **Tests on x86:** `tests/test_stacks.py` passes there, including the slow ones (a real install through the
  proxy, then the no-network run).
- **Teams > New team in the app,** clicked through as a person ("Field Media", Google Drive, A few of us, Yes, Ask
  me each time). Set it up opened the new workspace: Idli on the left, the Builder on the right with the setup
  answers. Rough edges:
  - the tab header reads "Analyst" while the Builder is shown (its own tab is only an icon);
  - Claude Code's banner shows the account email.
- **The Builder, as a person** ("We keep screenshots of tables from reports in Drive... turn them into
  spreadsheets... Do what you think is right"). It built a reader with Tesseract and img2table in 10 min, with one
  install prompt. In the laptop's narrow right pane, the prompt showed only "For: ..." and "(+25 more lines)": the
  person couldn't see what was installed. **Fixed:** the prompt now starts with "Adds: ..." and "Runs on this
  computer with no internet".
- **The 9B wasn't offered.** On the laptop the private model is reached through silo, but the menu and the stack's
  model door only knew the DGX's `127.0.0.1:8291`. **Fixed:**
  - `stackwall.model_upstream()` uses silo with Cloudflare Access when it is set up, and forces model `idli-9b`;
  - the door accepts only JSON chat, so nothing can reach Muse;
  - the router has `/idli/9b/props`;
  - the Builder has a live `capability_menu` tool.
- **Left chat, @ finance_caste_table.png.** The table's shape was right, but numbers were wrong (2.5% read as 25%,
  4.5% as 45%, 2005 as 200). Told so, as a person, the Builder added a second OCR reader: two readers must agree,
  otherwise the cell is flagged. Retried, every number was right and the one doubtful cell was flagged.
- **Bugs a person hit, all fixed:**
  - the @ picker offers the team's downloaded copies (`drive/...png`, `.png.csv`, even `.source.json`), and Idli
    answered "Add files with @". A copy now means its Drive original;
  - "(read as csv)" now reads "(read as table)";
  - "Accept Idli's choices" hid every number. A reader's table hid all text columns, and "92.8%" counted as text.
    Numbers, percentages, amounts and years now count as numbers. Phone and ID digit strings never do;
  - the name detector hid number columns under a person-sounding heading ("Caste category of enterprise owner").
    In a reader's table, a column of numbers stays visible;
  - a percentage or year hidden once stayed masked in every file (free-text matching). Percentages and years are
    no longer matched in free text;
  - the Analyst said the team "can't read images": its list was written before the Builder added the reader. It
    now has `team_capabilities`, and its instructions say to check it first.
- **End of the journey:**
  - in the review, the person switched the label and number columns on, then Done and Switch to Claude;
  - the Analyst gave three correct figures (% firms with institutional finance, Rural: 3.6%, 2.5%, 3.3%), with
    where each came from, and asked the person to check them against the picture.
- **Still rough:**
  - row labels ("Rural", "SC") stay coded, because the second screenshot's all-hidden choice marks them private.
    The person sees real words in replies, but Claude works blind on labels;
  - the @ picker matches loosely ("@caste_tab" picked finance_caste_table.png.csv);
  - the "+" in the left pane opens a menu, and "Agent" didn't start a new chat;
  - Claude Code shows the account email in its banner;
  - the Builder's tab title is only an icon.
