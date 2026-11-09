# Paseo patches for Idli

Changes to Paseo (https://github.com/getpaseo/paseo, we run v0.15.2) that Idli needs. Each is small, kept as a
patch file until we decide between upstream PRs and our own build. Running list.

| # | Patch | Why | State |
|---|---|---|---|
| P1 | **Silent browser downloads**: a `will-download` handler on the browser profile session saves into `PASEO_BROWSER_DOWNLOAD_DIR` (or Downloads), never overwriting | Without it, a download from Paseo's browser opens a system Save dialog titled with the long Google URL, often behind the app; Idli can't click it, and people don't recognise it | ✅ written + vitest: `benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/desktop/paseo-browser-downloads.patch`; not built or installed |
| P2 | **Default sidebar order from config**: when the app has no saved order, order projects (headings) by a list in `~/.paseo/config.json` (e.g. `"sidebar": {"projectOrder": ["Start here", "Idli", "Claude"]}`); anything the user drags later wins | Heading order lives only in the app's local storage (`packages/app/src/stores/sidebar-order-store.ts`), which nothing outside the app can set, so a fresh install shows headings in arbitrary order | ❌ to write |
| P3 | **Default permission mode per provider**: let a provider in `config.json` set its default mode (e.g. `"defaultModeId": "bypassPermissions"` for the Idli providers) | Claude-based providers default to Auto (`claudeModeCatalog` in `packages/server/src/server/agent/providers/claude/agent.ts`); Auto's safety check can't run with Muse, so every tool call in a new Idli chat is blocked until the user switches to Bypass | ❌ to write |
| P4 | **Pinned tab** (optional): keep a chat (Start here) as the first tab, not closable | Paseo can pin workspaces, not tabs; dragging the tab first does persist, so this is nice-to-have | ❌ optional |
| P5 | **Hide providers** (optional): a config switch to hide built-in providers (Claude, Codex, OpenCode, ...) from the model picker | The picker shows every provider; an Idli install should show only Idli 30B, (Idli 9B), Claude | ❌ check whether `enabled: false` in config already does this |
| P7 | **Show a browser tab from outside the app**: extend the agent deep link (`paseo://h/<server>/agent/<id>`) to workspace tabs, e.g. `paseo://h/<server>/workspace/<id>?open=browser:<tabId>` (the app already parses `?open=` for agent/terminal/file/draft tabs) | After a yes on a card, Idli brings the drive-index progress tab forward. Today `lib/uiswitch.py` clicks it through the DevTools port, which only the dev launcher opens. Chats (to the Teach chat in Claude and back to Idli) already work in a normal install via the existing agent deep link | ⚠️ prototype via DevTools; patch to write |
| P6 | **Cosmetic**: no red `GUEST_VIEW_MANAGER_CALL ... ERR_FAILED (-2)` line when a navigation turns into a download | Looks like an error to people; it's only the page load being replaced by the file | ❌ optional |
| P8 | **Links in chat open in a Paseo tab** (in this workspace) instead of the system browser, at least for docs.google.com / drive.google.com | "Found tech_reimbursement_form" could be a link to peek at the file. Today Idli asks with a card and opens the tab itself (`file_peek`), which works without a patch | ❌ optional |
| P9 | **Upload a file into a browser tab** (or a daemon call that drops a local file onto a tab), for Drive uploads | `working_copy` puts a marked-up copy next to the original in Drive by dropping the file on a Drive folder tab. Dev builds do it through the DevTools port (`Input.dispatchDragEvent`, `lib/uiswitch.py` Page.drop_file); a normal install has no way in, so Idli says where the local copy is and the person drags it in | ⚠️ prototype via DevTools; patch to write |
| P10 | **Delete in the app** (chat and workspace menus), not only Archive | The app only archives; archived chats stay in `~/.paseo` forever and people expect Delete to remove them. The CLI already has `paseo delete` | ❌ optional |
| P11 | **Browser tab viewport = visible pane**: when the window is narrow, size the guest page to the pane it is shown in | Seen 2026-11-09: a dashboard tab laid out at 1280 px while the pane was 630 px, cropping its right side; another tab in the same workspace correctly reported 630 | ❌ to investigate (repro: narrow window, open a browser tab, switch tabs) |

Notes
- Tab layout (which tabs, their order) is saved per workspace in the app's storage too; Start here's chat ends up
  as tab 0 because the bootstrap creates it before opening the Drive and Gmail tabs.
- Plugins (`packages/plugin`) run in the daemon and app UI, not in the browser session: P1 can't be a plugin.
  The bootstrap could be one (daemon lifecycle hooks).
- Until P1 ships, dev builds skip the Save box by setting each browser tab's download behaviour over the DevTools
  port for the length of one download (`lib/uiswitch.py` QuietDownloads, used by `file_get`). Browser-wide
  `Browser.setDownloadBehavior` does not reach Paseo's browser tabs; per-tab `Page.setDownloadBehavior` does.
