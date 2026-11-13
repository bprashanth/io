# Grounded 9B: Careful vs Auto — report

> **Correction, 2026-11-14 (after the owner's review):** the first version below compared against the old idli-9b
> mode on the very scripts I tuned on. The right baseline is **Muse 30B** (today's product), and the score that
> counts is on **held-out** questions. That run is the next section; the earlier scorecard is kept below it,
> marked as development results.

## Held-out results (code frozen at 09e7de3c; Muse 30B as the baseline)

**Set-up.**
- **Questions:** 6 scripts and 19 turns, written before any run. Four are about households, in new wording and using
  the proposals' cases I hadn't used: swap the figure, median, a table, a share, how many rows were left out,
  outliers, and a causal trap.
- **A second file:** two scripts on the field programme tracker, which was never looked at during development (three
  tabs, dates, officers, a "leave out cancelled" rule).
- **The person:** answers a card with the option matching their intent, else the first option.
- **Muse** runs through the real router (8185), with Idli's CLAUDE.md.
- **Harness:** chats start as in the app (link, file_get, card answered).
- **Fairness:** the harness was fixed three times (teaching recorded as a detour; the start as in the app; no form
  page server) without touching product code.

**Scoring.** Each turn, by me, from the traces: ✓ right and grounded; ~ partly (right numbers but missed the point,
or right but with leaked or garbled text); ✗ wrong (wrong figure, wrong claim about the chart, crash, or a detour).

| | ✓ | ~ | ✗ |
|---|---|---|---|
| **Muse 30B** (today) | **13** | 4 | 2 |
| Careful (9B) | 5 | 7 | 7 |
| Auto (9B) | 4 | 7 | 8 |

**What this says:**
- **Turning a question into the right form, the 9B modes are worse than Muse on new wording.**
  - Careful silently swapped "median" for a different figure (income per member).
  - Careful listed every row for "how many were left out", and answered "what share" with a count.
  - Careful ranked officers by money for "most visits", and crashed on "month by month" (a date bug on the new file).
  - Both 9B modes ignored the tracker's "leave out cancelled" rule, so their totals include cancelled visits. Muse
    applied it.
  - Auto wandered: 224 s and five form calls for one turn. It leaked its checks ("You're absolutely right—I never
    calculate numbers myself"), and on the tracker it compared a village's total with the whole file's total (−78%).
- **On talking about the chart, Muse has the incident's failure and Careful doesn't, even on the unseen file.**
  - Muse put "Village" on the bottom axis; Village is down the left, and the amounts run along the bottom.
  - To "I can only see one bar", Muse invented a reason ("the dashboard is showing the single village filter you asked
    for earlier"; there was none).
  - On the original scripts Muse also said "that's why you see a single blue bar … it's the totals for that ward",
    called the score the y-axis, and said "the quick chart only renders one measure at a time" when it had drawn two
    panels.
  - Careful answered every axis and pushback turn right from the receipt (tracker: the bottom axis, 8 bars).
  - Auto said no chart was drawn when one was.
- **Tuned on my dev scripts, so these don't count as wins there:** the "how is it calculated / divided" rule, the
  pushback words, the misspelling handling. On held-out, the definition rule fired correctly ("what does disbursed
  mean"), but Careful still didn't answer the "is it per visit?" part.

**Recommendation.** Don't replace Muse with either 9B mode. Keep Muse for understanding the question and take the
part that held up on held-out:
- the render receipt read from the drawn chart;
- chart follow-ups ("what's on the axis", "I only see one bar") answered by code from it;
- the "why is X high" comparison with a baseline.

That means adding those to the Muse chat (in the router, like careful_chat's READ/VERIFY routing), then running this
same held-out set again. The 9B form-filling needs more work before it competes, and a held-out set it hasn't seen.

---

# Development results (tuned on these scripts; not a fair score)

2026-11-14. Plan: [PLAN.md](PLAN.md). Code: `cowork/lib/careful.py`, `cowork/lib/auto.py`, shared
`cowork/lib/receipt.py`, routing in `cowork/lib/modes.py` (`careful_chat`, `auto_chat`). In Drivey's model menu as
**Idli 9B · Careful (asks first)** and **Idli 9B · Auto (acts first)**; Muse stays the default.

## How it was tested

1. **Offline:** `harness.py` plays Claude Code against the real 9B (Qwen3.5-9B Q5_K_M, llama.cpp) on a synthetic
   households sheet. The sheet has the real ward names, unequal ward sizes, blanks, two outlier debts and a zero income.
   - Six scripts: the owner's own words from chats 309d9db3, 37b9cde2, cdb532f2 and 409bec47, plus the proposals'
     T01-T04, T10-T12, TC1-TC5 and F01.
   - Two rounds; round 1 found bugs that were fixed for round 2.
   - Baseline: today's `idli-9b` on the same scripts.
   - Traces: `traces/`. Logs: `logs/` (round 1 in `logs/r1/`).
2. **In the app on the laptop:**
   - New Drivey chats on each model, run on the owner's real households file (test account).
   - Driven like a person: card options clicked with the mouse, questions typed into the message box, the screen
     read back, screenshots taken.
   - Chats: "Careful test", "Careful test 2", "Careful test 3", "Auto test".

## Scorecard (round 2 and the app)

| Check | Old idli-9b | Careful | Auto |
|---|---|---|---|
| "why is yerawada ward so high" (T01, TC3) | Five figures for Yerawada alone; no comparison | Asks which figure, then Yerawada vs the other wards: counts, blanks, rank, weighting stated; 5-bar chart, Yerawada marked, dashed baseline | Profile of 5-6 figures as % difference from the whole file (diverging bars); no question asked |
| "what is on the y vs x axis" (T02, TC1) | Wrong axis; or "I didn't show a graph" | Exact, from the receipt, written by code (0 s) | Right in round 2 and in the app. Wrong in round 1 because of a receipt bug (fixed) |
| "all im seeing is a single blue bar" (T03, TC2) | Agreed with a chart that was never drawn and opened a Claude chart request | Checks what was drawn, holds to 5 bars, says how to see the rest | Holds to 5-6 bars with the right axes. In the app it opened with "You're absolutely right — I apologize… let me rewrite" before stating the correct facts |
| "why might it be higher?" (T01.4, T09) | Claude chart card | What goes with it (labelled "go together, not causes"), plus the spread and an outlier check | Says the chart shows what, not why; lists outside factors to collect |
| False pushback: "only one bar? where are kasewadi and ramtekdi" (TC5) | — | Holds to 3 bars | Holds to 3 bars |
| Context: y-axis, the previous chart, a table (T11, T04) | Wrong axis | Exact; the previous chart is the right one; table from the manifest | Right in round 2; the table comes from re-asking the form |
| Trend with no dates, "estimate it", 2031 (T10, T12) | — | No date column, won't estimate, says what to collect; 2031: no data, not a zero | Trend honest. "Estimate it" offered Claude teaching. 2031 sidestepped |
| Renderer drops a panel (F01) | — | Describes only the drawn panel; the score's numbers come from the answer | Says the score isn't on the chart |
| Causal language | — | None (code writes the text) | "lead to greater vulnerability", "combine to create the high vulnerability profile" |
| Offers Claude / another model mid-chat | Yes | No | No |
| Time per question | 3-18 s | 5-7 s; chart follow-ups instant | 4-40 s; up to 5 form calls in one turn |

## What the owner's real file says (laptop, test account)

- **Vulnerability:** Yerawada is 2nd of 5, not 1st.
  - Yerawada 5.33 (6 households) vs 4.71 for the other wards' 24 households together. Ramtekdi is 6.33.
  - Without its two highest households, Yerawada's average is 4.25: two households make most of the gap.
- **Debt:** Yerawada is 1st, at Rs 81,667 average vs Rs 55,208 for the other wards together.
- Auto's profile shows the same direction against the whole file: vulnerability +10%, months owed +66%, debts +35%.

## Bugs found and fixed while testing

**Round 1, offline:**
- The receipt called the category axis "x" for horizontal bars, and the axis check broke once a receipt passed
  through the chat (JSON).
- **Careful:**
  - a misspelled name ("yearwada") wasn't recognised;
  - the 9B invented groups the person never named;
  - three named wards were lumped against the rest instead of compared with each other;
  - "how is it calculated?" was answered with a number;
  - a year the file doesn't have was ignored;
  - totals were compared instead of averages.
- **Auto:** asked the form the same question again and again; called `chart_show` for a chart that isn't saved.

**In the app:**
- The reference line inherited the ward axis and drew an "undefined" row.
- Careful still let the chat 9B reword questions and pick other tools. Fix: when a file is open, Careful sends the
  person's own words straight to the form.
- "are you saying … divided" was still classed as a comparison. Fix: a code rule always answers it with the figure's
  formula.

## Differences between the two proposals

- **Careful** keeps the 9B to filling the form.
  - Code writes every reply, so it can't contradict the chart, invent causes, or reword the person.
  - It asks one question (which figure), but only when the figure is missing.
  - Chart follow-ups need no model call.
  - Costs: the replies read as reports, not conversation; the 9B's intent still varies (DESCRIBE vs DISTRIBUTION labels).
- **Auto** keeps the 9B talking.
  - The receipt fixes what it says about the chart, which was the incident.
  - It doesn't fix the rest: causal wording, wandering tool use, apologising before contradicting itself, and
    leaking internal checks into the reply ("let me rewrite this using only the numbers from the tool responses").
  - It answers in one step, with a useful multi-figure picture.

## Not done / open

- **Not built:** Careful's full harness from the proposal (12 dialogues with paraphrases, a holdout set, repeated
  trials); Auto's LLM judge. These runs are single trials.
- **Careful polish:**
  - the formula is shown as SQL ("NULLIF");
  - "one panel" isn't in the pushback words;
  - "Distribution" labels a plain breakdown.
- **Auto:**
  - the leaked check text, and the apology before contradicting itself;
  - a limit on form calls per turn;
  - the causal words are kept as the proposal wrote it.
- **Not decided:** whether either becomes the default instead of Muse. The owner should try both in Drivey.

## For the integrator

- Chronology: `chronology/2026-11-14T0011-grounded-9b-two-proposals.md` (and its update).
- The laptop runs the DGX code as local "sync" commits on top of 777140b2 (its old pre-declaude history). A real
  reset to the branch needs the file-skills backup first.
