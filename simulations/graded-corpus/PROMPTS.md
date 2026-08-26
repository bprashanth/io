# graded-corpus

## Survey Question

Across many kinds of organisations, which model answers correctly, and where does each one fail?

## Data

`../../benchmarks/t0/ngo-corpus/`

Eight synthetic organisations, each in its own folder: education, SHG savings, community health, disability welfare, donor operations, mixed programmes, rural development, and agriculture. Open one org folder at a time. Three of the orgs also exist as ready packets here: asha-kiran, sunrise-shiksha, krishi-jal-vikas.

## Suggested Questions

All 40 questions are in `../../benchmarks/t0/ngo-corpus/cases.json`, four to seven per org, each with a written expected answer. Ask them in order for one org and score each answer right or wrong against the `expect` field.

## Answers

The `expect` and `expected_rows` fields in cases.json are the answer key. The planted traps: merged headers, dd/mm dates, totals rows, amounts in paise, drifting column names.

## Results

Existing comparison results are available in:

- `../../benchmarks/runs/2026-08-22-t0-ask-v1/` (a laptop-class 9B scored 20/22 on the ask subset)
- `../../benchmarks/astronaut/README.md`

## Verification

1. Try it in Antigravity.
2. Try it in Antigravity with the shield. Press `Ctrl+Shift+P`, verify the vault, and check the last request.
3. Try it in io. Open the generated page on the local network and keep it ready for the next session.
