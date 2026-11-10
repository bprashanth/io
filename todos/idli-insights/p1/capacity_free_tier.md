# Free tier capacity: how many people can one DGX serve? (E11)

Added 2026-11-10. Decide after the current evals (E6, E7):
- **If E7 shows the local 9B with the split (a separate dial-setting call to itself) holds up near Muse,** move
  this to p2 and run the capacity test with the 9B only.
- **If it doesn't,** keep this at p1 and test a challenger as well (below).

## The question
Which model gives the most for the money for about 100 people on one DGX (GB10: 128 GB of memory, read at
about 273 GB/s), with Muse still running? Is it a 9B in total, or a bigger model that uses 9-12B per word?

## The reasoning so far (estimates from public specs, not measured)
- **Reading the prompt** costs in proportion to the active parameters (the part of the model used per word).
  Idli is heavy on this: long prompts (instructions, tools, the chat, tool results) and short replies.
- **Writing the reply** to many people at once costs in proportion to the total parameters in a big
  mixture-of-experts model. With 100 people's words in one step, nearly every expert gets read. A dense 9B
  reads about 6 GB per step; Ling (124B total, 5B active) reads about 65 GB.
- **Each conversation's memory** (the KV cache) needs space for every user and is read every step. At 100 users
  with prompts of 5-10k tokens this is likely the biggest pressure: roughly 60-120 GB for an ordinary 9B, 15-30 GB
  for models with cheaper attention in most layers.

| Option | Prompt cost | Reply cost at 100 users | Room left | Verdict |
|---|---|---|---|---|
| Dense 9B with itself (~6 GB) | medium | cheap | lots (~80 GB beside Muse) | the default |
| Small MoE, 35B total / 3B active (~21 GB) | cheapest | medium | good | the only challenger, if its answers hold up as the chatting model |
| Ling with itself, 124B / 5B (~65-70 GB) | cheap | expensive | tight; Muse must go | not for 100 users |
| Big MoE with 9-12B active (e.g. 122B-A10B) | same as the 9B | expensive | tight; Muse must go | worst of both |

## Bigger wins than the choice of model (do these whatever the result)
- **Share the common start of every prompt across users** (prefix caching). Muse's notes show this was broken:
  tools listed twice, and a per-user path in the prompt.
- **Shorter prompts:** 12 tools instead of 34, and a short context for the dial-setting call.
- **Fewer words written:** show the code's answer instead of rewording it (E4).
- **A server built for many users** (vLLM or SGLang, which mix everyone into the same step) instead of
  llama.cpp's fixed slots.
- **The real load:** 100 people is about one Idli turn a second (3 model calls), not 100 calls at once.

## The test
- **Load:** replay the benchmark chats (link-first, 12 tools) as 10, 25, 50 and 100 simulated people, each sending
  a message every 60-120 s.
- **Setups:** the local 9B with the split, in llama.cpp with N slots and in vLLM if it runs on the GB10, with
  prefix caching on. Add 35B-A3B only if it stays at p1 and a quick quality check holds up first.
- **Measure:**
  - how long a person waits per turn (typical and worst-case);
  - words per second per person;
  - memory and memory speed used;
  - how many people fit before the worst-case wait passes about 30 s.
- **Rules:** run beside Muse with a memory cap (GPU_COORDINATION.md), at a time when Muse is quiet, since they
  share memory speed. Record the effect on Muse's own latency.
