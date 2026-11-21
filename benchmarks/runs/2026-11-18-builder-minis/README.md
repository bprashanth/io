# Builder first, folder insights, Minis to ask, turn on and fork (2026-11-18)

The owner's round after the sandboxes run. Spec: [UX.md](../../../narrative/UX.md), sections "The Builder is Claude
Code first", "Minis: ask, activate, fork", "Insights details". Driven on the laptop over CDP, as a person. The test
accounts are 87profligate@gmail.com ("me") and 88profligate@gmail.com ("a lead").

## Results

| # | Step | Result | Shots |
|---|---|---|---|
| 1 | The owner's bug: a new Builder chat opened on Idli 9B and split into two panes | Reproduced | 00-03b |
| 2 | Builder after Paseo idli26: the old 9B chat is one pane (its empty right pane closed itself) | Pass | 04 |
| 3 | New Builder chat: the model menu shows only Claude, Opus 5.5 ticked. No Idli Careful or Auto | Pass | 05, 06 |
| 4 | The composer says "Build with public data here. For private data or your own accounts, type /sandbox." | Pass | 07, 10 |
| 5 | "hi, what can I do here?" on Opus: the same in Claude's words, one pane | Pass | 08 |
| 6 | New tab, Agent inside the Builder: Opus, the same hint, one pane | Pass | 09, 10 |
| 7 | Without Claude Code the menu falls back to Idli 9B and 30B | Unit test only (Claude Code is connected on the laptop) | n/a |
| 8 | Insights: the owner's "Strategy Classics" folder (18 PDFs, no spreadsheets) | Pass: "Strategy Classics has 18 PDFs and no spreadsheets. Idli answers questions from spreadsheets. Reading these files is not a building block yet: ask the Builder for it." Before: "Could not open those files." | 12, 14 |
| 9 | Insights: @ a folder that holds spreadsheets: uses them and says which, skips the rest | Unit tests only. No Drive folder on the laptop holds spreadsheets, and I didn't add one to the account | n/a |
| 10 | Privacy page on "Strategy classics": the hidden Notes column | Pass: "Notes entirely withheld". Before: "Notes (blank) ->" with nothing after it | 15, 16 |
| 11 | Open the Lead replies Mini | Pass: the card plus "Not on for an account yet... Ask how it works, or 'show me what you would draft'. Nothing is written until you say 'run it'. To change it, press Fork on its card." The first open ran the Mini once for real (an example run meant for chart Minis). Nothing doubled (drafts and bookings are keyed). Fixed in 7127882b | 17 |
| 12 | "how are leads picked? which file does it use?" | Pass, thin: the 9B named the leads sheet and its id, and "replied in the last two weeks". It left out how the replies are classified | 18 |
| 13 | "show me the draft response you'd write" | First ask: correct "no drafts", since every reply was already handled. After 88 sent a fresh "yes" ("Reading programme visit"): the whole reply draft, with three times, and "Nothing was drafted, booked or sent". 87's Drafts has no draft for that thread (checked through the API). The 9B's summary line above it came back empty ("Here is what it found.") | 19 |
| 14 | "Activate this mini on my account" (87 standing in) | Pass: "Turned on for 87profligate@gmail.com, starting from today (18 Nov)... Running it every morning on its own is not a building block yet." The card reads "On for 87profligate@gmail.com from 18 Nov." | 20, 21 |
| 15 | Fork: Fork button, Claude explains, change to the last 2 days, show results, save, original unchanged | Pass. Sandbox Claude laid out the flow and asked how to change it. It explained how leads are picked, set `DAYS_BACK = 2` in its copy, and ran `script_try` in preview after the person's yes. The real output showed on the left as "Run from Claude: Lead replies, last 2 days", with the full draft and nothing written. The draft card offered only a new Mini. Save made "Lead replies (last 2 days)" with `forked_from`. The original keeps `DAYS_BACK = 14`, its file is unchanged, and it is still on for 87. The fork session's tool results hold no real email or name | 22-27 |
| 16 | Drivey regression at the end | Pass: the "Household debt by ward" Mini answered "which ward owes the most?" with the ward table | 28 |

The laptop's tunnel dropped at about 16:42 IST. The owner restarted it, and steps 13 to 16 were run after that.

## What changed

- **Paseo idli26** (`desktop/paseo-idli-split.patch`, `utils/idli-builder.ts`): Builder chats are one pane; their
  menu is Claude only (Opus first), or Idli 9B and 30B when Paseo has no Claude Code; the /sandbox hint.
- **Laptop config and `setup-laptop.py`**: Idli Careful and Auto left the menu (the router still serves them).
- **`lib/drivestubs.py`, `lib/modes.py`**: a folder from the @ picker comes without its trailing slash and is now
  read as a folder. The reply names the files it used and what it skipped, or says there are no spreadsheets.
- **`lib/privacy.py`, `lib/journey.js`**: the privacy page shows filled cells, and says "<column> entirely
  withheld" when a hidden column is all blank or each cell became one code.
- **`lib/minitalk.py`** (new tool `mini_talk`, routed by `lib/modes.py`): explain, preview, run, turn on or off,
  change (points to Fork).
- **`lib/blocks.py`**: `IDLI_PREVIEW=1` collects drafts and bookings instead of writing them; `IDLI_SINCE`
  limits Gmail searches.
- **`lib/minifork.py`**, Fork on `lib/mini-card.html`, `/api/mini-fork`.
- **`script_try`**: preview by default; the real output is shown on the left as "Run from Claude: <title>".
- **Checks before saving a Mini draft** run in preview.
- **Opening an action Mini** no longer runs it.

## Tests

- `tests/test_builder_minis.py`: 11 tests.
- `utils/idli-builder.test.ts` (Paseo): 3 tests.
- **Laptop** (pytest through `uv run --with pytest`, since the laptop venv has no pytest): 325 passed, 5 skipped,
  11 failed in `tests/`, `lib/test_ccproxy.py`, `lib/test_home.py`, `lib/test_privacy*.py`, `lib/test_chat.py`.
- **DGX:** 324 passed, 5 skipped, 11 failed in the same set. The 11 are 10 in `lib/test_chat.py` and
  `lib/test_home.py::test_launcher_config_and_proxy`. They fail the same way at fe862842, before this round.
