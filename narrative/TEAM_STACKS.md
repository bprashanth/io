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

## Results (2026-11-17, DGX)

**Method.**
- Two development requests (D1, D2) were used while building.
- The code was then frozen (commit `50a33a05`). Five held-out requests, written before any code
  (`benchmarks/runs/2026-11-17-team-stacks/requests.md`), each ran once through the real Builder, Claude Code in
  tmux. I played a non-technical person: plain answers, "do what you think is right", and yes to every install
  prompt.
- Every result was then checked on files the Builder never made: public recordings from Wikimedia Commons, or
  documents and forms I wrote.

| | Request | What the Builder chose | Install prompts | Build time | On real files |
|---|---|---|---|---|---|
| D1 | Cut silences and empty stage from event videos, no faces or voices | Silero VAD, YAMNet (speech vs music), EfficientDet-Lite0 (people by position) via LiteRT. A timeline reader plus a cut tool. "Save back to Drive" went to platform requests | 8 (most from my proxy bugs, fixed) | about 30 min with my bugs | 10 min of real conference video: the timeline matched the footage (it kept talks and cut the stage-wide transition and the music break). 14 s to read; cut 600 s to 479 s |
| D2 | Type out Hindi and Marathi voice notes into a table | faster-whisper large-v3-turbo, plus the 9B for the columns. Test voices from Piper | 1 | 5.5 min | Real recorded Hindi and Marathi speech: good transcripts with small spelling slips, and the topic and problems right. 45 to 57 s per 75 s note |
| H1 | A Hindi voice chatbot about our scheme | Whisper, the FAQ read from a .docx, the 9B answering only from the FAQ, Kokoro speaking. A practice **page**. Phone and WhatsApp went to platform requests | 2 | 8.8 min | My own FAQ: eligibility answered right, an off-topic question went to "staff will call back", a real recording got "please repeat". **One wrong fact** (June instead of July). The spoken reply round-trips through Whisper word for word. About 30 s per voice question |
| H2 | Translate the monthly report into Hindi and Marathi | IndicTrans2 first, but its weights need a Hugging Face login, so it used NLLB-200 (licence CC-BY-NC; the Builder said so). A .docx tool that keeps the layout | 1 | 6.5 min | My own report: the layout, the table and every number kept, 17 s. Three meaning slips a reviewer would catch ("tailoring" became "embroidery"; Marathi dropped "anaemia"; "households with water" became "household appliances") |
| H3 | Leads: email, then calendar, then hot or cold in the sheet | No install: the person's own rule (money, a date, or a known foundation) as a tool. Reading Gmail, creating Calendar events and writing to the Sheet went to 3 platform requests | 0 | 2 min | My own sheet of 6 leads: all marked by the rule, with a "Why" column, and an existing mark kept |
| H4 | Short Hindi-subtitled training clips for WhatsApp | faster-whisper (word timings), Noto Sans Devanagari, ffmpeg with burned-in subtitles. WhatsApp sending went to platform requests | 3 | about 15 min, plus 10 min to fix speed | A real 3:15 Hindi screencast tutorial. First run: no result after 22 min. With all 20 cores as threads, Whisper ran 25 times slower. Told "it's too slow", the Builder found the cause itself: now 150 s. The quick transcript (Whisper small) is rough. The clip tool re-transcribes the chosen part with a better model: a 28 s clip, readable burned-in Hindi subtitles, 0.6 MB, fits WhatsApp |
| H5 | Photos of handwritten Hindi survey forms into a spreadsheet | A Hindi OCR stack (ONNX), page straightening, tick-box ink measurement. It did not use the 9B's vision: my menu still said the private model couldn't read images | 2 | 9.5 min | My two photographed forms: 11 of 14 fields right. Every number and every tick right. Both names were partly wrong but flagged "check". One village line was missed, unflagged. The 9B's vision on the same photos: 13 of 14, 7.5 s each |

**Teammate install.** Event Media's definitions were cloned into a fresh team folder and installed from the locks
alone:
- 41 s;
- identical repo commits and download sha256;
- both tests pass;
- a byte-identical cut list for the same video.

**Attacks.**
- A lock with a wrong sha256 was refused.
- A setup step that tried example.com, pastebin.com, plain HTTP and a raw socket was refused on all four, with
  each host logged. It saw no home folders.
- The run wall had no network, no API keys and no write access to the stack, and could reach only the 9B's chat
  endpoint.

**Bugs the held-out runs found, fixed after the freeze (platform bugs, not tuning):**
- the page door kept a 10 s read timeout (voice questions died at 10 s);
- `team_save` committed the installed stack (up to 2.2 GB of models and package caches) into team git, and left a
  stale lock when git timed out;
- the capability menu said the private model can't read images, after the 9B got its vision;
- Whisper with every core as threads ran 25 times slower on the DGX's mixed cores. The wall now sets
  `IDLI_THREADS` and `OMP_NUM_THREADS`, and the skill says to use them.

**What the Builders did well, across requests:**
- one question at a time, about the work;
- plans in the person's words, with where each step runs;
- purpose-built models over home-made rules;
- licences and sizes stated up front;
- platform needs logged, never worked around;
- honest caveats ("check the names before printing", "tested only on a fake video").

**What still needs work:**
- **Readers pass their own fake-sample tests and can still fail on real files.** D2's first real file and H5's
  missed village line are examples. The p1 exit-test todo (the person judges the first real result) is the fix.
- **Speech to text on CPU is slow** (about 0.6 to 4 times real time). Whisper should probably be a platform
  private-model service on the GPU, like the 9B, with stacks calling it through a door.
- **The 9B's facts:** H1's wrong month came from the 9B, with the FAQ in front of it. An answer page should quote
  the FAQ line it used.
- **Tool outputs** (a marked leads sheet, a transcript) land in `outputs/`. They don't yet go through the privacy
  review to become masked copies the Analyst can use.
- **Not built:** the WSL2 image, the Mac VM, sharing the bundle through silo and joining a team, and the laptop run
  (its git fetch from the DGX hit a Tailscale browser check only the owner can pass).
