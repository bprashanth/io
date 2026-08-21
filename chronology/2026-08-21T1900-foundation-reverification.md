# Foundation re-verification: ranking holds, router and routed replay do not

A fresh agent re-derived the local-first ladder evidence before extending it.

Rescoring every saved gate-v2 SQL against the current gold and evaluator
reproduces the model ranking (XiYan 11/19, Arctic 24–26, Qwen 28–30). Three
things did not hold. The "routed replay 30/30" substituted Qwen's oracle passes
without passing them through the router; the current router rejects all five
of Qwen's correct `time-change-per-group` answers, so the shell would fail
closed there. The router was edited twice after the holdout-v1 result labelled
"frozen". And Qwen's 30/30 is the best of three reps (28, 28, 30).

A new realistic holdout (`benchmarks/v2/query-holdout-v2.json`, 30 cases,
messy headers, `State Total` trap, text dates, joins) was frozen and run once
per configuration. Arctic Q4: 19/30 with either prompt; router accepted 6–7
wrong answers. Qwen 3.8 27B: 23/30 with the gate prompt, 29/30 with the shell
prompt. Qwen 3.5 27B with thinking disabled: 29/30 on both suites in ~100 s.
Qwen 3.5 9B with thinking disabled: 25/30 on gate-v2 (equal to Arctic Q4) and
24/30 on holdout-v2 (better). Gemma 4 26B-A4B: 23/24. GPT-OSS 20B: 28/22.

Two runner defects were found and fixed without touching saved evidence: the
gate discarded thinking-model responses with empty `content` (the real cause of
the earlier "Qwen 3.5 9B timed out" verdict), and the gate prompt differed from
the shell prompt. The runner now has `--reasoning-effort none` and
`--prompt-style gate|shell|shell-plus`, and manifests may declare separate
absolute/relative tolerances.

Visual re-inspection: the local agriculture page is correct but thin (~6.5–7/10),
Antigravity's page is a real multi-panel dashboard with correct numbers; the
Antigravity "page never changed" result is confounded by the headless CLI's
artifact-path error inside the container harness.

Arctic container was started from the verified Q4 hash and stopped afterwards.
Leftover `io-screening-*`/`io-smoke-*` web containers from 2026-08-20 were left
running untouched.

Evidence: `docs/foundation-reverification-2026-08-21.md`,
`benchmarks/results/foundation-reverification-2026-08-21.json`,
`benchmarks/runs/2026-08-21-v2-query-holdout-v2/`,
`benchmarks/runs/2026-08-21-v2-query-gate-v2-small-general/`.
