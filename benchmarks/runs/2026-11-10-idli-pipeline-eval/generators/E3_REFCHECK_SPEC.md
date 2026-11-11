# E3 reference check: task for Codex

Context: `harness/e3_rescore.py` scores E3 chats (see `generators/E3_RESCORE_SPEC.md`); `results/e3/rescore.json`
has per-chat records (plotted values vs `scenarios/e3.json` step 5 `check.ref.numbers`). The refs were computed
with raw pandas on `fixtures/<stem>.xlsx`. Idli answers from its *cleaned* tables (`lib/chartkit.py` `tables()`,
cowork at `../2026-11-06-oss-desktop-independent/cowork/`, python `.venv/bin/python` there), which skip layout
rows and read "approx 12", casing etc. So some refs may be wrong for what Idli should say.

Write `harness/e3_refcheck.py` and `results/e3/refcheck.md`. Do not edit any other file. No network.

For each of the 9 chats in `scenarios/e3.json`:
1. State the hard question (step 3) and how the ref was computed (find the generator: `generators/cursor-e3.log`
   may show it; otherwise reverse-engineer from the numbers).
2. Recompute the answer from Idli's cleaned tables (chartkit.tables with the chat's taught skill — any
   `results/e3-logs/*/<chat>/teach/*/skill` will do, or `results/e6/fake/<stem>/skill`) and from raw pandas.
   Show the per-group counts (numerator/denominator) for both, and say exactly which rows differ and why
   (instruction rows, casing, units, blanks, "n/a", duplicate, out of range...).
3. Verdict per chat: is the ref right for what Idli *should* answer (given the owner's decisions: inconsistent but
   readable values are read quietly; template instruction rows are not data)? Give a corrected ref list if not.
4. For each run's chart in `results/e3/rescore.json` that failed, say whether it's wrong vs the corrected ref, and
   for passes with many plotted values (more than 2x the ref count), say whether the chart actually answers the
   question (e.g. a per-district chart when an overall share was asked) or only matched by chance.

Done = `results/e3/refcheck.md` with a table: chat | question | old ref | corrected ref | reason | per-run verdicts.
Keep it plain and short. End your final message with that table.
