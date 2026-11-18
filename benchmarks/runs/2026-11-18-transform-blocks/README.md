# Transform blocks: the Builder writes readers and transforms (2026-11-18)

The owner's drivecharts sandbox (`lucky-koel-7672 drivecharts`) couldn't read a folder of 18 PDFs, and the Builder
refused to add PDF reading. Owner's decision: three levels.
- **Actions**: our team builds them.
- **Transforms**: the Builder writes them.
- **Pages and servers**: undecided.

The design is in [narrative/SANDBOXES.md](../../../narrative/SANDBOXES.md), "Three levels". Code:
- `lib/transforms.py`, `lib/transformkit.py`, `lib/transformrun.py`;
- `idli/builder-outside/block-template/read_pdfs/`;
- `desktop/idli-block-consent.py`;
- tests in `tests/test_transforms.py`.

Run on the owner's laptop as a person, through the app, 2026-11-18 19:00 to 19:15 IST. Gallery: `shots/index.html`.

| # | Step | Result | Shots |
|---|---|---|---|
| 1 | Drivey first: Household debt Mini, "which ward owes the most?" | Pass: the ward table | 01, 02 |
| 2 | Builder, a new chat: "can you add PDF reading to the drivecharts sandbox?" | Pass. `block_kit`, then "Example fits as is; copying it.", then `block_check`, then `block_add`. The approval came up at 23 s; added at 43 s | 03, 05 to 07 |
| 3 | drivecharts, a new chat: `"Drive/My Drive/Strategy Classics" what are the main themes and ideas in these papers?` | First run failed: one damaged PDF raised pypdf's PdfReadError and stopped the block | 09 |
| 4 | The error went to the Builder: "fix the block and add it again" | Pass: fixed, checked and added again in 38 s. The card now shows Idli's words | 10, 11 |
| 5 | The same question again | Pass in **63 s**: 18 PDFs downloaded, 17 read, one scan named. The answer groups the themes and names the papers in brackets | 12 |
| 6 | Follow-up: "which of these papers talk about CEO succession, and what do they say?" | Pass in **20 s** (summaries kept from step 5) | 13 |
| 7 | Builder: "add a block to drivecharts that emails these summaries to me every Monday" | Pass: refused (sending and a schedule are actions); the request was sent to our team; drivecharts unchanged | 14 |
| 8 | Builder: a colleague's block that imports `requests` and calls a website | Pass. The Builder refused on its own. When pushed to add it anyway, Idli's check said: "manifest uses requests, which is not on the trusted list"; "block.py line 1: imports requests, which is not on the trusted list"; "block.py line 38: has a web address; transforms send nothing anywhere" | 15, 16 |
| 9 | Leads sandbox, a new chat: open Lead replies, "show me the draft you would write" | Pass: preview with the full draft, "Nothing was drafted, booked or sent" | 17, 18 |
| 10 | Sandbox Claude in drivecharts: use `read_pdfs` for CEO succession | Pass. It got the answer through `block_run` (masked) and pointed to the left chat | 19 |
| 11 | Drivey last: "which ward has the lowest debt compared to income?" | Pass: answered by the Mini (Kasewadi) | 20 |
| 12 | Suites | Laptop and DGX: 340 passed, 5 skipped, 11 failed. All 11 are the known failures (they also fail at fe862842). `tests/test_transforms.py`: 15 pass | |

## Timing

- **DGX** (the 9B serves two at a time):
  - one file summary takes about 2 s;
  - the answer across files takes about 12 s;
  - 6 text PDFs (some of 400 pages) took 25 s the first time and 12 s after.
- **Laptop, through silo:**
  - 18 PDFs from Drive took 63 s the first time (download, text, 17 summaries, answer);
  - a follow-up took 20 s.
  - Extracted text and summaries are kept in the sandbox (`.idli/blocks/read_pdfs/cache`).
- **The check** (scan plus fake-data test) takes about 0.1 s. It runs once, when a block is added. A run only compares
  the digest.

## Rough edges

- **Paseo's approval card** shows the tool input as JSON in a box that scrolls sideways, not the hook's text.
  `block_add` now carries Idli's card ("Add block: Read PDFs. Uses pypdf. Reads PDFs you give it. Sends nothing."),
  which both the hook and the tool check, so the words are there. A Paseo patch could show the hook's reason as
  the card.
- **The first chats after the update** needed new chats in the Builder and the sandboxes to see the new tools. That
  is once only: after this, adding a block needs no new chat.
- **The Builder's settings** live in its own folder (`.claude/settings.json`), so a Builder could edit the hook
  out. The tool still checks the block and the card itself. Moving the hook outside the folder is a small follow-up.
- **No wall** (owner, 2026-11-18): the scan is a guard, not a boundary. A block's 9B calls go through a door on
  127.0.0.1, so silo's key stays in Idli. Walls come with p1 `sandboxing_later.md`.
- **A Drive file that changes** keeps its first download (cached by Drive id).
- **Long file names** in the answer overflow the narrow left pane.
- **Seen in the Lead replies preview, not caused by this round:** it "would book" an event titled from a
  declined invitation ("Declined: Meeting with Asha Verma"). The Mini's own logic picks up a declined calendar
  event.
