# io (pronounced: aiyo)

<img src="assets/io.jpg" alt="Jupiter and Io" width="360" align="left" style="margin-right: 15px; margin-bottom: 10px;">

This repository is working toward an event experience more than a specific
product. At the event, users (typically someone from the social sector, eg
working at a NPO) will point some AI at a directory containing data files like
CSVs/workbooks, PDFs/chat dumps and ask a few plain-language question. The goal
of this event it to show them how to get a correct desktop dashboard which they
can refine without debugging an agent or installing a new stack.

Two things can ship out of this repo: a privacy plugin for Antigravity and the
io desktop app. Depending on user feedback, the io app can grow. The
Antigravity plugin is more of illustrative purposes as we don't control the
settings it relies on and they seem to be buried in the documentation. 

## Quick start

Install Antigravity first. The plugin is pinned to Antigravity **1.107.0**
(`antigravity --version`; that's the build version, which is released as 1.23.2
[here](https://antigravity.google/releases) ).

*Debian/Ubuntu x86 (apt):*

**IMPORTANT**:  `sudo apt purge antigravity` first if the output of `antigravity --version` is not `1.107.0`. 
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


**NOTE**: you only need this OR the apt install above, NOT both.  
```
cd ~/Downloads                      # or wherever the tarball is
tar -xvzf Antigravity*.tar.gz       # filename case varies
sudo rm -rf /opt/antigravity        # nuke any old copy
sudo mv Antigravity /opt/antigravity   # the extracted app dir (holds bin/, resources/)
sudo ln -sf /opt/antigravity/bin/antigravity /usr/local/bin/antigravity
antigravity --version               # must print 1.107.0
```

**NOTE**: if you want to turn off permission requests for the term of this session, you can find the setting that say "Auto Execute" and "Review Policy" and set them to "Always Proceed". You can always turn this back to "Request Review" later. These settings are found in the bottom right corner of antigravity. 

**A. The privacy shield in Antigravity**

1. Extensions view (the 4 small boxes on the left panel), "Install from VSIX",
   pick `extension/privacy-shield-0.3.0.vsix`.
2. Command palette (ctrl/cmd + shift + p), `Privacy Shield: Enable`. First time
   it offers a one-time install (about 500 MB download, 1.7 GB disk install,
needs python3 on the machine) and asks for one relaunch.
3. The status bar shows `N calls - X ms - vault M`. The status page has the
   audit: bytes and rough tokens out, what was hidden, the exact last request
that left.
4. Anything wrong, or uninstalling:
   [`extension/privacy-shield/TROUBLESHOOTING.md`](extension/privacy-shield/TROUBLESHOOTING.md).

**B. io, the desktop app**

1. `cd app/io && ./install.sh` (~Windows: `install.ps1`~ currently doesn't work). One time: makes its
   own venv and caches the scanner model.
2. Double-click `run.sh` (or `npm start`). Give it an API key or a server
   address; it is kept in memory only. Ask the organizers for this. 
3. Add a sheltered dir, review the highlights, the "Preview" button shows
   exactly what leaves, then ask. 
4. Cheat sheet; use `@` while you chat to address specific files, and `~name~` looks up a person (or any pii) in the vault and redacts it from your request. 

Details and flow: [`app/io/README.md`](app/io/README.md).

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
