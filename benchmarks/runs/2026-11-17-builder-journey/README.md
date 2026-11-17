# Builder journey with test accounts in Chrome profiles (laptop, 2026-11-17/18)

The design is in [BUILDER_JOURNEY.md](../../../narrative/BUILDER_JOURNEY.md). Run in the real Paseo app on the
laptop, with me playing a non-technical person. The test accounts were two real Chrome profiles the owner signed in
to by hand:
- `me-test`: 87profligate@gmail.com, role "me";
- `lead-test`: 88profligate@gmail.com, role "lead".

The owner's own "Leads" team, Drivey and Start here were not touched.

## What happened

1. **New team.** Teams > New team "Leads Rehearsal": Google Drive, A few of us, Yes, Ask me each time, then
   Set it up. The sidebar shows "Leads Rehearsal" with one item, **Builder**. The Builder fills its pane alone. There
   is no Idli chat and no Analyst (`shots/01-new-team-builder-only.png`).
2. **The request** (the owner's own words from Leads, 23:45). The Builder restated it as 5 steps and named Gmail,
   Calendar and Sheets. It asked "Is that right?".
3. **Test accounts.** It said it needs two (one plays you, one plays a lead who writes back). It found the two open
   Chrome windows, and asked whether they are test accounts and which email is in each.
   - It called `test_account_set` twice.
   - Idli's prompt read: "Use 87profligate@gmail.com in Chrome profile me-test as a TEST account for this team?
     Only say yes if it is not a real account."
4. **One question:** meeting length and hours (it offered 30 min, weekdays 10 to 5, three choices). Answered "do
   what you think is right".
5. **Rehearsal data, made by the Builder itself:**
   - a "Leads (test)" sheet in me-test's Drive with made-up leads plus the lead account (as "Asha Verma");
   - an email from me to the lead, and the lead's reply agreeing to meet;
   - three busy blocks in me-test's calendar.
6. **It learned the apps and built team site tools:**
   - `offer-meeting-times`: read the sheet, search Gmail for each lead, judge the reply, find free times, and save
     a draft reply in the same thread;
   - `book-picked-time`: read the lead's pick, and prepare the calendar invite.

   It used 99 browser calls. Tests replay saved pages with no browser.
7. **Stuck once (platform bug, fixed).** Sheets showed a "Leave site?" box, and every browser call hung. The Builder
   asked the person to click Leave. See "Bugs fixed".
8. **Rehearsal end to end on the test accounts:**
   - the draft was checked;
   - sent from "me", playing the person;
   - the lead replied "Friday at 2pm works well for me";
   - the booking run prepared the invite for Fri 20 Nov, 2 pm, with the lead as guest;
   - the Builder, playing the person, saved it and sent the invitation;
   - a second booking run said "already in the calendar" and prepared nothing new.
9. **`team_check` passed** and `team_save` was done. It ended with how it goes live: the real account in a
   separate Chrome window only Idli opens, "draft and show me" first.

Time: 23:45 to 00:23, about 38 minutes, including about 8 minutes stuck on the "Leave site?" box.

## Checked independently (not the Builder's word)

| Check | Result |
|---|---|
| me-test calendar, 20 Nov | "2pm to 2:30pm, Call: 87 profligate and Asha Verma, Accepted" (`shots/02-...`) |
| lead-test calendar, 20 Nov | "2pm to 2:30pm, Call: 87 profligate and Asha Verma, 88 Profligate, Needs RSVP" (the invite arrived) |
| lead-test inbox | Thread "Following up on our partnership programme" (4 messages, last "Friday at 2pm works well for me") and "Invitation: Call: 87 profligate and Asha Verma @ Fri" (`shots/03-...`) |
| me-test Drive | "Leads (test)" sheet (`shots/04-...`) |

## The seven laptop checks

| # | Check | Result |
|---|---|---|
| 1 | New team opens one "Builder" item, Builder alone, no Analyst. Drivey still split | Pass (`shots/01`, `shots/05`) |
| 2 | Profiles listed without emails until confirmed | Pass. `profiles` returned `signed_in_accounts: 1`, `confirmed_test_account: false`, no emails |
| 3 | Confirm prompt text, then both confirmed | Pass (see step 3). Both calls came in parallel. My "1" answered the first, and the Enter I sent after it accepted the second (default Yes). The email and profile matched |
| 4 | Chrome relaunches with debugging, Gmail stays signed in, and read, click, type and shot work | Pass. All of Gmail, Calendar and Sheets worked in both profiles after the relaunch |
| 5 | Unconfirmed profile or wrong email refused | Pass. For "89profligate@gmail.com" in an empty Test 3 profile, Idli's hook denied `test_account_set` with no prompt. A direct `browser_tabs('test-3')` was refused: "No Google account is signed in to Test 3 yet...". (Given 87profligate for Test 3, the Builder itself declined: that account already plays "me".) |
| 6 | Draft from lead to me, reply, and a Calendar or Sheets rehearsal | Pass, end to end (above) |
| 7 | `profile_new("Test 3")` opens plain Chrome at Google sign-in | Pass. Its main Chrome process had `accounts.google.com/` and no `--remote-debugging-port`. Closed and its folder deleted afterwards |

## Bugs fixed (platform)

- **A "Leave site?" box hung every browser call** (`9d9e3b31`).
  - `uiswitch.Cdp` dropped page events, so nothing saw the box.
  - Now each browser call's own connection turns on page events. Leave-page boxes and alerts are answered (Leave,
    OK). A question box (confirm, prompt) stops the call and says what it asks, so the person answers it.
  - A call that still times out says a box may be open and to ask the person.
  - New test in real Chromium: `test_leave_site_and_alert_boxes_are_answered_question_boxes_are_not`. Full suite
    237 passed, 3 skipped.
  - **Limit:** a box that opened before any call was listening can't be seen. Chrome doesn't report it to a new
    connection, and `Page.enable` hangs behind it. That one still needs the person. Here I closed the stuck tab,
    as the person would; Sheets saves as it goes.

## Rough edges a person hits

1. **A site tool can't ask the private 9B.** The Builder filed a platform request: "Let a site tool (kind tool with
   "profile") ask the private model on this computer". Today "did they agree, which time did they pick" uses word
   rules, plus "unclear, please read". This is the next platform step, since the owner wants the 9B to read real
   replies.
2. **The Builder ends with "in the left chat, ask ...".** A new team has no left chat any more. The instructions,
   and the place where the person runs a workflow day to day, need updating (the Routine/Idli chat idea).
3. **The New team plan still says** "Ask on the left, Claude helps on the right."
4. **Claude Code pre-fills a suggested reply** ("yes that's right", "done, I've signed in to Test 3 now") that a
   person could send with Enter, including claims that aren't true.
5. **Two parallel confirm prompts:** one keypress too many accepts the second without reading it. Asking for one
   account at a time would be safer.
6. **Terminal redraw:** the first screen of the Builder pane was garbled (overlapping lines) until it redrew.
7. **Calendar's "dark mode" popup** covered the lead's calendar in screenshots. Harmless to the tools, but noisy
   for anyone looking.

## Left on the laptop

- The Leads Rehearsal team, its site tools and both test profiles. The test accounts now hold the fake sheet, the
  email thread and the Fri 20 Nov event.
- No tools are installed (the catalog wasn't needed).
