# 2026-11-13, 11:55 IST — Checkpoint: Minis shared over real Drive; strategy brief; Drivey, WhatsAppy, Canvay; Paseo P16

## Sharing Minis, end to end with real Google Drive (laptop, test account)

- A Mini is a dashboard for one Drive file; Share gives a code (`IDLI-XXXX-XXXX`) that carries the workflow and the
  file's id, never data rows. Opening a Mini fetches the file fresh as the person, using the app browser's Google
  session (cookies read through DevTools, sent only to Google).
- Measured: 7 KB sheet fetched in 1.0 s, 127 KB in 1.5 s (byte-identical); a file the account can't open was
  refused in 0.45 s. A second, empty Idli home on the laptop added the code and got the same answer; the DGX added it
  through silo and correctly said "Sign in to Google first".
- Fixed on the way: `fetch()` inside a Google tab can't read Drive's cross-origin redirect to
  googleusercontent.com, so `lib/drivefetch.py` uses the session cookies only.
- Not tested: two different Google accounts.
- Detail: [proposals/idli-sharing.md](../proposals/idli-sharing.md). Commits `9ad3153d`, `bb491208`, `32431d7d`,
  `eeb83ed6`.

## Strategy brief

[narrative/IDLI_DESKTOP.md](../narrative/IDLI_DESKTOP.md), for brainstorming with another agent:
- Paseo as an aggregator of CLIs; drop-offs are tool switching, privacy, correctness and safe editing.
- Minis as the unit of learned org work: Drive analysis, an org kit (for example Canva), UI as API (funder
  portals), and cross-app (for example WhatsApp).
- The pattern: a frontier teacher on test accounts or fake data, a small private worker acting as the person in
  their browser, with approval.

## Sidebar: Drivey, WhatsAppy, Canvay

- The Idli workspace is now **Drivey**, renamed in place: chats, tabs and the split panel are unchanged. "Idli"
  stays the app's and the private model's name in the instructions; Start here now points to Drivey.
- New **WhatsAppy** (`~/idli-insights/whatsappy`) and **Canvay** (`~/idli-insights/canvay`): empty folders, plain
  Claude chats (the owner's subscription), no Idli tools, no split. They are open spaces for the experiments in
  the brief.
- `desktop/idli-bootstrap.py`: `CLAUDE_SPACES`, `OLD_NAMES`, `chat(provider=)`. On the laptop only the folder,
  workspace and chat steps were run. A full bootstrap would archive the two stray "Greet and …" workspaces, which
  the owner hasn't confirmed.
- Gap: Paseo's New chat uses the model picked last anywhere in the app, not a model per workspace. A per-workspace
  default would need a Paseo patch (not written).
- Commits `4a84cb9f`, `777140b2`.

## Paseo P16: the in-app browser presents as Chrome

- WhatsApp Web said "WhatsApp works with Google Chrome 100+" in Paseo's browser. The engine is Chromium 152; the user
  agent carried `Paseo/0.15.3 … Electron/44.2.0`.
- Checked first with a DevTools user-agent override on that tab: the QR login appeared.
- The patch: `prepareBrowserWebview` (`packages/app/src/desktop/browser/resident-webviews.ts`) sets `useragent`
  without the Electron and Paseo tokens. Build `~/idli-builds/paseo-app-dist-0.15.2-idli7.tgz` on the DGX; installed
  on the laptop (the previous UI is kept as `~/idli-insights/paseo/app-dist.idli6`). After a full reload the
  WhatsApp tab sends plain Chrome 152 and shows "Scan to log in".
- `desktop/install-paseo-ui.sh` takes `FILE=<build.tgz>`, because scp from the laptop to the DGX now hits a
  Tailscale SSH re-auth that only the owner can complete. This time the build went over the tailnet by a short
  `http.server` and was checked by sha256; code reached the laptop as git bundles through a Paseo terminal.
- Commit `83d8715e`; P16 is in [todos/idli-insights/p1/paseo_patches.md](../todos/idli-insights/p1/paseo_patches.md).

## Where things live

- The Paseo source with the patches applied is a temporary checkout in a Claude Code scratchpad on the DGX,
  not in this repo. `cowork/desktop/paseo-idli-split.patch` is its `git diff -- packages/app` (equal to that diff
  as of this checkpoint) and is what to reapply on a fresh 0.15.2 checkout.
- The laptop runs repo commit `777140b2` (it doesn't need `83d8715e`, which is the patch file and docs) and UI
  build idli7.

## Open

- Tailscale SSH re-auth on the laptop (the owner).
- Test with two Google accounts; make Mini titles look clickable; fix the low-contrast "Open it in Drive" link in
  dark mode.
- A per-workspace default model (Paseo), so New chat in WhatsAppy and Canvay is always Claude.
