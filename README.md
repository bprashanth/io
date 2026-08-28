# io (pronounced: aiyo)

<img src="assets/io.jpg" alt="Jupiter and Io" width="360" align="left" style="margin-right: 15px; margin-bottom: 10px;">

This repository is working toward an event experience more than a specific
product. At the event, users (typically someone from the social sector, eg
working at a NPO) will point some AI at a directory containing data files like
CSVs/workbooks, PDFs/chat dumps and ask a few plain-language question. The goal
of this event it to show them how to get a correct desktop dashboard which they
can refine without debugging an agent or installing a new stack.

Two prototypes in this repo: a privacy plugin for Antigravity and the
io desktop app. Depending on user feedback, the io app can grow. The
Antigravity plugin is more for illustrative purposes as we don't control the
settings it relies on. 

## Quick start

Install Antigravity first, then the io app.

**Antigravity install:**
[macOS](installation/ANTIGRAVITY-mac.md) -
[Windows](installation/ANTIGRAVITY-windows.md) -
[Linux](installation/ANTIGRAVITY-linux.md)

The plugin is pinned to Antigravity **1.107.0** (released as 1.23.2). A newer version will
not match it, so each page also says how to stop it updating itself.

First time you open Antigravity it asks a few setup questions. The important ones are here:
[installation screenshots](installation/ANTIGRAVITY-first-run.md).

**NOTE**: if you want to turn off permission requests for the term of this session, you can find the setting that say "Auto Execute" and "Review Policy" and set them to "Always Proceed". You can always turn this back to "Request Review" later. These settings are found in the bottom right corner of antigravity. 

**A. io, the desktop app**

Find your machine > download > unzip > click/double-click.

| your machine | download |
|---|---|
| Windows | [io-win-x64-offline.zip](https://github.com/bprashanth/io/releases/latest) |
| macOS (Apple Silicon) | [io-mac-arm64-offline.dmg](https://github.com/bprashanth/io/releases/latest) |
| Linux | [io-linux-x64-offline.tar.gz](https://github.com/bprashanth/io/releases/latest) |

These packs carry everything needed to run the app inside them.

[macOS](installation/INSTALL-mac.md) -
[Windows](installation/INSTALL-windows.md) -
[Linux](installation/INSTALL-linux.md)

1. Start io.
2. Give it an API key or a server address; it is kept in memory only. Ask the
   organizers for this. 
3. Add a local dir, review the highlights, the "Preview" button shows
   the tokenized versions of data that leaves your laptop. 
4. Cheat sheet; use `@` while you chat to address specific files, and `~name~` looks up a person (or any pii) in the vault and redacts it from your request. 

Details and flow: [`app/io/README.md`](app/io/README.md).

**B. The privacy shield in Antigravity (optional, linux only)**

1. Extensions view (the 4 small boxes on the left panel), "Install from VSIX",
   pick `extension/privacy-shield-0.3.0.vsix`.
2. Command palette (ctrl/cmd + shift + p), `Privacy Shield: Enable`. First time
   it offers a one-time install (about 500 MB download, 1.7 GB disk install,
needs python3 on the machine) and asks for one relaunch.
3. The status bar shows `N calls - X ms - vault M`. The status page has the
   audit: bytes and rough tokens out, what was hidden, the exact last request
that left.
4. Anything wrong or uninstalling:
   [`extension/privacy-shield/TROUBLESHOOTING.md`](extension/privacy-shield/TROUBLESHOOTING.md).

## Developers: Repository map

If you're only here to use the product, ignore this..

- `docs/` contains architecture decisions, implementation findings and
  operational runbooks. Start with the current event decision above.
- `benchmarks/` contains frozen cases, scripts, raw run evidence and derived
  aggregates. Read [`benchmarks/DESIGN.md`](benchmarks/DESIGN.md) before adding
  cases or changing a scorer.
- `chronology/` is the append-only, timestamped experiment trail. It explains
  what happened in order, including failed and excluded runs.
- `narrative/` turns the chronology and evidence into readable field notes.
- `checkpoint/` is a local, gitignored handoff for the next agent. On this
  machine, read `checkpoint/CHECKPOINT.md` after this README. If it is absent,
  reconstruct the state from the current decision, chronology and aggregate.
- `proposals/` contains forward-looking ideas. A proposal is not measured
  evidence or a current decision. The current demo plan is in [demo_and_flow](proposals/demo_and_flow.md)

## Developers: Working here

Reverify a suspicious claim against its raw run before replacing the current
winner. Do not tune routing, extraction or validation to sector names or to the
answer bank. Extend through general table shapes, operators, provenance rules
and observable failures. Keep development, diagnostic, counted and holdout
runs labelled separately.

Every reportable experiment should retain its exact inputs and questions,
model and settings, selected SQL or plan, deterministic checks, browser output,
screenshot, timing and cost. Append a chronology entry as the work progresses;
update a narrative only when there is a coherent new result.
