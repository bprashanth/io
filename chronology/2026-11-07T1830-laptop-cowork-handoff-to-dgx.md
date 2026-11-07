# 2026-11-07, 18:30 IST — Laptop: co-work POC handed to the DGX agent

The owner wants the DGX agent to drive this laptop's Paseo over a tunnel, verify it, and fix a bug from the
owner's manual test before designing new experiments.

## Built

- **`cowork/desktop/laptop-up.sh`:** one ssh connection opened by the laptop:
  - `-R 46767` → Paseo daemon;
  - `-R 49333` → app DevTools;
  - `-L 8181` → Muse, unless it's already forwarded.
- **`cowork/desktop/paseo-remote.sh`:** the Paseo 0.15.2 CLI from the DGX's `io-oss-paseo` image (the DGX host has
  no Node), with `--host 127.0.0.1:46767`.
- **`cowork/desktop/drive.py`:** Python Playwright over DevTools. It can screenshot, list tabs, open a workspace and click.
- **`cowork/desktop/check-from-dgx.sh`:** one script that verifies everything from the DGX:
  - the tunnel;
  - the providers;
  - the two workspaces;
  - a laptop terminal command;
  - a screenshot;
  - the site tests from the DGX copy, through the tunnel.
- **`cowork/desktop/setup-laptop.py`:** idempotent recreation of the laptop side. It ran here with no changes.
- **Docs:**
  - [driving-desktop.md](../docs/driving-desktop.md);
  - [cowork-poc.md](../docs/cowork-poc.md), the agent's entry point, with known bugs;
  - [cowork-manual-test.md](../docs/cowork-manual-test.md), the owner's checklist.

## Verified by hand, from the DGX through the tunnel

- `paseo --host 127.0.0.1:46767 ls` and `provider ls` (from the container) list the laptop's agents and providers.
- `terminal create` / `send-keys … Enter` / `capture` ran `git log` in the laptop's DIY workspace.
- DevTools reached the app: it listed the app page and every webview, and saved a screenshot.

Not run yet: `check-from-dgx.sh` on the DGX as a whole. It needs the pulled branch and `accounts.local.json`.

## Notes

- The laptop has no sshd, so the DGX has no shell on it. Paseo terminals are the way to run commands there.
- DevTools exposes every workspace tab, including real Gmail. Keep the tunnel down outside experiments.
- **Code path:** the DGX edits and commits on `oss-desktop-eval` in `io-oss-eval`. The laptop pulls with
  `git pull dgx oss-desktop-eval` through a Paseo terminal.
- **Commits:** the 16:15, 17:50 and this session's commits were `declaude`d and pushed to `origin/oss-desktop-eval`
  at the owner's request.
