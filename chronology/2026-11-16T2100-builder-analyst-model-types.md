# 2026-11-16 21:00: Model types (Assistant, Consultant, Analyst, Builder); a team can extend itself

**Asked**
- The outside service question at setup gets three answers: Yes, Ask me each time (both "Only masked data is
  sent") and No.
- When a team can't do something, the person extends it themselves with a **Builder**:
  - **Analyst** (the right half): works within what the team knows and has tested, and extends Minis;
  - **Builder**: adds new abilities with tests;
  - **Assistant**: the 9B on the left;
  - **Consultant**: DeepSeek.
- The Builder knows the platform it builds for. Nothing installs anything. Changes can be undone with git, and like
  a Chrome extension they work without a restart.
- Label the two Claude Code terminals Analyst and Builder, visibly different, and change nothing else.
- Document the boundaries in `narrative/MODEL_TYPES.md`. Build and test on the DGX first, then on the laptop.

**Built:** see `narrative/MODEL_TYPES.md`, "Platform boundaries" and "Built and tested".
- **Team capabilities** (`lib/teamcaps.py`): the base plus extensions in `<team>/extensions/`, with a manifest,
  readers, tests and git. A capability counts only while its test passes on the current files.
- **Readers** run in the chart sandbox (no network, read-only, home hidden). They turn a file into CSV tables, which
  then go through the usual privacy review and masked copies.
- **The capability menu** (`lib/capmenu.py`): OCR (Tesseract), speech to text, text to speech, ffmpeg and
  pdftotext, cheapest first. A missing tool means a platform request; nothing is installed.
- **The Builder** (`desktop/claude-builder.sh`): the person's own Claude Code in `extensions/`, with:
  - the `build-team` skill;
  - the platform source readable and edits denied;
  - a sandbox that keeps out the team's files, other teams, Idli's folders and transcripts;
  - tools `team_check`, `team_save` and `platform_request`;
  - a checkpoint before it starts.

  It opens as a "Builder" tab on the right of the team's workspace (`lib/builder.py`). Its request is masked.
- **The Analyst** gets the team's tested capabilities and the way out ("say so, offer the Builder") in its
  `CLAUDE.md`, the team's Analyst skills, and `builder_open`.
- **The left chat:**
  - a Builder card for files the team can't read;
  - "build it";
  - "open the Builder";
  - "can you read photos?";
  - Yes at setup skips the query service card.
- **Teams page:** three outside answers; on the cards, Added and Versions with Go back.
- **Labels:** a teal ANALYST or amber BUILDER status line, a startup announcement, and the tab title. Claude Code is
  otherwise unchanged.

**Tested:** 179 tests pass. Real Claude Code CLI on the DGX with a test team, Field Photos; details are in
MODEL_TYPES.
- **The Builder** chose Tesseract by itself and built and tested a register-photo reader in 7.5 minutes.
- **Walls:** it couldn't read the team's file (shell: no such file; Read: denied). It couldn't edit the platform
  (Edit: denied; shell: read-only).
- **A leak, found and fixed.** A photo read with generic column names left a village visible in the masked copy.
  - Fixed in the platform: a reader's text columns start hidden.
  - Fixed through the Builder: asked, it changed the reader to use the heading row and saved a second version.
- **The Analyst** answered from the photo table correctly. The wire log had 0 real values.
- Asked to transcribe voice notes, **the Analyst** offered the Builder and called `builder_open`. Opening the tab
  needs Paseo: that is the laptop test.
- **Teams page,** headless: the three answers, Versions, and Go back.

**Next:** the laptop run (the owner brings up the tunnel).
