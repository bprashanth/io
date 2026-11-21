# Handoff prompt for the next agent (2026-11-21)

Paste this to start a new agent on this repo. Keep it current: the agent that ends a session rewrites it.

---

You are picking up the Idli scaffold work in `~/src/github.com/bprashanth/io` (branch `oss-desktop-eval`, on the
DGX). The repo has a long history; focus on the last few days. Read in this order before doing anything:

1. `docs/idli-handoff.md`, the top checkpoint (2026-11-21): what this phase is, what to read, the state, the rules.
2. `narrative/GOALS_V0.6.md`: the scaffold as built and tested (sync, commands, search by words and meaning, `ask`,
   the yes card, judging with Clef, kind chips, what crosses the masking line, evidence, what isn't built).
3. `todos/idli-insights/p1/scaffold_core_round1.md`: the running list: every bug with evidence, decisions, proposals.
4. `chronology/2026-11-20T1400-scaffold-hands-on.md`, `chronology/2026-11-21T0000-search-defaults-agent-trial.md`.
5. `../dune/.index.md` and `../dune/docs/cli.claude.md`: what will move to the new repo `../dune`, and every term
   and command with an example. The owner copies what they understand into `../dune/docs/`.

**What we do here.** The owner tests the scaffold by hand on test account 87profligate (`~/idli-sbx/t2`):
`cd benchmarks/runs/2026-11-06-oss-desktop-independent/cowork; IDLI_SANDBOX=~/idli-sbx/t2 desktop/idli ask "..."`.
When something fails, find the cause in `<sandbox>/log.jsonl` (every command and every `ask` turn, with the masked
prompt, the plan, the menu, chips and struggle), check the right answer with read-only SQL (`idli query`), and fix
it **generally**: never for one question. Prefer code over prose (a sentence in the 9B's instructions); the prose
has a size budget (`tests/test_scaffold_prose.py`). Add the owner's questions, with SQL-checked answers, to
`benchmarks/runs/2026-11-19-record-store/bank/tasks_owner_dev.json`. Measure with the dev bank; claim only on a
held-out set run once on frozen code.

**Models on the DGX** (all on 127.0.0.1): the 9B (Q5, port 8291) maps and words replies; `idli-9b-bf16` (8292)
for `--mapper nine`; `idli-embed` (Qwen3-Embedding-0.6B, 8293) for meaning; Clef-flash via OpenRouter (Cloudflare
only) judges and labels the kind of ask. Hosted Clef sees real content: test accounts only. Muse (8181) is shared,
client-only: never restart it.

**Rules.** Commit as you go; run `bash -ic 'declaude origin/main'` after committing (it rewrites hashes: quote
hashes only after it). Never push; the owner reviews and pushes. Plain words in anything a person reads; say
"idli-remote", never the provider's name. Never print tokens, OAuth files or silo headers. Grinding (long
benchmark runs, blind grading, bulk checks) goes to Cursor `agent` or `codex exec`; nothing under `~/.codex` is
edited. Keep `docs/idli-handoff.md`, the chronology, the running list and `../dune/.index.md` current as you go,
and rewrite this prompt before you stop.

**Where things stand** (end of 2026-11-21): see the checkpoint's "Being built now" and the running list's top.
