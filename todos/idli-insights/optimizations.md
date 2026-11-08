# Idli: optimizations not yet integrated

Running list of things we've measured or spotted that could make Idli faster or cheaper, mostly by moving work
off Muse (the private 30B) onto a smaller model or onto plain code. **Only what isn't integrated yet**: once
something ships, delete it from here (the chronology in `docs/cowork-poc.md` records it). Decision for now
(2026-11-08): Muse does everything; these wait.

Privacy rule for every item: a smaller model only counts if it runs locally (laptop or Muse's server). The 9B
today goes through OpenRouter, so file names, summaries and questions would leave the machine.

| # | Optimization | What it saves | Evidence so far | What's missing |
|---|---|---|---|---|
| 1 | **Find without a model**: a search box on the drive-index page (or the chat front end) calls `driveindex.search` directly; the model only joins to open a form or answer about contents | Muse's 30-80 s per "find" turn becomes ~0.3 s | Index alone: right file first 22/25, top 3 24/25 ([search eval](../../benchmarks/runs/2026-11-08-oobe/search_eval.py)) | Page UI; how a result hands off to an Idli chat |
| 2 | **Smaller local model for find turns** (9B class): it only calls `drive_find` once and relays the answer | ~7 s vs 34-80 s on Muse when the result is clear | 4-question chat test: 9B 7 s on a clear hit, but wandered (downloads, 3 extra live searches, up to 150 s) when unclear; Muse steady on 3/4 ([search_chat.jsonl](../../benchmarks/runs/2026-11-08-oobe/search_chat.jsonl)) | Run locally; rerun on all 25 questions with the "find doesn't download" rule |
| 3 | **Vector index over the info cards** (name, type, folder, summary, 300 chars of first rows; one vector per file, fastembed bge-small) | +1 question over today's lexical search; 4 ms per search; helps "described" questions | 23/25 first vs 22/25 lexical; blending added nothing | Worth it only for bigger, messier Drives: re-measure there |
| 4 | **Smaller model for index summaries** (4B class instead of Muse) | Frees Muse's 4 slots during the 1-2 min summarising phase | Summaries are one line from name + folder + 400 chars; same quality bar as search eval | Compare search hit@1 with 4B-written vs Muse-written summaries |
| 5 | **Skip or cap Muse's reasoning on simple turns** (greeting, go-ahead, relaying a tool result) | Most of each 30-80 s turn is reasoning at ~30 tok/s, even on low thinking | OOBE and chat timings ([OOBE run](../../benchmarks/runs/2026-11-08-oobe/)) | A per-turn reasoning budget, or a no-think mode for tool relays |
| 6 | **A small router** that decides find / form question / other before Muse sees the turn, sending finds to #1 or #2 | Muse only for turns that need it | Form-fill eval: 3-4B models fail at building specs (21-36%) but a route is a much smaller job | Build and score a router on real phrasings |
