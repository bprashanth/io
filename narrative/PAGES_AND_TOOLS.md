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

## Log

- **2026-11-17:**
  - Wrote down the pixi and bwrap design and the comparison with Docker.
  - Gathered the earlier Windows sandbox evidence, the io.idli.cc prototype, and what Claude Code and Antigravity do
    on Windows.
  - The laptop now pulls the DGX branch through Tailscale (`git fetch dgx`) instead of the chunk sync.
