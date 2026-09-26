# Sandboxing: what the assistant's commands can reach

Part of [ARCHITECTURE.md](ARCHITECTURE.md). The argument behind these choices is in
`narrative/2026-09-15-sandboxing-field-note.md`.

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

**A conversation** (no folder) runs with the wall on and commands online, whatever the folder
settings say. See the open issues below.

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

## Is the wall on? Proven, on every platform

Before Codex starts, io runs one probe (`wallProbe` in `app/io/codex.js`): a small program run
through `codex sandbox -P io` under io's real profile. It must fail to read a file placed
beside the folder, and succeed in writing inside it. A control run with the file placed where
the wall does grant access comes back readable, so the probe's "no" is a real refusal.

The terminal bar shows the result on every platform: green **Wall on, checked on this
computer**, or red **Wall OFF**. The footer says **Protected by io** only when both the codes
and the wall hold, and **Codes only: no wall** otherwise.

## When the wall cannot run

**Ubuntu 24.04** ships an AppArmor rule that strips bubblewrap's capabilities as soon as it
creates a namespace, so neither io's wall nor Codex's own sandbox runs. The remedy is a small
AppArmor profile per bubblewrap binary, installed once by an administrator.

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

- **A conversation with an attached file.** Commands are online in a conversation, and
  attaching a file does not change that. Measured: a command read the attached file and
  reached example.com. Planned: ask the person whether the file is private, and if so relaunch
  the conversation offline.
- **The probe has never run on macOS or Windows.** If it cannot start there, io reports the
  wall as unproven, which is the safe direction to be wrong in.
- **Offline refuses to open a page without saying why.**
