# 2026-11-14, 15:00 IST — No more dead-end loops, a chart popover, and a per-file privacy choice

The owner asked for three things after the held-out run: interactive charts that let a person point at the confusing
piece, no more "same useless answer again" loops (their chat dac6846c: "monthly income" read as a trend three times),
and a per-file choice between a fake copy and a masked copy for Claude, with "always ask" or "auto" review.

## Built
- **Loop fix (Careful, lib/careful.py):**
  - a reading the file can't answer, or the same reading again after a correction, becomes a "Which view" card of
    what the file can show (the named ward highlighted), never a repeated refusal;
  - a typed correction keeps the figure, and the 9B is told which reading was rejected;
  - a figure's name ("monthly income") is not a trend;
  - the figure the question's words name beats the 9B's guess (on the real file it had answered "monthly income"
    with debts);
  - unnamed groups the 9B invents are dropped, and "all wards / no filter" clears any filter;
  - "why is it low?" naming no group carries the group under discussion.
- **Chart popover (lib/form.html, formserver /api/say):** click a bar on the dashboard for "How is this number worked
  out?", "Show the rows behind it", "Compare it with the others", "This looks wrong", a comment box, or "Narrow the
  dashboard". The question arrives in the chat as the person's message naming the bar (`paseo send`).
- **Per-file privacy:**
  - Codex built the engine in worktree io-idli-mask (lib/privacy.py and privacy_engine/, from io's regex + GLiNER +
    vault, review page /privacy, 7 tests);
  - I wired it in: a privacy card when a file opens (every model; lib/modes.py privacy_route, also on Muse's path in
    the router); `file_privacy` saves it and opens the column review;
  - in mask mode each question is shown masked on a "Send to Claude" card; Claude (`claude -p`, the person's own
    account, Idli's config stripped) plans the form spec; the numbers are worked out locally; "Keep it on this
    computer" falls back to the private model;
  - definition questions and answers to Idli's own cards never go to Claude;
  - a short place name in a question gets the file's code (yerawada -> the Yerawada Ward code).

## Tested
- **Offline (real 9B, synthetic file):** the loop, popover, mask and earlier dev scripts all pass after the fixes.
- **In the app on the laptop (owner's real households file, test account), clicking and typing like a person:**
  - the privacy card;
  - the column review: household names weren't flagged because the laptop has no scanner, so I ticked the column by
    hand;
  - "Send to Claude" with the masked text shown, then "Planned by Claude from: … Worked out on this computer";
  - "Keep it on this computer";
  - the popover on the Kasewadi bar arriving in the chat;
  - a fresh Careful chat: "how has vulnerability changed from last year?" gave the "which view" card, then "not over
    time, just across the wards" gave all five wards.
- **Bugs found in the app and fixed:**
  - the Drivey tool allow-list lacked file_privacy;
  - the router missed the mode saved by file_privacy;
  - Claude Code's new card-answer wording leaked into questions;
  - Careful's own card answers were offered to Claude;
  - the debt-for-income figure pick.

## Open
- The laptop has no GLiNER scanner (regex only), so names aren't suggested for masking there. The DGX privacy server
  on the tailnet answers without a token.
- Masked list answers ("highest debt") don't show the sorted column.
- Muse's first turns took 4-6 minutes today.
- Old test chats in Drivey: Privacy test, Privacy test 2, Loop test 1-3, plus the earlier Careful/Auto tests.
