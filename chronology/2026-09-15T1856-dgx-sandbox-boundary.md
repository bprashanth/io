# 2026-09-15, 18:56 IST — DGX: the sandbox does run here, and why it did not

Machine: DGX Spark, Ubuntu 24.04.4, kernel 6.17 (nvidia), aarch64, no display. Follows the
laptop's three entries of today and answers the handoff's first task: establish the
boundary between what the DGX can verify and what only the laptop can. The answer moved
the boundary a long way.

## Why bubblewrap failed on this box - measured, not guessed

Ubuntu 24.04 ships `kernel.apparmor_restrict_unprivileged_userns = 1`. Any *unconfined*
binary that creates a user namespace is transitioned by AppArmor into a profile called
`unprivileged_userns`, which strips its capabilities. The kernel audit log shows it
exactly (`sudo dmesg`):

    apparmor="AUDIT"  operation="userns_create" info="Userns create - transitioning profile"
                      profile="unconfined" comm="bwrap" target="unprivileged_userns" execpath="/usr/bin/bwrap"
    apparmor="DENIED" operation="capable" profile="unprivileged_userns" comm="bwrap" capname="setpcap"
    apparmor="DENIED" operation="capable" profile="unprivileged_userns" comm="bwrap" capname="net_admin"

So the namespace is created, then `bwrap` may not set up the uid map
(`setting up uid map: Permission denied`) or bring up loopback in the new network
namespace (`loopback: Failed RTM_NEWADDR: Operation not permitted`). It is not the kernel
version, not the sandboxed shell this agent runs in, and not "the DGX cannot run bwrap".
`unshare -U` succeeding was a red herring: util-linux's `unshare` is confined by its own
AppArmor profile, and inside the namespace `CapEff` is all zeros.

The remedy Ubuntu itself uses for its packages is an AppArmor profile that grants
`userns` to the binary:

    abi <abi/4.0>,
    include <tunables/global>
    profile io-codex-bwrap <path-to-bundled-bwrap> flags=(unconfined) { userns, }
    profile io-system-bwrap /usr/bin/bwrap flags=(unconfined) { userns, }

Two profiles, because Codex prefers a system `bwrap` on PATH when one exists
(`linux-sandbox/src/launcher.rs`, confirmed by `execpath=/usr/bin/bwrap` in the audit) and
falls back to `codex-resources/bwrap` only otherwise. Loaded with `apparmor_parser -r`
from a file in the scratchpad: **transient**, not in `/etc/apparmor.d`, gone at reboot,
removable now with `apparmor_parser -R`. The text is saved as
`benchmarks/runs/2026-09-15-dgx/io-codex-bwrap.apparmor`. Whether to make it permanent on
the DGX is the owner's call; this entry only reports that it works.

With the grants loaded, the bundled `bwrap` creates user, network and pid namespaces and
a command inside has no network: the sandbox runs.

## The wall, measured on the DGX (`wall_probe.py`, `wall-with-profile/`)

Two instruments. `codex sandbox -p io -- bash -c ...` runs a command under io's profile
with no model in the loop. `codex exec -p io` with the dev provider (OpenRouter behind the
same proxy) runs a real session in which the model is asked to run `probe.sh` once; the
script writes its verdicts to a JSON file inside the workspace and we read the file, not
the model's prose. The `exec` runs hung for 300 s at first: `codex exec` appends stdin to
the prompt and waits for EOF, and the harness never closed it (`stdin=DEVNULL` fixes it;
`spike2` had been lucky). `-a never` is an interactive flag; `exec` rejects it and is
non-interactive anyway.

Verdicts written inside the sandbox, identical for Offline and T4GC tools:

| probe | result |
|---|---|
| `ls /home/beeps` | only `src` - the path skeleton to the folder; nothing else in the home exists inside |
| `ls ~/.local/share/io` (io's data, `auth.json`) | "No such file or directory" |
| `cat /etc/hostname` | readable (`/etc` is in `:minimal`; the laptop's refusal came from the model, not the wall) |
| write `/tmp`, write the folder | ok, ok |
| `command -v python3`, `import pandas, numpy, openpyxl` | io's venv; `3.0.5 2.5.2 3.1.5` |
| `curl 127.0.0.1:<listener on the host>` | exit 7, listener saw nothing |
| `curl https://example.com` | exit 6 (could not resolve) |
| `command -v rg` | Codex's bundled `codex-path/rg` |
| `id -u`, `CapEff` | 1000, all zero |

Open: loopback reached the host listener (`listener ok`, the listener logged `/probe`)
and host interfaces are visible - the network namespace is shared - **but the internet
still failed with exit 6**. Cause: `/etc/resolv.conf` on a systemd-resolved system is a
symlink into `/run/systemd/resolve`, which `:minimal` does not include, so there was
network and no DNS. Fixed in `codex.js`: when a setting allows network, the profile grants
`/run/systemd/resolve` read. After the fix, under `codex sandbox`: Open gets `200` from
example.com, T4GC tools still `000 exit=6`. The laptop's table had marked Open's network
as "yes" from the config rather than from a test; this is the first time it was tried.

## Stock Ubuntu 24.04, simulated by unloading the grants

This is what a participant with an Ubuntu 24.04 laptop gets, and it is not good:

- io's profile: `bwrap: loopback: Failed RTM_NEWADDR` - no sandboxed command at all.
- Codex's own default sandbox, no io profile at all: the same failure. **Codex's sandbox
  does not run on stock Ubuntu 24.04**, io or no io; every command becomes a "run outside
  the sandbox?" prompt, or fails under `-a never`.
- Codex's legacy Landlock backend (`features.use_legacy_landlock=true`): refuses io's
  profile outright ("permission profiles requiring direct runtime enforcement are
  incompatible"); with Codex's default profile it runs, network is off, writes outside the
  folder are blocked, but the whole home directory is readable (17 entries, io's own data
  dir among them) and in this quick test even the workspace write was denied. Not a wall.

The earlier participant crash (Chromium's setuid helper, 2026-08-30) came from the same
setting on the same distribution. Pop!_OS, where all the laptop testing happened, does not
carry the restriction, which is why none of this was visible there.

## Boundary, restated

(a) Verified on the DGX now: everything in the table above, for all three settings, with
the model in the loop and without. This includes the four items the handoff listed as
DGX-unverifiable: network per profile, readability inside the wall, `python3` resolving to
io's runtime with pandas, and the runner starting inside the sandbox.

(b) Reasoned about only: `-a never` suppressing the escalation prompt in an interactive
session (needs a TUI drive; can now be done here under Xvfb); MCP servers getting network
while commands do not (proved on the laptop; re-provable here now); `xdg-open`, D-Bus and
page opening (no display on the DGX - laptop only).

(c) For the laptop, written to be run as-is: none needed for the wall itself any more.
One remains for the desktop: open a page under each setting and confirm Offline refuses,
T4GC tools opens it, and the link provider makes a bare filename clickable.

## Decisions this raises

1. Keep the AppArmor grants on the DGX permanently (`/etc/apparmor.d/`), so the wall is
   testable here every day? Transient today.
2. Participants on Ubuntu 24.04 cannot have the wall without a one-time admin step (the
   same two-profile file, or `sysctl kernel.apparmor_restrict_unprivileged_userns=0`).
   io promised never to ask for a password. Options: detect the setting at launch
   (`namespaceSandboxUsable` in main.js already reads it for Chromium) and say plainly
   that this computer needs a one-time step from an admin; offer to do it through `pkexec`
   with an explanation; or accept "no wall" mode on those machines with the footer saying
   so. This is a product decision, not a code one.
