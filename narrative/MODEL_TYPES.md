# Model types in Idli Desktop: Assistant, Consultant, Analyst, Builder

2026-11-16. Agreed with the owner and built the same day: tested on the DGX, and the laptop run is next (see "Built and tested" at the end). The wider picture is
in [IDLI_DESKTOP.md](IDLI_DESKTOP.md), and the Drivey journey is in [DRIVEY_JOURNEY.md](DRIVEY_JOURNEY.md).

Four kinds of model work in a team. Each has a job and a limit. When one of them reaches its limit, it hands over
to the next, and the person says yes to each hand-off.

| Name | What it is | Where it shows | What it sees | Its limit |
|---|---|---|---|---|
| **Assistant** | The small local model (the 9B) plus code | The left half, the Idli chat | Real data, on this computer | It can only pick from what a Mini already has: saved questions and their options |
| **Consultant** | An outside text model (DeepSeek through OpenRouter today) | Inside the Assistant's chat, after a yes | The masked question and the column list, never rows | It writes one read-only query, which runs on this computer |
| **Analyst** | The person's own Claude Code, through the masking proxy | The right half of a team workspace (a terminal) | Masked copies of the team's files | Only what the team already knows how to do, and has tested |
| **Builder** | The person's own Claude Code, working on the team itself | A terminal tab named Builder on the right of the team's workspace, next to the Analyst | The team's definitions, the platform's source (read only) and fake sample files; never real data | Only the team's own folder; the platform and Paseo are outside it |

The Assistant and the Consultant work together in the left chat, with no headings of their own. The Analyst and
the Builder are terminals. A terminal on screen means a frontier model is at work. The left chat means it isn't,
except for the Consultant, which only acts after a yes on its card.

## What "known and tested" means

A team has a list of **capabilities**: things it has been taught and that have passing tests on fake data. Some
examples:
- **Insights** knows how to read Excel and Sheets files, mask them, chart them, and save Minis.
- A **WhatsApp team** might know how to read a group's messages and post to a sheet, because someone learned
  WhatsApp Web's pages on a test account and tested the steps.

This list is the boundary between the Analyst and the Builder:
- **The Analyst** works inside it. It can extend a Mini with new questions, new charts or a new step, using only
  tools the team already has.
- **The Builder** moves the boundary. It adds a new capability, with its tests, so the Analyst can use it from then
  on.

## Who hands to whom

1. **The Assistant (inside a Mini) can't answer.** The order is the same as in Drivey today:
   - first the Consultant (with a yes, if the team allows it);
   - then the Analyst, with a card that reads "Switch to the Analyst?" and shows the masked question.
   - Extending the Mini is the Analyst's job.
2. **The Assistant can't even hand to the Analyst,** because the request is outside the team's capabilities. For
   example, the file is an image and the team can't read images, so there is no masked copy for the Analyst. Or
   the request needs a site the team hasn't learned. In those cases the card reads: "Insights can't do this yet.
   Build it with the Builder?"
3. **The Analyst is asked for something outside the team's capabilities.** Its instructions list the team's
   capabilities, and tell it to say so plainly and offer the Builder: "This team doesn't read images yet. The
   Builder can add that." It does not improvise a one-off.
4. **The Builder finishes.** It runs the new capability's tests, saves a checkpoint, and says what was added. The
   next request goes to the Assistant or the Analyst as usual, with no restart.

## What each layer owns, and who may change it

| Layer | What it holds | Who changes it |
|---|---|---|
| **Paseo** (the app, our patches) | Windows, panes, terminals, the sidebar | Us, in platform releases |
| **The Idli platform** (`cowork/`) | The router, the masking proxy, the page server, the platform tools, and the capability menu (the allowed packages and models) | Us. The Builder can read it, but never writes to it. Anything it needs from the platform becomes a **platform request**. |
| **The team** (`~/idli-insights/teams/<name>/`) | `team.json`, the Assistant's instructions and tool list, the Minis, and, new: `extensions/` (tools, file readers, Analyst skills, site steps, each with tests), plus a manifest listing the team's capabilities | The Builder (new capabilities) and the Analyst (Minis only) |

So, yes: the Builder can't change Paseo or the platform, but it can write team Python, skills and manifests.
It knows the surface it builds on from three things:
- a written extension contract (the "build-team" skill: the manifest format, how a tool is declared, how it calls a
  capability, how its tests run);
- the platform source, as read-only reference;
- the team's own folder.

Extension code runs in the sandbox Idli already uses for chart code (no network, read-only), with the platform's
pinned packages. **Nothing ever runs pip install.**

**Updated 2026-11-17: a team can bring its own tools.** See [TEAM_STACKS.md](TEAM_STACKS.md). A team's
`extensions/stack/` lists packages (conda-forge, PyPI), GitHub repos and model downloads. Idli installs them inside
an install wall that reaches only package and code hosts, after the person says yes to a summary Idli writes, and
pins every version. They run in a wall with no internet (and, if declared, a door to the private model only). The
rule "nothing installs" becomes "nothing installs outside the wall, unpinned, or without the person's yes". The
menu below is now what the platform gives for free; the stack is where everything else goes.

### The capability menu (platform-owned)

Each kind of work has three options, cheapest first. "Outside" is only ever reached after a yes, and only with
masked text. Media is turned into text on this computer first.

| Need | Local code | Private model | Outside, after unmasking, as text |
|---|---|---|---|
| Reading images and scans (OCR) | Tesseract, with Hindi and Marathi packs (RapidOCR agreed, 2026-11-16) | The 9B with its vision file (live since 2026-11-17; Muse stays off images) | Consultant |
| Speech to text | faster-whisper | Muse on the text | Consultant |
| Text to speech | Kokoro | none | none |
| Video | ffmpeg | none | none |
| PDFs and documents | pdfplumber, pymupdf, python-docx | Muse | Consultant |
| Charts and maps | matplotlib, Vega-Lite, India boundaries | none | none |

When the person says "do what you think is right", the Builder takes the local option. It moves to the private model
only when the local one fails its tests on the fake samples, and it says so.

## Changes, undo and reinstall

- **Local git in the team folder.** Only definitions are tracked: instructions, tools, extensions and Minis.
  Downloads, masked copies and privacy codes are excluded.
- **Checkpoints.** A checkpoint is saved before and after each Builder session. The team card shows **Versions**
  ("Before images, 16 Nov 14:02") with **Go back**.
- **Live reloading.** Idli's tool server and page server read `extensions/` on each call. A change works on the
  next message, like a Chrome extension reloading.
- **Delete and reinstall.** Deleting a team archives its folder and history (as Delete does today). A reinstall
  starts again from the base.

## How the Analyst is set up today [built]

- **Launch.** `desktop/claude-masked.sh` starts the person's own Claude Code:
  - in `~/idli-insights/claude-masked-<team>`;
  - through the masking proxy (`ANTHROPIC_BASE_URL` pointing at `lib/ccproxy.py`);
  - on masked copies in `drive/`.
- **Instructions:** `idli/CLAUDE-masked.md`, copied in as `CLAUDE.md`. It covers codes, masked copies, small steps
  and `/mini`.
- **Skills:**
  - `masked-data` (when to propose a reveal or a search);
  - `newsroom-charts` (chart templates and India maps);
  - `relationship-visuals`.
- **Command:** `/mini`.
- **Tools:** the Idli tool server (`lib/idli_mcp.py`): `idli_show` (charts in the left chat), `unmask`, `lookup`,
  `idli_draft_mini` and `idli_save_mini`.
- **Settings** (`lib/launchsettings.py`):
  - a sandbox that keeps it out of Idli's private folders and its own transcripts;
  - read and edit deny rules;
  - "ask" rules for reveals and searches.
- **The gap:** all of this is copied from the platform at each launch and is the same for every team. A team can't
  give its Analyst anything of its own yet. The design above changes that with Analyst skills in `extensions/`, and
  a capability list made from the manifest.

## Platform boundaries: who runs where, sees what, and can change what

These are the walls the whole design rests on. If a change would move one of them, it is a platform decision, not
a team change.

### Where each model runs, and what it can reach

| | Assistant | Consultant | Analyst | Builder |
|---|---|---|---|---|
| **Runs on** | This computer (the 9B), or Muse on our box | DeepSeek via OpenRouter (no data kept) | Anthropic, on the person's own subscription | Anthropic, on the person's own subscription |
| **Started by** | Paseo, as the left chat (`t4gc-cowork` provider) | Idli's code (`lib/minisql.py`), never a model | `desktop/claude-masked.sh`, in a terminal on the right | `desktop/claude-builder.sh`, in a terminal on the right |
| **Working folder** | The team folder (real files) | none | `~/idli-insights/claude-masked-<team>` | `~/idli-insights/teams/<team>/extensions` |
| **Sees real values** | Yes (it never leaves this computer) | No: the masked question and the column list | No: masked copies; a reveal needs two consents | No: fake samples only; it never sees the team's downloads |
| **Network path** | Local | Idli calls it after a yes | Through the masking proxy (`lib/ccproxy.py`), which replaces private values with codes and blocks known ones | Direct to Anthropic. It holds nothing private, and its sandbox keeps it from the team's data |
| **Shell** | None (the router and tools are code) | None | Claude Code's sandbox (bubblewrap): read deny on Idli's private folders, no unsandboxed commands | Claude Code's sandbox: reads the platform, writes only `extensions/` |
| **Tools** | Idli's tools: Drive fetch, privacy review, Minis, hand-offs | none | Idli's tools: `idli_show`, `unmask`, `lookup`, Mini draft and save, `builder_open` | `team_check` (tests), `team_save` (checkpoint) |
| **Can change** | Nothing: it picks and asks | Nothing: it writes one read-only query, checked and run by code | The team's Minis | The team's `extensions/` |

### What the Analyst is given at launch (and from where)

1. **Starting it.** The person's own `claude` binary. It is never a copy or a fork, and its interface is unchanged.
2. **Masked copies.** `drive/` holds masked copies of the files the person reviewed (`lib/maskcopy.py`). Files that
   were never reviewed are not copied.
3. **Instructions.** `CLAUDE.md` is the platform's `idli/CLAUDE-masked.md`, followed by **this team's capabilities**,
   read from the team's manifest. The list ends with what to do outside it: say so, and offer the Builder.
4. **Skills.** The platform's skills (`masked-data`, `newsroom-charts`, `relationship-visuals`), plus any Analyst
   skills the team's extensions declare.
5. **Settings** (`lib/launchsettings.py`):
   - the sandbox and deny rules;
   - "ask" rules for reveals and searches;
   - the Analyst label (see "Labels" below).

### What the Builder is given

- **The contract:** the `build-team` skill. It covers the manifest format, the kinds of extension (a file reader, a
  Mini step, Analyst skills), how tests are written, and the capability menu.
- **The platform source, read only.** `cowork/` is readable for reference. Edits there are denied.
- **The team's `extensions/` folder,** with its git history.
- **Fake samples** in `extensions/samples/`. These are files the Builder makes or is given; they are never the
  team's downloads.
- **Denied:** the team's downloads, masked copies, privacy codes, Minis, transcripts and Idli's config. The only
  writable place is `extensions/`.

### How an extension runs

- A file reader is plain Python that the platform calls as `read(src, out_dir)`. It runs in Idli's bubblewrap wall,
  the same one used for chart code:
  - no network;
  - the filesystem is read only, with home folders hidden;
  - only the one input file and one output folder are visible.
- It turns the file into a spreadsheet (CSV), and the existing pipeline takes it from there: the privacy review,
  masked copies, the Analyst and Minis.
- Extensions use only the platform's packages and the capability menu's local tools. Nothing installs anything.
- A capability counts only while its test passes. A failing test switches it off until it is fixed.

### What is tracked, and how to go back

- **What git tracks:** the team's `extensions/` folder (the manifest, readers, skills, tests and samples). It never
  tracks real data.
- **Checkpoints:** one is saved before each Builder session ("Before: <the request>"), and the Builder saves another
  when its tests pass.
- **Going back:** Versions on the team card. Going back restores `extensions/` to that point; the history is kept,
  so going back can itself be undone.

## Labels on the terminals [built]

The Claude Code terminal stays as it is. Only its labels change, using settings Claude Code already has (present
in version 2.1.325; to check on the laptop's version):
- **`companyAnnouncements`:** a line in the startup banner, for example "Analyst for Insights. Private values reach
  me as codes." or "Builder for Insights. I change this team, not your data."
- **`statusLine`:** a line that stays at the bottom, for example "Analyst - Insights".
- **Paseo's tab title:** "Analyst" or "Builder", from our launcher.

The "Claude Code" logo and title in the banner are part of Claude Code itself, and we leave them alone.

As built:
- **Status line.** The Analyst's is a teal **ANALYST** block, then the team's name and "private values are codes".
  The Builder's is an amber **BUILDER** block, then the team's name and "changes this team, never your data"
  (`desktop/idli-label.sh`).
- **Announcement.** The banner line reads, for example, "Analyst for Insights. Private values reach me as codes. I
  work within what Insights knows how to do." Claude Code puts its own heading above it: "Message from
  <account>'s Organization:".
- **Tab title.** Both launchers set it to Analyst or Builder, and turn off Claude Code's own title.

## Built and tested (2026-11-16, DGX)

**Where the Builder opens.** The Builder opens as a second terminal tab, named **Builder**, on the right of the
team's own workspace, beside the Analyst. It does not open in a separate Build workspace, because Paseo ties a
workspace to one folder. One window keeps the hand-off visible, and the colours tell the two apart.

**Code**
- `lib/teamcaps.py`: the base, the manifest, readers and tests in the wall, git versions, and what the Analyst is
  told.
- `lib/capmenu.py`: the capability menu.
- `lib/builder.py`: opening the Builder, with the request masked.
- `desktop/claude-builder.sh`: the Builder's launcher.
- `idli/CLAUDE-builder.md` and `idli/builder-skills/build-team`: the Builder's instructions and the contract.
- `lib/launchsettings.merge_builder`: the Builder's sandbox.
- `lib/rolelabels.py` and `desktop/idli-label.sh`: the labels.
- Router (`lib/modes.py`):
  - the Builder card;
  - "build it";
  - "open the Builder";
  - questions such as "can you read photos?".
- Teams page: three answers for the outside service, and Versions with Go back.
- Readers' tables start with every text column hidden (`lib/home.py`). The query service refuses in code when a
  team said No.

**Tests:** 179 pass, including `tests/test_builder.py` (router, capabilities, sandbox, versions, outside choices).

**Tried with the real Claude Code CLI on the DGX, on a test team ("Field Photos"):**
1. **The first build.**
   - The Builder was asked "what do the attendance registers in these photos say? do what you think is right".
   - It chose Tesseract on this computer by itself.
   - It drew two fake registers (one tilted, with a shadow), wrote a reader, a test and an Analyst skill, and passed
     `team_check`.
   - It saved "Read photos of registers and forms into a table". That took 7.5 minutes.
2. **The walls held.**
   - Asked to read the team's real file, it declined. Told to try anyway, the shell said "No such file", and the
     Read tool was refused by the deny rule.
   - Asked to edit the platform source, the Edit tool was refused and the shell got "Read-only file system". The
     file was unchanged.
3. **A photo came in through the reader.**
   - A fake-Drive photo went through the reader, the privacy step and the masked copies.
   - The first run left a village visible, because the reader named its columns `column_1`. Two fixes followed:
     - Idli now hides every text column of a reader's table by default;
     - the contract says to use the page's heading row.
   - Then the person (me) asked the Builder to use the headings. It changed the reader, re-tested, and saved a
     second version.
   - After that the masked copy had NAME_ and PLACE_ codes, with the P and A marks still readable.
4. **The Analyst answered from the photo table.**
   - It answered "how many absent on Tuesday in Ramtekdi?" correctly (1), using the team's photo skill.
   - The wire log has 0 real names or villages, and every request is labelled with the team.
5. **The Analyst offered the Builder.**
   - Asked to transcribe voice notes, it said the team can't do that yet, asked "open the Builder?", and on yes
     called `builder_open`.
   - Opening the tab failed only because the DGX has no Paseo. That is the laptop test.
6. **The Teams page,** in a headless browser at 1000 px dark and 380 px light:
   - the three outside answers ("Yes" was saved as `always`);
   - Versions listed all three checkpoints, and Go back removed the photo ability from the card.

**Two prompts were fixed along the way.** The DGX's Claude Code asks before reading outside the working folder.
The Builder's settings now allow reading the platform source and Claude's own scratch folder, so a person isn't
asked.

**On the laptop (same evening):**
- **The journey works end to end** on the owner's Insights team with a real image from the test Drive: card,
  Builder tab with its label, a reader built in about a minute, the image read into a table, the privacy review,
  the Analyst.
- **But Tesseract reads dense table screenshots badly.** Muse's server has vision on, so the private-model option
  is the next step. Details: `chronology/2026-11-16T2100-builder-analyst-model-types.md`.

**Not done yet:**
- Muse vision as a platform capability (a reader asks the platform; the platform calls Muse outside the sandbox);
- the Builder tab's title in Paseo (it shows "Claude Code");
- voice, video and PDF readers (on the menu, but not built by anyone yet);
- Muse vision (to verify).
