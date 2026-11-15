# Binder in the Drivey chat, Sent to Claude log, lookup withheld (2026-11-15 afternoon)

## Decisions (owner)
- `lookup` withheld from Claude: reveal then WebSearch. Search stays for the 9B later. Running a script on the real
  file with masked output is the p1 todo `run_on_real.md`.
- Wire log in Start here, per app, searchable, kept simple.
- Charts and the Mini draft go in the left chat as a running binder.
- Query service: keep DeepSeek for now, bound the cost, plan a smaller-model experiment (p1 `query_service_model.md`).

## Built
- `lib/wirelog.py` + `/wire` page ("Sent to Claude", tab in Start here). Always on: one line per request with only
  what was new, app tag from `X-Idli-App` (dropped before forwarding), refused requests keep only the codes. 7 days.
  The folder is in Claude's sandbox deny list from first launch. Laptop: 21 requests = 124 KB (about 6 KB each; full
  bodies were about 150 KB each).
- Binder: `idli_show` and `idli_draft_mini` send "Chart from Claude: <title>" / "Mini draft from Claude: <title>" to
  the left chat; the router calls the new laptop tool `binder_item`, which returns the inline page. The chart shows its
  headline, Pin and source note, sized to its box. The Mini draft is the editor page inline (`/mini-card`): growing
  question boxes, options folded, pinned charts, Save. No Paseo rebuild (it already embeds `view` and `mini-card`).
- Query service bounds: reply cap 700 tokens, column list cap 12,000 characters, 200 calls a day.
- Start here's own server was down after earlier restarts (Minis tab said Forbidden); restarted and the tab repointed.
  The laptop restart script now leaves it alone.

## Tested on the laptop, start to finish (owner's field_vars_indicators file, Paseo idli21, real Claude, 9B)
New Drivey workspace; question with the Drive file; Accept Idli's choices; masked question card; Switch to Claude;
Claude's answer; two charts arrived in the left chat in order, each pinned; /mini; Claude built five questions, ran
every option and posted the draft; edited question 1 inline and saved; a new Drivey chat lists the Mini; opening it
shows the pinned charts and the edited question; "which transects have big cestrum trees?" mapped to question 2 and
answered with a table and chart.

## Findings left
- The 9B didn't map "where along the transects does cestrum grow?" to question 2 (big-tree wording); the query
  service answered from the Density sheet instead. Correct but different. Worth a mapping eval case.
- The chat shows "Chart from Claude: ..." as the person's own bubble (no Paseo change). Fine for now.
- Each Drivey workspace's tool process loads code at start, so code changes need a new workspace.
