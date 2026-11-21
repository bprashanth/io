# Judge models: which model should label rows for a definition? (2026-11-20)

The scaffold's `idli judge` asks the 9B one question per row ("Is this about X?") and keeps the answer as a label.
This round asks two things: does a different model judge better or cheaper, and does what the model is shown matter
more than which model it is.

## The set

38 synthetic files written in `build_data.py` (everything is invented and in the file, so it can be reviewed):
- 18 should be yes, 20 should be no; 21 are marked hard;
- 7 CSV, 6 Excel, 9 PDF, 6 Word, 6 text, 4 Python;
- the question: "Is this about endangered species?", answers yes, no, unsure (as `idli define` makes them).

The hard ones are near misses and traps:
- **Yes without saying so:** camera-trap rows of tigers and pangolins; a hatchery rota; a tiger-corridor budget;
  a file called `Sheet1.xlsx` holding gharial nest counts.
- **No that looks like yes:** endangered languages; extinct dodos; a "red list" of overdue library books; CR, EN and
  VU as accounting codes; a rugby team called the Bengal Tigers; a livelihood project near a tiger reserve.

The labels are the agent's. The owner confirms them (see "Labels to confirm").

## Conditions

- **content:** every file shows its first 1,200 characters of text. This is the design target.
- **today:** what `recstore.judge` sends now. PDFs and Word files show text. CSV, Excel, text and Python files show
  only their name and folder.

The chat models get the same prompt, answers and JSON schema as `recstore.judge`. Muse is the exception: it reasons
whatever the template says, and a schema grammar on top stalled it, so it gets a JSON object and room to think, as
`lib/driveindex.py` calls it.

## Candidates

| Name | What | Where it runs |
|---|---|---|
| nine_q5 | Qwen3.5-9B, Q5_K_M (what `idli-9b` serves today) | DGX, port 8291 |
| nine_bf16 | Qwen3.5-9B, full BF16, same llama.cpp build and settings | DGX, port 8292 (`idli-9b-bf16`, new) |
| muse | Muse-Glimmer 28B dense, Q4 | DGX, port 8181 |
| clef | Cloudflare Clef-flash, a decision model (a scoring head on a tuned Qwen3.5-9B). Gives P(yes); 0.35 to 0.65 counts as unsure | OpenRouter `/api/v1/systemone`, provider Cloudflare only |
| remote | idli-remote (DeepSeek via OpenRouter) | OpenRouter |

## Results

```
model-condition   | right | hard right | missed yes | false yes | unsure | s/item (median) | cost $ (38 items)
clef-content      | 38/38 | 21/21      | 0          | 0         | 0      | 0.47            | 0.00037
remote-content    | 38/38 | 21/21      | 0          | 0         | 0      | 0.98            | 0.00357
nine_bf16-content | 35/38 | 18/21      | 0          | 1         | 2      | 3.84            | -
nine_q5-content   | 33/38 | 16/21      | 0          | 1         | 4      | 1.71            | -
muse-content      | 33/38 | 17/21      | 1          | 0         | 4      | 6.93            | -
clef-today        | 33/38 | 17/21      | 3          | 1         | 1      | 0.43            | 0.00028
remote-today      | 26/38 | 11/21      | 0          | 0         | 12     | 1.01            | 0.00415
nine_bf16-today   | 21/38 | 7/21       | 0          | 1         | 16     | 4.12            | -
nine_q5-today     | 20/38 | 6/21       | 0          | 0         | 18     | 1.96            | -
```

Raw answers with each model's reason are in `results/`. `python run.py --score` prints the table.

## What it says

1. **What the judge sees matters most.** The same 9B goes from 20 to 33 right when CSV, Excel and Python files show
   their contents instead of their names. Today's `judge` only reads PDFs and Word files, so most spreadsheets and
   scripts come back unsure. This is a scaffold fix (B10), and it helps every model.
2. **Clef-flash is the best value.** It was perfect with content, at 0.47 s per item hosted (network included) and
   about $1 per 100,000 items. Cloudflare reports 39 ms per decision on its own hardware. It also says yes or no
   from a probability rather than from generated text, so "unsure" is a threshold we choose.
3. **But the hosted Clef sees real content.** Like idli-remote, it is only usable on test or synthetic data. For
   real data it has to run on the person's computer or the DGX: 18.8 GB plus a 0.24 GB head, its own runtime
   (transformers or SGLang), and no sharing with our 9B (its weights differ; checked tensor by tensor).
4. **BF16 vs Q5:** 35 against 33 right, at about twice the time per item. A small gain. Both 9B variants are
   cautious: their mistakes are mostly "unsure" on the no side, plus one shared error (extinct dodos called endangered).
5. **Muse is no better than the 9B here** and four times slower.
6. **The set is too easy at the top.** Clef and idli-remote both scored 38/38, so this round can't separate them. A
   harder second set (longer files where the clue is past the first 1,200 characters, mixed-language text, scanned
   images) would.

## Labels to confirm (owner)

The calls most open to argument, where a model disagreed or the label is a judgement:
- `Collections/museum_extinct_specimens.csv` (extinct dodo, passenger pigeon): labelled **no**; both 9B runs said yes.
- `Reports/lantana_removal.pdf` (invasive plant removal): **no**; the 9B said unsure.
- `Reports/forest_carbon_paper.pdf` (a passing mention of habitat): **no**; the 9B said unsure.
- `Budgets/tiger_corridor_budget_2026.xlsx`: **yes** (a budget, but for a tiger corridor).
- `Volunteers/turtle_hatchery_rota.txt`: **yes** (logistics for a threatened species).
- `Field data/hornbill_nest_notes.docx`: **yes** (great hornbill is Vulnerable, not Endangered; read here as
  "threatened").

## Reproduce

```
python build_data.py                       # needs LibreOffice for the PDFs
python run.py nine_q5 --cond content       # and nine_bf16, muse, clef, remote; --cond today
python run.py --score
```
