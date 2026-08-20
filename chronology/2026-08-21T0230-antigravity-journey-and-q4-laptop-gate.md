# Antigravity journey replay and Q4 laptop gate

The agriculture journey was frozen before either product run in
`benchmarks/cases/v2-agriculture-journey-001/case.json`. It uses one synthetic
CSV and three ordinary follow-ups: rank 2024 Monsoon yield, show the 2023--2024
trend, then restrict the website to Bhojpur and Wardha and compare the change.

Antigravity CLI 1.1.15 was run twice with untouched defaults in the pinned
outer container. Its logs resolved the actual model to **Gemini 3.7 Flash
(High)**.

- Repetition 1 produced a correct and visually strong first page, but every
  first-turn result was internally marked `ERROR` because Antigravity tried to
  declare a `/workspace` file as an internal artifact. Turn 2 then failed with
  a network error and turn 3 never ran. The counted journey failed after
  258.332 seconds.
- Repetition 2 returned numerically correct chat answers for all three turns in
  147.442 seconds. However, all three results were again internally marked
  `ERROR`, and the HTML hash never changed after turn 1. The final browser page
  still showed the original all-block 2024 ranking rather than the requested
  two-block change view. This is a correct chat follow-up but a failed website
  follow-up.
- The repetition-2 page is visually excellent when online, but it requires
  Tailwind, Chart.js, Font Awesome and Google Fonts from public CDNs. In the
  saved offline replay it raises `Chart is not defined`, loses its layout and
  shows blank chart regions. Both online and offline screenshots are retained.

Evidence is under
`benchmarks/runs/2026-08-21-v2-dashboard-journey/agriculture/antigravity-default/`.
The local Arctic BF16 journey, by contrast, regenerated a self-contained page
for all three turns, passed browser interaction/download checks, and made no
external requests. Antigravity has the higher visual ceiling on the surviving
online first page; the local pipeline is the only one of these runs that met
the complete durable-website journey.

For laptop feasibility, the exact Arctic model was downloaded as a community
Q4_K_M GGUF. The file is 4,683,074,144 bytes with SHA-256
`9c005244e3ab7fada2c53a9511999f4d22fbbd4f76a4416416a6d41d82702255`.
It was served locally using the official ARM64 CUDA 13 `llama.cpp` server image
and the same frozen evaluator used for BF16.

Q4_K_M scored **25/30 (83.3%)** in 434.925 seconds: close, but below the 85%
standalone gate. It had no request timeouts or final execution failures. The
five semantic misses were one wrong ranking direction, one wrong
percentage-point calculation, one collapsed two-year comparison, and two
concatenated entity filters that returned empty results. The previously frozen
gold-free router escalated four of the five wrong answers but silently accepted
the collapsed two-year comparison; it also escalated one correct answer. Q4 is
therefore not a qualified safe first rung. Raw evidence and the router replay
are in
`benchmarks/runs/2026-08-21-v2-query-gate-v2/arctic-text2sql-r1-7b-q4km/`.

The next bounded experiment is Q5_K_M of the same checkpoint. The threshold is
not being weakened and candidate prompts are not being tailored to the misses.
