# Handing work between agents

io is built by more than one agent on more than one machine, with the owner moving work
between them. This page is how that is done so nothing is lost at a handoff and no agent
builds on a claim it has not checked. It is about principles, not about any one machine; what
a specific machine can and cannot do belongs in the chronology, where it can go stale in the
open.

## The rule underneath all the others

**The repository is the conversation.** Agents do not share memory and the owner should not
have to relay reasoning by hand. Everything an agent learned that the next one needs goes into
a file in this repository before the agent stops. A chat transcript is not a handoff.

## Where things go

| place | what it holds | tracked |
|---|---|---|
| `chronology/` | the lab notebook: one entry per working session, append-only | yes |
| `narrative/` | field notes that argue what several entries add up to | yes |
| `proposals/` | designs not yet built, and decisions that are not an agent's to make | yes |
| `docs/` | how things are, now: the design, and pages like this one | yes |
| `benchmarks/runs/<date>-<machine>/` | evidence an entry points at: dumps, results, scripts | yes, except screenshots |
| `.prompt/` | the message for the next agent, for the owner to paste | no |

Screenshots stay on the machine that took them (`benchmarks/runs/**/*.png` is ignored). A
link to one resolves where the entry is read and dangles on GitHub, which is the accepted
trade.

## Writing a chronology entry

Name it `YYYY-MM-DDTHHMM-<machine>-<topic>.md`, using the local time the session ended and a
short machine name (`laptop`, `dgx`, ...). The machine name is not decoration: it tells the
next reader which machine could actually prove a claim.

An entry says, in this order where it applies:

- what was seen, with the evidence path;
- the cause, when found, and how it was found;
- what was changed;
- the re-test, with its result;
- **what was not tested, and why**. This line is the one most often left out and the one the
  next agent most needs.

Never edit an old entry to make it right. When an earlier entry was wrong, the new entry says
so under a "Correction to <entry>" heading. The narrative may compress the record; it may not
erase the failed attempts.

## Claims and evidence

- **Measured, reasoned, or assumed: say which.** "The wall denies reads outside the folder"
  is a different sentence depending on whether a probe was run, the code was read, or the
  config was trusted. Several findings in this project reversed a confident reading of code
  or of a tool's documentation. Prefer running the thing.
- **A test that cannot fail proves nothing.** When a check says "no", also show the case where
  it says "yes" (a control). When a test is skipped, the entry says it was skipped.
- **What one machine proves, another may not.** A distribution setting, a display, a login, a
  driver: the same code can behave differently. If a claim depends on the machine, name the
  machine.
- **A number or a line of output beats a description of it.** Paste the exit code, the header,
  the one log line.

## Splitting work between machines

Each machine is good at some things. Work goes where it can be done and checked, not where it
happens to be open.

- The agent that receives a handoff checks the boundary first: what it can verify here, what
  it can only reason about, and what must go back. That list goes in its first entry.
- Work that needs another machine is not guessed at. It is written as a request: the exact
  commands or steps, what result would confirm it, and what would refute it, precise enough to
  run without further design.
- When the boundary moves (a machine turns out to be able to do something after all), the
  entry says so plainly, and any handoff note that said otherwise is replaced.

## Decisions

An agent changes code and tests inside the product (`app/io/` and `app/io/tests/` for io).
A change of design, a new dependency, anything touching privacy guarantees, or anything outside
those directories is a decision for the owner. The agent stops and writes it down in
`proposals/` or at the end of its entry, with options and a recommendation, and does not act
on it. Once the owner decides, the decision is recorded in the next entry.

## Before a commit

- Run the test suites and put the counts in the entry (for io:
  `app/io/.venv/bin/python app/io/tests/test_codex_proxy.py` and
  `node app/io/tests/test_codex_launcher.js`).
- Commit messages say what changed and why, in prose. The reader is the next agent, not a
  changelog.
- Use synthetic data only in anything committed.
- Do not push or touch `main` unless the owner asked. The owner opens pull requests and moves
  branches between machines, and strips agent attribution from commit messages first; commit
  hashes can therefore change after a handoff, so refer to commits by message as well as hash.

## The handoff note itself

The note in `.prompt/` is short and specific to one round of work. It points into the
repository rather than repeating it:

1. Where the work stands: branch, top commit, and whether it is pushed.
2. What to read, in order: the entries since the last handoff, then any narrative or proposal
   they refer to.
3. What changed since the last handoff, in a few lines.
4. What the receiving machine should verify first, and what it should not attempt.
5. What is open, most important first.
6. Anything in an earlier note that is now wrong.

Write it last, after the entry and the commit, so it can point at both. When it goes stale,
replace it rather than adding to it.
