# Who fills the file form? (2026-11-08)

Question: in the single-file flow, what does the model actually do, and could something smaller do it?

With file forms (see [JOURNEY.md](JOURNEY.md)) the model's only file job is to turn a typed question into a
**form spec**: which measure, which breakdown, which filters, which dates, or to say the form can't answer it
(then Idli offers teaching). Code runs the spec. So we scored exactly that: the spec each option produced is run
by Idli's own code and its **numbers** compared with a reference spec's numbers (any spec giving the same answer
counts; a few equivalent shapes, such as a row listing vs. a breakdown with the same rows, are accepted).

## Question sets (85 questions, 4 files: tech reimbursements, volunteer register, households, 3-tab field tracker)

| Set | n | Author | Note |
|---|---|---|---|
| `questions.json` | 30 | me | written before any run; the keyword baseline was tuned on it |
| `holdout.json` | 15 | me | written after the baseline was frozen, never tuned on |
| `codex.json` | 20 | Codex CLI, from the form descriptions only | casual English, lakh / FY |
| `cursor.json` | 20 | Cursor agent, from the form descriptions only | Hinglish ("FY me software claims kitne aaye") |

Each set has questions the form can't answer (ratios, row-by-row comparisons, growth); the right move is "teach".
Reference specs from Codex and Cursor were used as written.

## Results (with one retry: the model sees the tool's error once, as Idli does in a chat)

| Model | Dates | questions | holdout | codex | cursor | All (first try / one retry) | s/question | runs |
|---|---|---|---|---|---|---|---|---|
| 9b | v1 | 24/30 | 13/15 | 16/20 | 16/20 | 58 / 68 of 85 (81%) | 1.8 | 4 |
| 9b | v2 | 22/30 | 11/15 | 11/20 | 17/20 | 53 / 61 of 85 (71%) | 1.9 | 4 |
| gemma4b | v1 | 9/30 | 3/15 | 6/20 | 4/20 | 22 / 22 of 85 (26%) | 1.4 | 1 |
| gemma4b | v2 | 6/30 | 3/15 | 5/20 | 4/20 | 18 / 18 of 85 (21%) | 1.3 | 1 |
| keywords | - | 21/30 | 4/15 | 6/20 | 8/20 | 39 / 39 of 85 (46%) | 0.0 | 1 |
| ministral3b | v1 | 7/30 | 3/15 | 4/20 | 4/20 | 17 / 18 of 85 (21%) | 1.3 | 1 |
| ministral3b | v2 | 16/30 | 4/15 | 4/20 | 7/20 | 27 / 31 of 85 (36%) | 1.2 | 1 |
| muse | v1 | 28/30 | 13/15 | 18/20 | 18/20 | 77 / 77 of 85 (91%) | 24.8 | 1 |
| muse | v2 | 29/30 | 13/15 | 17/20 | 20/20 | 78 / 79 of 85 (93%) | 22.9 | 1 |

- **Muse 30B** fills the form almost perfectly (91–93% with either date wording), on every author's questions,
  including Hinglish. It is slow
  per question (~23 s, mostly thinking), which a chat turn already pays.
- **Qwen3.5-9B** is right ~80% of the time; one retry adds ~10 points (its first tries are often format slips).
  Its real misses are dates (an unasked "this year", "last month" from the 8th, FY ending in the wrong year,
  "after August" from 1 Aug) and extra filters nobody asked for.
- **3–4B models** (Gemma 3 4B, Ministral 3B) are not viable: they mostly refuse ("teach"/"ask") or pick wrong ids.
- **Keywords + a date parser, no model:** 21/30 on the questions it was tuned on, 4/15 on the held-out set and
  6–8/20 on the independent sets (~25% off its home set). A classifier would need training data per file; the
  form itself (dropdowns) is the real no-model path.
- **Tried and dropped:** letting the model copy the user's date words and having code resolve them (`v2`,
  `lib/formkit.py:parse_when`). It made the 9B *worse* (71% vs 81%, 4 runs each; it put words like "September"
  on the wrong date column and invented dates more), and the 30B scored about the same either way (91% / 93%, one run each). The tool keeps the period/from-to
  wording; `parse_when` stays in the code, unused by the model.

## What this says about the model's role

For a known file the model is a **translator from the user's words to the form**, plus the conversation (finding
the file, offering teaching, asking when unclear). It never computes. The 30B does that reliably; the 9B does it
4 times in 5 and fails mostly on dates. Something smaller than 9B does not work here, and keywords don't
generalise. Practical setup: the form is always there (dropdowns are exact and free), the 30B fills it from chat,
and every answer opens the form with the filters it used, so a wrong reading is visible at a glance.

## Run it

```
cd ../2026-11-06-oss-desktop-independent/cowork
.venv/bin/python ../../2026-11-08-form-fill-eval/formfill.py --questions holdout.json --models keywords,muse,9b
python3 ../../2026-11-08-form-fill-eval/summarize.py
```
Muse is called at `MUSE_URL` (default `http://127.0.0.1:8181`); others via OpenRouter, key from
`~/.config/idlisseus/openrouter.json` (never printed). Temperature 0, one retry on a tool error. OpenRouter runs are
not deterministic even at temperature 0, hence repeated 9B runs. `--rescore` re-scores saved outputs.
