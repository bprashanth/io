# Prototypes for io

<p align="center">
  <img src="assets/io.jpg" alt="Jupiter and Io" width="360">
</p>

This repository is working toward one practical event experience: user
(typically someone from the social sector, eg working at a NPO) drops in a
CSV/workbook or PDF/chat dump, asks a few short plain-language question (no
engineering hints, coding etc) and gets a correct desktop dashboard which they
can refine without debugging an agent or installing a new stack for every file.

The current guide is [the demo plan](proposals/demo_and_flow.md). Everything
built and measured on the way is in `chronology/` (append-only, timestamped);
the stage ledger in [`docs/stages/`](docs/stages/README.md) is the short
version. Two things ship from here: the privacy shield plugin for Antigravity
(a shield for the common Antigravity user) and the io desktop app (for the
serious privacy user: scan on the laptop, send tokenized values).

## Quick start

Install Antigravity first. The plugin is pinned to Antigravity **1.107.0**
(`antigravity --version`; that's the build version, which is released as 1.23.2
[here](https://antigravity.google/releases) ).

*Debian/Ubuntu x86 (apt):*

If an older copy was ever installed, `sudo apt purge antigravity` first.
```
sudo install -m 0755 -d /etc/apt/keyrings
curl -s https://us-central1-apt.pkg.dev/doc/repo-signing-key.gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/antigravity-repo-key.gpg
echo "deb [signed-by=/etc/apt/keyrings/antigravity-repo-key.gpg] https://us-central1-apt.pkg.dev/projects/antigravity-auto-updater-dev/ antigravity-debian main" \
  | sudo tee /etc/apt/sources.list.d/antigravity.list
sudo apt update && sudo apt install -y antigravity=1.23.2-1776332190
sudo apt-mark hold antigravity     # pin until after the event
antigravity --version              # must print 1.107.0
```

*No-apt / ARM fallback (tarball):* download
[x86](https://edgedl.me.gvt1.com/edgedl/release2/j0qc3/antigravity/stable/1.23.2-4781536860569600/linux-x64/Antigravity.tar.gz)
or
[ARM](https://edgedl.me.gvt1.com/edgedl/release2/j0qc3/antigravity/stable/1.23.2-4781536860569600/linux-arm/Antigravity.tar.gz),
then:

```
cd ~/Downloads                      # or wherever the tarball is
tar -xvzf Antigravity*.tar.gz       # filename case varies
sudo rm -rf /opt/antigravity        # nuke any old copy
sudo mv Antigravity /opt/antigravity   # the extracted app dir (holds bin/, resources/)
sudo ln -sf /opt/antigravity/bin/antigravity /usr/local/bin/antigravity
antigravity --version               # must print 1.107.0
```

**A. The privacy shield in Antigravity**

1. Extensions view, "Install from VSIX", pick
   `extension/privacy-shield-0.3.0.vsix`.
2. Command palette, `Privacy Shield: Enable`. First time it offers a one-time
   install (about 500 MB download, 1.7 GB disk install, needs python3 on the machine)
   and asks for one relaunch.
3. The status bar shows `N calls - X ms - vault M`. The status page has the
   audit: bytes and rough tokens out, what was hidden, the exact last request
   that left.
4. Anything wrong, or uninstalling:
   [`extension/privacy-shield/TROUBLESHOOTING.md`](extension/privacy-shield/TROUBLESHOOTING.md).

**B. io, the desktop app**

1. `cd app/io && ./install.sh` (Windows: `install.ps1`). One time: makes its
   own venv and caches the scanner model.
2. Double-click `run.sh` (or `npm start`). Give it an API key or a server
   address; it is kept in memory only.
3. Add a sheltered dir, review the highlights (click to keep), Preview shows
   exactly what leaves, then ask. `@` picks files, `~name~` looks up a person
   without typing the full name, built pages get "share on your network".

Details and flow: [`app/io/README.md`](app/io/README.md).

## Repository map

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
  evidence or a current decision.

## Working here

Reverify a suspicious claim against its raw run before replacing the current
winner. Do not tune routing, extraction or validation to sector names or to the
answer bank. Extend through general table shapes, operators, provenance rules
and observable failures. Keep development, diagnostic, counted and holdout
runs labelled separately.

Every reportable experiment should retain its exact inputs and questions,
model and settings, selected SQL or plan, deterministic checks, browser output,
screenshot, timing and cost. Append a chronology entry as the work progresses;
update a narrative only when there is a coherent new result.
