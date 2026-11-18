# Escalation models: who decides what, inside a sandbox

Written 2026-11-18, from the owner's sandbox redesign. A sandbox workflow mixes three kinds of work:
- **fetching and acting** on real accounts (scripts);
- **judgement** on real content (the private 9B);
- **design**, done by the sandbox's Claude on redacted data.

Where the line between scripts and models sits can be drawn three ways. We keep all three in mind, and start with
the simplest that fits each kind of workflow.

## A. Claude writes the workflow; the 9B is a call inside it

The sandbox's Claude writes scripts from the building blocks:
- `gmail_search` and `gmail_read`;
- `calendar_freebusy` and `calendar_book`;
- `sheet_read`;
- a `nine_b` call: a prompt plus an answer shape, for example `{agreed, picked_time, unclear}`.

Idli runs the script on the real account. The 9B sees real content only inside that call, and an unclear answer
goes to the person.
- **Good for:** action workflows that are clear and repeatable (leads replies, booking, drafting).
- **Risk:** the script is fixed. A new kind of question needs Claude again.
- **Today:** this is how leads routines run (`lib/routines.py`, the judge step).

## B. The 9B picks the script, as Minis do today

The person clicks a Mini or types a question in the left chat. The 9B picks which saved script or Mini answers it,
and runs it. When it can't, it escalates to Claude, which sees only the question and redacted data.
- **Good for:** insights. The questions vary, but the answers come from a known set of scripts.
- **Risk:** the 9B's choice is the weak point. Today it is guarded by Mini tests and the "can't answer, ask Claude"
  path.
- **Today:** this is Drivey and the insights teams. Unchanged.

## C. A stronger model picks the scripts from the redacted question; the 9B calls stay in the code

A frontier or mid-size model sees the redacted question and picks the scripts and their order. The scripts
themselves call the 9B for judgement on real content.
- **Good for:** many blocks and open-ended requests, where the 9B alone picks badly.
- **Risk:** cost, plus one more model that must only ever see redacted text.
- **Today:** not built.

## Start

- **Insights sandboxes:** B, exactly as Drivey works.
- **Action sandboxes (leads):** A. The person assembles the steps in the left chat ("read my emails from x", "book a
  time"), sees each one work, and saves the result as a Mini. A Mini for an action workflow is a script with `nine_b`
  calls.
- **C:** revisit when a sandbox has more blocks than the 9B can pick from reliably.
