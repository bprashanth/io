# 2026-11-20: the owner's first hands-on session with the scaffold, and what it changes

Follows [2026-11-18T0900-catalog-routines-sandboxes.md](2026-11-18T0900-catalog-routines-sandboxes.md), section 14
(GOALS_V0.5 written up). The owner chose to focus on the scaffold loop alone before the app, Paseo, or the move to a
new repo (`../dune`). The running list of bugs, decisions and proposals is
[todos/idli-insights/p1/scaffold_core_round1.md](../todos/idli-insights/p1/scaffold_core_round1.md). The docs to
carry into dune are indexed, sparingly, in `../dune/.index.md`.

## 1. What the scaffold is, checked against the code

- `desktop/idli` runs `lib/idlicli.py` over one DuckDB file at `$IDLI_SANDBOX/store.duckdb`.
- **Layer 1, no model:** `sync` copies one Google account into the store (the account is fixed in code: `ACCOUNTS`
  in idlicli.py); `list`, `get`, `query` and the rest are SQL.
- **Layer 2, `ask`:** the question, the menu and the grammar are masked once; the mapper (idli-remote, or the 9B with
  `--mapper nine`) returns commands as JSON; Idli runs them (one repair round, up to two continue rounds); the 9B
  words one to three sentences; numbers not in the result drop the wording. `session.json` keeps 6 turns.
- **The menu** is built by code each turn (`menu()`): descriptions typed by a developer in `RESOURCES`
  (recstore.py), column names from DuckDB, "is one of" values sampled from the data, then definitions and views.
- **Not built:** Minis and chains. The store has `views` and `definitions` only, sandbox-wide.
- The default sandbox `~/idli-insights/scaffold` was empty; the benchmark's sandboxes were temporary copies. Every
  test starts with a sync.

## 2. The owner's session (`~/idli-sbx/t1`), checked with read-only SQL

| Ask | What happened | Verdict |
|---|---|---|
| "show me meetings with Asha", 9B | `--where "'Asha' in guests"`; guests holds addresses, the name is in titles | wrong (empty) |
| same, idli-remote | `--search "Asha"`, 6 events | right |
| "emails from everyone I've declined meetings with", 9B | 0 declined events in the store (5 accepted, 5 organizer); the mapper read an incoming "Declined:" notice as the owner declining; the reply described step 2's rows while the last step showed nothing | wrong |
| `judge files --def economics` (yes, no, contains_economic_data) | 187 of 191 "unsure" were crashes: `ResourceInUseException` | bug |
| "show me docs on economics", 9B | the mapper re-ran `define economics` (v2, yes/no), dropping the owner's third answer, judged only Docs (35), not PDFs (86); 16 yes | definition replaced silently |

Root causes found:
- **B1:** judge's 4 threads share one DuckDB connection; first-time PDF text writes collide. Reproduced on a copy:
  about half of threaded reads fail.
- **B2:** a failed judgement is saved as `unsure`.
- **B3/B9:** the menu shows each definition's question but not its answers, and nothing stops the mapper redefining.
- **B4/B5:** the reply is worded from all steps but only the last is shown; spelled-out numbers skip the check.
- **B7:** `get event X` is `id = X OR title ILIKE %X% ... LIMIT 1`, a silent first match.
- **B8:** "is one of" lists any short column with 10 or fewer values, so a small calendar lists titles as choices.

## 3. Decisions (owner, 2026-11-20)

1. `sync` names the place (`sync gmail`, `sync gcalendar`, `sync drive`); other verbs name the record (`list mail`,
   `list calendar`, `list files`). `events` becomes `calendar`.
2. Fewer verbs: `count` into `list --count / --group-by`; `read`, `summarise`, `describe` into `get file`. `--by`
   becomes `--group-by`. One way per thing (`--search` vs `--where ~` split the two mappers on the same ask).
3. When the mapper has to supply a meaning the menu doesn't hold, it says so; a yes saves it as a view. A
   definition's card states the judging cost. Code also flags any raw `query` or cross-resource join. View vs
   definition: decidable exactly from fields and joins is a view; needs reading content is a definition.
4. `ask` shows the last step's rows and words the reply from those only; every step goes to `--verbose` and the log.
5. Every turn is logged to `<sandbox>/log.jsonl` with its context; on request the agent checks turns with SQL and
   adds them to the dev bank, asking the owner only where it can't tell. Never to the held-out set.
6. Document text is read in the background when a sandbox is made, newest first, with a cost estimate up front
   (to try and see). One row per page, full-text index.
7. Script steps (Sandbox Claude) write their output as a table in the sandbox store, registered with an about line,
   owned by the Mini that made it. Record kinds move from the `RESOURCES` dict to a registry in the store.
8. Boundary: a rule over columns already in the store is a view (Sandbox Claude); a rule that needs data the store
   doesn't copy is a connector change (Builder). Writing verbs stay with our team.
9. The judge model test moves up (section 4).

## 4. The judge model test (started)

- Topic "about endangered species", with near misses, across CSV, Excel, PDF, Python and Docs; about 40 synthetic
  items in `benchmarks/runs/2026-11-20-judge-models/`.
- Candidates: the 9B as served (Q5 GGUF), the 9B uncompressed (BF16 GGUF, second llama-server), Clef-flash, Muse 28B,
  idli-remote as a reference.
- Facts checked:
  - **Muse is dense,** not MoE: `muse-glimmer` architecture, 28B, 52 blocks, no expert keys. The 2026-11-16 image
    crash was a flake (owner); images are fine.
  - **Clef-flash** (`Cloudflare/clef-flash`, Apache-2.0) ships 18.8 GB of weights plus a 0.24 GB scoring head. Its
    attention and MLP weights differ from Qwen3.5-9B (the LoRA is merged), so it can't share memory with our 9B.
    OpenRouter lists it (hidden from the main list: output "decisions") via DeepInfra (FP8), PrimeIntellect and
    Cloudflare. The owner chose Cloudflare as the provider, no fallback.
  - The full Qwen3.5-9B (BF16, 19 GB) was in `~/.cache/huggingface`.
- `idli ask --mapper nine` will mean the uncompressed 9B and `nine_compressed` today's Q5.

## 5. Housekeeping

- `~/.cache/huggingface` (about 50 GB): deleted with the owner's agreement a partial Qwen3-Next-80B, a partial
  Qwen3.5-122B, dinov2 and 13 empty leftovers. Hammer2.1-7b (15 GB) and 37 files under `modules` are owned by root
  (no sudo for the agent), so neither the delete nor the move to `/mnt/seagate/hf-cache` was done; the owner runs
  `sudo rm -rf ~/.cache/huggingface/hub/models--MadeAgents--Hammer2.1-7b && sudo chown -R beeps: ~/.cache/huggingface`
  and the move follows. The masking service (`io-privacy-server`) uses its own `app/io/hf-cache` and is untouched.
- Earlier sessions' untracked results and traces committed (siblings already tracked; no test-account addresses).
