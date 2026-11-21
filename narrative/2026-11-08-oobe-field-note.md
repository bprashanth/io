# The first five minutes

Idli is a desktop app (Paseo underneath) where a private model answers questions about an NGO's own Drive.
What should happen the first time someone opens it? We played a new user through it, many times, on the
owner's laptop with the private 30B model (Muse) and a 9B for comparison.
[Chronology](../docs/cowork-poc.md), numbers in [the OOBE run](../benchmarks/runs/2026-11-08-oobe/).

The shape that works:
- **Three things in the sidebar.** Start here (a setup chat), Idli (where the work happens), Claude (where Claude
  teaches Idli a new spreadsheet, from fake data). A script lays this out on first launch.
- **Start here opens with Idli already talking.** "Sign in to Google in the Drive tab, then say yes and I'll
  index your Drive." The only manual step is the Google sign-in.
- **"Yes" builds a local index of the Drive in 3 to 6 minutes**: names, folders, dates, the first rows of every
  sheet, and a one-line summary per file written by the private model. After that, finding a file is a 0.3 s
  lookup instead of minutes of live searching, and nothing leaves the machine.

What we learnt getting there:
- **Don't make the model interpret control words.** The launcher opened the chat with "start", and the person
  also typed "start"; Muse spent 43 seconds deciding which rule applied. Plain rules ("anything that means go
  ahead") and low thinking got the reply-to-action time down to about 5 seconds on both models. A yes/no
  question card works on the 30B but the 9B ignores it, so it isn't the answer on its own.
- **A chat can't show progress by itself.** A tool can't stream into the chat, and neither model reliably writes
  "still listing, 120 files" between waits: the 30B stops after one line, the 9B waits silently. Progress lives
  in a small page instead, opened as a tab labelled "drive-index.localhost" (Paseo opens agent tabs in the
  background, and a bare 127.0.0.1 label went unnoticed). The finish message with next steps arrives in the
  chat either way: the 9B writes it when its wait ends, and for the 30B the indexer posts a short status note
  that prompts it.
- **Search quality isn't the bottleneck; the model is.** On 25 realistic questions about a 182-file Drive, plain
  name matching put the right file first 20 times, names plus first rows plus summaries 22, a small local vector
  index 23, and blending them added nothing. Every method missed "money we gave out" for the disbursements sheet:
  the gap is everyday words, so summaries now include them. But the 30B takes 30 to 45 s to answer a "find"
  question in a new chat, almost all of it generating its reasoning at about 30 tokens a second; the lookup is
  0.3 s and the 9B answers in 7 s.

Still open: the heading order and Bypass-by-default need small Paseo patches; the 30B's thinking time is the
first thing a new user will feel; and a vector index is only worth adding once Drives get bigger and messier
than this one.
