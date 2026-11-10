# Could a 9B run Idli?

Idli's chat runs on Muse, a 30B model on the DGX. On 2026-11-10 the owner asked whether a 9B could do the same
work, as a free tier, within about 10 points of the 30B, and without junk output, loops or a worse experience.
[Benchmark](../benchmarks/runs/2026-11-10-idli-9b/), [chronology](../docs/cowork-poc.md).

We split Idli into the jobs Muse does today: greet and show the start card, find a file, open it through its
cards, turn questions into form specs and relay the answers, draw charts, hand unknown files to Claude, run the
clean-up flow, manage what Idli has learned, run the indexing chat, and write the Drive index's summaries. Each
was tested on a fake Drive (synthetic livelihoods tables, public road-kill and tree-plot data, the taught-skill
mocks) with Idli's real tools, in scripted chats written in the owner's voice, including sets the fixes were never
tuned on.

What we found:
- **The 9B mostly fails at protocol, not thinking.** It writes a card's options as text instead of showing the
  card, opens a file "to look at" when the person asked to check it for mistakes, deletes without asking. Muse
  makes some of the same mistakes, less often.
- **Small, general guards close most of that gap.** A Stop hook that sends the model back once when a card it was
  given isn't shown, or when a reply has a number no tool produced; a find tool that takes the person's goal and
  opens the spreadsheet itself; a delete that always shows its card. With these, the 9B matched Muse on the
  conversations they were tuned on and on a held-out set.
- **Long back-and-forth is where it still lags.** On a fresh set of longer chats full of "same but ward A", "those
  ones", "there", the 9B builds the wrong form more often than Muse. That is the place to invest: a spec builder
  that keeps the form's state, or a larger model only for that step.
- **Writing the index summaries, the 9B is better and 17x faster.**
- **The algebra LoRA did not transfer.** Trained for a different contract, it was worse than the raw 9B at Idli's
  tool protocol. As chat.idli.cc found, letting the agent backtrack mattered more than fine-tuning.
