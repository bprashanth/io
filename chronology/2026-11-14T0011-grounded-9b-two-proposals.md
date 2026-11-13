# 2026-11-14, 00:11 IST — Two proposals for the Yerawada failure, built side by side on the 9B (in progress)

The owner brought two external proposals for the same failure and asked for both, built independently, on the 9B,
as two choices in the UI, tested by me in the app as a person would. Plan, harness and traces:
[benchmarks/runs/2026-11-13-grounded-9b](../benchmarks/runs/2026-11-13-grounded-9b/PLAN.md).

## The failure, from the owner's chat

Chat `309d9db3` on the laptop (mode idli-9b, 2026-11-12). "help me understand why yerawada ward is so high":
- The 9B's spec had five measures and a filter to Yerawada alone, and the chart drew one blue bar.
- Asked about the axes, the 9B described a grouped multi-ward chart.
- Told "all im seeing is a single blue bar", it defended the description and sent Claude a chart request.

Since then, commit `0a2c80ed` stopped drawing charts for a single row. The rest of the failure was not fixed.

## Built (commit 2a3e544e)

- **Careful** (`idli-9b-careful`, `lib/careful.py`):
  - the 9B fills a typed partial intent, in llama.cpp's JSON-schema mode;
  - code asks "which figure?" when none was named;
  - a "why is X high" question compares X with the other wards, with counts, blanks and the weighting stated;
  - "why might it be higher" lists what goes with it (labelled not causal) and checks the spread for outliers;
  - follow-ups about the chart are answered by code from the manifest, and "table" re-renders it.
- **Auto** (`idli-9b-auto`, `lib/auto.py`):
  - the 9B fills the form plus an archetype, an ambiguity flag and candidate figures;
  - code adds a baseline;
  - an ambiguous figure gets a profile of each candidate as a % difference from the whole file;
  - the render receipt is the 9B's only source about the chart;
  - when the person pushes back, the wrong turn is masked and the receipt is re-injected;
  - other models are never offered.
- **Shared** (`lib/receipt.py`):
  - the receipt reads the bars actually drawn from the SVG, since vl-convert labels every mark;
  - it records which axis is x and which is y, as on screen;
  - it holds the unit list, the pushback detector and the reply checks.
- **Menu entries** "Idli 9B · Careful (asks first)" and "Idli 9B · Auto (acts first)", in `desktop/setup-laptop.py`.

## First offline results (real 9B, synthetic file with the real ward names)

- **Careful on the owner's Yerawada words:**
  - it asked which figure, then drew 5 bars with Yerawada marked and the baseline dashed;
  - it read the axes from the receipt;
  - on "single blue bar" it checked and said the chart has 5 bars;
  - "why might it be higher" gave associations plus the outlier check.
- **Auto, the same script:**
  - it showed a profile of five figures as % difference from the whole file;
  - it held its ground on "single blue bar", quoting the receipt.
- **Found on the way:**
  - the receipt first called the category axis "x" for horizontal bars, so the 9B put the categories on the wrong axis. Fixed: the receipt now records the axes as drawn, and the check catches a wrong axis.
  - Auto's 9B wrote "lower income and higher debt lead to greater vulnerability". Proposal 2 has no causal rule, so this was kept as a difference between the two, not patched.

Next: all six scripts in three modes, fault injection, then the laptop.

## Update, 00:50 IST: round 2 and the app

- Both modes are in Drivey's menu on the laptop. The code was copied there as local sync commits, the Paseo config
  backed up and reloaded, and the DGX router (muse-prefix-proxy) restarted twice.
- **Tested in the app on the owner's real households file**, typing and clicking like a person.
  - **Careful:**
    - asked which figure;
    - compared Yerawada with the other wards. Yerawada is 2nd of 5 on vulnerability; Ramtekdi is 1st;
    - axes exact; holds to 5 bars on "single blue bar";
    - "why might" found two households driving most of the gap;
    - debt (misspelled "yearwada") compared on averages;
    - the formula question answered with the formula;
    - no-dates trend refused.
  - **Auto:**
    - diverging %-difference profile;
    - axes right, holds to 5 bars on pushback;
    - but opened with "You're absolutely right — I apologize" before the correct facts;
    - used causal wording;
    - wandered between tools offline.
- **Fixed in the app round:**
  - an "undefined" row in reference-line charts;
  - Careful now sends the person's own words to the form;
  - a code rule answers "how is it calculated / divided" with the formula.
- Report with the scorecard: [REPORT.md](../benchmarks/runs/2026-11-13-grounded-9b/REPORT.md).
