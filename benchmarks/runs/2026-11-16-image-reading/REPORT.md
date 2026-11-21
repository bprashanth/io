# Reading table images: Tesseract, RapidOCR, the 9B and Muse (2026-11-16)

**Why.** On the laptop, the Builder's Tesseract reader garbled the owner's table screenshot. Before choosing what the
capability menu offers, we compared four readers on the same images.

**Images.**
- **Synthetic** (`synthetic/`, made by `make.py`): a clean register, a downscaled dense screenshot, a tilted and
  shadowed register photo, a Hindi register, and a table without lines in italics. The correct answers are in
  `truth.json`.
- **Real:** three table screenshots from the owner's test Drive (Strategy Content/Caste:
  `finance_caste_table.png`, `size_caste_table.png`, `caste_tab;e.png`). The correct answers were typed by reading
  each image. They are not committed.

**Scores** (`score.py`): the share of cells with 3 or more characters that each reader got exactly right (numbers
normalised: "56.9 %" counts as "56.9%", and "35,951,686" as 35951686). The row-similarity numbers are in the run
logs.

| | Tesseract (--psm 6) | RapidOCR (onnxruntime) | 9B + mmproj, thinking off | Muse 30B, reasoning low |
|---|---|---|---|---|
| Synthetic: clean register | 24 | 100 | 100 | 100 |
| Synthetic: dense screenshot | 100 | 98 | 100 | 100 |
| Synthetic: register photo | 86 | 95* | 100 | 100 |
| Synthetic: Hindi register | 0 (no hin pack) | 0 | 100 | 100 |
| Synthetic: no lines, italic | 100 | 100 | 100 | 100 |
| Real: finance_caste_table | 0 | 95 | 100 | 100 |
| Real: size_caste_table | 2 | 100 | 100 | 82 |
| Real: caste_tab;e | 6 | 91 | 96 | 92 |
| Time per image | 0.2 to 0.4 s | 0.5 to 4 s (CPU) | 2.5 to 8 s | 4 to 44 s |

\* RapidOCR read the words of the tilted photo correctly, but our simple row grouping put them on the wrong rows
(52% landed in the right row).

**What each one gets wrong**
- **Tesseract** garbles text when a table has grid lines (the clean register and all three real ones), even when
  the words are crisp.
- **RapidOCR** reads printed English and numbers well, but its default models don't read Devanagari. Rows have to
  be rebuilt from boxes, which tilt breaks.
- **The 9B** missed 2 numbers in one row of `caste_tab;e`. With thinking on it can spend its whole token budget
  reasoning and return nothing, so it must run with thinking off (production Idli already does).
- **Muse** ignores `enable_thinking`. It needs `reasoning_effort: low`, or it reasons through 2,500 or more tokens
  and returns nothing. It left out the values on the group rows of `size_caste_table`: a layout reading, not
  misread digits.

**The Muse crash (production, 21:18).** One image request to production Muse (`idli-muse`) aborted llama-server:
`CUDA error: operation not permitted` in `ggml_cuda_kernel_can_use_pdl`, inside `clip_encode`. The container
restarted itself and was back in about 3 minutes. Was it a system or resource problem?
- **Not memory or the host:** 60 GB was free, the kernel log had no Xid or OOM messages around the crash, and there
  has been no reboot since 6 Nov.
- **Not a plain bug in the image or the model files:** separate copies of Muse with the same files and image,
  including the draft model, 4 slots, a prompt cache, and images and text sent in parallel, read about 30 images
  with no crash. The 9B with its projector on the GPU encoder didn't crash either.
- **So it was production's runtime state:** 6 days up, a 262k context across 4 slots, a 32 GB prompt cache, and
  whatever else it was doing at that moment. The likeliest cause is a rare race between image encoding and CUDA
  work on another slot. It isn't reproducible on demand.
- **Rule until the owner decides:** don't send images to production Muse. A fresh restart might make it fine, but
  that is the owner's call.

**Takeaways for the capability menu**
- **Local:** RapidOCR beats Tesseract by a wide margin on printed tables, but not on Hindi or Marathi.
- **Private model:** the 9B with its vision projector read everything, Hindi included, at 6 to 8 s on the real
  images. It was at least as accurate as Muse and faster.
- **Muse** is no better at this task and carries the crash risk.

Servers used: `idli-test-9bv` on 127.0.0.1:8296 and `idli-test-musev` on 8297, both started for the test and
stopped afterwards. The 9B projector was downloaded to `/mnt/seagate/io-models/Qwen3.5-9B-GGUF/mmproj-F16.gguf`.
