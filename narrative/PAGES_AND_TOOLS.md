# Pages and tools: where a team's own software runs

A living note. It holds what we decide about running a team's own tools and pages (the team stacks of
[TEAM_STACKS.md](TEAM_STACKS.md)), and why. Update it as the discussion moves.

Started 2026-11-17.

## What exists today (Linux, tested on the DGX and the laptop)

A team's Builder can add three kinds of software. All of them run inside Idli's wall:
- **reader:** turns a file into tables or text for the privacy review;
- **tool:** works on the originals and writes files to `<team>/outputs/`. The Analyst calls it with `team_run`;
- **page (app):** a small web page the person opens with `app_open`, for example the voice chatbot.

Two pieces do the work:
- **pixi** installs the software;
- **bubblewrap (bwrap)** walls it in.

### pixi: what gets installed

- The definition is `<team>/extensions/stack/` and lives in the team's git:
  - `pixi.toml` lists packages from conda-forge (native builds like ffmpeg, tesseract and whisper.cpp) and PyPI;
  - `stack.json` lists GitHub repos at a tag or commit, sha256-pinned downloads, extra hosts and a setup task.
- The locks are `pixi.lock` (every package, for linux-64 and linux-aarch64) and `stack-lock.json` (repo commits,
  download hashes).
- A teammate installs from the locks and gets the same stack, or a failure. It never gets something different. On
  the DGX that took 41 s, with identical output.
- pixi is one binary in `~/idli-insights/platform/bin`. It needs no admin, no daemon and no licence.

### bwrap: what the software can reach

| | Install wall | Run wall |
|---|---|---|
| Network | Only Idli's egress proxy: HTTPS to package and code hosts, plus hosts the person agreed to. Every host is logged | None. Optionally one door to the private 9B (JSON chat only, forced to `idli-9b`, so it can't reach Muse) |
| Writes | The stack folder | One output folder and a scratch `/tmp` |
| Sees | System files and pixi | The stack (read-only), the input files, Idli's `lib/` |

Everywhere, home folders, `/mnt`, `/media` and `/run/user` are hidden, and the environment is empty, so no keys or
tokens leak in.

A page gets one inward door. The browser reaches `127.0.0.1:<port>`, which goes through a unix socket to the page
inside the wall. The page itself can't connect out.

### Consent

The Builder never installs anything itself. It calls `stack_install`. A hook outside the Builder's reach makes
Claude Code ask the person, with a summary Idli writes, which starts with "Adds: …". Idli asks again only when
something new is added.

## The recipes the Builders made (2026-11-17 test runs)

Each row is one team's stack, built by the real Builder from a plain request. Results are in
[TEAM_STACKS.md](TEAM_STACKS.md), "Results". "Installed" is the size on the DGX, packages plus models.

| Team | Request | Packages (pixi) | Models and downloads | Private model | Kind | Installed |
|---|---|---|---|---|---|---|
| event-media (D1) | Cut silences and empty stage from event videos, without recognising anyone | ffmpeg, numpy, onnxruntime 1.19.2, ai-edge-litert 1.2.0 (LiteRT), piper-tts (only for fake test speech) | Silero VAD (speech), YAMNet (speech or music), EfficientDet-Lite0 (people by position), a Piper voice. All sha256-pinned, from Hugging Face and storage.googleapis.com | No | Reader (timeline) plus tool (cut) | 1.0 GB + 0.1 GB |
| field-notes (D2) | Type out Hindi and Marathi voice notes into a table | ffmpeg, faster-whisper, piper-tts | Whisper large-v3-turbo, a Hindi Piper voice for test notes | Yes, to fill the table's columns | Reader | 1.0 GB + 1.6 GB |
| helpline (H1) | A Hindi voice chatbot about our scheme | numpy, faster-whisper 1.1.1, kokoro-onnx 0.4.7 | Whisper, Kokoro TTS (from its GitHub release) | Yes, answers only from the FAQ | **Page**, on 127.0.0.1 | 0.6 GB + 1.9 GB |
| comms (H2) | Translate the monthly report into Hindi and Marathi | pytorch-cpu, transformers, sentencepiece, python-docx | NLLB-200 distilled 600M (CC-BY-NC, non-commercial; IndicTrans2 needed a Hugging Face login). Its weights are `pytorch_model.bin`, a pickle file | No | Tool (.docx in, .docx out) | 1.1 GB + 2.4 GB |
| leads (H3) | Email, then calendar, then hot or cold in the sheet | None | None | No | Tool (the person's own rule). Gmail, Calendar and Sheet writes went to platform requests | 0 |
| training (H4) | Short Hindi-subtitled training clips for WhatsApp | ffmpeg (libass for burned-in subtitles), faster-whisper 1.1.1, piper-tts | Whisper small (quick pass) and large-v3-turbo (the chosen clip), Noto Sans Devanagari | No | Reader plus tool | 1.0 GB + 2.1 GB |
| survey (H5) | Photos of handwritten Hindi survey forms into a spreadsheet | RapidOCR 3.x, onnxruntime, OpenCV, pyclipper, shapely and helpers | RapidOCR's Hindi models, fetched on first use from modelscope.cn (extra hosts the person agreed to) | No (the 9B's vision did better: 13 of 14 fields against 11) | Reader | 1.5 GB |
| field-media (laptop) | Screenshots of tables in Drive into spreadsheets | tesseract, img2table, OnnxTR, onnxruntime, opencv-contrib, pandas, openpyxl | OnnxTR's text models (the second reader, so two readers must agree) | No | Reader | 1.8 GB |

**Common shapes:**
- Speech: faster-whisper. Speaking: Piper or Kokoro. Video and audio cutting: ffmpeg.
- OCR: Tesseract, RapidOCR or OnnxTR, or the 9B's vision.
- Translation: NLLB.
- Anything needing judgement: the 9B through the model door.
- Every stack is Python 3.11 from conda-forge, with PyPI only where conda-forge lacks a package. None used a
  GitHub repo checkout: GitHub was used only for release downloads.
- Most installs are 1 to 4 GB, mostly models.

### Would these run without Linux? (solved 2026-11-17)

Each stack's `pixi.toml` was solved for `win-64` and `osx-arm64` (`pixi lock`, solve only, nothing installed or
run):
- **11 of 12 solve.**
- The one failure is event-media on Windows: `ai-edge-litert==1.2.0 has no wheels with a matching platform`.
  LiteRT has no Windows build. The Builder already swapped MediaPipe for LiteRT once, when MediaPipe had no ARM
  Linux build, so it could swap again (for example, YAMNet and EfficientDet through onnxruntime).
- field-media (laptop) was not solved for Windows or Mac.

**So the packages are mostly not the reason for Linux. The wall is.** A solve doesn't prove a stack runs: native
DLLs and paths on Windows are still untested.

## How much isolation each recipe needs (discussed 2026-11-17)

**The setting:** a laptop on ordinary home or office wifi. Other devices are on the same network, the internet is
reachable, and nothing else protects the laptop. Run without a wall, a tool runs as the person:
- it can read every file, including browser sign-ins, SSH keys, Idli's private folder and the unmasked originals;
- it can reach the internet and every device on the wifi;
- install scripts run as the person too.

Three things decide how much wall a recipe needs:
- **what the code loads:** a binary package, a pickle file, or a download at run time;
- **what data it touches:** faces, voices, names;
- **whether it listens:** a page or server.

| Recipe | Browser only (StackBlitz-style) | Plain pixi, no wall, OK? | Needs a wall (bwrap; so WSL2 or a VM, or the DGX, off Linux) | Needs Docker |
|---|---|---|---|---|
| leads rule (H3) | Yes. A few lines of rules, and it could be JavaScript | **Yes.** No packages, no downloads, no listening | No | No |
| field-media OCR (laptop) | Partly. tesseract.js exists, but img2table and OnnxTR don't run in a browser | **Mostly.** Well-known binary packages, no network once the models are in. The risk left is the Builder's own code reading files it shouldn't | Better with one: the inputs are screenshots of reports | No |
| survey OCR (H5) | Partly (tesseract.js, onnxruntime-web). Not RapidOCR as built | No. It downloads models from modelscope.cn on first use, a host most people wouldn't know. Inside the wall that fails closed, outside it happens silently | **Yes**, for the downloads and because forms carry names | No |
| translation (H2) | Possible in principle (NLLB has a transformers.js port). 600M in a browser tab is heavy | **No.** NLLB's weights are a pickle file (`pytorch_model.bin`), and loading a pickle can run code | **Yes** | No |
| voice notes (D2), training clips (H4) | Possible in principle (Whisper in transformers.js or whisper.cpp WASM), but very slow on long audio, and big files in a tab | Packages are fine. But faster-whisper fetches weights from Hugging Face by default, and the audio is real people's voices | **Yes**, so "nothing leaves this computer" is enforced, not promised | No |
| event videos (D1) | No. Gigabytes of video, plus ffmpeg.wasm on CPU | Packages are fine (Linux and Mac). The video shows real faces | **Yes**, same reason as voices. On Windows it also needs Linux, because LiteRT has no Windows build | No |
| helpline page (H1) | The page, yes. Its speech parts are heavy (see voice notes) | **No.** It's a server. It's on 127.0.0.1 only because the Builder was told to. One wrong address (0.0.0.0) would put it on the wifi for anyone. It also talks to the 9B. Outside the wall it could use the person's sign-in to reach anything on silo | **Yes.** The wall's inward door keeps it local, and the model door limits it to the 9B's chat | No |

**What this says:**
1. **No recipe needed Docker.** Every one installed from conda-forge and PyPI under pixi. Docker would only be
   needed for a project shipped as `docker compose`, and none of these were.
2. **None runs in StackBlitz as built.** WebContainers run Node in the browser, not conda or native Python. Only the
   rule (H3) and the page's front end would move to a browser easily. Browser ports exist for the models (Whisper,
   NLLB, OCR, Kokoro), but they are slow on CPU and limited by tab memory. That's fine for a demo, not for an hour
   of video. StackBlitz also needs a commercial licence for production use.
3. **Plain pixi without a wall** suits only stacks that:
   - install known binary packages;
   - download nothing at run time;
   - load no pickle files;
   - don't listen on a port;
   - work on data that is not about people.

   In these tests that was only the leads rule, and arguably the table OCR.
4. **The wall earns its place** where the data is faces or voices, the weights are pickles, models download at
   run time, or the tool is a page. That was most of the requests a real team asked for.

**What this suggests for Windows and Mac:** split by risk, not by package.
- **Low-risk stacks** (the list in point 3) could run as native pixi on Windows and Mac, with no WSL and no VM:
  - Idli checks those properties when the stack is installed;
  - Idli sets offline variables (`HF_HUB_OFFLINE=1`) and a loopback-only rule for anything that listens;
  - on Mac, Seatbelt (Claude Code's open-source `sandbox-runtime`) is a real wall at no extra install.
- **Everything else** runs in Linux: WSL2, a VM, or a DGX container.

The person would rarely need WSL2 for simple tools. It would come up when a team adds something like a voice or
video tool.

## Why pixi and not Docker (discussed 2026-11-17)

pixi is the installer. The security comes from the wall around it.

**What pixi gives us:**
- one binary, no admin, no daemon, no licence;
- native packages plus PyPI under one lock, for several platforms;
- a short declarative file. That lets Idli show an honest "Adds: …" summary, which a Dockerfile (any command can
  run) would not;
- plain folders, which are easy to bind into bwrap.

**Where Docker is stronger:**
1. **The whole OS is pinned.** pixi uses the host's kernel and glibc. That's fine on the Linux we control, but it
   could bite on an odd distro.
2. **Some projects only ship `docker compose`,** or need apt packages and wired-up services. pixi can't run those
   as published. This is the real gap.
3. **A pulled image is self-contained.** A package removed from conda-forge or PyPI would break a fresh install
   from the lock. The fix is a shared package cache per team.
4. **Familiarity.** READMEs assume Docker.

**Docker on Windows** means Docker Desktop: an admin install, often a reboot, a root daemon, a paid licence for
organisations with more than 250 staff or $10M revenue, and several GB of images per stack. Underneath it is WSL2
anyway.

**Decision for now:** keep pixi as the default.
- Later, add a container option only for projects that need one: rootless Podman inside the same Linux, no network
  by default, the same consent and output flow.
- Add a per-team package cache.

## The open question: where does the Linux come from on Windows and Mac?

The wall is bwrap, so it needs Linux. That's simple on Linux. On Windows and Mac someone has to provide Linux. The
owner wants local execution, but not a hard install.

### What we already know

**Native Windows sandboxes are not ready (2026-09-27, io/Codex experiments:**
[decision](2026-09-27-local-remote-execution-decision.md),
[evidence](../benchmarks/runs/2026-09-27-execution-decision/README.md)):
- Codex 0.154's elevated Windows sandbox kept outside files out and blocked the public internet. But parent and
  child processes could still connect to services on the same machine (loopback and the host's own address), and
  it sometimes failed to launch (error 5).
- Codex 0.157's MXC path needs Windows "process security environments". Those were unavailable on both CI images.
  Microsoft calls MXC maturing and advises against treating its profiles as a security boundary.
- Those runs were Windows Server CI with admin accounts. None was a real Windows 11 desktop under a standard user.

**What has never been tested here:** WSL2. Every Windows experiment so far was a native sandbox. So there is no
evidence yet, good or bad, for "WSL2 plus our bwrap wall" on a real Windows laptop.

**A per-user Linux on the DGX already exists in prototype: io.idli.cc (V1 gateway, 2026-09-27**,
[note](2026-09-27-v1-remote-workspace.md),
[chronology](../chronology/2026-09-27T1728-dgx-v1-gateway.md)):
- Cloudflare Access identity maps to one persistent workspace container per person, with files that survive
  restarts.
- 39 gateway and 19 isolation checks passed. A second identity couldn't read, stream or proxy the first person's
  workspace. Docker networks blocked A to B. No ports were published.
- Codex's bwrap ran nested inside the container, with seccomp and AppArmor exceptions.
- It was never finished: there was no completed human sign-in turn, no quota or backups, no billing, and no
  Windows or Mac client run.

### What Claude Code and Antigravity offer (checked 2026-11-17)

**Claude Code:**
- Its sandbox uses Seatbelt on macOS, and bwrap plus a network proxy on Linux and WSL2.
- On native Windows it doesn't sandbox at all. Commands run unsandboxed, and the docs say to run Claude Code inside
  WSL2 to get the sandbox. WSL1 is not supported.
- So it doesn't remove the WSL2 step on Windows. It is the same design as our wall: bwrap plus an allowlisting
  proxy.
- Its sandbox engine is open source (`sandbox-runtime`, Apache 2.0). That matters for the Mac, below.
- Its sandbox wraps the agent's own shell commands. It doesn't wrap the stack's tools and pages, which run later
  without the agent.

**Antigravity:**
- Its terminal sandbox uses Seatbelt on macOS and kernel namespaces on Linux.
- On Windows it uses an AppContainer inside a "process security environment", and only on Windows 11 24H2 or later
  with the August 2026 update. That is the same MXC/PSEC technology the Codex experiments found unavailable and
  Microsoft calls not yet a security boundary.
- Defaults: no network, writes only to the workspace and temp folders. Hosts allowed for `read_url` become the
  outbound allowlist.
- On Windows, "some package installs" must be retried outside the sandbox, with approval.

**Conclusion:** neither tool has a trick that makes native Windows easy. Both point the same way: Linux isolation
(bwrap or namespaces) is mature. Seatbelt on Mac is mature. Native Windows isolation is new, needs a recent build,
and is not yet trusted. On top of that, many GitHub projects a team wants are Linux-only, so a native Windows wall
would still not run them.

### The options

**A. Local Linux everywhere** (the current plan in TEAM_STACKS.md):
- WSL2 on Windows with a small image Idli imports itself;
- a light VM on Mac.

| For | Against |
|---|---|
| Real data never leaves the laptop | One admin step and maybe a reboot on Windows, once |
| Works offline. No server cost | Needs virtualization on in the BIOS. Some corporate machines block WSL |
| CUDA works in WSL2 | Untested here |
| | The Mac VM has no Apple GPU |

**B. A per-user container on the DGX** (the io.idli.cc pattern, with pixi and bwrap inside):

| For | Against |
|---|---|
| Nothing to install on the laptop | Originals of the files a tool works on go to the team server |
| Same Linux for everyone. GPU available | Upload time for big media (video) |
| We already have the gateway, isolation tests and Access sign-in | Server cost and capacity: one DGX shared with the 9B and Muse |
| | Needs storage quotas and backups. Doesn't work offline |

Images already go to the 9B on the DGX through the model door. So the DGX is already inside the trust boundary for
model calls. Option B makes that last longer: the originals stay on the server, not just one request.

**C. Mac without a VM:** use Seatbelt through `sandbox-runtime`, or our own profile, around a native osx-arm64 pixi
environment.

| For | Against |
|---|---|
| No VM. Metal GPU for local models | A third platform in the lock (osx-arm64) |
| | Linux-only repos won't run |
| | A second wall to keep correct next to bwrap |

**D. Mixed, chosen per computer:** the stack's contract is already location-free (inputs in, an output folder out,
an optional model door). So "where it runs" can be a backend:
- Linux native;
- Windows: WSL2 if it can be turned on, else the DGX;
- Mac: VM or Seatbelt, else the DGX.

The person sees one line in the consent prompt: "Runs on this computer" or "Runs on your team's server".

### Recommendation (for discussion)

Go with **D**, and test the risky part first.

1. **Test WSL2 on a real Windows 11 laptop under a standard account, before building more.** This is the cheapest
   test that decides the most. Measure:
   - clicks, admin prompts, reboots and minutes from a fresh machine to a working stack;
   - whether the existing `tests/test_stacks.py` passes inside the imported image, including the wall attacks;
   - whether CUDA works.

   If it is one prompt and one reboot, A is fine for most people.
2. **Revive the io.idli.cc gateway as the fallback**, for machines where WSL2 can't be turned on. Same pixi lock,
   same wall, inside the per-user container. Two things are needed first:
   - an explicit consent line that says originals go to the team server;
   - quotas.
3. **Mac: try Lima first** (the closest to Linux). Keep the Seatbelt option for teams that need the Apple GPU.
4. **Keep the native Windows sandbox on watch.** If PSEC/MXC becomes a trusted boundary on common Windows builds,
   revisit it then.

### Decisions needed from the owner

- May a team's tools run on the team server (the DGX) with the person's originals, when the laptop can't run them?
  This changes the "real data stays local" promise, for tools only.
- Is one admin prompt plus a reboot at Idli install acceptable on Windows?

### As built (2026-11-17)

**Catalog server.** The router serves `/idli/catalog/` from `/mnt/seagate/silo/idli-catalog/`. It refuses path
tricks and doesn't list folders. Requests go to `requests.jsonl`. The repo copy and the vetting steps are in
`benchmarks/runs/2026-11-17-trusted-catalog/catalog/`.

**The 14 tools:**
- media-ffmpeg;
- speech-whisper-small and speech-whisper-turbo;
- voice-piper and voice-kokoro;
- translate-nllb (converted from Meta's pickle to CTranslate2 int8);
- ocr-tesseract and ocr-rapidocr;
- speech-vad;
- sound-classes (YAMNet converted to ONNX, so it runs on Windows);
- face-blur (YuNet);
- voice-anonymise (Whisper, then Piper);
- office-files;
- page-server.

All 14 solve on linux-64, linux-aarch64, osx-arm64 and win-64. On the DGX each was installed from its pins, and its
example ran with no network. Mirrored files come to 3.3 GB.

**Found while vetting:**
- **Hindi subtitles:** burned-in Hindi subtitles are broken with ffmpeg's plain `subtitles` filter (vowel signs
  misplaced, joined letters not joined). The vetted example converts to ASS with `shaping=complex`. The 2026-11-17
  training clips were probably affected.
- **RapidOCR:** its line-turning step flips Devanagari lines, so it is off, and photos must be the right way up.
- **Tesseract tables** need the `configs/hocr` files beside the language data.
- **Licences:** the Hindi Piper voice is CC-BY-NC-SA, and the English one comes from research-licence data. Kokoro
  is the choice for public material.

**Client.**
- New files: `lib/catalog.py` (fetch, platform, resources, check, request) and `lib/toolhome.py` (the tools home and
  `installs.json`).
- `stack_install(tools=[ids])` checks this computer, then asks for consent ("From Idli's vetted list", with sizes
  and cautions), then installs.
- New Builder tools `catalog` and `catalog_request`.
- An **Installed tools** page, linked from the top of Teams: installs by tool and by team, used and free disk,
  Remove, Remove all, and Add with the check.

**The DGX tools home is split:**
- `/mnt/seagate` is exFAT and can't hold symlinks, which pixi environments need;
- models go to `/mnt/seagate/idli-tools`, environments to `~/idli-insights/tools/envs` (about 1 GB per team, root
  disk);
- putting environments on the Seagate would need a reformat or a mounted ext4 image (root).

**Known gap:** removing one tool rewrites the team's `pixi.toml`, but its packages stay on disk until the team's
next install.

## Local Kubernetes (k3s, Rancher Desktop, minikube, kind)? (discussed 2026-11-17)

On Windows and Mac every one of these still needs a Linux VM underneath, so each is "a VM plus more":
- **kind** is Kubernetes inside Docker: Docker Desktop first, then a control-plane container.
- **minikube** runs on a driver: Docker, Hyper-V or VirtualBox (Hyper-V and VirtualBox need admin), by default a
  2 CPU / 2 GB VM.
- **k3s** is Linux only. On a laptop it runs inside WSL2 or a VM.
- **Rancher Desktop** packages that: WSL2 on Windows, Lima on Mac, with k3s and containerd inside. It is free
  (Apache 2.0) and Kubernetes can be switched off.

Overhead on top of plain Docker, roughly:
- the API server, datastore, kubelet, CoreDNS and an ingress use about 0.5 to 1 GB of RAM at idle;
- startup is slower (tens of seconds);
- more parts can break: certificates, networking, image pulls.

Isolation is the same as plain containers. Kubernetes adds scheduling across machines, which one person's tools on
one laptop don't need.

Ranking by weight on a laptop, lightest first:
1. pixi with no wall;
2. WSL2 or a VM with bwrap and pixi;
3. Docker;
4. local Kubernetes.

**Decision:** no local Kubernetes. On the DGX, k3s could later manage many per-user containers. For a POC, the V1
gateway's plain Docker is enough.

## The DGX for the POC: sign-in and files (discussed 2026-11-17)

### Sign-in

- **silo** (the 9B and Muse) uses one Cloudflare Access **service token**. It is a client id and secret in a file
  on the laptop, sent as `CF-Access-Client-Id` and `CF-Access-Client-Secret`.
- **io.idli.cc** (the V1 gateway) expects a **person**. `app/io/gateway/identity.py` requires a signed Access token
  with `sub` and `email`, and of type `app`. It maps that person to their own workspace container. A service token
  has no person in it, so the gateway refuses it as written.

Options:
- **Reuse the silo token:**
  - Access lets one service token be allowed on several applications, or the router could carry a path for stack
    runs, as it already does for `/idli/9b`;
  - the gateway would key the workspace on the token's name instead of a person;
  - it's quick, but one secret means one shared identity, and anyone holding the laptop's file is that workspace;
  - fine for a POC on the test account; one token per person would make it per-person.
- **Sign in as a person** (email code in a browser window, as V1 built): proper per-person workspaces. One more
  sign-in, and the Access session expires.

### Files

The DGX can't see the laptop's disk, so every input goes up and every output comes down.

| Recipe | Typical input | Over a 20 Mbps home upload |
|---|---|---|
| Table and form OCR | 0.1 to 3 MB photos | instant |
| Voice notes | 1 MB per minute | seconds |
| Report translation | under 1 MB | instant |
| Event video (10 min, 1080p) | 300 to 600 MB | 2 to 4 minutes |
| An hour of video | 2 to 4 GB | 15 to 30 minutes |

**Request size:** Cloudflare's proxy caps one request body at 100 MB on the Free and Pro plans (more on higher
plans). Big files through silo or io.idli.cc would need chunked, resumable uploads. Tailscale goes direct and has no
such cap, but needs Tailscale on every laptop.

**Drive-backed teams:**
- their files are already in Drive, so the DGX could fetch them from Drive itself, without using the laptop's
  upload;
- that means a Drive sign-in held on the server, which is a new trust step;
- today the laptop's copies come from Drive anyway.

**Outputs:** mostly small (tables, a 0.6 MB clip, a .docx). Cut video is the exception.

**Takeaway:**
- the DGX is easy for documents, photos and audio;
- for video it is a real cost, unless the files already live in Drive;
- local WSL2 or a VM wins exactly for the video and voice teams, which are also the ones that need the wall most.

## Decision 2026-11-17: a catalog of trusted tools, plain pixi everywhere (POC)

**Owner's call:**
- Idli keeps a server of software we have vetted. The Builder picks from it.
- The person is on wifi and the tools are vetted, so for the POC tools install with plain pixi on every platform.
- Proper sandboxing is evaluated later (p1 todo `todos/idli-insights/p1/sandboxing_later.md`).

**The catalog (on silo):**
- It lives on the DGX at `/mnt/seagate/silo/idli-catalog/` and is served by the router (`muse_prefix_proxy.py`):
  - `GET /idli/catalog/catalog.json` returns the list;
  - `GET /idli/catalog/files/<path>` returns mirrored model files;
  - `POST /idli/catalog/requests` appends a request for a new tool.
- The laptop reaches it through silo.idli.cc with the same Cloudflare Access service token as the 9B.
- Each tool entry has:
  - `id`, `name`, `for` (plain words), `licence`, `vetted` (date);
  - `pixi`: dependencies and PyPI dependencies, version-pinned;
  - `platforms`: only those where `pixi lock` solved (linux-64, linux-aarch64, osx-arm64, win-64);
  - `models`: each with `file` (path on silo), `source` (the public upstream URL), `sha256`, `bytes`;
  - `needs`: `disk_gb`, `ram_gb`, `cores`, `gpu`;
  - `example`: a short script showing the tool's use;
  - `cautions`: for example "non-commercial licence".

**The Builder's three steps:**
1. Pick catalog tools for the team's workflows (`catalog` tool). It only offers tools that solve on this platform.
2. Check resources before offering an install: free disk where tools go, RAM, cores, GPU, and platform. If the
   computer can't run it, the Builder says so plainly and suggests a smaller option, or the platform, or a request.
3. If nothing in the catalog fits, it sends a request (`catalog_request`): what is needed and why, in general
   words, with no team data. Our team vets it and adds a tool.

**Where installs go:**
- One folder per computer, `IDLI_TOOLS_HOME`: by default `~/idli-insights/tools`, and on the DGX
  `/mnt/seagate/idli-tools`. It holds each team's environment and a shared model folder, with each model stored
  once.
- `installs.json` records which team installed which tool, the size, the date and the platform.
- **Mission control** has a page listing every install by team and size, with Remove and Add. Removing the last
  team's use of a model frees it.

**The wall:** on Linux the install and run walls stay, since they cost nothing there. On Mac and Windows tools run
with plain pixi, for the POC.

## Log

- **2026-11-17:**
  - Wrote down the pixi and bwrap design and the comparison with Docker.
  - Gathered the earlier Windows sandbox evidence, the io.idli.cc prototype, and what Claude Code and Antigravity do
    on Windows.
  - The laptop now pulls the DGX branch through Tailscale (`git fetch dgx`) instead of the chunk sync.
- 2026-11-17 (later): added the recipes from the test runs; solved every stack for win-64 and osx-arm64 (11 of 12
  solve, LiteRT has no Windows build); sorted the recipes by how much wall they need (none needed Docker; only the
  leads rule clearly runs without a wall).
- 2026-11-17 (later): local Kubernetes options and their overhead; DGX sign-in (silo service token vs the
  gateway's per-person Access) and moving files over the network.
