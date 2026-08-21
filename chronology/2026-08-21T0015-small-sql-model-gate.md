# Small SQL model gate and evaluator correction

The v2 local-first experiment began with the smallest verified SQL specialist,
`XGenerationLab/XiYanSQL-QwenCoder-3B-2504`. The exact BF16 checkpoint was
downloaded to `/mnt/seagate/io-models/XiYanSQL-QwenCoder-3B-2504` and served in
an isolated vLLM container on port 8020 without changing the shared 2B and 8B
services. The model revision is
`b883e58ed83f74bab037d6a7b90c4b8706d357d7`; its two weight shards total about
5.8 GiB. The first full diagnostic gate scored 10/30. After correcting selected
dataset context it scored 11/30. It was reliable on missing-value detection but
systematically failed time deltas, denominator selection, grouping, and
multi-measure queries. It is not safe as the event's query planner.

The first gate version also exposed two evaluator defects. All five unrelated
tables were shown for every independent question, and several shorthand
paraphrases omitted a dataset, date range, denominator, or unit that the gold
answer silently assumed. Exact tuple comparison also rejected answers that
contained every requested value plus a useful context column. Those runs are
preserved under `benchmarks/runs/2026-08-21-v2-query-gate/`; the manifest is
marked retired rather than rewritten out of history.

`benchmarks/v2/query-suite-v2.json` is the corrected frozen gate. Each of its 30
prompts is standalone, schema evidence is limited to the dataset(s) selected for
that task, and every paraphrase states the same scope and unit. Its comparator
accepts the required result as a column projection of a wider answer, but it
still rejects extra rows, wrong values, wrong units, missing obligations, and
incorrect ranking order. This is a generic obligation rule, not a model- or
sector-specific exception.

`XGenerationLab/XiYanSQL-QwenCoder-7B-2504` was downloaded in BF16 (about 15
GiB) and served locally through the same endpoint. It scored 19/30 (63.3%) on
the corrected full gate at temperature 0.1. A zero-temperature six-pattern
smoke scored 4/6, so sampling was not the main problem. The 7B specialist is
also below the accepted 85% standalone threshold.

Qwen 3.8 27B through OpenRouter scored 25/30 under the intermediate exact-shape
version of the corrected gate. Three misses contained all required values plus
useful context columns, while two prompts still had unstated percentage units.
After those generic evaluator defects were fixed and temperature set to zero,
the final rerun passed its first 16/16 prompts. The next hosted request then
hung beyond 180 seconds because Python's socket timeout was not a hard
wall-clock deadline. The run was deliberately interrupted and preserved. The
runner now enforces a SIGALRM wall-clock timeout and retries a transport timeout
without feeding it back as a semantic SQL error. A complete final 27B run is
still required.

An OpenRouter smoke for stock `qwen/qwen3.5-9b` was inconclusive rather than an
accuracy failure. Default reasoning consumed the entire 1,024-token allowance;
the corrected low-effort 2,048-token call then failed to return within three
minutes and was stopped. This hosted route is not presently suitable for the
event's bounded interaction loop.

Raw requests, responses, SQL, executed tuples, errors, timings, and summaries
are stored below `benchmarks/runs/2026-08-21-v2-query-gate*`. No private event
data was used. The next small-model candidate is
`Snowflake/Arctic-Text2SQL-R1-7B`; its download was in progress when this
checkpoint was written.
