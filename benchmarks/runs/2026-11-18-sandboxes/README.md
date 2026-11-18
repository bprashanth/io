# Sandboxes: the journey on the laptop (2026-11-18)

The design is in [SANDBOXES.md](../../../narrative/SANDBOXES.md) and
[ESCALATION_MODELS.md](../../../narrative/ESCALATION_MODELS.md).

**Setup:**
- The laptop is a test account. 87profligate@gmail.com plays "me" and 88profligate@gmail.com plays a lead. Both were
  already connected to Idli's Google app.
- I drove the real Paseo app over CDP, as a person: clicking, typing, and reading the screen. Screenshots are in
  `shots/`.
- The person's Send on a draft and the lead's replies were done through Gmail's API from the two test accounts
  (`gmail_send_draft` and `gmail_send` with `rehearsal=True`). That was the only stand-in.

**Before the run:**
- Code reached the laptop as checksummed chunks, because `git fetch dgx` hit Tailscale's re-authentication check.
- The old teams (Leads, Leads Rehearsal, Leads Daily) were archived with `teams.delete_team`, which also removed
  their tools. The Chrome profiles and Google tokens were kept.
- The bootstrap added the Builder heading and archived the Teams entry and WhatsAppy.

## Results

| # | Step | Result | Shots |
|---|---|---|---|
| 1 | Sidebar after the bootstrap | Start here (Privacy, Logins), Drivey, Builder. No Teams, no WhatsAppy | 01, 02 |
| 2 | **Drivey regression (first):** open a Mini, ask in your own words | Pass. "Household debt by ward" answered with a table | 02, 03 |
| 3 | Drivey: a question no Mini fits | Pass. The outside-service card showed the masked question and columns (wards as PLACE codes, no rows). After Yes, the query ran on this computer and gave a debt-by-ward table | 04, 05 |
| 4 | Builder: an unrelated Claude Code task ("a small HTML dashboard of these numbers") | Pass. `dashboard.html` in 34 s | 06, 07 |
| 5 | Builder `/sandbox` for **insights** ("questions about our household survey spreadsheets in Drive") | Pass. It asked one question at a time (names? outside service? which account?), said the plan in blocks, then made **quiet-tiger-0760 survey**, which opened in two halves. The right pane is titled Sandbox Claude, with a SANDBOX CLAUDE status line | 08, 09 |
| 6 | In the sandbox: @households, ask "which ward has the highest average debt?" | Pass after fix 1. Download, privacy choice, masked question, then Switch to Claude. Sandbox Claude worked on PLACE codes; the person sees ward names. The chart came back to the left, then a Mini draft, and Save Mini saved `minis/debt-by-ward-…` | 10-17 |
| 7 | Builder `/sandbox` for **leads** (the owner's request word for word) | Pass. Plan: sheet rows, drafts, find and read emails, the private model, free times, bookings. Made **merry-parrot-7ac1 leads** with 87 as me and 88 as lead | 18, 19 |
| 8 | Left chat, one step at a time: read the leads sheet | Pass after fixes 2 and 3. Five leads with emails | 20 |
| 9 | "Find my emails from Asha in the last day" | The 9B searched by name and found nothing: the lead's account isn't named Asha. "Search for emails from 88profligate@gmail.com…" found and summarised it | 21 |
| 10 | "Find three free 30 minute times next week and write her a reply draft" | Pass. Three times in a reply draft in the thread, checked in 87's Drafts | 22 |
| 11 | Draft sent (stand-in for the person), the lead replies "Friday 20 Nov at 1:00 PM works" | n/a | n/a |
| 12 | "Did Asha reply and pick one of the times? If she did, book the meeting" | Pass. The 9B read the pick and booked it. The API shows the event on **both** calendars: Fri 20 Nov 13:00 IST, guest 88 | 23 |
| 13 | Sandbox Claude: make it a Mini I can run every morning | Pass after fix 4. Sandbox Claude asked for the sheet link (a question card), wrote the script with `blocks` and `nine_b`, and tried it with `script_try` (each a permission prompt the person approved; output masked). Saving first timed out at 60 s. After the fix, the draft came up with one question and a "dry" option, and Save Mini saved `minis/lead-replies-…` | 24, 27 |
| 14a | Run the Mini from the left chat | Pass. The 9B read 10 replies from the lead: 5 picks were already on the calendar ("not booked again"), plus 1 earlier yes, 4 no-action, and 4 leads with no reply. Times drafted 0, booked 0. **Nothing was doubled** | 30, 31 |
| 14b | What Sandbox Claude received from the accounts | Pass. In its transcript, 10 `account_peek` and `script_try` results contain no real email address and no name. They show codes: 8 EMAIL codes, 5 name codes | n/a |
| 15 | **Gap:** `/sandbox` "Every Friday, post our week's programme updates and photos to our Instagram account" | Pass. It named both gaps (posting to Instagram, running on a schedule), wrote them to `builder/platform-requests.md`, and made no sandbox | 25 |
| 16 | **Drivey regression (last):** a Mini question in Drivey | Pass. "Which households owe more than 6 months of income" answered by the Mini, unchanged | 32 |

## Bugs found and fixed

1. **A sandbox lost Drivey's routing.** Its extra account tools broke the left chat's tool-set check, so an @ file
   went to the free 9B, which asked for a Sheet link. Now the account tools are allowed: @ files, Minis and cards
   route as in Drivey, and a plain request goes to the 9B (`lib/modes.py`, tested).
2. **The 9B never saw the account tools.** It only gets a fixed list of Drivey tools and the Drivey prompt. Sandbox
   chats now keep their account tools and get a short sandbox prompt.
3. **An account tool's result was caught by the Drivey route** ("Send a question or open a Mini.") and never
   reached the 9B. Account tool results now go back to the 9B.
4. **Sandbox Minis were cut off at 60 s.** A morning run asks the 9B about each reply. Sandbox Minis now get five
   minutes, and Sandbox Claude's MCP calls get ten.
5. The Builder picked `sheet_read` and `nine_b` for a Drive-questions workflow. Its instructions now say Drive
   questions need only `drive_files`.

6. **Long-running processes kept the old code** (Sandbox Claude's MCP server, the left chat's MCP server, and the
   sandboxes' page servers). After the timeout fix, each had to be restarted: `/mcp` Reconnect, a new chat tab,
   and the page server restarted by pid. A person never sees code change mid-session, but an Idli update needs
   them restarted. Recorded, not fixed.

Fixes 1 to 3 run in the DGX router (`muse-prefix-proxy`, restarted 3 times; Muse untouched).

## Rough edges a person meets

- **The sandbox start card says "Ask about your Drive files"** even in a leads sandbox.
- **Searching by a lead's name finds nothing** when their Gmail account isn't named that way. The 9B could look the
  name up in the sheet first.
- **Email times are shown in UTC** ("today at 05:45") instead of local time.
- **Claude Code's banner says "Message from <the owner's email>'s Organization"** above Sandbox Claude's
  announcement. This was already seen in other Claude panes.
- **"+" in the left pane didn't start a new question.** The chat kept going in the same thread.
- **Sandbox Claude called the left side "the Drivey chat".** Its guide now says "the chat on the left".
- **A Mini that needs a sheet link has it written into the script.** Sandbox Claude said so; a parameter would be
  better.
- **Teams-era docs and the old team code are still there**, unlinked.
- **A saved Mini card keeps its page server's port.** After the sandboxes' page servers restarted, the leads
  sandbox's draft card still pointed at port 8801, now the survey sandbox's server. "Mini draft from Claude: Lead
  replies" reopened it on the right port (8802). The tokens differ per sandbox, so the other server can't save into
  the wrong one, but the card stops working.
- **"New tab" then "Agent" opens a plain chat**, not the start card with the sandbox's Minis. Typing "Open Mini:
  <name> [<id>]" worked.
- **The saved-Mini message says "start a new Drivey chat"**, even in a sandbox.
- **A morning run reads 14 days of replies.** With many threads from one test lead it takes about a minute.
