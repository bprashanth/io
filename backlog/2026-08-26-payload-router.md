# Payload router for big folders (do later)

The measured problem (`benchmarks/runs/2026-08-26-payload-roi/`, 120-file 18.5MB corpus):
sending everything under a 150KB cap scores 0/12, naive per-call caps score 0/12, BM25
chunk retrieval 5/12, BM25 + a locally computed manifest 7/12.

The plan, user-proposed two-step router:

1. At scan time the laptop computes a deterministic per-file summary (the manifest):
   tables get rows, columns, sums/means of numeric columns (pandas, already open during
   scanning); chat exports get message count, date range, sender codes; PDFs/text get
   size, pages, headings. No model, no cost, no PII beyond tokenised values.
2. First call, tiny: the question plus the manifest only. "Given these summaries, which
   files do you need to answer this?"
3. Second call: the chosen files, whole when they fit, chunks when they do not, manifest
   always included. Budget bound (about 300KB / 6 files) as the outer safety limit, never
   as the selection mechanism.
4. A file named in the question or picked with @ skips the router. The answer line says
   "searched N files, sent M" so the user knows what the model saw.

BM25 stays as the offline fallback ranking when no provider is configured. What no
payload strategy solves: folder-wide needles and computations - those belong to the local
ask lane (or the deferred harness discussion).

Until this is built, the app refuses open questions on big folders and asks for @ (done,
see chat guard in app/io/service.py).
