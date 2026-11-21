# Co-work POC: DIY mode builds site tools, co-work mode uses them on private data

The POC splits the work between two models:
- **DIY mode** (Claude Code, the user's own subscription) writes "site plugins" against **test** accounts and mock files.
- **Co-work mode** (the private T4GC model, no shell) uses those plugins on the user's **real** accounts and files.

The user's personal data only reaches the private model. When co-work can't do something, it prints a
gap report. The user removes personal details from it and pastes it into DIY. DIY builds the tool, and the
user retries in a new co-work chat.

Everything here is a laptop POC (Pop!_OS, Paseo 0.15.2) with the shortcuts listed under "Caveats".

## Layout

| Path | What |
|---|---|
| `sites/<site>/tools.py` | One plugin per site: `TOOLS = {name: (fn, description, schema, required)}` and `whoami()` |
| `sites/<site>/site.json`, `tests.json` | What it covers, and the tests run against the test account |
| `sites/google/` | Gmail search/read/draft, Drive search, Docs read, **`gsheet_read` (written by DIY mode, see below)** |
| `sites/sheets/` | Excel/CSV in the workspace folder: profile (header detection, spelling variants), DuckDB SQL, bar-chart dashboards |
| `lib/browser.py` | Drives the user's tabs in Paseo's workspace browser through the daemon's agent endpoint |
| `lib/accounts.py` | Picks the test account when testing, the signed-in account in co-work |
| `cowork_mcp.py` | Co-work MCP server. Loads only the sites listed in the workspace's `cowork.sites` file and adds `report_gap` |
| `run_tests.py` | Runs every site's tests against its test account and records pass/fail in `site.json`. If the test account isn't signed in, the test fails with "sign in and rerun" |
| `.claude/skills/add-site/`, `CLAUDE.md`, `.claude/settings.json` | DIY mode: the build skill, the scope rules and the sandbox settings |
| `dashboard-links/` | Paseo plugin. A reply that mentions an `.html` file gets an **Open** button, which serves the file locally and opens it in the workspace browser |
| `make_sample_sheets.py` | Synthetic NGO field-visit workbooks: `test` is the mock; `real` stands in for private data |
| `~/idli-insights/config/accounts.json` (outside the repo) | `{"google": {"test": "<email>", "fixtures": {...}}}`; see `lib/accounts.py` |

## Paseo wiring (`~/.paseo/config.json`)

- `pluginsEnabled: true`, plus the `dashboard-links` plugin.
- `daemon.browserTools.enabled: true`.
- **`t4gc-cowork`, "Co-work · T4GC":**
  - extends `claude`;
  - `--mcp-config cowork.mcp.json`;
  - `CLAUDE_CONFIG_DIR` → Muse;
  - `ENABLE_TOOL_SEARCH=false`;
  - `disallowedTools` removes Bash, the file and web tools, Task, Skill and `mcp__paseo`.
- **`cowork-9b`:** the same, pointed at a local llama.cpp Qwen3.5-9B (see below).
- **`diy-claude`, "DIY · Claude":** plain `claude`. Its workspace is this folder.

## Results (2026-11-07, one run each)

| Test | Model | Time | Result |
|---|---|---|---|
| Field-visits Excel: top village, referrals, dashboard | Muse 30B | 1m44s, 11 calls | Referrals ✅ 41/120. Top village ❌: Halaguru 31 instead of Kirugavalu 32. It merged case but not spelling variants, and offered to. Dashboard ✅ |
| Same | Qwen3.5-9B, laptop CPU (llama.cpp) | 29m | Referrals ✅. Top village ❌: 19, no merging at all, despite the new `spelling_variants` warning. Dashboard ✅. Tried `drive_search` first |
| Same | Qwen3.5-9B via OpenRouter | 33s, 9 calls | Top village ✅ Kirugavalu 32 (used `spelling_variants`). Referrals ❌ 18: it counted Y/y but missed "Yes". Dashboard ✅ |
| Dashboard link | — | — | ✅ Open button under the reply, which opens a rendered page in a workspace-browser tab. The tab does not come to the front by itself |
| "Which bank has the highest P/BV in my Drive sheet?" with no sheet tool | Muse 30B | 2m24s | ✅ Found the sheet, tried the sheets tools, called `report_gap`, and showed the report with paste instructions. It put the sheet's name in the report, which is why the user scrubs it |
| Paste the scrubbed report into DIY | Claude Opus 5.5 | 12m56s, 33 steps | ✅ Used the `add-site` skill and built `gsheet_read` (gviz HTML table via snapshot, tab names from the edit page, CSV handed to `sheets`). Tests 8/8 |
| Retry in a new co-work chat | Muse 30B | 2m09s | ✅ Kotak 4.21 highest; India 2.915 vs US 0.6975, both correct |
| AWS "payment not received" email | Qwen3.5-9B via OpenRouter | 4m17s, 29 calls | ❌ Said no such email exists. It fixed on `from:invoicing@aws.com`, but the mail is from no-reply@amazonaws.com. Muse found it in 11 calls |
| Wildfires grammar | Qwen3.5-9B via OpenRouter | 36s, 2 calls | ✅ mostly: 17 corrections, a few wrong or unneeded ("diss"→"dismiss", a mangled "are", quoting x/y). The first try failed on a browser-tab timeout (now retried) |
| P/BV sheet (uses DIY's `gsheet_read`) | Qwen3.5-9B via OpenRouter | 33s | ✅ Kotak 4.21; India 2.92 vs US 0.70 |

## Findings

- **Narrow tools beat raw pages.** On the same Muse, Excel and Sheets questions finish in about 2 minutes,
  with only tool results in context.
- **Cleaning is where small models slip.** Both models counted spelling variants as separate villages.
  The profile now lists the variant groups. The next step is a tool that applies the merge, rather than relying on SQL.
- **The gap → DIY → retry loop works end to end with copy and paste.** The report is generated by a tool, so its
  format is stable. The model still writes personal names into it.
- **The Claude Code sandbox on Linux blocks the local Paseo port.** That happened even with
  `network.allowedDomains: ["127.0.0.1:6767"]`. In bypass mode DIY simply re-ran its commands outside the sandbox.
  So the sandbox is not a boundary here as configured. A fix would be `excludedCommands` for the test runner only,
  or a Unix-socket proxy.
- **Qwen3.5's chat template rejects Claude Code's mid-conversation system messages.** I patched it to render
  them in place (`qwen35-midsystem.jinja`).
- **On Muse, first-turn latency is spent reading Claude Code's own prompt**, not on the question. Measured
  2026-11-07 with "are you there?":

  | Provider | Prompt size | Reading it | Total |
  |---|---|---|---|
  | `t4gc-claude` (all tools) | 33,752 tokens | 38.2 s at about 880 tokens/s | 40.4 s |
  | `t4gc-cowork` (shell and file tools removed) | 16,438 tokens | 19.2 s | 22 s |

  Anthropic's servers have the same prompt cached, so Claude replies in about 10 s. Muse's prompt cache had
  evicted it ("removing oldest entry"). Ways to cut it, none of them tried yet:
  - a larger llama.cpp prompt cache on the DGX (`--cache-ram`), so the shared Claude Code prefix stays warm
    across chats;
  - fewer slots;
  - a shorter Claude Code system prompt for co-work.
- **Gmail `/mail/u/<email>/` URLs give "Temporary Error".** `?authuser=<email>` works for Gmail, Drive and Docs.

## Caveats (POC shortcuts, agreed)

- DIY is kept in bounds by instructions and settings, not real isolation. Paseo workspaces share one cookie
  store, so test and real Google accounts are separated by `authuser`, not by the browser. In this POC the
  "test" Google account and the "real" one are the same account.
- Users remove personal details from gap reports by hand.
- The agent endpoint the plugins use has no authentication when the Paseo daemon has no password.
- Single runs. The OpenRouter 9B runs sent that test data (Gmail, Drive and the synthetic sheet) to OpenRouter.
  That was a deliberate test-only choice because no 9B was running on the DGX. Real use would serve the 9B on
  the DGX (`local-9b/serve.sh` plus the template; the laptop has no space for it). The laptop CPU run (about
  8–20 prompt tokens/s) was stopped and purged.
- The first browser tab in a fresh Paseo workspace often times out. `lib/browser.tab_for` now retries and re-checks.
