# Grounded 9B answers: two proposals, side by side

2026-11-13/14. The owner gave two proposals for the same failure and asked for both, built independently, on the 9B,
as two choices in Drivey's model menu, tested by me in the app as a person would (using the owner's own phrasing).

- **Careful** (`idli-9b-careful`): "Reliable Conversational Spreadsheet Analysis". It asks before guessing: typed
  partial intents, a validator, a baseline for "why is X high", a result manifest, follow-ups routed to
  READ / VERIFY / MODIFY / RE_RENDER / INVESTIGATE, and replies written by templates from the manifest.
- **Auto** (`idli-9b-auto`): "Grounded Small-Model Analytics Pipeline". It acts first: intent archetype + ambiguity
  flag + candidate measures, code injects the baseline and shows a %-difference profile, a render receipt is the
  only source for chart talk, pushback masks the wrong turn and re-injects the receipt, and Claude is never offered.

## The incident (owner's chat 309d9db3, mode idli-9b, 2026-11-12 ~18:00)

1. "help me understand why yerawada ward is so high". The 9B's spec had 5 measures, group_by ward, filter ward =
   Yerawada. The chart drew one blue bar.
2. "what is the graph you showed telling me? what is on the y vs x axis". The 9B described a multi-ward,
   multi-metric chart.
3. "how are you combining all thos enumbers here? all im seeing is a single blue bar?". It defended itself and
   sent Claude a chart request.

Today's code already draws no chart for a single row (0a2c80ed) and gives each figure its own panel. Not fixed:
no baseline, guessed measures, the 9B describing a chart it never read, defending itself, offering Claude.

## Shared (both use it; built once)

- `lib/receipt.py`: what was actually drawn, read from the SVG that vl-convert wrote (marks counted in the file,
  not taken from the plan), plus the axes and categories from the Vega-Lite spec that drew it; units from the
  measures' taught `format`; a pushback detector; a check of the 9B's prose against a receipt; a Claude-mention
  scrubber.
- The 9B's form-filling uses llama.cpp's JSON-schema mode (`response_format`), so its output always parses.

## Switches

New model ids only (`lib/modes.py`): `idli-9b-careful`, `idli-9b-auto`. `file_ask` gets a hidden `pipeline`
argument, added by the router, never by the model. Muse, idli-9b and Steam are unchanged.

## Data

- Fixture: the owner's taught households form (v2, copied from the laptop; no rows) and a synthetic sheet
  (`fixtures/make_fixture.py`) with the five real ward names, unequal sizes, blanks, outlier debts and a zero income.
- Human tests on the laptop use the owner's real households file in Drivey (test account; data stays on the laptop).

## Tests

1. Offline chat loop on the DGX (real 9B, synthetic file): the owner's phrasings plus the proposals' scripts
   (T01-T04, T06, T11 of Careful; TC1-TC5 of Auto), and fault injection (a renderer that drops series).
2. In the app on the laptop, typing and reading the screen, with screenshots.
