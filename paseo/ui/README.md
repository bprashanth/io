# Idli's UI on Paseo: where everything lives

Idli runs inside **Paseo** (0.15.2), an Electron desktop app that hosts agent chats (Claude Code, Codex and others),
terminals and a browser pane. Idli's UI has three layers. Only the first is a change to Paseo itself.

| Layer | What it is | Where it lives |
|---|---|---|
| 1. Paseo's own UI | patches to Paseo's React app: the Drivey split panel, the WhatsApp browser fix and others | patch files in this repo; a Paseo source checkout to build from |
| 2. Idli's pages | the dashboard, Minis, the privacy review: plain web pages shown in Paseo's browser pane | `cowork/lib/*.html`, served by `cowork/lib/formserver.py` on the laptop |
| 3. Idli's logic | tools, the chat routing for every model, masking, the grounded 9B modes | `cowork/` (on the laptop) and `dgx/` (the router) |

Paths below are relative to `benchmarks/runs/2026-11-06-oss-desktop-independent/` unless they start with `~` or `/`.

## 1. Paseo's own UI (patched)

- **Patches** (the durable copy of every change):
  - `cowork/desktop/paseo-idli-split.patch`: all changes to `packages/app` (P13–P16), made with
    `git diff -- packages/app` in the Paseo checkout:
    - the Drivey split panel (Idli on the left, Claude on the right);
    - pairing a chat with its side pane (`utils/idli-pairing.ts`, `utils/idli-side-pane.ts`);
    - agent navigation;
    - P16: `desktop/browser/resident-webviews.ts` strips the `Electron/…` and `Paseo/…` tokens from the browser's
      user agent, so sites like WhatsApp Web stop asking for "Chrome 100+".
  - `cowork/desktop/paseo-browser-downloads.patch`: P1, silent browser downloads in `packages/desktop`. It has tests
    but was never built or installed.
- **Status of every patch:** `todos/idli-insights/p1/paseo_patches.md` (repo root).
- **Source checkout** (temporary): Paseo 0.15.2, commit `e896c05b`, with the patches applied, at
  `/tmp/claude-1000/-home-beeps-src-github-com-bprashanth-io/89b0f21c-c677-4103-ad2f-cc63bbc75af6/scratchpad/paseo`.
  It is in a session scratch folder and can disappear on a reboot. To rebuild from scratch, check out Paseo 0.15.2
  and apply the patch with `git apply`.
- **Build** (UI only; Electron's main process is unchanged):
  `cd packages/app && PASEO_WEB_PLATFORM=electron npx expo export --platform web`, then tar the output as
  `~/idli-builds/paseo-app-dist-0.15.2-idliN.tgz` on the DGX, with the matching `paseo-idli-split-idliN.patch`.
  **The laptop runs idli24** (2026-11-15: teams work like Drivey and Start here chats look like Drivey's, P20;
  idli22 added Idli pages inside chats, P19). The tables below still describe idli7.
- **Install on a laptop:** `cowork/desktop/install-paseo-ui.sh`, which uses `BUILD` (default idli7) or
  `FILE=<build.tgz>` for a local file.
  - It unpacks the build to `~/idli-insights/paseo/app-dist` and points `/opt/Paseo/resources/app-dist` at it with a
    symlink.
  - Earlier builds are kept beside it (`app-dist.idli6`, `app-dist.old`).
  - Restart Paseo afterwards.

## 2. Idli's pages (shown in Paseo's browser pane)

These pages are not Paseo code. `cowork/lib/formserver.py` serves them on the laptop at
`http://dashboard.localhost:<port>/…`, behind a per-run token. Idli's tools open them in the Drivey workspace's
browser tab.

| File (`cowork/lib/`) | Page |
|---|---|
| `form.html` | **The dashboard** for one file: pick figures, breakdowns and filters; table, live Vega-Lite chart, "how this was worked out". Clicking a bar opens a popover: how it's worked out, rows behind it, compare with the others, looks wrong, a comment, or narrow the dashboard. The question goes into the chat as the person's message (`/api/say` → `paseo send`). |
| `skills.html` | **Minis**: the taught skills on this computer. Share one (a code via the Idli server), add one from a code, open one (the Drive file is fetched fresh, with the viewer's own Google access), delete. |
| `privacy.html` | **File privacy review**: Fake copy or Mask, Always ask or Auto, and a toggle per column showing real samples beside what Claude would receive. |
| `index.html` | The Drive file index. |
| `vendor/` | Vega, Vega-Lite and vega-embed (no data). |

Also part of the Paseo side:
- `cowork/dashboard-links/` is a Paseo plugin that opens dashboard links inside Paseo.
- `cowork/desktop/setup-laptop.py` adds Idli's providers and model menu (Idli 30B, Idli 9B · Careful, Idli 9B ·
  Auto) to `~/.paseo/config.json`, keeping a backup.
- `cowork/desktop/idli-bootstrap.py` creates the workspaces:
  - **Drivey** (chats open with the split panel; the tool allow-list is written to `cowork.tools`);
  - **WhatsAppy** and **Canvay** (chats open straight to Claude).

## 3. Idli's logic

- `cowork/sites/files/tools.py`: Idli's tools (`file_get`, `file_open`, `file_ask`, `file_privacy`, `teach_file`,
  `chart_request`, …), served to the chat by `cowork/cowork_mcp.py`. Every file result carries the file's privacy
  setting.
- `cowork/lib/modes.py`: what the chat does, per model.
  - It runs inside the DGX router `dgx/muse_prefix_proxy.py` (systemd user service `muse-prefix-proxy`, port 8185,
    reached as silo.idli.cc).
  - `privacy_route` (all models): the privacy card when a file opens, and masked questions with the "Send to Claude"
    card.
  - `careful_chat` / `auto_chat`: the grounded 9B modes.
- `cowork/lib/careful.py`, `cowork/lib/auto.py`, `cowork/lib/receipt.py`: the two 9B modes and the record of what each
  chart actually drew.
- `cowork/lib/privacy.py`, `cowork/lib/privacy_engine/`: masking.
  - Column suggestions come from regexes, plus GLiNER when a scanner is reachable (`IDLI_SCANNER`); the laptop has
    none today.
  - A code vault stays local; questions are masked; a leak check runs before sending.
  - The planner is the person's own `claude -p`.

## Where it runs

- **DGX:** the repo, on branch `oss-desktop-eval`, is the source of truth. The router (`muse-prefix-proxy`) and the
  9B (`dgx/idli-9b.sh`) run here.
- **Laptop:**
  - Paseo with the idli7 UI;
  - the repo at `~/src/github.com/bprashanth/io`, synced from the DGX as local "sync" commits (it can't pull right
    now);
  - Idli's working folders under `~/idli-insights/` (Drivey is `cowork-real`).
- **After changing the code:**
  - `modes.py` or the router: restart `muse-prefix-proxy` on the DGX.
  - `tools.py` and `lib/`: copy to the laptop; new chats pick it up.
  - `formserver.py`: stop the laptop's formserver, and the next tool call restarts it.
  - Paseo UI patches: rebuild and reinstall.

## Checkpoint 2026-11-14 (known good; revert to this)

The state tested in the app on 2026-11-14, with Drivey, WhatsAppy and Canvay, the chart popover and file privacy.

| Piece | Checkpoint | Check |
|---|---|---|
| Paseo desktop shell (laptop) | 0.15.3 (`/opt/Paseo`, unpatched) | `app startup { version: '0.15.3' }` |
| Paseo UI source | upstream 0.15.2, commit `e896c05b09707e711a2324fcab7da84a0ae57291`, plus the patch below | |
| UI patch (P13–P16) | `cowork/desktop/paseo-idli-split.patch` | sha256 `fe0abd98…` (matched the checkout byte for byte) |
| Desktop patch (P1, not installed) | `cowork/desktop/paseo-browser-downloads.patch` | the staged desktop diff, sha256 `42147c92…` |
| UI build | `~/idli-builds/paseo-app-dist-0.15.2-idli7.tgz` on the DGX | sha256 `2b0b8d51…` |
| Installed UI (laptop) | `/opt/Paseo/resources/app-dist` → `~/idli-insights/paseo/app-dist` (idli7) | |
| Laptop backup | `~/idli-insights/archive/paseo-checkpoint-2026-11-14/` | listed below |
| Idli code | git tag `paseo-ui-checkpoint-2026-11-14` (DGX repo) | |

The laptop backup holds:
- `config.json`: Paseo's config with providers `t4gc-cowork` (Muse, Careful, Auto), `idli-teach`, `diy-claude` and
  others; mode 600; may contain settings, don't share it;
- `app-dist-idli7.tgz`: the installed UI as it was (sha256 `481ef37d…`);
- `cowork.tools`: Drivey's tool allow-list;
- `workspaces.txt` and `plugins.txt`.

The `declaude` rewrite before a push changes commit hashes. If the tag ends up on a pre-rewrite commit, find the
same state by this README's text and the checksums above.

**To revert the laptop to this checkpoint:**
1. Quit Paseo.
2. Restore the UI:
   ```sh
   K=~/idli-insights/archive/paseo-checkpoint-2026-11-14
   rm -rf ~/idli-insights/paseo/app-dist
   tar xzf $K/app-dist-idli7.tgz -C ~/idli-insights/paseo
   ```
   The symlink in `/opt/Paseo/resources` already points there.
3. Restore the config: `cp $K/config.json ~/.paseo/config.json` (keep the current one first), and
   `cp $K/cowork.tools ~/idli-insights/cowork-real/`.
4. Restore the code: on the DGX, `git checkout paseo-ui-checkpoint-2026-11-14 -- benchmarks/runs/2026-11-06-oss-desktop-independent`;
   restart `muse-prefix-proxy`; copy `cowork/` to the laptop.
5. Start Paseo with `--remote-debugging-port=9333`.

**To go back to stock Paseo:** remove the `/opt/Paseo/resources/app-dist` symlink (the packaged UI in `app.asar` is
used), restart Paseo, and restore the backed-up `config.json` without the Idli providers. Or reinstall the Paseo
package.

**To rebuild idli7 from scratch:**
1. Clone Paseo and check out `e896c05b`.
2. `git apply cowork/desktop/paseo-idli-split.patch`.
3. In `packages/app`: `PASEO_WEB_PLATFORM=electron npx expo export --platform web`.
4. Tar the output and install it with `install-paseo-ui.sh FILE=…`.

## History

`chronology/` (repo root) records each step. The latest are `2026-11-13T1155-drivey-whatsappy-canvay-p16.md`,
`2026-11-14T0011-grounded-9b-two-proposals.md` and `2026-11-14T1500-loop-fix-chart-popover-file-privacy.md`.
