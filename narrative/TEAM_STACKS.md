# Team stacks: a team brings its own tools

2026-11-17. Asked by the owner on 2026-11-16 ("enable such free-wheeling innovation rather than get in the way, but
in an easy manner that is not insecure"). Built and tested overnight on the DGX. The wider picture is in
[IDLI_DESKTOP.md](IDLI_DESKTOP.md), and the four model types are in [MODEL_TYPES.md](MODEL_TYPES.md).

## The idea in one paragraph

**The platform owns the models, masking, consent, logins and the wall. A team owns a locked stack of open-source
tools that runs inside that wall.** When someone makes a team, they answer Idli's fixed questions (privacy, the
outside service, who uses it), and then talk to the team's **Builder** about the work itself. The Builder plans in
plain words, picks tools from conda-forge, PyPI, GitHub and Hugging Face, and builds the team's readers, tools and
pages. Idli installs those tools only after the person says yes, pins every version, and runs them with no
internet. Teammates install exactly the same lock, so they get the author's workflow.

We don't cherry-pick tools into the platform any more. We decide only the models, the ways models work together,
and the walls. The team decides the rest.

## The journey

1. **Teams > New team.** The same question cards as before (name, goal, where the data is, who uses it, private
   fields, the outside service). The plan card adds: "Next, the Builder asks about your work and sets up the team
   with you."
2. **Set it up** makes the team, opens its first workspace, and starts the Builder on the right with the answers
   as its first message (`builder.setup_prompt`; the goal is the person's own words, so it is masked). The answers
   are the platform's promises: the Builder can't loosen them.
3. **The Builder talks** (the `setup-team` skill): one question at a time, about the work, not about technology.
   "What's the one task you'd most like help with?" "Walk me through the last time you did it."
4. **The plan,** one line per step: what happens, and where. The places are "on this computer", "the private model
   on this computer", "Claude, with names as codes", or "needs a platform feature". Anything new from the internet
   is named, with its size. Then "Shall I set this up?"
5. **The install prompt.** When the Builder calls `stack_install`, Claude Code shows the person a yes/no prompt.
   Idli writes the text from the stack files (a PreToolUse hook), so the Builder can't word it:
   ```
   Install for this team?
   For: Make a timeline of event videos (is someone speaking, is music playing, are people on stage) ...
   Packages: ffmpeg, numpy, onnxruntime, ai-edge-litert
   Download: huggingface.co/.../model.onnx
   Download: storage.googleapis.com/.../yamnet.tflite
   Also allowed while installing: storage.googleapis.com
   These install inside the team folder only. They run on this computer without internet and see only the files
   you pick.
   ```
   It asks again only when something new is added. Retrying with other versions of the same packages doesn't ask.
6. **Build and test** on fake samples (`stack_run`, `team_check`), save a version (`team_save`), and tell the person
   how to try it. Anything that needs the platform (reading Gmail, sending WhatsApp, writing to a Google Sheet)
   goes to `platform_request` and to the "Waiting for the platform" list in the team's `TEAM.md`.

## What a team can now have

| Kind | What it is | Who uses it | Example from tonight |
|---|---|---|---|
| reader | A kind of file turned into tables. The person reviews them, and the Analyst gets masked copies | The left chat (with @), then the Analyst | A video's timeline: speech, music, people on stage, by second |
| tool | Work done on the original files, writing new files to the team's `outputs/` | The Analyst, with `team_run`, after deciding from masked tables | Cut a video at the Analyst's timestamps; translate a report |
| app | A page the person uses in a browser tab, served from the stack | The person; the Analyst opens it with `app_open` | A Hindi voice chatbot practice page |
| skill | Instructions for the Analyst | The Analyst | How to read a video timeline |

A reader, tool or app with `"stack": true` runs with the stack's own Python and packages.

**The pattern for media,** from the owner's marketing example: the reader turns sensitive media into signals with no
faces, voices or words in them. Claude reasons over the signals, and a tool executes the decision on the original,
on this computer. Masking for spreadsheets is the same idea.

## The stack, on disk

```
<team>/extensions/stack/
  pixi.toml          packages (conda-forge first, PyPI when needed) and tasks, for linux-64 and linux-aarch64
  pixi.lock          every package pinned (written at the first install)
  stack.json         GitHub repos (at a tag or commit), downloads, extra hosts, private model use, a setup task
  stack-lock.json    each repo's commit and each download's sha256 (written at the first install)
  tools/             the Builder's code that uses the stack
  .pixi/ repos/ models/ .cache/    what got installed (not in git)
```

The definition is in the team's git, with Versions and Go back as before. What got installed is not, and can be
rebuilt from the locks.

## The walls (lib/stackwall.py)

Both are bubblewrap with the whole filesystem read-only, `/home`, `/root`, `/mnt`, `/media` and `/run/user` hidden,
an empty environment (no API keys or tokens from the person's session), and no network namespace of their own.

| | Install wall | Run wall |
|---|---|---|
| Network | One door: a bridge to Idli's egress proxy. HTTPS only (CONNECT to port 443), only to conda-forge, prefix.dev, PyPI, the PyTorch index, GitHub and Hugging Face, plus hosts the person saw on the prompt. Every host asked for is logged | None. With `"model": true`, one door to the private model's `/v1/chat/completions` (and `/v1/models`), nothing else on that server |
| Writable | The stack folder | One output folder (and a scratch `/tmp`) |
| Readable | System files, pixi | The stack (read-only), the input files, the platform's `lib/` |
| Runs | git clone and checkout (pinned), curl (sha256-pinned), `pixi install`, the `setup` task | A reader, a tool, a test, or a page |

A **page** (app) gets one more door, inwards: the person's browser reaches `127.0.0.1:<port>`, which goes through a
unix socket to the page inside the wall. The page can't open any connection out.

The Builder never runs pip, conda or curl itself. Its own Claude Code sandbox keeps it out of the team's data, as
before. Its settings (`.claude/`), the installed stack and `stack-lock.json` are denied to its Edit tool. The
install hook lives in a settings file outside `extensions/` (`<team>/.idli/builder-settings.json`), and so does the
record of what the person agreed to (`.idli/stack-consent.json`).

## Mac, Windows and Linux

Stacks are Linux, everywhere:
- **Linux:** native, as tested tonight.
- **Windows:** WSL2 with a small Linux image Idli ships and imports itself (`wsl --import`). No Docker Desktop. It
  needs one admin step and maybe a reboot, once, at Idli install. CUDA works inside WSL2.
- **macOS:** a light Linux VM (Lima, or Apple's container tool on recent macOS). There is no Apple GPU inside the
  VM, so stack models run on CPU. That is fine for the sizes the Builder picked tonight (VAD, YAMNet, Whisper
  turbo, NLLB 600M, Kokoro).
- **Models stay outside the stack,** native on the platform with the GPU. A stack reaches the private model
  through its door.

Every stack lists both `linux-64` and `linux-aarch64`, so pixi solves for laptops (x86) and Apple Silicon VMs (ARM)
at the first install. Tonight that caught a real problem: MediaPipe has no ARM Linux build, and the Builder switched
to LiteRT.

**Not built yet:** the WSL2 image and the Mac VM. Everything tonight ran on the DGX (Linux, ARM).

## Teammates

The locks are the bundle: `pixi.toml` + `pixi.lock` + `stack.json` + `stack-lock.json` + the team's extensions git.
A teammate's install uses the same files, checks every repo commit and download sha256 against the lock, and fails
rather than install something different. Their own install prompt shows the same summary. **Not built yet:**
sharing the bundle through silo and the "join a team" flow.

## Results

(Filled in below after the overnight runs.)
