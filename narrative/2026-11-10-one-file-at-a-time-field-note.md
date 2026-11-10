# One file at a time, and what a 9B can do

On 2026-11-10 the question was whether a free tier could run on a 9B model instead of Muse, the private 30B.
The answer reshaped the journey. [Chronology](../docs/cowork-poc.md); the 9B report is on branch
`idli-9b-bench` (`benchmarks/runs/2026-11-10-idli-9b/REPORT.md`); the next evals are in the
[pipeline eval plan](../benchmarks/runs/2026-11-10-idli-pipeline-eval/PLAN.md).

What a question about a file actually takes, in three model calls:
- **The chat model passes the question on in full words.** "Native ones only there?" becomes "how many native
  species in Karian Shola" inside the same call that picks the tool. No extra step.
- **A second call sets the form's dials.** It sees only the form, the last few questions in this chat and the
  new question, and returns which measure, which breakdown and which filters, or "send this to Claude". Then
  code computes the answer.
- **The chat model words the reply** from the code's answer. This is where numbers get lost: under Claude Code
  the 9B dropped totals and paraphrased.

What we learnt:
- **Narrow calls beat a bigger model.** A 9B asked to set the dials while also chatting and choosing among 29
  tools got 40% of fresh chats right. Giving that job a call of its own raised it to 79%. Muse got 83%. Swapping
  in larger models for the dial call (Ling-3.0-flash, gpt-oss-120b, Qwen 122B-A10B) moved the result by about 3
  steps out of 48, which is within luck. Most of the 9B's remaining failures were a card shown where the person
  should type.
- **Read the failures, not the scores.** Two of the test's questions asked for rows that the test file
  doesn't have, so every model failed them, Muse included. Another failure was a reply that was right but left
  out the total. Both are fixes to the test, not to Idli.
- **Guessing what to redact hurts more than it protects.** With Claude setting the dials on a question
  redacted by GLiNER, only a fifth of questions left unchanged. Seasons were tagged as villages and animal
  groups as castes. The next version redacts using the data itself: values from columns marked personal
  become tokens, and nothing else is touched.
- **The fake copy is the part nobody has measured.** Claude learns each file, and writes its checks, from a
  copy whose numbers are drawn at random inside the real range. Links between columns (DBH 2 only with DBH 1,
  density matching the tree count) don't survive that. The next evals plant known mess in files and judge
  the skill Claude learns from the fake copy against the real file.

The decision: no upfront Drive index. Idli takes one link or upload at a time, learns it, cleans it and
analyses it. Each file it learns leaves a context card (what a row is, columns, measures, links to other
learned files). The cards are the index, and later a graph of files, places, plots and species, drawn like
the idlisseus site-pack graph. The Start here chat, reindexing, and the minute Muse spent writing summaries
drop out of the journey. With them go most of the 29 tools the model chose from: a conversation about one
file needs about nine.
