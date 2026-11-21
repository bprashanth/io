# Query service: can a smaller or local model write the SQL?

Today (2026-11-15) Mini questions outside the saved ones go to an external service (`lib/minisql.py`, DeepSeek Flash
through OpenRouter). It gets the masked question and the column list, never rows, and returns one SELECT or a
question back with 2 or 3 concrete options. Idli runs the query locally in DuckDB.

Cost bounds in place: one call per question plus one per pick from an ask-back, replies capped at 700 tokens, the
column list capped at 12,000 characters, 200 calls a day per computer (`IDLI_SQL_DAILY_LIMIT`). A call is
1,000 to 3,000 tokens in, so cost is a fraction of a cent per question.

## Experiment
Same question set, four models through the same prompt and checks:
- DeepSeek Flash (today's baseline)
- Muse 30B (DGX, private)
- Qwen 3.5 9B (local, already the Drivey router)
- One small text-to-SQL model (a 7B SQL coder or similar), local

Questions: 40 or so over three files (shola fixture, households fixture, one wide survey), a third deliberately vague
("big trees", "which ward is worse"). Expected answers written first, by running reference SQL. Held out from any
prompt tuning (see the eval baseline and held-out rule).

Score per model:
- query runs and passes Idli's checks
- answer matches the expected rows
- on vague questions, asks back with options that each resolve to a correct answer
- seconds per question, and cost or GPU time per question

## Decision it feeds
If Muse or the 9B is within a few points of DeepSeek, keep the query service private (nothing leaves, no key, no
cost). If not, keep the external service and use the local model only to decide when to ask back.
