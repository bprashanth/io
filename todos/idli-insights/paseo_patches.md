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
| P6 | **Cosmetic**: no red `GUEST_VIEW_MANAGER_CALL ... ERR_FAILED (-2)` line when a navigation turns into a download | Looks like an error to people; it's only the page load being replaced by the file | ❌ optional |

Notes
- Tab layout (which tabs, their order) is saved per workspace in the app's storage too; Start here's chat ends up
  as tab 0 because the bootstrap creates it before opening the Drive and Gmail tabs.
- Plugins (`packages/plugin`) run in the daemon and app UI, not in the browser session: P1 can't be a plugin.
  The bootstrap could be one (daemon lifecycle hooks).
