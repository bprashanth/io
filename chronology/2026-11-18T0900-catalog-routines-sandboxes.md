# 2026-11-17 to 2026-11-18: trusted catalog, routines through Google's APIs, then the Builder outside and sandboxes inside

Follows [2026-11-17T0200-team-stacks-overnight.md](2026-11-17T0200-team-stacks-overnight.md). Most of the grinding
was done by subagents; the results and their evidence are in the benchmark folders named below. All commits are
local on `oss-desktop-eval`. Only the `catalog-ci` branch was pushed (with declaude), for GitHub CI.

## 1. Where tools run, and the trusted catalog (2026-11-17)

- **Discussed** ([PAGES_AND_TOOLS.md](../narrative/PAGES_AND_TOOLS.md)):
  - pixi against Docker, and local Kubernetes (no);
  - WSL2 against a per-user DGX container (the io.idli.cc V1 gateway);
  - what Claude Code and Antigravity sandbox on Windows (Claude Code needs WSL2; Antigravity needs a 2026 Windows 11
    build with technology Microsoft doesn't yet call a boundary);
  - which test recipes need a wall: faces and voices, pickle weights, run-time downloads and pages do.
- **Owner's decision:** a server of vetted tools on silo. Plain pixi on every platform for the POC. Proper
  sandboxing later (p1 `sandboxing_later.md`, and a postscript in the 2026-09-15 sandboxing field note).
- **Built:**
  - the catalog on silo (`/idli/catalog/*` in the router, files on the Seagate), with 14 tools: Whisper small and
    turbo, Piper, Kokoro, NLLB (converted from pickle), Tesseract, RapidOCR, VAD, YAMNet ONNX, face blur, voice
    anonymise, office files, page server, ffmpeg;
  - client `lib/catalog.py` and `lib/toolhome.py`;
  - Builder tools `catalog`, `catalog_request` and `stack_install(tools=[ids])`, with the three steps (pick, check
    this computer, request what's missing).
- **Results** (`benchmarks/runs/2026-11-17-trusted-catalog/`):
  - DGX W1 to W10 all passed after 2 platform fixes;
  - laptop W1, W4 and W6 passed as a person;
  - GitHub CI was green on macOS 15, Windows and Linux after 2 fixes (UTF-8 on Windows; Whisper needs macOS 14).
- **Vetting finds:** ffmpeg's plain filter breaks Hindi subtitles, RapidOCR flips Devanagari, and the Hindi Piper
  voice is non-commercial.
- **A mistake:** while checking the catalog from the laptop, I printed silo's Access service token into my output
  and the laptop terminal. I cleared the scrollback and asked the owner to rotate the token.
- **Cleanup on the owner's word:**
  - all test teams and tools on both machines were removed;
  - the Installed tools page became one line ("Tools use X. Y free.");
  - deleting a team removes its tools, and orphans and the pixi cache are swept.

## 2. Builder journey with test accounts (2026-11-17 night)

- **Google blocks sign-in** in Paseo's embedded browser ("This browser or app may not be secure"). So the test
  accounts live in real Chrome profiles that Idli manages (`lib/chromeprofiles.py`, `lib/chromectl.py`):
  - 87profligate@gmail.com is "me", 88profligate@gmail.com is "a lead";
  - a per-team allowlist, confirmed by the person through a hook prompt;
  - the Builder's browser tools refuse any other profile.
- **A new team opened in one "Builder" chat** (since superseded, see 4).
- **Laptop rehearsal ("Leads Rehearsal"):** the Builder made the fake sheet and emails itself, learned
  Gmail and Calendar, built site tools, and booked Fri 20 Nov 2 pm on both test calendars. All 7 checks passed.
  `benchmarks/runs/2026-11-17-builder-journey/`.
- ReadCube appeared in a profile through Chrome sync; it wasn't from Idli.

## 3. Routines, then Google's APIs (2026-11-18)

- **The owner wants it reproducible.** A routine is a set of steps Idli runs: fetch, filter, judge (9B), act,
  approve, record. Built `lib/routines.py`, a Runs page, and Builder tools `routine_check`, `routine_config_set` and
  `routine_rehearse`.
- **First through Google's web pages** (`lib/google_web.py`): it needed 12 fixes for page quirks (draft saving, Save
  clicks, background tabs, stale searches), and each run took 60 to 80 s.
- **Owner's switch to OAuth:** Idli's own Desktop client in GCP project `bitrot-in`, published unverified (the
  person clicks Advanced, then Go to idli; 100-user cap; no weekly expiry).
  - `lib/google_api.py`: stdlib only, PKCE, consent in the account's Chrome profile, tokens per email in
    `~/.config/idlisseus/google-tokens/` (0600). It covers Sheets values, Gmail search, raw messages, reply drafts
    and an `Idli/handled` label, free/busy, and bookings with a fixed event id (never twice).
  - Each run now takes 1.4 to 9 s.
  - It passed end to end twice from a clean state, the second time with Book it on the Runs page.
  - One real bug: Gmail's mixed time zones, so dates are now compared in UTC.
  - `benchmarks/runs/2026-11-18-leads-routine/`.

## 4. The owner's redesign: the Builder outside, sandboxes inside (2026-11-18, in progress)

- **Model** ([UX.md](../narrative/UX.md), [ESCALATION_MODELS.md](../narrative/ESCALATION_MODELS.md),
  [SANDBOXES.md](../narrative/SANDBOXES.md)):
  - the Builder is an ordinary Claude Code project;
  - `/sandbox` asks the old Teams questions and maps the request to building blocks, or names the gap and refuses;
  - a sandbox (named like `merry-parrot-7ac1 leads`) is a Drivey-style split: Idli on the left with only its blocks,
    and Sandbox Claude (renamed from Analyst) on the right, with account content masked;
  - the person assembles the workflow step by step and saves it as a Mini;
  - Teams, the wizard and Installed tools are gone from Start here. Drivey is unchanged.
- **Escalation:** A for action workflows (Claude's script calls the 9B), B for insights (as Drivey), C later.
- **Laptop run so far** (`benchmarks/runs/2026-11-18-sandboxes/`, 28 screenshots):
  - the Drivey regression passes;
  - the Builder did an unrelated task;
  - the insights sandbox passes after fixes;
  - the leads sandbox: sheet, find the lead's email, draft three times, the 9B reads the pick, booked on both
    calendars;
  - the gap case (Instagram, plus scheduling) was refused with both gaps named;
  - the leads Mini then passed. Sandbox Claude wrote it with `nine_b` and `script_try`. Run from the left, it read
    10 replies and doubled nothing. Its transcript shows only codes, no real email or name;
  - the Drivey regression passed again at the end;
  - the full suite: 265 passed, 3 skipped.
- **Fixes:**
  - sandbox chats lost Drivey's routing;
  - the 9B didn't see the account tools;
  - account tool results were swallowed;
  - Minis were cut off at 60 s;
  - the Builder over-picked blocks for Drive questions.

  Three of the fixes run in the DGX router (restarted; Muse untouched).
- **Rough edges:**
  - the start card says "Ask about your Drive files" in a leads sandbox;
  - searching by a lead's name fails;
  - email times show in UTC;
  - the "+" button doesn't start a new question;
  - a sheet link is hard-coded in a Mini.

## Docs and todos written

- [PAGES_AND_TOOLS.md](../narrative/PAGES_AND_TOOLS.md), [BUILDER_JOURNEY.md](../narrative/BUILDER_JOURNEY.md),
  [ESCALATION_MODELS.md](../narrative/ESCALATION_MODELS.md), [UX.md](../narrative/UX.md), and ONGOING section 4.
- p1: `sandboxing_later.md`, `pixi_catalog_refinements.md`, `installation_backend.md`.
- p2: `agent_browser.md` (Chrome for Testing as Idli's own browser; parked).

## Still open

- Rotate silo's Access token (owner).
- Connect the person's real account, with "start from today".
- Redaction of account data at the same standard as files.
- What a Mini is for an action workflow, and how the person edits it.
- Where team stacks, the catalog and Chrome profiles sit in the sandbox model.
- Laptop `git fetch dgx` hits Tailscale re-authentication again. The laptop has two chunk-synced commits
  (`be7ffadc`, `92e0e058`) to reconcile on the next pull.
- Sandbox rough edges:
  - running chats and page servers keep old code until restarted;
  - a Mini card remembers a stale port;
  - New tab > Agent lacks the sandbox's Minis;
  - "Drivey" wording inside sandboxes.

## 5. Owner round: Builder first, folder insights, Minis to ask, activate and fork (2026-11-18, in progress)

Spec in [UX.md](../narrative/UX.md): "The Builder is Claude Code first", "Minis: ask, activate, fork", "Insights
details". Evidence in `benchmarks/runs/2026-11-18-builder-minis/`.

- **The laptop's git is back.** `git fetch` by the DGX's Tailscale IP works again. The two hand-synced commits had
  the same content as the DGX's; the laptop moved to the DGX head with `reset --keep` (branch
  `backup-before-dgx-reset-2026-11-18` kept). Code now reaches the laptop with `git pull`.
- **Builder (Paseo idli26, commit 8554b33d).** The owner's new Builder chat had opened on Idli 9B, and P15 (every
  Idli-provider chat gets a Claude pane) split it. Now:
  - a Builder chat is one pane, whatever its model; an old empty right pane closes itself;
  - the model menu in the Builder shows only Claude, with Opus 5.5 first. With no Claude Code, it shows Idli 9B
    and 30B;
  - Careful and Auto left the Idli menu everywhere (laptop config and `setup-laptop.py`);
  - the composer says "Build with public data here. For private data or your own accounts, type /sandbox.", and
    the Builder answers "hi" the same way.
  Checked on the laptop: shots 04 to 10.
- **Insights, the owner's attempt.** They first picked the sheet "Strategy classics" (lower-case c), then typed the
  folder "Strategy Classics", which failed: a folder from the @ picker comes without its trailing slash, and
  `drivestubs.fetch` only read folders ending in "/". Now a path that holds files is read as a folder, and Idli
  says which files it used and what it skipped. That folder has 18 PDFs and no spreadsheets, so on the laptop
  Idli now says: "Strategy Classics has 18 PDFs and no spreadsheets. Idli answers questions from spreadsheets.
  Reading these files is not a building block yet: ask the Builder for it." (shot 14). A folder with
  spreadsheets is covered by tests only: no Drive folder on the laptop holds spreadsheets, and I didn't add one to
  the account.
- **Privacy page.** The owner saw "Notes (blank) ->" with nothing after it: the first three cells were blank. The
  page now shows filled cells, and a hidden column of whole text cells (or nothing at all) reads "Notes entirely
  withheld" (shot 16). Long-running chats and page servers had to be restarted to pick this up (page servers on
  the same ports).
- **Minis: ask, activate, fork (code in 3db57720, deploying).**
  - `lib/minitalk.py`: anything typed while a saved action Mini is open goes to the new `mini_talk` tool. The 9B
    reads the Mini's steps and code and decides: explain (answers from the code), preview (Idli runs the Mini on
    the real accounts with `IDLI_PREVIEW=1`: reading as usual, drafts and bookings only collected and shown, never
    written), run, turn on or off, or change (points to Fork). Before this, the owner's three questions all got
    "This Mini can't answer that. Add files...".
  - Turn on: the Mini is bound to an account from today; its Gmail searches get `after:<today>`. Scheduling stays
    a gap and the reply says so.
  - Fork: a Fork button on the Mini card copies the scripts (values coded again) into Sandbox Claude's
    `forks/<id>/` with FORK.md, and types the prompt into Sandbox Claude on the right. `script_try` now runs in
    preview by default, and shows its real output in the left chat ("Run from Claude: <title>"); Claude still
    gets it masked. A fork's draft saves as a new Mini, never into the original.
  - Found while testing: opening an action Mini ran it once for real (an "example" run meant for chart Minis).
    Drafts and bookings are keyed, so nothing doubled, but opening must not act: fixed. Checks before saving a
    draft now run in preview too.
- **Laptop checks of the Minis.**
  - Opening the Mini shows the new line.
  - "How are leads picked? Which file?": the 9B named the sheet and the two-week window, but not the
    classification.
  - "Show me the draft you'd write": the preview ran and wrote nothing. It found no draft to write, because every
    reply was already handled.
  - 88 then sent a fresh "yes", but the laptop's reverse tunnel (49333 and 46767) dropped at about 16:42 IST.
    Turning the Mini on, Fork end to end, the draft shown in full and the final Drivey regression were not run on
    the laptop. Unit tests cover them.
  - The owner needs to run `desktop/laptop-up.sh start` on the laptop.
  - Results so far are in `benchmarks/runs/2026-11-18-builder-minis/README.md`.
- **Laptop back (owner ran `laptop-up.sh`).** (1) Full draft preview: the earlier ask had gone through just as the
  link dropped. "Show me the draft you'd write" for 88's fresh "yes" showed the whole reply draft (three times,
  Thu 19 Nov 1 PM, Fri 20 Nov 1:30 PM, Mon 23 Nov 12:30 PM) with "Nothing was drafted, booked or sent". 87's Drafts
  checked through the API: no draft for that thread. Pass (shot 19). The 9B's one-line summary above it came back
  empty ("Here is what it found.").
- (2) Turn on: "Activate this mini on my account" turned it on for 87profligate from today (18 Nov), and said that
  a schedule is not a building block yet. `mini.json` has `active: {role: me, since: 2026-11-18}`. The card now
  reads "On for 87profligate@gmail.com from 18 Nov." above the Fork button. Pass (shots 20, 21).
- (3) Fork, on the laptop:
  - Fork on the Lead replies card answered "Claude has your copy on the right". Sandbox Claude laid out the flow
    in 7 steps and asked how to change it (shot 22).
  - "First explain how leads are picked": it explained from the script, including two small issues it noticed
    (shot 23).
  - "Only look at replies from the last 2 days, then show me the results": it changed `DAYS_BACK` to 2 in its
    copy, then asked for `script_try` (preview), which I approved as the person (shot 24).
  - The real output landed on the left as "Run from Claude: Lead replies, last 2 days": 5 leads, the draft for 88's
    "Reading programme visit" in full, and "Nothing was drafted, booked or sent" (shot 25).
  - "Save it as a new Mini" put a draft card on the left, offered only as a new Mini, with no "Add to Lead replies"
    (shot 26). Save made `lead-replies-last-2-days-d6992c7c` with `DAYS_BACK = 2` and `forked_from` (shot 27).
  - The original still has `DAYS_BACK = 14`, an unchanged file (mtime from its save this morning), and it is still
    turned on for 87.
  - Gmail: no draft for "Reading programme" in 87's Drafts.
  - Masking: in this sandbox's transcripts, the real emails and names appear only in the left chat's (Idli's)
    records and in the morning run's Sandbox Claude session, where the person typed "Asha". None appear in the
    fork session's tool results.
  - Pass.
- (4) Drivey regression (last): a new Drivey question, the "Household debt by ward" Mini, then "which ward owes the
  most?". Answered by the Mini with the ward table (Yerawada first). Pass (shot 28).
- (5) Laptop suite (pytest through `uv run --with pytest`): 325 passed, 5 skipped, 11 failed. The 11 (10 in
  `lib/test_chat.py`, plus `test_launcher_config_and_proxy`) also fail at fe862842, before this round. They are not
  new.
- Not built: escalating a Mini question the 9B can't place, masked, to an outside model. It needs the per-question
  consent card that the "ask each time" setting promises, and this sandbox was made with the outside service off,
  so the laptop couldn't exercise it. Left as a rough edge.
- Gallery: http://100.82.28.38:8766/ (30 shots).

## 6. Transform blocks the Builder writes (2026-11-18)

The owner's drivecharts sandbox couldn't read 18 PDFs, and the Builder refused to add PDF reading: the "fixed list"
rule was written too strictly. Owner's decision: three levels.
- **Actions** (account writes, sending, posting): our team builds them; the Builder still refuses.
- **Transforms** (readers and transforms): the Builder writes them and adds them to a sandbox, existing ones too.
- **Pages and servers**: undecided (local or on silo).
No bwrap on Linux for now; every platform the same. The trust split: the Builder sees the trusted list and fake data,
never real data; Sandbox Claude sees masked data and only the blocks plugged in.

- **Phase 1, built (DGX):**
  - `lib/transforms.py`: the trusted imports baked into the build (stdlib transforms, pandas, numpy, openpyxl,
    pypdf, python-docx; silo's catalog may add `trusted_imports`); `scan` (AST: only trusted imports; no open, os,
    sys, subprocess, network, eval, private `_` parts, web addresses or outside paths); `check` (scan plus the
    block's fake-data test, about 0.1 s, once when added; the digest is kept and a run only compares it); `add`;
    `run` (downloads the @ Drive files once, runs the block in its own process, the 9B through a door on
    127.0.0.1 so silo's key stays in Idli).
  - `lib/transformkit.py`: the kit a block gets (files, remember, ask, judge, summarise_all two at a time and kept,
    answer, sample, fake_pdf for tests).
  - The example and first block, `idli/builder-outside/block-template/read_pdfs` (pypdf; first 10 pages plus three
    further in).
  - `block_run` in every sandbox (left chat and Sandbox Claude, masked for Claude); the left chat sends @ PDFs to it
    when the sandbox has a block that reads them, and follow-up questions too.
  - Builder: `block_kit`, `block_check`, `block_add`; one card from Idli's hook (`desktop/idli-block-consent.py`),
    which refuses a block that fails the check without asking.
  - Sandbox Claude's Mini scripts get the same scan in `script_try` and when a Mini is saved.
  - pypdf and python-docx join the build's venv (`setup-laptop.py`).
- **Timing on the DGX 9B** (6 text PDFs, some of 400 pages): 25 s the first time, 12 s for the next question.
  One summary is about 2 s with two at a time. 18 PDFs should take about 50 s the first time.
- Tests: `tests/test_transforms.py` (13). DGX suite: 338 passed, 5 skipped, the same 11 known failures.
- **Phase 2, on the laptop (as a person):**
  - Drivey first: the Household debt Mini answered "which ward owes the most?" with the ward table (shot 02).
  - Builder, a new chat: "can you add PDF reading to the drivecharts sandbox?". It called `block_kit`, said
    "Example fits as is; copying it", checked it and called `block_add`. The approval card came up 23 s after the
    question; added at 43 s (shots 05 to 07).
  - drivecharts, a new chat: `"Drive/My Drive/Strategy Classics" what are the main themes...`. The first run
    failed: one damaged PDF raised pypdf's PdfReadError and stopped the block. Fixed in the example (a bad page or
    file is skipped and named), and the person's error line went to the Builder, which fixed the block and added it
    again in 38 s (shots 10, 11).
  - Then the themes question answered in **63 s** the first time (18 PDFs downloaded, 17 read, one scan named,
    summaries two at a time, one answer naming the papers in brackets), and a follow-up ("which talk about CEO
    succession?") in **20 s** from the kept summaries (shots 12, 13).
  - Paseo's approval card shows the tool's input as JSON, so `block_add` now carries Idli's card text (checked by
    the hook and the tool) and the person reads "Add block: Read PDFs. Uses pypdf. Reads PDFs you give it. Sends
    nothing." in it. Paseo doesn't show the hook's own reason.
- **Phase 3, the rest on the laptop:**
  - Builder, "add a block that emails these summaries every Monday": refused (sending and a schedule are actions),
    request noted, drivecharts unchanged (shot 14). It had passed `read_pdfs` to `sandbox_create` as a "gap";
    fixed: a transform the Builder wrote is not a gap.
  - A block importing `requests` and calling a website: the Builder refused on its own. Pushed to add it, Idli's
    check listed the untrusted import and the web address (shots 15, 16). A failing block now gets no card.
  - Leads sandbox, a new chat: Lead replies previewed the full draft and wrote nothing (shot 18).
  - Sandbox Claude used `block_run` and got the answer masked (shot 19).
  - Drivey last: answered by the Mini (shot 20).
  - Suites: laptop and DGX 340 passed, 5 skipped, the same 11 known failures.
  - Docs: SANDBOXES.md "Three levels", UX.md, ONGOING 4. Gallery: http://100.82.28.38:8768/.

## 7. The chain for Mini questions: no free 9B (2026-11-18, in progress)

The owner's explorations in the leads sandbox gave random answers. Two finds:
- **The sheet link:** a sandbox chat with no Mini open sent "show my list of leads" to the 9B with its account tools,
  and the 9B made up a sheet link (`1BxiMVs0...`, Google's own sample sheet from its API docs) and got a 404. It
  never knew the leads sheet: only the Mini's script holds it.
- **"Here is what it found." with nothing under it:** in the Mini chat, "show me the list of leads" was sorted as a
  preview, the whole Mini ran, and the 9B's summary of its output came back empty, so the reply was only the lead
  line and the footer.

Owner's rules (built in phase 1, commit b46249da):
- The 9B answers a workflow Mini only where a question maps cleanly (explain, the whole preview, run, turn on, run
  step N). Anything else is mapped, not answered freely: to the Mini's named steps and the sandbox's read blocks (a
  sheet the Mini reads, a Gmail search, meetings between two days, free times). Writes are never on the menu.
- Who maps: the outside service (minisql's endpoint) with the person's consent (the card shows the masked question
  and the menu), or, on No or when the sandbox was made without it, the 9B with the same menu. Idli runs the choice
  on the real accounts in preview and shows its output as code wrote it.
- What can't be mapped ends at a Fork card: Claude gets a copy and the masked question.
- A sandbox question with no Mini open goes to Sandbox Claude, masked, to build it in steps (`blocks.run_steps`).
- PDFs that come with spreadsheets go to Claude too, as masked text (`lib/docmask.py`).
- New `blocks.meetings` (titles, guests, declined) under the calendar block.
- **Phase 2 on the laptop so far** (`benchmarks/runs/2026-11-18-mini-escalation/`): Drivey unchanged first (9 s);
  a blind "which meetings do I have this week?" went to Claude masked, which wrote a 3-step script, ran it
  through Idli (real meetings on the left) and saved "My meetings this week"; in Lead replies, "list of leads"
  (outside service, 9 s: the sheet's 5 rows), "meetings yesterday" (the calendar), "which emails are new" (No: the
  9B mapped it to an email search, 18 s), "the draft for Asha" (the whole preview, 44 s), "step 2" (no steps:
  Fork card) all worked. The fork made "Lead replies in steps" (6 named steps, calendar notices skipped).
  The merry-parrot sandbox's outside setting was changed from Never to Ask for this test.
- **More on the laptop:** "Lead replies in steps" ran step 1 (5 leads, 3 s) and step 3 (the 9B's reading of 10
  replies, 71 s) on their own; "which leads agreed but have not picked a time?" was mapped by the outside service to
  step 4 (the full draft shown, 94 s). "Post each booked meeting to Instagram" ended at the Fork card; in the fork,
  Sandbox Claude said only the Builder can add an Instagram block, but it then opened the old per-team Builder beside
  itself (a Teams leftover). Interrupted before it wrote anything; fixed: no `builder_open` for Sandbox Claude in a
  sandbox. Opening a workflow Mini now says what it can see and lists its steps.
- **Left:** the insights folder (public NDSA 2021 Fixity Survey: report PDF and data CSV, CC BY 4.0; the Dryad set
  needs a login now), adding the 2025 data and extending the charts as a new Mini, Drivey last, README, gallery,
  docs, suites.
- **The laptop link dropped at about 21:45 IST** (Paseo daemon tunnel and CDP refused), before the insights round
  and the final Drivey check. The owner needs to run `desktop/laptop-up.sh start` again.
- **PDF masking on the DGX** (NDSA 2021 Fixity Survey report, public, CC BY 4.0; the Dryad set the owner named needs
  a login now): whole pages through the name scanner left all 11 cover authors; line by line, in parallel, they were
  coded. 53 s for the first 150,000 characters, kept per file version (ed3d7708).
- **Docs:** SANDBOXES "Routing in a sandbox" (replaces the free-9B routing), ESCALATION_MODELS "The chain", UX,
  ONGOING section 4. README with 16 steps and shots in `benchmarks/runs/2026-11-18-mini-escalation/`. DGX suite:
  355 passed, 5 skipped, the 11 known failures.
- **Finished after the owner reopened the laptop (23:00 to 23:55):** the NDSA 2021 report and data went into a
  folder in 87's Drive; "help me analyse this study" sent the CSV through the privacy review and the PDF as masked
  text (the cover's 11 authors coded). One bug: the PDF note was lost after the review (fixed, c4225579). Claude
  made two charts and the Mini "Fixity checks 2021"; adding the 2025 data and report with that Mini open went to
  Claude with the Mini as context (6dbab66e), which drew 2021 vs 2025 and saved "Fixity checks 2021 and 2025" as a
  new Mini; the first is unchanged. Drivey last: unchanged. Laptop suite: 356 passed, 5 skipped, the 11 known.
  Round complete; README and gallery in `benchmarks/runs/2026-11-18-mini-escalation/`.
