# Sandboxing: what the assistant's commands can reach

Part of [ARCHITECTURE.md](ARCHITECTURE.md). The argument behind these choices is in
`narrative/2026-09-15-sandboxing-field-note.md`.

This page describes the local main application unless explicitly marked remote. The separate
V1 gateway launcher always executes remotely; see [rollout guide](execution-and-laptop-rollout.md).

## Why a wall at all

The proxy protects what goes to the model. It never sees what the **commands** Codex runs do.
A command can read files and, if allowed, reach the internet, and nothing in that traffic is
coded. So io runs every command inside a wall: Codex's own sandbox, under a permissions
profile io writes.

## The wall

Codex enforces it: bubblewrap on Linux, Seatbelt on macOS, a restricted token on Windows. io
supplies the profile, rewritten at every launch (see [ARCHITECTURE.md](ARCHITECTURE.md)).
Inside the wall a command may:

- read and write the chosen folder;
- write temp;
- read what the platform needs to run at all (Codex's `:minimal` preset);
- read Codex's own package, and io's python runtime, so `python3` has pandas, numpy, openpyxl
  and matplotlib;
- read io's `AGENTS.md`;
- read the system's name-resolution directory, only when the setting allows the internet.

And nothing else. Measured: the home directory shows only the empty path to io's folders,
`.bashrc` is refused, and the person's own Codex sign-in is invisible.

## The settings

Chosen after picking a folder and before anything is scanned. They decide what commands may
reach, never what the model sees.

| setting | commands online | toolbox | io opens pages | wall |
|---|---|---|---|---|
| Offline | no | no | no | yes |
| T4GC tools (suggested) | no | yes | yes | yes |
| Open | yes | yes | yes | yes |
| `unwalled` (fallback only) | yes | yes | yes | **no** |

The setting can be changed mid-conversation. Codex is relaunched under the new profile and
resumes the same thread.

**A new conversation** (no folder) starts with the wall on and commands online.
Its terminal bar says whether commands are online or offline. On attachment, io
asks whether the file is private before copying it. It stops the old assistant,
scans the copy, and resumes only after review. **Yes** makes this conversation
T4GC-tools-only, with command networking off; **No** preserves its current setting.
Private status persists outside the working folder and cannot be undone by a later
public attachment or restart. A private attachment is refused without a proven wall.
The model traffic's coding is unchanged.

## Escalation is closed everywhere

Codex can normally ask the person to run a command outside the sandbox. Someone who says yes
gives that command the whole machine. io launches every setting with that prompt closed
(`-a never`, `approval_policy = "never"`).

## The toolbox

Tools T4GC has reviewed run as a local MCP server that io starts **outside** the wall, so a
tool can reach the network while commands cannot. The server is registered with
`default_tools_approval_mode = "approve"`, which Codex checks before the approval policy, so
tools run without a prompt even though escalation is closed. Measured: a shell command could
not reach a loopback listener while a tool reached it.

One tool today: the renderer, which shows the model a coded picture of a page it wrote. See
[tokenization.md](tokenization.md).

## Pages Codex writes

A page is the widest way out of the wall, and it is io's own doing. An HTML file Codex writes
carries whatever data was put in it, and once it is open in a browser it has the whole
network. Demonstrated: such a page sent real names, phones and GPS coordinates to a listener,
with the proxy and the wall both uninvolved.

So Codex cannot open a browser from inside the wall. io watches the folder and shows new pages
and charts in its own viewer window, which refuses every request that is not a local file.
"Open in your browser" is a separate, deliberate step, and it is disabled under Offline.

## Startup indication versus full conformance

Before Codex starts, io runs one probe (`wallProbe` in `app/io/codex.js`): a small program run
through `codex sandbox -P io` under io's real profile. It must fail to read a file placed
beside the folder, and succeed in writing inside it. A control run with the file placed where
the wall does grant access comes back readable, so the probe's "no" is a real refusal.

The terminal bar shows the result on every platform: green **Wall on, checked on this
computer**, or red **Wall OFF**. The footer says **Protected by io** only when both the codes
and the wall hold, and **Codes only: no wall** otherwise.

The startup probe covers only a narrow read/write boundary. It does not prove network,
child-process or path-traversal confinement. Qualify a local installation with the complete
synthetic conformance suite, not the green startup indicator alone.

## DGX state: verified 2026-10-11

**The bundled bubblewrap works on this box.** Fresh Codex 0.154.0 conformance passed all
17 properties (workspace read/write, outside reads/writes, child execution/confinement,
symlink traversal, loopback/host-interface/public TCP under the intended profiles).
A newly created remote Docker container also completed its inner Linux conformance check;
the synthetic container was then removed. [Evidence](../benchmarks/runs/2026-10-11-dgx-sandbox/README.md).

`kernel.apparmor_restrict_unprivileged_userns` remains 1. `/etc/apparmor.d/io-bwrap`
grants user namespaces to `/usr/bin/bwrap` and this checkout's bundled bwrap path.
This is a configured-host result, not proof that every stock Ubuntu install works.
Moving the checkout or replacing the binary path may require updating the grant and retesting.
Neither `IO_CODEX_NO_SANDBOX` nor `IO_CODEX_NO_WALL` is needed for supported execution here.

The remote runtime additionally uses the named `io-remote-experiment` AppArmor profile and
`seccomp=unconfined` to permit nested bubblewrap. Those outer-container exceptions remain
experimental hardening limitations. Passing the inner command tests is not a production
multi-tenant isolation certification. Remote mode uses user-owned ChatGPT OAuth directly;
it does not currently use the local masking proxy described elsewhere in these docs.

On October 1 this coding-agent session could not access Docker or the user service bus.
That was an agent permission restriction, not a new failure of IO's bubblewrap sandbox.
Docker/service access was restored and exercised on October 11.

## When the wall cannot run

**Ubuntu 24.04** can restrict unprivileged user namespaces through AppArmor, preventing
bubblewrap from starting without a suitable grant. The supported remedy is an explicit
AppArmor profile for the bubblewrap binary, installed once by an administrator, followed
by a fresh conformance run. That setup is already present on this DGX.

When the probe fails, io shows a dialog that states the cost plainly:

- **Linux with that rule:** **Set up the wall** installs the profile through the desktop's own
  password prompt (`pkexec`), then probes again.
- **Linux without pkexec:** the command an administrator can run.
- **macOS and Windows:** there is nothing io can install.
- **If setup fails or is declined:** the person may continue with `unwalled`. The model
  traffic is still coded; commands run without a wall; the bar says so in red for as long as
  it lasts.

The main process enforces this, not only the page: a walled setting is refused where the wall
failed, and `unwalled` is refused where the wall works.

For development, `IO_SANDBOX_TEST=broken` or `fixable` simulates a failed wall, and
`IO_CODEX_NO_SANDBOX=1` bypasses it entirely.

## Open issues

- **Cross-platform evidence has limits.** Both Mac architectures passed direct sandbox
  conformance in September CI. Windows experiments did not establish the required contract.
  A real laptop must pass the complete suite for its actual build/backend; CI client tests
  are not native sandbox certification. See [rollout steps](execution-and-laptop-rollout.md).
- **Offline refuses to open a page without saying why.**
