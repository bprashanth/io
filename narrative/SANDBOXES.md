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

- **Gaps.** A step with no block is a gap. The Builder says so plainly and makes no sandbox. The gap goes to
  `~/idli-insights/builder/platform-requests.md` for our team.
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

## Routing (lib/modes.py, served by the DGX router)

- **The Drivey route still owns the left chat.** It handles @ files, Minis, cards and handoffs.
- **A sandbox chat** has extra account tools (`mail_search`, `mail_read`, `mail_draft`, `free_times`,
  `book_meeting`, `sheet_rows`). With those tools:
  - a typed request with no @ file and no open Mini goes to the 9B;
  - the result of an account tool goes back to the 9B;
  - the 9B gets those tools and a short sandbox prompt, in place of the Drivey prompt.

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

## Tested

See `benchmarks/runs/2026-11-18-sandboxes/README.md`, which has screenshots for each step.
