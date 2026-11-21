# Idli: a smart model teaches a private model, and the desktop app keeps what it learned

Written 2026-11-12, after the split-panel and Vega-Lite work. This is the design as it stands, and why. The running
log is [cowork-poc.md](cowork-poc.md); how to resume work is [idli-handoff.md](idli-handoff.md).

## The idea

There are two models.
- **The teacher** is a frontier model (Claude). It is good at open-ended work: reading a messy spreadsheet,
  deciding what a column means, writing checks, designing a chart. It must never see the person's data.
- **The worker** is a private model that runs where the data is allowed to be (Muse 30B on our own box today; a 9B
  was tried as the free tier). It is not good at open-ended work. It is good enough to follow a scaffold: pick
  from a short menu, fill in a form, show a card.

The teacher never touches the real thing. It learns from **stand-ins**, a fake copy of a file (same shape, made-up
values) or a test account on a website. What it hands back is never an answer about the person's data. It is
**scaffolding**: a form with named measures, breakdowns and filters, the checks that catch mistakes, chart code,
and site tools that read a page like an API. The worker then runs that scaffold on the real data, on the
person's machine.

So the worker's job shrinks to choosing. It chooses which form dials to set, and which card to show next. Code does
the arithmetic, the rendering and the wording of numbers. Every time the teacher teaches something, the worker can
do a slightly bigger set of tasks well, and the next person with the same kind of file doesn't need the teacher at
all.

Data analysis is the first domain because it is where privacy bites hardest (household surveys, beneficiary
registers, payments). The pattern is general: any open-ended task where a strong model can learn from stand-ins and
leave behind code that a weak, trusted model can drive.

**The desktop app's purpose** is to make that teaching loop easy for a non-technical person, and to keep what it
produces (the scaffold and the worker's tooling) as reusable, shareable artifacts.

## What the person sees

One window (Paseo, a desktop app that runs Claude Code chats, with our patches):

- **Start here**, a system workspace: the **Logins** chat (Google, Claude and the private model are checked and
  signed in) and a **Minis** tab that lists the workflows Idli has learned, one per kind of file, each with a Share code. A Drive tab
  appears only while Google needs a sign-in.
- **Idli**, the person's workspace. Every Idli chat comes with a **split**:
  - on the left, the worker (Idli, on the private model), working on the real file;
  - on the right, that chat's own teacher conversation (Claude, on a fake copy), or a placeholder until there is
    one. Switching Idli chats swaps the right side to that chat's Claude conversation.
  - the side in control has a bright border and the other side is dimmed, so a hand-off reads as "focus moved",
    not "I'm somewhere else".

A typical session:
1. **Open.** Paste a sheet link. Idli downloads it through the app's browser and opens its form (a dashboard tab).
2. **Clean.** If the checks find problems, a card offers a **checked copy** in the person's Drive (problem cells in
   red, a comment per kind). "Continue" reads the copy back from Drive with their fixes.
3. **Ask.** The worker sets the form's dials. The answer text and the chart are rendered by code.
4. **Drill down.** In the chat ("break Ward D down by household head"), or by clicking a bar in the dashboard.
5. **Teach.** When the form can't do something (a share of a total, a new measure, a chart it can't draw), a card
   offers to send Claude a fake copy. On yes, Claude opens on the right, asks its questions with cards, writes
   the measure or the chart code against the fake copy, and hands focus back. Idli then runs that code on the real
   file.

## The pieces

| Piece | What it is | Where |
|---|---|---|
| **Fake copy** | Same tabs, columns and shape as the real file; every value made up; people's names replaced consistently (places stay places); the question rewritten with the same fakes. The person sees exactly what Claude gets before saying yes. | `cowork/lib/filekit.py` |
| **File skill** | What the teacher leaves behind for one file: `skill.json` (columns, measures, breakdowns, filters, presets, normalising rules, checks), the fake copy it learned from, tests, and chart code. Versioned; the dashboard and the worker read it. | `cowork/file-skills/<file>/` |
| **Form engine** | Turns a spec (measures, group_by, filters, date, preset) into SQL over the real file and the answer text. It also forgives the worker's slips: period names, date ranges written as filters, "not everything but one" read as that one value. | `cowork/lib/formkit.py` |
| **Checks and the checked copy** | The skill's validations flag problem rows; the checked copy puts them in the person's Drive to fix; nothing is ever silently dropped or merged. | `formkit`, `fixkit.py`, `workcopy.py` |
| **Charts** | Code picks the chart from the answer's shape (bars, a panel per figure, a time line, a heatmap, a point map, nothing for one row). The same Vega-Lite spec renders as an SVG in the chat (offline) and interactively in the dashboard, where a click drills down. Claude's own charts are chart code run in a sandbox on the real data. | `cowork/lib/vlchart.py`, `chartkit.py`, `form.html` |
| **Tools and cards** | The worker's tools (`file_get`, `file_open`, `file_ask`, `form_explain`, `working_copy`, `chart_request`, `teach_send`, ...) return a `card` and a `then`. Every decision point (upload a copy? continue? send to Claude?) is a card with fixed options. Consent is code's, not the model's. | `cowork/sites/files/tools.py`, `cowork_mcp.py` |
| **Teaching chat** | Claude Code with the teach-file skill, run by a launcher in the fake-data folder with no browser tools, opened beside the Idli chat it serves (label `idli.pair`). | `cowork/desktop/claude-teach.sh`, `.claude/skills/teach-file` |
| **Model router** | Idli's chats reach the private model through one endpoint that can route by model name (Muse today; 9B and "steam" code-only modes kept for experiments). | `dgx/muse_prefix_proxy.py`, `cowork/lib/modes.py` |
| **App patches** | P13 opens a chat on one side of a split and focuses it; P14 draws the focus border; P15 pairs each Idli chat with its Claude chats and shows a placeholder. Built from Paseo 0.15.2 and installed by pointing the app at our build. | `cowork/desktop/paseo-idli-split.patch`, `install-paseo-ui.sh` |

## Design rules we arrived at (and the evidence)

- **The model sets dials; code computes and words the numbers.** When the 9B reworded answers it dropped a number in
  13 of 53 turns; code rendering kept every fact (E4). Unit formats come from the skill, not label guesses (a
  count was printed "Rs 16").
- **Keep the planner that works; move coordination into code.** Codex's experiment: replacing the form planner made
  things worse (12/20 vs 4/20 and 9/20). Keeping it and moving the chat-moving into code kept 19/20, with a third of
  the calls. The "steam" mode tested that in the app. It was fast but unreadable, and it couldn't converse, so the
  shipped worker is Muse with code-owned cards.
- **Every step that changes something is a card.** Upload, continue, send to Claude. The 9B once sent a fake copy
  to Claude after "Not now"; code now refuses that without the yes.
- **Never drop or merge rows quietly.** Messy rows are drawn as they are and marked in the checked copy (owner
  rule).
- **Ask, or say it isn't there.** Vague words ("poor", "big villages") and names not in the file ("the IAF funder")
  went to Claude to teach. With a clarify/absent reply and code hints listing the matching values, Muse asked or said
  "not there" in 29 of 32 steps (9B: 24). Not in the product yet.
- **The teacher only ever sees stand-ins.** Fake copies are checked for real values. Labels the person ticks are the
  only real values that cross.
- **Show the hand-off.** One window, the worker left and its teacher right, and a border that moves. People lost
  track when the teacher lived in another workspace.

## What is reusable, and why sharing matters

What a teacher produced for one person's file is useful to everyone with the same kind of file: the same register
template, the same survey form, the same tax export. A skill holds no data rows (it was written against a fake copy)
except labels the person chose to share. So the natural next step is for one person to **share a skill (form,
checks, charts) or a site plugin** with another person, and for that person to use it without teaching
again. That is what turns a one-off teaching session into a growing library. Shipped: a share code per Mini
([proposals/idli-sharing.md](../proposals/idli-sharing.md), which also has the ways tried and the open sync
questions).

## Open problems

- Claude's charts are still code (matplotlib), not Vega-Lite specs, so they look different from the form's charts and
  can't be drilled into.
- The clarify/absent replies and code value hints help a lot on Muse but are not shipped; the 9B is not reliable at
  them.
- Paseo patches must be rebuilt for each Paseo release (0.15.4 is pending); the split relies on one workspace per
  folder, because Paseo doesn't tell a chat which workspace it is in.
- Website teaching (test accounts in the browser) is parked; it needs the browser, which the teaching chat in the
  split deliberately doesn't have.
