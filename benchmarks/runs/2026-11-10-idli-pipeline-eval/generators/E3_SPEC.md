# E3 task for cursor-agent: the bounce to Claude, end to end

Goal: measure whether a question the form can't answer (or a chart it can't draw) goes to Claude and comes back
answered. Idli's chat model is the local 9B (Qwen3.5-9B Q5 served by `harness/serve9b.sh up`, model id used in E7:
see `results/e7-local12` and `variants/e7-soft12`) with the split, 12 shipped tools, soft phases (variant
`e7-soft12`). Muse is the baseline (model id `muse30b`, same variant). The chat harness is the 9B benchmark's:
`../2026-11-10-idli-9b/harness/{convo.py,idli.py,run.py,score.py}`, run through `harness/e7_env.sh`
(see `harness/e7_one.sh` for one chat). Read those first, and `harness/teach_run.py` (headless Claude Code teaching
with the product's teach-file skill, Haiku as the scripted owner).

## Files to create (do NOT edit cowork/lib/filekit.py; other work is editing it right now)
1. `scenarios/e3.json` (same format as `scenarios/held3.json`): 9 chats about the round-1 files
   (`fixtures/*.xlsx`: tree_plots_transects, household_survey_messy, field_visits_messy,
   germination_protocol_filled; NOT tax_missing_info_fake). Each: the link → (card click to analyse) → one normal
   question the form answers (control) → one question or chart the form CAN'T do (a measure/filter it lacks, e.g.
   "average DBH per species only for trees taller than 10 m" if no such filter; or a chart: share of a total, two
   filters side by side, a trend of a computed value) → the card yes to send to Claude → the "teaching finished"
   message → the same question again. Also 2 of the 9 chats should ask something the form CAN answer but phrased
   unusually (to count wrong bounces). Natural, analyst-level phrasing in the owner's voice. Write the reference
   answers by running the form engine on the real fixture with the spec Claude would need (for the re-ask after
   teaching, the reference is computed with pandas directly from the fixture; store it as numbers in the check).
2. The starting forms: each fixture needs a learned skill before the chat. Use the round-1 skills from
   `results/e6/fake/<stem>/skill/` (copy them into the chat's Idli home as the harness expects). Register the
   fixtures in the chat's fake Drive (see how idli.py `_drive()`/fixtures/drive works) with their links.
3. `harness/e3_bounce.py`: runs one E3 chat. It drives convo.py's loop (import it, or add a small hook in
   idli.py's `_teach_send` stub ONLY behind an env var such as IDLI9B_E3=1, default unchanged) so that when the model
   calls `teach_send` (after `teach_file` with `missing`) or `chart_request`'s yes, the harness:
   - takes the request Idli made (its inbox folder: request.json + mock.xlsx with fake values),
   - runs headless Claude Code with the teach-file skill on it, as `harness/teach_run.py` does (reuse its functions;
     add a mode that takes an existing request folder instead of making one). Haiku is the owner, answering from
     `fixtures/<stem>.doc.md`.
   - copies the extended skill (or the chart code) back into the chat's Idli home, exactly as the real product's
     "back to Idli" does (see cowork `sites/files/tools.py` and `lib/teachwatch.py` for what the watcher does),
   - continues the chat with the product's message that teaching finished (find the exact text in tools.py /
     teachwatch.py), then the scenario's re-ask.
   Records per hop: routed (teach_file/chart_request called, with `missing`), card yes → sent, Claude finished
   (minutes, cost, cards), skill/chart came back, re-ask answered (numbers match the reference) or chart_show ran on
   the real data without error; plus wrong bounce (control/unusual questions sent to Claude) and never-returned.
4. `harness/e3_table.py`: summary table per model: chats, routed right, sent, Claude done, came back, answered
   right after, wrong bounces, minutes per bounce, $ per bounce.
5. Run: first 1 chat on the 9B as a smoke test and fix problems; then all 9 on the 9B (2 repeats) and once on Muse.
   Muse is shared and must not be stopped: run its chats one at a time. Start the 9B with `harness/serve9b.sh up`
   and leave it up. Run long things in the background with nohup and logs under `results/e3-logs/`; results under
   `results/e3/<model>/`.

Rules: no Claude or other model ever sees the real fixture values (Claude only gets Idli's fake copy, as in the
product). Don't touch the owner's real files, ~/.codex, or anything outside this eval folder except a guarded hook
in `../2026-11-10-idli-9b/harness/idli.py`. Don't print API keys. Do not commit. Finish by printing the e3_table output.
