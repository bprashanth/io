# Leads routine, end to end on two test accounts (laptop, 2026-11-18)

**The team:** "Leads Daily" on the laptop, started through the same code as Teams > New team > Set it up.

**The two test accounts:**

| Account | Chrome profile | Role |
|---|---|---|
| 87profligate@gmail.com | `me-test` | me (the person) |
| 88profligate@gmail.com | `lead-test` | lead (Asha Verma in the leads sheet) |

Sending email between these two was allowed by the owner. WhatsApp was never touched.

Design: [BUILDER_JOURNEY.md](../../../narrative/BUILDER_JOURNEY.md), "Routines".

## 1. The Builder wrote the routine (as the person)

I typed the owner's leads request word for word, plus "I want this to run every day reliably". The Builder:
- restated it in six plain steps, naming Gmail, Calendar and Sheets;
- asked whether me-test and lead-test were test accounts, and which email was in each. The two confirm prompts
  showed exactly the right email and profile; I approved each with one key;
- wrote `routines/lead-replies.json`:
  - steps: sheet, mail (`from_in: leads.email`), free, `prepare.py`, the 9B judge, `decide.py`;
  - the 9B prompt has examples, and its schema has `wants_meeting`, `declined`, `picked`, `other_time`, `unclear`
    and `why`;
- rehearsed on the test accounts about 13 minutes after the confirmations;
- filed three fair platform requests: the sheet read failed, unread-only mail, and a Calendar tip over Save.
- **Fixes:**
  - all three requests were fixed;
  - I typed one line as "a note from the Idli team" after reconnecting its tool server.

  Then it rehearsed again end to end (pass), and reported it plainly, with the Runs page path.

## 2. Through Google's web pages (rounds A to H)

First version: fetch and act through stable Google addresses in the signed-in Chrome profile (`lib/google_web.py`).
Each round:
1. the lead emails;
2. the routine drafts an offer of three times;
3. the person sends it (a click in Gmail);
4. the lead picks the second time;
5. the 9B reads the pick;
6. the booking waits for the person's yes, then is booked;
7. it is checked on both calendars;
8. the routine runs again;
9. a "maybe" goes to the person.

**Round H ran uninterrupted from a clean state**, about 6.5 minutes in all. Each run took 60 to 80 s.

**Getting there took a fix per page quirk.** Each is a commit with a test where possible:

| # | Quirk |
|---|---|
| 1 | A Sheets read ran in the Calendar tab (per-site pinned tabs) |
| 2 | The Sheets export address redirects to another site, and fetch can't follow (gviz CSV) |
| 3 | Gmail's unread Atom feed lags and lists only unread mail (search instead) |
| 4 | The same search address twice doesn't search again |
| 5 | A Calendar "Got it" tip ate the Save click |
| 6 | Save pressed while the page was still drawing its Meet link was lost |
| 7 | Clicks in a background tab are ignored (bring the tab to the front) |
| 8 | "Draft saved" shows before Gmail has saved the draft, and leaving at once lost it |
| 9 | The Drafts search lags behind (wait, then look) |
| 10 | Gmail's Send click left a draft (test helper) |
| 11 | Chrome's `/json/new` cut a page address at its first "&" (the Runs page lost its team) |
| 12 | A retry could write a second draft (look for it first) |

## 3. Through Google's APIs with OAuth (rounds APIA to APIC): the owner's decision

The owner switched to the APIs after seeing the list above.
- The client is Idli's own "Desktop app" OAuth client (GCP project bitrot-in), published but not verified.
- The code is `lib/google_api.py`, stdlib only.
- Tokens are kept per email in `~/.config/idlisseus/google-tokens/` (0600). Claude and the Builder can't read that
  folder.

**Sign-in, done for both accounts** (consent opened in each account's own Chrome profile, with `login_hint`, PKCE
and a one-time page on 127.0.0.1). Google allowed it in a Chrome running with remote debugging. The person clicks:
1. **Advanced.** It's a plain link on the older layout of Google's "hasn't verified this app" page, which 88 got.
   87 got the newer layout.
2. **Go to idli (unsafe).**
3. **Select all** (or every box). Google lets people untick permissions; Idli now refuses a partial grant and says
   to tick every box.
4. **Continue.**

**Bugs found while signing in:**
- my first clicker ticked "Select all", then unticked the rest, so only Gmail was granted. That's why partial grants
  are now refused;
- the one-time page hung on an idle connection Chrome kept open, so it is now threaded with a read timeout.

**Results:**

| Step | APIA (clean) | APIB (clean) | APIC (clean, the yes on the Runs page) |
|---|---|---|---|
| Lead's email to an offer draft in the lead's thread | pass (run 8.7 s) | pass (8.1 s) | pass |
| Person sends the draft (stand-in: Gmail API `drafts.send`, rehearsal only) | pass | pass | pass |
| Lead's pick (a reply in the thread) read by the 9B | pass: `picked: 2` | pass | pass |
| Booking waits for the person's yes | **fail**: went to the person (see below) | pass (6.3 s) | pass (6.0 s) |
| The yes books it, with the invitation sent | n/a | pass, 0.8 s (`routines.decide`, what Book it calls) | pass, 1.3 s, clicking **Book it** on the Runs page |
| On both calendars, invitation in the lead's inbox | n/a | pass | pass |
| Second Book it | n/a | n/a | refused: "That is no longer waiting." |
| Run again: nothing new | pass | pass (1.5 s) | pass (1.4 s) |
| "Hmm, maybe" goes to the person | n/a | pass (sent to the Runs page) | pass |
| Non-lead mail (87 to itself, "Yes, happy to meet") | ignored | ignored | ignored |
| Whole round | stopped at the bug | **80 s** | about 80 s |

**APIA's bug.** The 9B read the pick right (`picked: 2`). But Gmail stamped the lead's first email `-05:00` and the
reply `-06:00`. The Builder's script compares dates as text, so the later reply looked earlier, and the pick went to
the person as "no times on record". Fixed in the platform: mail dates are now given in UTC, and rehearsal mail
carries a Date. The Builder's script is unchanged.

**Never twice:**
- an event's id is fixed from the action's key, and a second insert answers 409, which Idli treats as "already
  booked";
- a draft carries a Message-ID from its key, and is looked for in Drafts and Sent before writing;
- handled mail gets the Gmail label `Idli/handled`, applied only after a run went through.

**Runs: web vs API.** A run took 60 to 80 s through the web pages, and 1.4 to 9 s through the APIs.

## What the person did

- Typed the request and answered the Builder's three questions.
- Approved two test-account prompts.
- Signed in each account: Advanced, Go to idli (unsafe), Select all, Continue.
- Pressed Send on each offer draft. The rehearsal stood in for this with Gmail's `drafts.send`; a real routine
  never sends.
- Clicked **Book it** on the Runs page (APIC).

## Rough edges left

- The Builder's own rehearsal (before the API switch) used a temporary routine. Its state folder
  (`.idli/routines/rehearsal-nosheet/`) is left behind; the Runs page doesn't show it.
- The Builder's script skips a lead who already has a meeting coming up, silently. Should it ask the person instead?
- On a first run, mail from the past 7 days from the sheet's addresses is read. With real history, that can make
  several offers at once. The rehearsals started "clean" (earlier lead mail marked handled). A real first run needs
  the same choice from the person: "start from today".
- The Runs page shows script names ("prepare.py: 0 actions") in the step list.
- The Builder has not yet been re-run on the API version. `google_connect` exists and does what the sign-in above
  did, but the Builder hasn't driven it.
- The real-account step (`real-accounts.json`, a real profile) is still not built.

## Screenshots (`shots/`)

- `APIC-runs-before.png`, `APIC-runs-after.png`: the Runs page before and after Book it (API).
- `F-runs-before.png`, `F-runs-after.png`: the same on the web version.
- `H-1-draft.png`, `H-2-calendar.png`, `H-3-lead-calendar.png`: round H's draft and both calendars (web version).
