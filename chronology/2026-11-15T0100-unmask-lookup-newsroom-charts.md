# Unmask, lookup and newsroom charts for the masked Claude

Built by Codex on `exp/unmask-visuals` (merged) to the design agreed on 2026-11-14. Then tested live on the DGX with
the real Claude Code CLI (interactive, in tmux), the masking proxy with its wire log, Idli's tool server and a headless
browser clicking the consent pages. The laptop went offline (its tunnels to the DGX dropped), so the laptop run is
still to do. Synthetic survey: 32 households with names, phones, ward, district, income, debt and GPS.

## What exists now
- **Column classes:**
  - personal: names, phones, emails, addresses, IDs, exact locations;
  - contextual: places, programmes, categories;
  - unknown counts as personal.
- **`unmask(code, reason)`:**
  - refuses personal codes;
  - for a contextual code, opens a consent page beside Claude showing the code, column, real value and reason, with
    "Reveal to Claude" / "Keep hidden";
  - Claude Code's own "Do you want to proceed?" prompt comes first (an "ask" rule that overrides auto mode);
  - 3 reveals per workspace, with "Allow 3 more" and "Hide again" on the /reveals page;
  - the proxy keeps blocking personal values even if one was listed as revealed.
- **`lookup(code, query, reason)`:**
  - the same two consents;
  - the search runs from this computer with the real value; Claude never sees the value;
  - results are masked before Claude gets them.
- **Skills:**
  - "masked-data": when to propose a lookup or unmask, and never for people;
  - "newsroom-charts": 9 templates, including GPS points and district maps from bundled DataMeet boundaries.

## Live test on the DGX (what happened)
- **Lookup:**
  - asked "is anything known about that area?";
  - Claude offered a web search in plain words;
  - CLI prompt -> Yes; consent page -> Allow search;
  - Claude: Satpur looks urban and industrial (news on Ambad-Satpur pollution, a planned metro), so drought or crop
    failure are unlikely; the survey cannot say why people borrowed; suggested asking about loan purpose and lender
    next time.
- **Unmask:**
  - to compare with the municipal ward list, CLI prompt -> consent page -> Reveal;
  - Claude: "The ward's real name is Satpur ... used one of this workspace's three reveals."
- **Asked for a person's name:**
  - Claude did not call unmask;
  - it said it cannot reveal names to itself and that the person's screen already shows the real name and phone;
  - no consent page opened.
- **Charts:**
  - a bar chart with a finding headline ("In one ward, debts equal almost 6 months of income"), Satpur highlighted
    and the rest grey;
  - a GPS map of all 32 households;
  - "Where did this come from?" works on map points.

## Found by auditing the wire, and fixed
1. **DuckDuckGo answers scripts with a bot challenge** (HTTP 202 "anomaly"), so every lookup was empty. Lookup now uses
   Google News RSS (recent local news) and Wikipedia search (background). If the full query finds nothing, it retries
   with the value alone.
2. **A place name went out inside a link** (`/wiki/Satpur_Kamil_Madrasah`), 40 s before the person revealed it.
   Masking now also finds values joined by `_` `+` `-` `%20` inside web links.
3. **Coordinates went out when printed with a trailing zero** (73.7354 as `73.73540`). Decimal values now match with
   trailing zeros.
4. **My first fix for 2 masked Claude's own tool name**: the scanner had once tagged "Idli" as a name, and with
   underscores as separators `mcp__idli__idli_show` became `mcp__NAME_032__NAME_032_show`, so charts stopped working.
   - The underscore rule is now limited to links.
   - Idli, Claude, Drivey, Paseo, Mini, Anthropic and Codex are never private.
   - The leak check follows the same rule. Before that, it refused a request, which was the safety net working.
5. **Charts failed on the DGX with an unhelpful error.**
   - The chart tool looked up the Claude terminal through Paseo's CLI, which the DGX lacks; that lookup is now
     optional.
   - Tool errors now pass Idli's own plain message through, with any path or page token removed.
6. **The skills linked their templates as `templates/...`**, which Claude read relative to its work folder. The links
   now use the full `.claude/skills/<skill>/templates/` path.
7. **GPS maps:**
   - every point carried its ward label, so 14 "Satpur" labels piled into a smudge;
   - the points had no colour;
   - bands sorted alphabetically.
   - Now: one label per group at its centre; `idli_map.color` colours the points; bands ordered by their numbers
     ("Under 3" < "3 to 6" < "Over 6").

Final live run, 18 requests to Anthropic:
- **Private values:** 0 names, 0 phones, 0 coordinates in any format, 0 wards or districts.
- **Lookup results:** reached Claude with the place masked.
- **Tool names:** intact.
- **Refused requests:** none.

Tests: 138 passed (2 optional skipped); browser suites for consent, reveals, the 9 templates and the journey pages
pass; the launcher check passes.

## Still to do
- Repeat the live run on the laptop with idli21 in Paseo (consent page on the right of Claude, real Drive files).
- Map basemap: state outlines only. Points close together overlap.
- The DGX's own `~/.claude` Stop hook ("MODEL GUARD") shows up in the masked Claude here; the laptop has no such
  hook.
