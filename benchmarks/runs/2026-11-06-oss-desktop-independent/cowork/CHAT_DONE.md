# Drivey chat: completed

All changes are inside this COWORK directory. No push or deployment was performed. CHAT_TASK.md, ~/.codex and docs/sandbox.md were left untouched.

## What changed

- `lib/modes.py`: Drivey routing runs first in `privacy_route`, including on Muse and all 9B modes. `Start Drivey` gets the exact opening line. Claude chart messages are echoed. `Open Mini: <name> [<id>]` calls `mini_open`. Subsequent questions in that chat are mapped by the local 9B, then call `mini_ask(id, qid, params)`. Mini introductions, options, examples, answers and refusal lists are composed by code. The chat model never writes them.
- `lib/home.py`: constrained question-specific JSON schemas, explicit no-match, validated choices and numbers, and a second constrained 9B check of the selected calculation and its parameters. Model outages decline instead of guessing. Laptop pages use MUSE_URL/the configured spec router; the DGX chat router uses IDLI_9B_URL (default port 8291). Script charts become SVG images and interactive views.
- `lib/drivestubs.py`: refreshes the uppercase `Drive/` mirror from the complete Drive index. Stub JSON has only id, url, kind and title. Refresh runs after indexing, at MCP startup, at launcher startup and before fetching. File and recursive folder mentions download through `drivefetch` into lowercase `drive/`; paths with spaces, duplicate file names, stale stubs, overlapping selections and source sidecars are handled. Download failures are reported per file while the remaining files are attempted. Selected sources are remembered per workspace for Mini saving.
- `sites/files/tools.py`: exports `drive_fetch`, `mini_open` and `mini_ask`. Bootstrap includes these in Drivey's tool allow-list.
- Privacy review: questions involving more than ten masked files with review set to ask show a warning suggesting Auto, both on the Send to Claude card and the privacy page. Home review shows the warning too.
- `lib/idli_mcp.py`: `idli_show` renders the CSV/spec to SVG, finds the workspace's left chat with the required label query, and posts the required chart message. Interactive clicks retain the correct Claude terminal. `idli_save_mini` records ISO date and author (IDLI_AUTHOR, account name, OS user), validates at most eight questions and three options per question, and requires listed choices/defaults. The launcher passes workspace identity explicitly into MCP configuration.
- `idli/CLAUDE-masked.md`: bounded questions/options, varied question types, choices/defaults, and testing every question against current files with results shown before saving. Visible text uses plain separators.
- `lib/formserver.py`: token-free, read-only `GET /api/minis-public`, containing exactly id, name, heading, date and author. CORS permits `paseo://app` and `null`. Private APIs retain their token checks.
- Laptop setup installs/upgrades vl-convert, includes the plain 9B model, and installs the stable `~/idli-insights/bin/claude-masked` launcher used by P19.

## Verification

Only synthetic workbooks from `benchmarks/runs/2026-11-13-grounded-9b/fixtures/drive` were used. The five sample scripts and their Mini manifest live in `lib/chat_fixtures/`.

```sh
.venv/bin/python -m pytest lib/test_chat.py lib/test_home.py lib/test_privacy.py lib/test_ccproxy.py -q
# 56 passed, 1 skipped (optional Chromium test)

COWORK_DATA_DIR="$PWD/.idli/index-test-data" .venv/bin/python -m lib.test_driveindex
# ALL PASSED

.venv/bin/python -m lib.eval_chat_mapping
.venv/bin/python -m lib.eval_chat_holdout
```

Python compilation, shell syntax, JavaScript syntax and `git diff --check` also pass.

Tests cover all four message kinds across every configured chat model and an unknown model, Mini state, actual script execution and SVG rendering, JSON constraints, mapper outages, stubs/refresh/folder expansion, failed downloads, filenames with spaces, source selection, author/date and limits, workspace MCP environment, label-targeted chart posting, public-list CORS and private API authentication, and the ten/eleven-file warning boundary.

An additional in-process integration check exercised `mini_open`, real 9B mapping, `mini_ask`, SVG creation and the exact code reply for both `idli-9b` and `muse-glimmer-30b`. Results: `lib/chat_router_results.json`.

### Real 9B mapping accuracy

The main fixed set has ten supported phrasings and three unsupported requests for each question type. A match is correct only if qid and every parameter match the expected values. Refusals require a null qid. The actual model was qwen3.5-9b on port 8291, temperature 0; these were real HTTP inference calls.

| Question type | Correct / total |
| --- | --- |
| Ranking | 13 / 13 |
| Filter by choice | 13 / 13 |
| Threshold | 12 / 13 |
| Comparison | 13 / 13 |
| Trend | 13 / 13 |
| Main set | 64 / 65 (98.5%) |
| Extra parameters through the real port-8186 spec router | 20 / 20 (100%) |
| Combined | 84 / 85 (98.8%) |

All twenty unsupported requests across both sets were declined. The one miss was a supported request: "Filter Kasewadi households to a debt to monthly income ratio greater than eight." It returned no-match and ran no calculation. The main run's median mapping time was 4.47 seconds (range 1.42-6.85 seconds).

Raw expected/actual results are in `lib/chat_mapping_results.json` and `lib/chat_mapping_holdout_results.json`. The extra set exercises different wards, measures, limits, number words, decimal thresholds and visit statuses.

During development, a single constrained pick scored 63/65 but accepted two unsupported comparisons. Prompt-only and short-reason variants scored 62/65 and 61/65. The final second check removed these false matches. The extra parameter set initially scored 19/20 before this check. Both fixed sets were rerun during development; these are regression measurements, not an untouched benchmark.

## Limits and rollout

- P19's UI patch is a separate task. This change implements the Idli contract; it does not edit or install Paseo's UI or create its split workspace.
- The local changes have not been copied to a laptop or loaded into the running chat router. After installing this code, rerun laptop setup/bootstrap to refresh the launcher, dependency and tool allow-list; restart the router and formserver, and open fresh chats. Drivey's formserver uses port 8797 when that port is available.
- Google downloads and Paseo chart posting were tested with synthetic files and CLI/HTTP doubles. No live Google account, Claude subscription session or graphical P19 session was used. Native files that Google cannot export, and inaccessible files, return download errors.
- Mapping can decline a supported paraphrase, as measured above; it does not fabricate an answer. Accepted mappings use two small-model calls. Failures of either call decline. The chat model is never used to compose a Mini answer.
- Mini scripts are trusted local Python scripts with a 60-second limit, not a command sandbox. Questions without chart output have text examples; chart-producing scripts have SVG and interactive examples. Existing Minis saved before this change retain blank date/author fields until saved again.
