# 2026-11-07, 17:50 IST — Laptop: co-work / DIY POC, the gap loop closed once, Muse 30B vs a 9B

Building on the [16:15 checkpoint](2026-11-07T1615-laptop-desktop-ux-and-cowork.md), the owner asked for a
POC of two modes, with deliberately cheap shortcuts:
- **DIY:** Claude Code builds site plugins against test accounts and mock files.
- **Co-work:** the shell-less private model uses those plugins on real accounts.

[Code, layout and the full results table](../benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/README.md).

## Built

- **Site plugins** (`sites/<site>/tools.py` plus `site.json` and `tests.json`):
  - `google`: Gmail, Drive and Docs, as before, now pinned to an account by `?authuser=`.
  - `sheets`: Excel/CSV in the workspace folder through DuckDB. It detects the header row under title rows, lists
    spelling-variant groups, runs read-only SQL, and writes bar-chart dashboards as plain HTML with inline SVG.
- **`cowork_mcp.py`:** loads the sites listed in the workspace's `cowork.sites` file. It adds `report_gap`, which
  prints a fixed-form report the user scrubs and pastes into DIY.
- **`run_tests.py`:** runs each site's tests against its test account, and fails with "sign in and rerun" when that
  account isn't signed in. Account-specific IDs live in a non-committed `accounts.local.json`.
- **DIY:** an `add-site` skill, a `CLAUDE.md` with scope rules, and Claude Code sandbox settings. The Paseo provider
  "DIY · Claude" runs in that folder.
- **`dashboard-links` Paseo plugin:** a reply that mentions an `.html` file gets an **Open** button. The plugin
  serves the file on 127.0.0.1 and opens it in that workspace's browser tab through the daemon's
  `browser_new_tab`. Timeline rows get no `navigation.openBrowser`, hence this route.

## Results (one run each)

| Step | Model | Result |
|---|---|---|
| Synthetic field-visits Excel | Muse 30B | 1m44s. Referrals right (41/120); top village wrong (merged case but not spellings). Dashboard renders in the workspace browser |
| "Highest P/BV in my Drive sheet?" with no sheet tool | Muse 30B | Called `report_gap`, with paste instructions. It put the sheet's name in the report |
| Scrubbed report pasted into DIY | Claude Opus 5.5 | 12m56s, 33 steps. Built `gsheet_read` (gviz HTML via snapshot → CSV → `sheets`). Tests 8/8 |
| Retry in a new co-work chat | Muse 30B | 2m09s, correct (Kotak 4.21; India 2.915 vs US 0.6975) |
| Excel / AWS email / Wildfires / P/BV | Qwen3.5-9B via OpenRouter | Excel: top village right, referrals wrong (18). AWS: ❌ "no such email" after 29 calls. Wildfires: mostly good, a few wrong fixes. P/BV: ✅ |

## Problems found

- **The Linux sandbox blocks the local Paseo port.** Claude Code's sandbox blocked 127.0.0.1:6767 even with
  `allowedDomains`. In bypass mode DIY re-ran its commands unsandboxed, so the sandbox was not a boundary.
- **Qwen3.5's template rejects mid-conversation system messages**, which Claude Code sends. Patched in
  `local-9b/qwen35-midsystem.jinja`.
- **Gmail `/mail/u/<email>/` gives "Temporary Error"; `?authuser=` works.** The first attempt navigated away from
  the tab holding the earlier LinkedIn draft. The draft was safe in Drafts.
- **The first tab in a fresh workspace times out.** That broke one 9B run; there is now a retry.
- **Infrastructure:**
  - The laptop CPU 9B ran at about 8–20 prompt tokens/s, 29 minutes per task.
  - The DGX needed a Tailscale re-auth and had no 9B running.
  - So OpenRouter was used by the owner's choice. The test data went to OpenRouter.
  - The local model, image and provider were purged; the laptop has no space.
- **The Paseo app was restarted with `--remote-debugging-port`** to screenshot the button while the screen was
  locked. Its tabs were restored.

## Not done

- 9B on the DGX GPU.
- Real isolation for DIY.
- A merge/clean tool for spelling variants.
- Focusing the dashboard tab automatically.
- Repeat runs.
- Testing whether non-developers can use the DIY loop.
