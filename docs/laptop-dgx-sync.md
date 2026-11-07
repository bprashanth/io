# Keeping the laptop and DGX agents in sync

Two agents work on branch `oss-desktop-eval`: one on the owner's laptop (Paseo desktop app, real
browser sign-ins) and one on the DGX (models, experiments, driving the laptop's Paseo). This page is
the mechanism between them. General rules for handoffs are in [agent-handoff.md](agent-handoff.md).
How the DGX drives Paseo is in [driving-desktop.md](driving-desktop.md).

## One place for each kind of thing

| What | Where | Shared how |
|---|---|---|
| Code and docs | `~/src/github.com/bprashanth/io` on **both** machines, branch `oss-desktop-eval`. No other worktrees. | git (GitHub `origin`, or the laptop's `dgx` remote) |
| Private config and data | `~/idli-insights/` on both machines (`config/` is chmod 700) | copied by the owner with `scp`, never git |
| DGX server state (passwords, proxy logs, screenshots) | `~/io-oss-state/` on the DGX | not shared |
| "What the other side must do" | the **What changed** list at the top of [cowork-poc.md](cowork-poc.md) | git |

Screenshots, `.venv/`, `__pycache__/`, test data and `accounts.json` are ignored or live outside the repo.

## The handoff message

Whichever agent changes something that needs action on the other machine adds a dated entry to
**What changed** in cowork-poc.md: what moved, the exact action for the other side, and anything the
owner must do by hand (for example an `scp`). Then it commits and pushes.

The owner then sends the other agent the same message every time:

> git pull, then read "What changed" at the top of docs/cowork-poc.md and do the actions listed for
> anything new.

The receiving agent does the actions, reruns the check below, and reports PASS/FAIL lines. When it
finishes an action, it adds a one-line entry of its own (for example "DGX: done, check passed at
`<commit>`").

## Git rules

- `git pull --ff-only` before starting and before committing. Both agents commit to the same branch.
- Run `declaude origin/main` before every push, then `git push --force-with-lease`. declaude rewrites
  only commits that carry trailers, so commits already pushed by the other machine keep their hashes.
- If a push is rejected, pull and retry. Don't force over the other machine's commits.
- Small code moves during an experiment can skip GitHub: the laptop runs `git pull dgx oss-desktop-eval`
  from a laptop terminal (see driving-desktop.md, "Moving code between the machines").

## What the owner starts on the laptop so the DGX can reach Paseo

1. **Paseo with its DevTools port.** Quit Paseo (check `pgrep -f /opt/Paseo/Paseo.bin`), then run
   `setsid /opt/Paseo/Paseo --remote-debugging-port=9333 >/dev/null 2>&1 &`. Or use the edited launcher
   from driving-desktop.md, which does this every time.
2. **The tunnel**, from the repo's cowork folder:
   ```sh
   cd ~/src/github.com/bprashanth/io/benchmarks/runs/2026-11-06-oss-desktop-independent/cowork
   desktop/laptop-up.sh            # also: status, stop
   ```
   It opens one ssh connection to the DGX with `-L 8181` (Muse) and `-R 46767` / `-R 49333` (Paseo daemon,
   DevTools). If it prints `ssh exited`, run `ssh beeps@gx10-0a47.tail5ef239.ts.net true` once by hand.
3. **Keep the laptop awake** while the DGX works. If the laptop sleeps, the tunnel drops and the DGX sees
   "Connection refused" on 46767. Rerun `laptop-up.sh` after waking.

Stop with `laptop-up.sh stop` when done. While the tunnel is up, the DGX can read every workspace-browser tab.

## The check

On the DGX:
```sh
cd ~/src/github.com/bprashanth/io && git pull --ff-only
cd benchmarks/runs/2026-11-06-oss-desktop-independent/cowork && desktop/check-from-dgx.sh
```
It ends in `ALL CHECKS PASSED`. The first FAIL line names the cause (tunnel down, DevTools port missing,
provider missing, no agent in a workspace, no `accounts.json`).

If the laptop has no DIY workspace (the repo's `cowork/` folder) or no agent in it, the DGX can create both:
```sh
P=desktop/paseo-remote.sh; L=<laptop path to the repo>/benchmarks/runs/2026-11-06-oss-desktop-independent/cowork
$P workspace create --isolation local --path "$L" --title "DIY (cowork)"
$P run --provider diy-claude --workspace <wks id> --title bootstrap "Reply with the single word OK. Do not use any tools."
```
The run is one short call on the owner's Claude subscription.
