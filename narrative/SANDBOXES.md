# Sandboxes: the Builder outside, the work inside

Decided by the owner on 2026-11-18. Built and tested the same day. This replaces teams, the Teams page and the
per-team Builder. Drivey is unchanged.

## The model

- **Builder** is an ordinary Claude Code project in the sidebar (`~/idli-insights/builder`). The person does any
  Claude Code work there: scripts, pages, dashboards.
  - It never sees private files or accounts.
  - When a workflow touches private accounts or files, the person types `/sandbox` (or just asks). The Builder
    then asks:
    - what they want to do;
    - whether the data has names, places or phone numbers;
    - whether Idli may ask an outside service (ask each time, never, or always; masked data only);
    - which accounts it uses (by role, e.g. "me", and for testing a second account playing a contact).
- **Blocks.** The Builder maps the workflow onto a fixed list of building blocks (`lib/blocks.py`):

  | Block | What it does |
  |---|---|
  | `drive_files` | Drive files, Minis and questions, as in Drivey |
  | `gmail_search`, `gmail_read`, `gmail_draft` | Find, read and draft mail. Drafts only: the person presses Send |
  | `calendar_freebusy`, `calendar_book` | Free times, and meetings with guests. A booking has a fixed key, so it is never made twice |
  | `sheet_read` | The rows of a Google Sheet, inside an account workflow (a leads list) |
  | `nine_b` | The private model's judgement on real content (did they agree, which time) |

- **Gaps.** A missing *action* is a gap: the Builder says so plainly and makes no sandbox, and the gap goes to
  `~/idli-insights/builder/platform-requests.md` for our team. A missing *transform* is not a gap: the Builder
  writes it (see "Three levels" below).
- **Sandboxes.** Otherwise the Builder makes a sandbox: a sidebar heading named like a container, e.g.
  `merry-parrot-7ac1 leads`, with exactly those blocks and accounts. It opens like Drivey:
  - **left:** Idli, the private 9B. @ files, Minis, the privacy review and the outside service work as in
    Drivey. Plain requests ("find my emails from x", "offer three free times", "book it") go to the 9B, which calls
    the sandbox's account tools on the real accounts.
  - **right:** **Sandbox Claude**, Claude Code on masked data.
    - Files reach it as masked copies, as before.
    - Account content reaches it only through `account_peek`, masked by `privacy.mask_account_text`. The codes
      are kept, so its replies show the person the real values.
    - It writes scripts that call the blocks, tries them with `script_try` (the person is asked first; the output
      comes back masked), and saves them as Minis.
- **Where things live.** A sandbox is a folder in `~/idli-insights/teams/<slug>`. Its `team.json` has
  `"kind": "sandbox"`, the blocks and the accounts. The masked-Claude launcher, the privacy proxy, Minis and
  delete all work as for the old team folders.

## Escalation (narrative/ESCALATION_MODELS.md)

- **Insights sandboxes use model B**, as Drivey does. The 9B maps questions to Minis, the outside service writes
  a query when no Mini fits, and Claude works on masked copies.
- **Action sandboxes (leads) use model A.** The person first assembles the steps in the left chat with the 9B.
  Sandbox Claude then writes the workflow as a script, with `blocks.nine_b` for every judgement on real content,
  and saves it as a Mini. The Mini runs on this computer, and a second run never drafts or books twice.

## Routing in a sandbox (owner, 2026-11-18; lib/modes.py, served by the DGX router)

The 9B never chooses freely. The earlier rule (a typed request with no file and no Mini went to the 9B with the
account tools) gave random answers: asked for the leads, the 9B made up a sheet link (Google's sample sheet from its
API docs) and got a 404.

- **The Drivey route still owns the left chat:** @ files, Minis, cards and handoffs. Drivey itself is unchanged.
- **No Mini open, no @ file:** the question goes to Sandbox Claude, masked, after a card that shows the masked
  question ("No Mini answers that yet..."). Claude builds it with the sandbox's blocks as a short script in named
  steps, runs it through Idli (`script_try`; the real result shows on the left) and offers to save it as a Mini.
- **A workflow Mini open** (`mini_talk`, `lib/minitalk.py`, `lib/miniscope.py`), in this order:
  1. **Direct.** Plain commands need no model ("run step 2", "run it", "turn it off", "fork"). The 9B sorts
     anything else into a few fixed kinds: explain (from the steps and code), the whole preview, run, turn on, turn
     off, change. If unsure, "other".
  2. **Mapped, with consent.** "Other" is mapped, never answered freely. The menu is short and fixed: the Mini's
     named steps (run steps 1 to N in preview, show step N), the whole Mini in preview, and the sandbox's read blocks
     (a sheet the Mini reads, a Gmail search, the meetings between two days, free times). Writes are never on it.
     A Gmail search can take `from_sheet` (a sheet code), which limits it to the people on that sheet and leaves
     out calendar notices. The mapper is told to use it for questions about the Mini's people ("lead replies"),
     and not for broad ones ("all my emails today"), 2026-11-19.
     The mapper answers with one or two items and their arguments, or "none". Idli runs them on the real accounts in
     preview and shows the output as code wrote it, with one line on who picked and "Nothing was drafted, booked or
     sent".
     - The sandbox's outside setting decides who maps. Ask each time: a card shows exactly what would go (the
       masked question and the menu); Yes sends it to the outside service, "No, Idli picks" has the 9B map it with
       the same menu (the person's quality choice). Always: the service, no card. Never: the 9B.
  3. **Fork.** "None", or a change, ends at a Fork card. The fork gets a copy and the masked question, and Sandbox
     Claude makes the smallest change that answers it (split a step, add one, print more), shows it with
     `script_try` and saves a new Mini. Something the blocks can't do: Claude says so and points to the Builder in
     the sidebar. Sandbox Claude has no `builder_open` in a sandbox (it used to open a per-team Builder beside
     itself).
- **Workflows in named steps** (`blocks.run_steps`): one function per step, each printing what it found;
  `--step N` runs steps 1 to N and shows N; `--list-steps` lists them without reading anything. Idli keeps the
  titles in mini.json; opening the Mini lists them and what it can see ("reads a sheet, reads your email, sees your
  calendar...").
- **Files:** @ files with no Mini go to Claude through the privacy review, as in Drivey. PDFs that come with
  spreadsheets go too, as masked text in Claude's folder (`lib/docmask.py`: pypdf, then the folder's known values,
  the rules and the name scanner line by line; about a minute for 50 pages, kept per file version). A folder of
  only PDFs still goes to the PDF block, if the sandbox has one.
- **New read block:** `blocks.meetings(start, end)` (title, time, guests, declined) under the calendar block.

## script_try asks twice, in the left chat (owner, 2026-11-19; lib/tries.py)

Claude Code's own prompt for `script_try` ("Script Try Tool", "Rule ... overrides auto mode") meant nothing to
people. So Claude Code no longer asks: `lib/launchsettings.py` moves `mcp__idli__script_try` from ask to allow, also
in older sandboxes on their next launch. Idli asks instead, in its own pane.

1. **Gate 1:** "Claude wants Idli to read more from your accounts: <title>. Nothing is written. You'll see what it
   finds here." The card is "Run it here?" with Yes or No. A run that isn't a preview says it may draft, book or
   send.
2. **On Yes,** Idli runs the script on this computer and shows the real output on the left.
3. **Gate 2:** "Claude would get this, with private values as codes:", then the first lines of the masked output.
   The card is "Send it to Claude?" with Yes or No.
4. **On Yes,** Claude gets the masked output. On a No at either gate it gets a plain note ("The person chose not to
   run this / not to share this output. Try another way, or ask them."), and nothing has reached it, or Anthropic.

How it's wired:
- Claude's call and the left chat meet through `<sandbox>/.idli/tries/<id>.json`.
- `script_try` posts "Try from Claude: <title> [<id>]" to the left chat. The router answers with `binder_item` kind
  "Try" and the two cards.
- Claude's pane only shows the call in progress.
- Each gate waits 10 minutes, and `MCP_TOOL_TIMEOUT` for Sandbox Claude is now 30 minutes.

Gate 2 earns its place. On its first run on the laptop it showed `NAME_001 Verma`, a surname that account masking
missed.

## What the person sees

- **Sidebar:**
  - Start here (Logins, Privacy);
  - Drivey;
  - Builder;
  - one heading per sandbox.

  The Teams entry and WhatsAppy are gone.
- **Account sign-in:** Google's own page in the person's browser (Idli's OAuth app). They click Advanced, then Go to
  idli, then Select all, then Continue.
- **Labels:** the right pane is titled "Sandbox Claude", with a teal SANDBOX CLAUDE status line.

## Saved action Minis: ask, turn on, fork (2026-11-18, owner)

A saved Mini is frozen. The person builds trust by asking it things, then turns it on, or forks it to change it.

- **Ask** (left chat, `mini_talk`, `lib/minitalk.py`). Anything typed while an action Mini is open goes to the 9B
  with the Mini's steps and code. It picks one:
  - explain: it answers from the code;
  - preview: Idli runs the Mini on the real accounts with `IDLI_PREVIEW=1`. Reading works as usual, but drafts
    and bookings are only collected. The 9B answers from the output, and drafts are shown in full. Nothing is
    drafted, booked or sent;
  - run: it runs for real (never twice);
  - turn on or off: binds the Mini to an account from today (`IDLI_SINCE` adds `after:` to Gmail searches).
    Running on a schedule is a gap;
  - change: points to Fork.

  Opening an action Mini never runs it.
- **Fork** (button on the Mini card, `lib/minifork.py`). The scripts are copied, values coded again, to Sandbox
  Claude's `forks/<id>/` with FORK.md. Sandbox Claude opens on the right with the current flow and asks how to
  change it. Its `script_try` runs in preview by default. The real output shows on the left as "Run from Claude:
  <title>", and Claude gets it masked. Saving makes a new Mini with `forked_from`; the original never changes.
- **Built since:** questions the 9B can't place go to the mapping above ("Routing in a sandbox").

## Three levels: actions, transforms, pages (2026-11-18, owner)

The Builder first refused to add PDF reading to a sandbox: "a sandbox can only use blocks from Idli's fixed list".
That was too strict. Reading a PDF is quick, common and sends nothing. The owner's three levels:

| Level | Examples | Who builds it |
|---|---|---|
| **Actions** | Gmail drafts, Calendar bookings, anything that writes to an account, sends or posts, a new website, a schedule | Our team (`lib/blocks.py`). The Builder refuses and sends a request |
| **Transforms** | Read PDFs, Word files or tables; summarise; ask the private model | The Builder writes them and adds them to a sandbox, including one that exists |
| **Pages and servers** | Page servers and similar | Not decided: they may run on this computer or on silo. Left as they are |

**The trust split.**
- The Builder (outside) writes transforms. It sees the trusted list and fake data, never the sandbox's files or
  what a block finds.
- Sandbox Claude (inside) sees masked data and can only use the blocks plugged into its sandbox. Its Mini
  scripts get the same scan as transform blocks, so it can't reach past them either.

**A transform block** is a folder: `manifest.json` (name, title, `reads` such as `pdf`, `uses` such as `pypdf`),
`block.py` (`def run(kit, **args)`) and `test_block.py` (`def test(kit, run)` on fake data). The Builder writes it in
`~/idli-insights/builder/blocks/<name>/`. Code: `lib/transforms.py`, `lib/transformkit.py`, `lib/transformrun.py`.

- **Trusted imports, baked into the build:**
  - pure-transform stdlib (json, re, csv, io, datetime and so on);
  - pandas, numpy, openpyxl, pypdf and python-docx (installed with Idli's venv).

  Silo's catalog may add `trusted_imports`. They are read from the local catalog cache; nothing is fetched at check
  time.
- **The check** runs once, when a block is added: about 0.1 s.
  - It scans every `.py`: only trusted imports, and none of the following:
    - `open`, `os`, `sys`, `subprocess` or sockets;
    - `eval` or `exec`;
    - private `_` parts;
    - web addresses, or paths outside the sandbox.
  - It runs the block's fake-data test.
  - It keeps the folder's digest. A run only compares the digest, so a run costs nothing extra, and a block
    changed after its check doesn't run.
- **Adding:** `block_kit` gives the list, the kit and a working example (`read_pdfs`). Then `block_check`, then
  `block_add`.
  - The person approves one card: "Add block: Read PDFs. Uses pypdf. Reads PDFs you give it. Sends nothing."
  - Idli's hook (`desktop/idli-block-consent.py`) checks first. It refuses a failing block with the plain reason,
    without asking.
  - The card's words are Idli's: the hook and the tool both check them.
- **Running:**
  - `block_run(name, paths, question)` is a fixed tool in every sandbox, so adding a block needs no tool-list
    refresh and no new chat.
  - When @ files are of a kind a sandbox block reads, the left chat runs it straight away ("Reading 18 PDFs with
    Read PDFs. The first time takes about a minute; after that it is quick."). Follow-up questions go to the same
    block.
  - Idli downloads the @ Drive files once and runs the block in its own process. The block reaches the 9B through
    a door on 127.0.0.1, so silo's key stays in Idli.
  - Text and summaries are kept in the sandbox, so later questions are quick.
  - Sandbox Claude can call `block_run` too. It gets the answer masked, and the real answer shows on the left.
- **No wall** (owner): every platform runs blocks the same way for now, without bwrap. The scan and the trusted
  list are a guard, not a boundary. Walls come with p1 `sandboxing_later.md`.

Tested on the laptop:
- the owner's "can you add PDF reading to the drivecharts sandbox?" was added in 43 s;
- 18 strategy PDFs were answered in 63 s, then 20 s for a follow-up;
- an emailing block was refused, and a block importing `requests` was refused with plain reasons;
- Drivey and the leads Mini were unchanged.

Details in `benchmarks/runs/2026-11-18-transform-blocks/README.md`.

## Capabilities as CLIs (owner, 2026-11-19; direction, not built)

Fixing one capability at a time (an email search that couldn't be limited to the leads) doesn't scale. Instead:

- **Every capability is a CLI with arguments**, for example:
  - `mail search --query --from-sheet --since --limit --role`;
  - `calendar meetings --start --end`;
  - `sheet rows --sheet`;
  - `nine-b judge --question --shape`;
  - `pdf read`.

  Its `--help` is its schema. It reads JSON in and writes JSON out, and runs in preview unless told to act. Reads,
  transforms and actions all share this shape.
- **A Mini is a chain of invocations.** Each step is one capability call. Some of its arguments are fixed by the
  Mini (the leads sheet), some are left open (since when, which lead), and a step can take an earlier step's output.
  Glue code is kept to a minimum. Running step N or the whole chain in preview falls out for free.
- **idli-remote fills in arguments.** It gets the masked question, the Mini's chain and the argument schemas. It
  returns which steps to run, with which values, and the result is checked against the schema. It never writes code.
  "This morning's lead replies" becomes `mail search --from-sheet SHEET_1 --since today`. "All emails today" becomes
  the same command without `--from-sheet`.
- **Sandbox Claude (inside)** chains capabilities with the right arguments, adds new arguments when a chain needs
  them, and draws charts. It stays within the sandbox's import surface. The left and right panes go back and forth
  for this, through the two gates.
- **The Builder (outside)** chooses each sandbox's surface: which capabilities, imports and sources it gets. It
  writes new capabilities from trusted packages and sources, and asks our team for new actions or new account
  reads.
- **Changing a capability that other sandboxes use:** copy on write in the sandbox, additive arguments only, Minis
  pinned to a hash, and the Builder promotes. See the p1 todo `todos/idli-insights/p1/capability_versions.md`.

## Tested

See `benchmarks/runs/2026-11-18-sandboxes/README.md`, `benchmarks/runs/2026-11-18-builder-minis/README.md` and `benchmarks/runs/2026-11-18-transform-blocks/README.md`, which have screenshots for each step.
