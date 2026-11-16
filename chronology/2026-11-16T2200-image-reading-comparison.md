# 2026-11-16 22:00: Reading table images; the Muse crash; the Builder's exit test (p1 todo)

**Asked:** add the exit-test idea to p1; test RapidOCR on its own; compare Muse and the 9B on images; check whether
the Muse crash was a system or runtime problem.

- **The p1 todo:** `todos/idli-insights/p1/builder_acceptance_tests.md`. The Builder asks for the exit test first;
  `team_try` runs on the real file and the person judges; on No, the next option on the menu.
- **The comparison:** `benchmarks/runs/2026-11-16-image-reading/REPORT.md`. Share of cells right on the owner's three
  real table screenshots:
  - Tesseract: 0 to 6%;
  - RapidOCR: 91 to 100%;
  - the 9B with its projector, thinking off: 96 to 100%, in 6 to 8 s;
  - Muse, reasoning low: 82 to 100%.

  On the synthetic set, everything except Tesseract scored 100. On Hindi, only the two models read it.
- **The Muse crash** was not memory or the host: no kernel errors, 60 GB free. It also didn't reproduce on Muse
  copies with the same files and settings under parallel load (about 30 images). The likeliest cause is a race in
  production's long-running state. Until the owner decides, no images go to production Muse (saved as a memory).
- **Nothing is wired yet.** The owner decides what the menu brings in.
