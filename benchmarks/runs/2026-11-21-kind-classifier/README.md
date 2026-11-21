# Can Clef tell what kind of ask a question is? (2026-11-21)

The kind chips (lookup / judgement / workflow / elsewhere) come from one Clef-flash call per question, with each
kind described in plain words (`idlicli.KINDS`). Measured on the first turn of every labelled task: 53 dev, 27
held-out and 11 of the owner's (`measure.py`, `results.jsonl`). The banks' kinds map as trust -> lookup,
own definition -> judgement, own workflow -> workflow, other site -> elsewhere.

| | shown | agree with the label | workflow chips right |
|---|---|---|---|
| every question | 91 | 57 (63%) | 12 of 17 |
| Clef's top answer >= 0.5 | 63 | 45 (71%) | 9 of 10 |
| >= 0.6 | 47 | 36 (77%) | 6 of 6 |
| >= 0.5, or >= 0.4 with a 0.15 lead (used) | 70 | 49 (70%) | 10 of 13 |

- "Elsewhere" (another site, or an action) is reliable: 14 of 15.
- Most disagreements are the labels, not Clef. The bank called "papers about power", "anything about caste" and
  "emails about the reading programme visit" own definitions (written on 19 Nov, before search-first); today they
  are searches, and Clef calls them lookups. "Move the fixity report into a folder" was labelled a workflow; Clef's
  "elsewhere" (an action Idli can't take) is the more useful chip.
- The descriptions were not tuned to these labels.

Used: a chip when Clef's top answer is at least 0.5, or at least 0.4 and 0.15 ahead of the next (two clear cases at
0.48 and 0.47 were missed at a flat 0.5); the probabilities are logged either way. The workflow
chip (9 of 10 right) is the one that triggers an offer.
