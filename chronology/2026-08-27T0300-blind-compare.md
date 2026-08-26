# 2026-08-27 03:00 - io: blind three-model compare, and what the first graded battery says

The model switcher is gone. Every question now fans out to 9b / 27b / frontier in parallel
over the same tokenised payload; the browser gets three shuffled anonymous cards (scrolling
bodies, page candidates as live iframes) with "choose this answer", "no difference",
"all bad". Input stays locked until a vote. The chosen answer becomes the canonical history
turn all three models see next round. Votes tally to ~/.config/io/votes.json; every vote
appends a full research record to ~/.config/io/compare-log.jsonl (conversation, turn,
redacted prompt, per-model answer/position/latency/tokens, outcome) - enough to build
per-task preference tables offline without ever burdening the user with classification.

## The 7-round graded blind battery (sunrise-shiksha + open-data, judged against cases.json)

| round (task) | blind winner | reveal |
|---|---|---|
| simple lookup: enrolment 320 | correct card | frontier (9b said 0) |
| data interpretation: dropouts | methodical card | 27b |
| data interpretation: lagging indicators | ranked card | frontier |
| numeric aggregation: June attendance (5641) | **all bad** | nobody: 5622 / 3040 / no number |
| simple explanation | no difference | tie |
| donor rewrite | warmest grounded card | **9b** |
| dashboard (sunrise) | executive page | frontier 26s; 27b partial join; 9b 14 min for an all-zero page |
| dashboard (open-data) | working filter page | frontier (27b string-concatenated "0239282411139") |

## What this says about the premium question

- **Language work (explain, rewrite): the premium is not justifiable.** The 9b tied or won
  blind. This is where laptops win outright.
- **Data interpretation: the premium starts paying.** Frontier and 27b split the wins; the
  9b loses on faithfulness (invented numbers, "0 enrolled").
- **Dashboards: frontier's territory** on both quality and latency (26s vs the 9b's 14
  minutes). The 27b middles - real numbers, broken joins.
- **Precise numeric aggregation: no tier earns the premium - all three failed 5641.** The
  answer is not a bigger model, it is local compute with receipts. This is the measured
  motivation for the ask-lane/duckdb story, produced blind by the product itself.

Warts logged for later: the question redactor tokenised "volunteer" and "funder" (over-eager
partial-name/validator passes - answers survived, comprehension risk); a 14-minute 9b page
build argues for a per-model timeout in compare mode; pending turns cannot be re-fetched by
a fresh client (folder reload clears them - acceptable, noted).
