# E3 rescoring: task for Codex

Write `harness/e3_rescore.py` (and nothing else; do not edit any other file). It rescores E3 chat logs strictly,
per hop, and prints a table per run folder. Work only inside this eval folder. No network. Do not print keys.

## Inputs
- Chat logs: `results/e3/<run>/<chat>.json` (run = e.g. `local-qwen35-9b-r0`, `muse30b-r0`). Each has `turns`
  (list; `turn["step"]` indexes `scenarios/e3.json` conversation `steps`; `turn["events"]` with `type`
  model/tool/card/guard, `name`, `args`, `result`, `error`, `text`).
- Scenarios: `scenarios/e3.json`. Each chat has 6 steps: 0 link, 1 card pick, 2 control question (the form can
  answer; `check.ref.spec` is the form spec), 3 hard question (form can't; `check.tools_any` says teach_file or
  chart_request), 4 card "yes", 5 the same hard question re-asked (`check.ref.numbers`, or `tools_any` chart_show).
- Claude's output per bounce: `results/e3-logs/<run>/<chat>/teach/<request_id>/` with `transcript.json`,
  `request.json`, `skill/` (the extended skill; chart code in `skill/charts/<name>.py`, function
  `make(tables, plt)` returning a matplotlib figure).
- Real fixtures: `fixtures/<ref_file>.xlsx`. Find how Idli builds `tables` for chart code (cowork
  `lib/chartkit.py`, at `../2026-11-06-oss-desktop-independent/cowork/lib/`) and do the same, in-process (no
  bubblewrap needed; this is the synthetic fixture). Use `../2026-11-06-oss-desktop-independent/cowork/.venv/bin/python`.

## Per chat, score these hops (booleans unless said)
1. `control_ok`: step 2 called `file_ask` and did NOT call `teach_file` or `chart_request` (else `wrong_bounce`=1).
2. `routed`: step 3 called `teach_file` or `chart_request` (either counts). Record which (`route`).
3. `sent`: step 4 has a `teach_send` event whose result has `done` true -> also `claude_done`. Record minutes
   (`secs`/60), `claude_cost`, `cards` from that result.
4. `came_back`: after `teach_send`, step 4 or 5 has a successful `chart_show` or a `file_ask` without error.
5. `answered_right` (the point of the eval), against step 5's `check.ref.numbers` (list of floats):
   - if the bounce produced chart code: run the chart code that `chart_show` showed on the real fixture, read the
     plotted values from the figure (bar heights/widths from `ax.patches`, line y data from `ax.lines`), and pass
     if every reference number is within 0.6 of some plotted value (percent shares are compared as given; if
     plotted values look like fractions 0-1 and refs are > 1, multiply by 100). Also record the plotted values.
   - else: pass if every reference number appears (within 0.6, after stripping % and commas) among the numbers
     in the model's texts in steps 4-5, or in the `file_ask` results' answer text there.
   - if there is no ref.numbers and the check is chart_show, pass if chart_show ran without error.
   Record `answered_how` = chart|text|none and `got` numbers.
6. `never_returned`: sent but not came_back.
7. `secs` total from the log.

## Output
- `results/e3/rescore.json`: one record per chat log.
- Print a markdown table per run: chats, control ok, wrong bounces, routed, sent, Claude done, came back,
  answered right, mean minutes per bounce, mean $ per bounce. Then a per-chat table (run x chat: route, answered
  right, plotted/got numbers vs ref).
- It must work while the batch is still running (skip missing logs).

Done = runs cleanly on `results/e3/local-qwen35-9b-r0/e3-tree-canopy-size.json` (that chat bounced as
chart_request; its chart code is at `results/e3-logs/local-qwen35-9b-r0/e3-tree-canopy-size/teach/*/skill/charts/`),
prints the tables, and you state in your final message what the plotted values were vs the ref
(65.12, 69.02, 69.12).
