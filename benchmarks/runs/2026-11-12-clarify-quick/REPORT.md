# Quick feel: should the split ask for details, or say "not in the data"? (2026-11-12)

One run, temperature 0, 32 steps in 6 conversations on the 9B benchmark's taught NGO files (volunteers, households,
programme tracker, reimbursements, MGNREGA, road kills). Each step goes through the product's own form brief,
the split prompt, this file's thread (follow-ups), and the form engine. Steps are labelled: clear (20, 6 follow-ups),
vague term (4: "senior", "poor", "big villages", "laptops"), not in the data (6: a person, a funder, a column,
"tigers"), needs Claude (2). Direction only, not a score.

- P0: the frozen split prompt (today; E7 and Codex's F).
- P2: P0 + two replies, `clarify` (question + options from the form) and `absent`, + code hints: the form's values
  that match words in the question, and names that match nothing (the brief lists only 15 values per filter).
  (P1, the prompt without the hints, barely moved the 9B: 23/32.)

| Split model | Prompt | Right | Clear (20) | Over-asked on clear | Vague (4) | Not in data (6) | Median s |
|---|---|---|---|---|---|---|---|
| 9B | P0 | 22 | 17 | 0 | 0 (all 4 sent to Claude) | 3 (none said absent; 5 sent to Claude) | 1.6 |
| 9B | P2 | 24 | 16 | 0 | 2 asked | 4 (2 said absent) | 1.4 |
| Muse 30B | P0 | 22 | 18 | 0 | 0 (all 4 sent to Claude) | 2 (6 sent to Claude) | 30.9 |
| Muse 30B | P2 | 29 | 18 | 0 | 4 (3 asked, 1 absent) | 6 (5 said absent) | 34.3 |

- Nobody over-asks on clear questions, with either prompt.
- Today, vague and missing things go to Claude to teach: "how is the IAF funder doing?" and "Ramesh Kumar" become
  teaching requests for something that isn't in the file.
- Muse with P2 does what the owner wants: "IAF funder", "Person9", "laptops", "literacy rate", "tigers" → absent;
  "poor" → "low income / high vulnerability / low savings / ...?"; "big villages" → the three villages. Its 3
  misses are "no json" (the reply ran out of tokens while thinking: a harness limit, not a routing choice).
- The 9B with P2 is half way: it asks about "poor" and "senior" and catches 2 missing names, but still sends "IAF
  funder" and "laptops" to Claude, sends 2 clear questions to Claude, and offered volunteer names as the
  options for "senior".
- Muse costs ~30 s per question (thinking) against the 9B's ~1.5 s.
- Split bugs seen in every variant: "total claims by category this year" breaks on the date filter; "which of those
  are still pending" drops Pending; P0 filtered "Person3" on a value that matched no rows (the hints fix it).

Run: `python run.py P0 P1 P2` (9B on 8291); Muse: `SPLIT_URL=http://127.0.0.1:8181/v1/chat/completions
SPLIT_MODEL=muse-glimmer-30b OUT=results-muse.json python run.py P0 P2`. Needs the 9B benchmark's harness and
fixtures (paths in forms.py).
