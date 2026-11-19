# Record store scaffold: plan (written before building)

2026-11-19. Tests the model in narrative/GOALS_v0.md and narrative/EXAMPLES_V0.md: connectors, a DuckDB record
store per sandbox, definitions (judge), chains, on the real test accounts 87 and 88, headless.

## Task bank (blind)

- **Writer:** Cursor `agent` inside the bwrap wall (`../2026-11-19-blind-tester/wall.sh`). It saw only
  `bank/BRIEF.md` (a person-level description of the accounts) and GOALS_v0 section 1. It never saw the grammar,
  schemas or code.
- **Size:** 80 tasks.
  - Dev: 53 (20 own_definition, 13 own_workflow, 10 trust, 10 other_site; 12 multi-turn).
  - Held-out: 27 (10, 7, 5, 5; 5 multi-turn).
- **Frozen:**
  - `bank/tasks_dev.json`: sha256 `3888e2523c469997641c4e2b4b91025c6bbe6a80f03a559cd95061c7723db168`
  - `bank/tasks_heldout.json`: sha256 `c81e4cd249e09e62fe3150254f59a3fd5c0e6ddaae715e78776092a394cd4587`
- **Who reads what:** the builder reads only the dev file. Held-out is run once at the end, and graded by a
  separate grader (another model, via OpenRouter or Cursor `agent`), not by the builder.

## Scores, kept apart

1. **Coverage** (every task). Can the four layers express it?
   - `yes`: with existing connectors, views, definitions, queries and chains.
   - `new_connector`: another site or Google API.
   - `new_write`: a write action our team builds.
   - `design_miss`: needs a per-question hack.

   Graded from the chain the system produced (or would need), by a grader who sees the grammar.
2. **Correctness** (Google tasks, read-only, real data):
   - `correct`, `partial`, `wrong`, `refused_ok`, `failed`;
   - checked against the store's data by the grader.
3. **Reply quality** (sessions): a blind grader rates, 1 to 5, four things:
   - fit to the question;
   - whether a pointing or correcting follow-up is acknowledged;
   - repetitiveness across the session;
   - whether every number in the reply appears in the result (code check).
4. **Costs:**
   - latency per turn;
   - 9B seconds spent judging;
   - store size on disk;
   - rows per table.

## Blind testers

Cursor `agent` personas in the wall with only `./ask`, going simple first, then a few steps, then the workflow, and
stopping at the first failure. One Gmail/leads world and one Drive insights world, as in
`../2026-11-19-blind-tester`.

## Rules

- Read-only on accounts and Drive. Write verbs preview only.
- Masking for anything to idli-remote or Claude.
- Muse untouched; images only to the 9B.
