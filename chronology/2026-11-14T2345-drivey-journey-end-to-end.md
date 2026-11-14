# The Drivey journey, end to end on the laptop (idli18)

The journey is written in `narrative/DRIVEY_JOURNEY.md`: make a Mini with Claude (no local model), then use it with
the 9B. Built by two Codex jobs against one contract (Idli side on `exp/idli-journey`, merged; Paseo P21, build
idli18), then walked on the laptop's test account the way a person would, with the 9B, and fixed where it broke or
read badly. Laptop screenshots (they show names from the owner's test file, so they stay out of git):
`~/idli-journey-shots/2026-11-14/` on the DGX. Page screenshots from the synthetic browser checks:
`benchmarks/runs/2026-11-14-drivey-journey/page-shots/`.

## Part A: making a Mini
- **"+" on Drivey:**
  - left: an empty chat box ("What would you like to find out?") with model Idli 9B and the Mini cartridges under it;
  - right: Claude Code through the masking proxy.
- **Asking:**
  - typed a question, picked `households` with `@`, pressed Enter;
  - Idli downloaded it from Drive (signed-in browser) and asked on a card: "Check each file" or "Accept Idli's choices";
  - no model ran.
- **Check each file:**
  - the privacy review opens inside the chat with a switch per column, real values next to codes, and the question
    as Claude will read it;
  - Done -> "Privacy checked" -> the card "Ready for Claude ... Claude will see: ...".
- **Switch to Claude:**
  - the masked question and file were typed into Claude and the right pane took focus;
  - Claude answered in a small step: a ward table, then the offer "Would you like a bar chart ...".
- **Chart:**
  - "yes" -> Claude's chart opened on the right beside Claude in 12 s;
  - tested: Pin (persisted), click a bar -> "Where did this come from?", right-click -> Copy to Claude, which switched
    back to Claude with the bar's details in the prompt, unsent;
  - asked about the bar; Claude listed the ward's households, real names shown locally.
- **Wire check:**
  - 16 requests to Anthropic during the session;
  - 0 occurrences of the real names or wards checked (Meera Singh, Sana More, Krishna Kale, Hadapsar, Yerawada ...);
  - 250 PLACE_ codes and 202 VALUE_ codes.
- **`/mini`:**
  - Claude proposed a title, story and 5 questions with options and checked in;
  - after "go ahead" it wrote and tested 5 scripts (every option) and showed the results;
  - the editor opened on the right with the story, 5 questions, and the 1 pinned chart;
  - Save -> "Your Mini is ready".
- **New cartridge:** "Household debt by ward" appeared under the chat box of a new Drivey workspace.

## Part B: using it (the 9B)
- **Opening the cartridge** showed the author's content in 6 s.
- **Mapping:**
  - "who owes more than 4 months of income in Ramtekdi?" -> 9B picked the threshold question with months 4 and ward
    Ramtekdi;
  - the Mini's script answered with 4 households in 7 s.
- **Out of scope:**
  - "why did debt go up this year?" -> the card "This Mini can't answer that ... Claude will see: ..." in 13 s;
  - the first out-of-scope question took 3 min 10 s, never seen again; most likely a cold first column scan for the
    chat.

## Broken, and fixed
- **Names were visible to Claude by default.**
  - The review's column suggestions defaulted to a local scanner address that isn't running. With regex only,
    `household_head` (people's names) was Visible while `ward`, `lat` and `lon` were hidden. Caught on the review
    page before anything was sent.
  - Fix:
    - the review uses the same scanner as the proxy (`privacy.idli.cc`);
    - headings like head, owner, respondent and farmer count as names;
    - a backstop hides any text column whose values mostly look like people's names, scanner or not;
    - regression test `test_names_hidden_without_scanner`;
    - the stale laptop setting for that file (written while the scanner was down) was removed.
- **"Switch to Claude" failed** ("I could not prepare those files").
  - The tool finds the chat's workspace from labels, and Paseo's agent JSON has none (known since P19).
  - Fix: try the label filter on each workspace with a "Claude" terminal, newest first, and cache the answer
    (`home._agent_workspace`, about 1 s the first time).

## Changed after seeing it (UX)
- **Chart "Where did this come from?"** was raw paths and a squashed table of `snake_case` columns. Now:
  - "From households in My Drive. Claude saw this file with private values replaced by codes";
  - "Worked out by Claude's script ward debt months";
  - this bar's values as a short labelled list (Total debt (Rs) 3,50,000), paths under "File details".
- **Copy to Claude** labels sources `redacted(...)` again (the merge had dropped it) and names the script by file.
- **Privacy review:**
  - hidden columns first, one line each (switch, plain name, "Krishna Kale -> NAME_001", the reason);
  - the columns Claude can see fold into one line ("Claude can see 7 columns: members, ...");
  - title "What Claude will see".
- **Handoff cards** show the masked question on its own line in quotes.
- **Opening a Mini:**
  - shows the title, story, where it reads from, the pinned charts live, and "You can ask" with each question's
    options in words;
  - it no longer runs every script and prints every table.
- **Mini answers:**
  - "Answered with: <question> (ward Ramtekdi)";
  - table headings in words, numbers grouped 3,50,000, at most 10 rows.
- **Mini editor:** options labelled in words ("Ward", "Choices one per line", "Starts with").
- **`/mini`:**
  - Claude agrees on the plan once and then opens the editor; the editor is the second check, so it no longer asks
    twice;
  - each question now carries "asks", 3 to 5 ways a colleague might phrase it, written by Claude.
- **9B mapping with asks**, on the real 9B and the saved Mini: 6 of 7 right, including "which families in kasewadi
  are the most stretched?" (top households, Kasewadi, sorted by months of income), which it declined before.
- **Column scan cached** per file version on this computer (0600), so the masked preview behind a card no longer
  rescans every column (it took 10 s).

## Still to do (Paseo P22, in progress)
- Drivey chat:
  - hide tool rows ("mcp__cowork__drive_fetch", "Used 3 other tools");
  - cards submit on click with no "Other..." box;
  - hide the High/Bypass selectors;
  - tab titles "New question" and the Mini's name;
  - the first message "Opened <Mini>" without the id.
- Hide the browser bar on Idli's own pages.
- Hide Commit and the worktree banner in Drivey.
- `@` picker ranks file names first.
- No scrollbars in embedded charts.
- The stray "t" in a fresh Claude pane.
