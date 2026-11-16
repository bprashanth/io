# 2026-11-16 11:00: Idli Desktop narrative; checkpoint for handoff

**Asked:** write up what we are doing: what a Team is, what a Mini is (a workflow such as email leads -> Excel ->
calendar, versus Drivey's data + scripts + narrative + follow-up questions; are they the same pattern?), and the
building blocks (small models, redaction, large and small models together, escalation with consent, logins and the
browser, sharing, organising Minis). The goal: an operating layer for NGOs to use AI first at a manageable cost,
with privacy. Then checkpoint so another agent can take over here.

**Written**
- [narrative/IDLI_DESKTOP.md](../narrative/IDLI_DESKTOP.md), rewritten in place. The 2026-11-13 strategy brief it
  replaces is `git show 459eed69:narrative/IDLI_DESKTOP.md`.
  - A Team is a collection of Minis, the people who use them and the rules they share, for one kind of work.
  - Data Minis and workflow Minis have the same shape:
    - what the Mini is bound to;
    - what the large model learned on;
    - entry points and the code behind them;
    - the small model's choices;
    - the narrative;
    - escalation;
    - how it grows.
  - They differ in effects: workflow Minis write, run over time, break when sites change, and need more trust. The
    data Mini is the read-only case.
  - The building blocks are each marked built, tested or idea.
- [docs/idli-handoff.md](../docs/idli-handoff.md): a new checkpoint at the top (state at 2026-11-16), and an updated
  reading order. The 2026-11-11 checkpoint is kept below it as history.

**State at this point**
- Commit `bed5c05d` (Teams page, Paseo idli25), plus this one; not pushed.
- The laptop is cleaned for the owner's test of the new team flow.
- Details: [2026-11-16T0930-teams-page-split-repair.md](2026-11-16T0930-teams-page-split-repair.md).
