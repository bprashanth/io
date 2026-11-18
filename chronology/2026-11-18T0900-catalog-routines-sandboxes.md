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
