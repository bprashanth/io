# Masked Claude reveals and newsroom visuals

Implemented in `benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/`.

## What changed

- `privacy.py` derives personal/contextual classes and `code_info` from the shared vault and source columns. Personal uses win across files. Names, contacts, identifiers and exact coordinates stay personal. Unknowns fail closed. Contextual `district_name` and `organisation_name` headings work without treating them as people's names.
- `ccproxy.py` honours approved contextual reveals in outgoing masking and the leak check. Personal values remain guarded even with a forged reveal entry or a disabled masking switch. Reveal changes invalidate cached history. Consent tools keep their code argument through JSON and streamed responses.
- `unmask` and `lookup` open an authenticated local consent page on the right with focus. They wait at most 120 seconds. Approval is single use. Denial, expiry, failed page opening and changed classifications keep the value hidden.
- Each `IDLI_WORKSPACE` starts with three reveals. Pending requests cannot overspend. Budget is spent before a reveal is published. `/reveals` lists reveals and approved lookups. Each item has **Hide again**. **Allow 3 more** extends the current workspace's budget. Hiding does not refund a reveal.
- Lookup uses DuckDuckGo's HTML endpoint from this computer with a plain User-Agent and a 10 second timeout. It uses the approved query, rechecks classification, guards personal values and returns at most six masked title/URL/snippet records. It masks against the full vault across all files, including revealed values. Lookup does not enable proxy reveals or spend their budget.
- The launcher merges the two MCP permissions into `.claude/settings.json` under `permissions.ask`. It preserves other settings and copies the two new skills and their resources.
- `masked-data` explains when to propose lookup or unmask. It requires a short question to the person and one request at a time. `CLAUDE-masked.md` points to it.
- `newsroom-charts` supplies nine templates: sorted bars, comparison dots, annotated outlier, slope, small multiples, ranged dots, heat table, GPS points and district choropleth. Templates include finding headlines, units, source descriptions, direct labels and muted colours. The viewer adapts subtitle and facet labels to dark mode.
- Maps use bundled DataMeet TopoJSON. State boundaries: 36 features and 116,990 bytes. District boundaries: 641 features and 458,827 bytes. Both are served at `/geo/<file>`. The adjacent [source and licence notes](benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/lib/geo/README.md) record the pinned revision, licences and simplification. The rebuild script is included.
- Map validation checks local boundary files, object names, numeric coordinates, numeric district values and duplicate districts. Name matching tolerates case, spacing, a district suffix, common aliases and conservative fuzzy matches. Ambiguous names stay unmatched. Descriptions list unmatched districts. All-unmatched input returns a clear MCP error.
- Geoshapes flatten GeoJSON properties for the same source and Copy to Claude interactions as bars. GPS points use the existing mark interactions. Maps render locally with a projection fitted to the data. Small district maps have direct labels.

## Verification

All tests used synthetic files, fake Paseo and mocked search responses. No real accounts or model requests were used.

From the cowork directory, with `/tmp/idli-journey-venv/bin/python`:

```sh
python -m pytest tests/test_unmask.py lib/test_privacy.py lib/test_ccproxy.py lib/test_home.py tests/test_journey.py -q
python tests/check_unmask_browser.py
python tests/check_journey_browser.py
```

- Combined suite: **136 passed, 2 skipped**. The skips are the older optional `HOME_BROWSER=1` checks. Both dedicated browser suites run separately and pass.
- New headless suite: **3 passed**. It exercises actual MCP calls in worker threads with real local consent clicks: approve, deny and timeout for both tools, in light and dark at 360 px. It checks ledger hiding, budget grants, authentication and all nine templates in both themes. Each template renders and supports source popovers and right-click Copy to Claude. Browser requests stay on the local server.
- Existing journey browser suite: **6 passed**. Privacy review, chart pin/zoom/source/copy, Mini editor and saving still work.
- `2026-11-14-relviz/check_launcher.py`: passed. It runs the real launcher twice in a fake installation, preserves custom skills and settings, refreshes templates and checks both ask permissions.
- JavaScript syntax, shell syntax and `git diff --check`: passed.
- Updated older home test fixtures to use the current editable Mini draft/save flow and fake Paseo. Updated the expected MCP tool list and the short-number regression for the stricter fail-closed policy.

Screenshots: [76 synthetic page captures](benchmarks/runs/2026-11-14-unmask-visuals/shots/). The [browser validation record](benchmarks/runs/2026-11-14-unmask-visuals/browser-validation.json) contains all 18 template/theme combinations. Test fixtures live in `tests/test_unmask.py` and `tests/check_unmask_browser.py`. Test dependencies and the boundary rebuild script are in the same artifact directory.

## Limits

- Hide again prevents future sharing. It cannot remove a value from Claude's existing context. Removing a lookup record cannot undo a completed external search.
- The proxy and reveal list are shared by the data directory. Reveal budgets are per workspace. A contextual reveal is therefore available to other workspaces using the same data directory.
- Lookup sends the approved contextual search to DuckDuckGo. Its live service was not contacted in the tests. HTML changes or service challenges can yield no results. Masking covers known values and supported patterns. It cannot identify every possible paraphrase.
- Boundaries are a simplified historic snapshot. They are not a current district register. Unmatched or ambiguous names need review. Fuzzy matching is English-name based. Transliteration is not provided. District maps with more than 12 matched regions use tooltips instead of crowding direct labels.
- GPS maps show India state boundaries rather than street tiles. Closely grouped points within one state can show only that state's interior at the fitted scale.
- Integration with a live signed-in Claude/Paseo session was not exercised. No push was performed. No credentials were printed or added. No files under `~/.codex` were changed.
