# Claude on masked copies, column reveals, and a query service for Minis

## Why
On the laptop, masked Claude named species it only saw as codes. Its transcript showed how: it took invasive
names from a web search, searched the real file for them with a script, and read back "VALUE_103 matches
ageratina". Codes hid values on the wire, but Claude's scripts ran on the real file, so any guess could be checked.
It also asked the person to name the codes instead of using unmask.

## What changed
- **Masked copies:**
  - `drive/` in Claude's folder holds copies of the reviewed files with codes in the hidden cells (same sheets,
    layout and number types), rebuilt on handoff, reveal and hide;
  - files that were never reviewed are not copied.
- **Sandbox:**
  - Claude Code's sandbox (`sandbox.filesystem.denyRead`, no unsandboxed commands) and Read/Edit deny rules keep its
    shell and tools out of Idli's private folder, caches, browser data and transcripts;
  - Idli's own tools run outside it.
- **The proxy:**
  - keeps codes in Claude's tool inputs, since its commands run on the copies;
  - text and display-only tools (questions with options) still get real values.
- **Charts and Minis:**
  - charts turn codes back into real values for the person;
  - a Mini draft gets real values in its title, story, choices and script string literals, so saved Minis run on
    the real file and work for colleagues.
- **Column reveal:** `unmask(code, reason, whole_column=true)` shows every value of a contextual column on one
  consent page and uses one reveal. Species columns are contextual.
- **Query service for Minis:**
  - when the 9B finds no saved question, Idli tells the person and asks an external service (default DeepSeek
    flash through OpenRouter, data collection denied) for one DuckDB query;
  - only the masked question and the column list are sent;
  - the service may ask back with 2 or 3 specific questions;
  - Idli checks the query and runs it locally with file access off.
- **False alarms:**
  - scanner ages and dates in running text are no longer private: "All six scripts" made "six" an age;
  - Anthropic's signed reasoning blocks are not leaks: that age then stalled a session with 403s.

## Live test (DGX, synthetic shola survey, real Claude Code CLI)
- **Species:** Claude asked to reveal the species column instead of asking for names. One consent showed all 14
  codes, and Claude identified wattle, lantana and Crofton weed.
- **Pointing Claude at the real file:** it used its copy. Asked to run commands on the private folder, it refused.
- **The sandbox itself:** a probe file was blocked by the permission rules (Bash and Read), and from inside the
  sandbox Python got "No such file".
- **Answers:** "big trees at Avalanche" and "which plot has the most rapcap" were correct against the real file.
- **The Mini:** its 6 scripts got real site and species names back and ran on the real file.
- **Wire, 52 requests:**
  - no recorder or site names;
  - no species before its reveal;
  - the account email only as a code.
- **Query service, real 9B, router and tools:**
  - saved questions still go to the 9B (rapcap, big trees at Avalanche);
  - "big trees", "what else grows where lantana is", "which recorder logged the most wattle", "is cestrum worse
    near the edge" and "lantana in plot 1 vs plot 5" went to the service, with asks-back where vague;
  - 1.5 to 7 s each.

## Still to do
- Sync to the laptop and test in Paseo:
  - restart the DGX router (the new path only runs for Minis opened with the new code);
  - copy the query service key to the laptop;
  - run the scanner locally.
- The service guessed which transects are "near the edge" because the Read me sheet was hidden in review. Hidden
  free-text sheets lose context the service needs.
- Old vaults hold scanner junk (for example "sppnam", "claude").
- No "Keep this question" yet for adding a service answer to the Mini.
