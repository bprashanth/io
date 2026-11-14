# 2026-11-14, 23:30 IST — Drivey as a 9B chat with @ Drive files, Mini cartridges, and Claude's CLI beside it

The owner reverted Drivey's left side to a chat with the private model (like Canvay), tested with the 9B:
- `@` picks Drive files or folders by path;
- Minis appear as slim cartridges under the opening message, and picking one turns the chat into that Mini (a small
  model maps questions to the Mini's scripts, else "I don't know");
- Claude Code's CLI sits on the right;
- Claude's charts appear in the left chat.

Style rules: no arrows (write "->", "up", "down"), no "·".

## Built (Codex x3 + me)
- **Idli side (Codex, exp/idli-chat; 56 tests; real 9B Mini mapping 84/85 incl. 20/20 declines):**
  - the router handles "Start Drivey", "Open Mini: …", "Chart from Claude:" and Drive mentions;
  - `mini_open` / `mini_ask` / `drive_fetch` tools;
  - the Drive mirror (`lib/drivestubs.py`, 166 placeholders);
  - the >10-files Auto suggestion in the review;
  - Mini limits and author/date for Claude;
  - `/api/minis-public`.
- **Paseo P19 (Codex; my fixes -> idli16):**
  - the Drivey heading's "+" creates a workspace, a labelled 9B chat (left, focused, no permission prompts) and the
    Claude CLI terminal (right, `IDLI_WORKSPACE` in its env);
  - Mini cartridges under the opening exchange;
  - P15 skips these chats.
- **Relationship visuals (Codex, exp/idli-relviz):** 5 related synthetic spreadsheets, a Claude skill with 7
  non-repeating chart templates, rendered proofs; the launcher installs the skill.
- **My fixes on the laptop:**
  - the router's typed-text detection (Claude Code sends a reminder-only message and a "system" message after the
    typed one);
  - `lib/minimap.py`, so the router (plain Python, no pandas) can map Mini questions;
  - Paseo's quoted `"Drive/…"` form;
  - Drivey chats run download -> open -> form themselves, with no cards;
  - drivefetch opens Drive in a background tab when no browser tab is open, to read the session;
  - the launcher follows its symlink;
  - idli_show finds the left chat by its label;
  - a short "[Open interactive]" link;
  - the Mini list falls back to the file's date and an author;
  - the cartridge layout.

## Tested on the laptop (real Drive, 9B)
- **The Drivey "+":** a 9B chat with an instant opening line, the Mini cartridge under it, and the Claude CLI (Pro)
  on the right.
- **Mini:**
  - picking the cartridge opened the description, the questions with options, and the example charts;
  - "which households in kasewadi owe more than 4 months of income?" mapped to ward = Kasewadi, months = 4 (Rahul
    Khan, 5.7);
  - "how many women head households in each ward?" got "I don't know" plus the list.
- **`@`:** the picker shows only Drive paths (after `git init` + an ignore file in cowork-real); Tab inserts the
  path; "how many trees are in …field_vars_indicators.xlsx?" downloaded it from Drive, opened it, and answered
  1,828 trees by species, with no cards.
- **Claude:** two multi-turn sessions with real names typed and answered in real names. A requested chart arrived in
  the left chat. In the last 12 requests that left the laptop, 0 real names and 0 ward names; only codes.

## Open
- The `git init` in cowork-real makes Paseo show "Commit" and a "worktree scripts" banner. Find another way to
  limit the picker.
- **Not yet tested live:**
  - a folder mention, including the >10 files warning (where the review shows in this flow needs deciding);
  - the relationship skill in a live Claude chat;
  - clicking an interactive chart from the left chat.
- The Claude terminal renders garbled at the laptop's narrow window width.
- About 14 test Drivey workspaces were created on the laptop; archive them.
- The author shows the OS user ("desinotorious") until IDLI_AUTHOR or accounts.json has a name.
