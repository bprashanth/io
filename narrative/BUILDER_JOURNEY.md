# The Builder journey: test accounts in Chrome profiles

2026-11-17. Owner's decisions of the same day, built on the DGX. The wider picture is in
[IDLI_DESKTOP.md](IDLI_DESKTOP.md). The model types are in [MODEL_TYPES.md](MODEL_TYPES.md). Team stacks are in
[TEAM_STACKS.md](TEAM_STACKS.md).

## Who does what

| Role | Works on | Never touches |
|---|---|---|
| **Builder** (the person's Claude Code, in the team's `extensions/`) | Test accounts and fake data. It learns each app and writes the team's tools with tests | The team's real accounts, files or values |
| **Idli** (the private 9B on this computer) | The real accounts and real content, through the tools the Builder wrote | Nothing leaves this computer |
| **Analyst** (masked Claude) | Open questions about data, with names as codes | Real values. It isn't opened for a workflow team by default |

A new team opens in **one chat titled "Builder"** under the team's heading in the sidebar. There is no Idli chat
or Analyst beside it. Drivey is unchanged.

## The six steps

1. **The workflow as steps.** The Builder writes the work back as a short numbered list and names the apps it
   touches ("Gmail, Calendar and Sheets"). The person corrects it until it is right.
2. **Test accounts.** The Builder says how many it needs and why. One is usual. Two when something must happen
   between two people, such as an email and its reply. For each one the person gets a new Chrome window and signs
   in to a test Google account. The Builder asks which email they used and asks Idli to record it. Idli asks the
   person to confirm.
3. **Rehearsal data.** The Builder proposes fake data and offers to make it in the test accounts: a fake sheet,
   emails between the two accounts, busy blocks in the calendar. It says which steps need the person (a captcha,
   a 2FA code, a consent click).
4. **Learn each app.** The Builder uses each app in the test profile. Then it writes the team's own site tools in
   `extensions/sites/<app>/`, with tests on pages it saved from the test account. A new app is not a platform
   request.
5. **Rehearse.** The Builder runs the tools end to end on the test accounts. It shows one line per step: pass or
   fail, and what it fixes.
6. **Going live.** The real account is signed in to a separate Chrome profile that only Idli uses. The first real
   runs are "draft and show me". The private 9B reads the real content. The Builder designed those steps with fake
   data. (Connecting the real account is the next step to build.)

## Why Chrome profiles

Google refuses sign-in inside Paseo's embedded browser ("This browser or app may not be secure"). So test accounts
live in real Google Chrome. Each account gets its own profile, a folder Chrome keeps its sign-ins in:
`~/idli-insights/browsers/<name>/`.

- **Signing in:** Idli opens the profile as plain Chrome. Remote control is off, because Google may refuse sign-in
  when it is on.
- **Working:** Idli closes that window and opens the profile again with remote control on, reachable only from this
  computer (DevTools on 127.0.0.1). The Builder's browser tools go through Idli. The Builder never gets the port or
  the folder.
- **Who is signed in:** Idli reads the emails from the profile's settings files. It never reads cookies or saved
  passwords.

## What the person does

- Says yes or no to the steps.
- Signs in to each test account in the Chrome window that opens. Makes a new test account if needed.
- Tells the Builder the email, and confirms it on Idli's prompt.
- Types a captcha or 2FA code when a site asks.
- Later: signs in to the real account in Idli's own profile (not built yet).

## The safety rules

- **The allowlist.** A team's test accounts are in `<team>/.idli/test-accounts.json`. It is outside `extensions/`,
  so the Builder can't read or change it. Only `test_account_set` adds to it. It checks that the email is really
  signed in to that profile.
- **The confirm prompt.** Before `test_account_set` runs, Claude Code shows the person words Idli writes: "Use
  <email> in Chrome profile <label> as a TEST account for this team? Only say yes if it is not a real account."
  The hook lives in a settings file the Builder can't edit. The Builder's settings never pre-approve it.
- **Every browser call checks.** Each browser tool refuses unless every Google email signed in to that profile is a
  confirmed test account of this team. A real account signed in later to the same window is caught at the next
  call.
- **Emails stay hidden** for profiles that aren't confirmed. The Builder asks the person instead.
- **The real profile is never driven by the Builder.** It is marked as real and left out of the Builder's list.
  Only Idli's `team_run` will open it.
- **Sending.** Email between the team's own test accounts is allowed during a rehearsal. Nothing else is sent.
  WhatsApp: never, from any account. The browser tools refuse a send on WhatsApp Web.
- **Site tools run in the wall.** A team's site tool has no network. Its only way out is a door to one profile's
  browser, for each account role it declares.

## Code

All under `benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/`:
- `lib/chromeprofiles.py`: the profiles, signed-in emails, the allowlist, opening and closing Chrome.
- `lib/chromectl.py`: drive a profile over DevTools (read, click, type, screenshot, tabs). `Replay` for tests. `Door`
  for tools in the wall.
- `lib/idli_mcp.py`: the Builder's `profiles`, `profile_new`, `test_account_set`, `browser_*` and `rehearse`.
- `desktop/idli-test-account-consent.py`: the confirm prompt.
- `lib/teamcaps.py`: tools may declare `"profile"`; `run_tool` gives them doors.
- `lib/builder.py` and `lib/teams.py`: the one "Builder" chat for a new team.
- `idli/builder-skills/setup-team`, `build-team` and `idli/CLAUDE-builder.md`: the Builder's instructions.
- `tests/test_chromeprofiles.py`: includes a real round trip on Playwright's Chromium and a site tool through its
  door.

## Routines: how a workflow runs every day (decided 2026-11-18)

**The owner asked** for a flow that is reproducible and always works. Three options were weighed:

| Option | Verdict |
|---|---|
| Idli's own browser | Google blocks sign-in there |
| Claude driving Chrome every day | Not reproducible, and Claude would read real mail |
| Download the mail, then the 9B | **Chosen** |

**Steps, run by Idli, never by Claude on real data:** fetch, then filter, then judge (the 9B), then act, then
approve, then record.

**Fetch and act go through Google's APIs with OAuth** (`lib/google_api.py`, the owner's decision the same day). The
first version drove Google's web pages through stable addresses (`lib/google_web.py`). It worked, uninterrupted, but
only after twelve fixes for page quirks in one evening:
- a read running in the wrong tab;
- a redirecting export;
- an unread feed that lags;
- a search that didn't refresh;
- a Save lost while the page drew;
- a tip over Save;
- background tabs ignoring clicks;
- "Draft saved" shown before it was saved, and a Drafts search that lags;
- a new tab cutting its address at "&".

Each run took 60 to 80 s. Through the APIs a run takes 1.4 to 9 s and doesn't depend on how the page looks. The web
version stays only as a fallback a step names (`"via": "web"`).
[Results](../benchmarks/runs/2026-11-18-leads-routine/README.md).

**Sign-in:**
- **The app:** Idli's own OAuth client ("Desktop app", `~/.config/idlisseus/io_oauth_client_gcp.json`, never
  shown). It is published, so tokens don't expire weekly, but it is not verified by Google. An unverified app can
  have at most **100 users**, which is fine for a POC. Verification (with a security review for Gmail access) is the
  step after.
- **Where:** the consent page opens in the account's own Chrome profile (`login_hint`, PKCE, a one-time page on
  127.0.0.1).
- **What the person clicks:**
  1. **Advanced** (on Google's "hasn't verified this app" page);
  2. **Go to idli (unsafe)**;
  3. **Select all**;
  4. **Continue**.

  The Builder says this first, in those words, and adds that it is our own app.
- **Partial grants:** Idli refuses one (Google lets people untick boxes) and says to tick every box.
- **Tokens** are kept per email in `~/.config/idlisseus/google-tokens/` (0600), a folder Claude and the Builder
  can't read. A refused refresh stops the run with "Sign in to Google again for <email>". There is no silent
  fallback.
- **The Builder** connects only confirmed test accounts (`google_connect(role)`). A routine's real account is
  mapped by the person.

**What the APIs do:**
- Sheets: the sheet's values.
- Gmail:
  - mail from the sheet's addresses, found by search, read or unread;
  - each message is read once; after a run goes through, it gets the label `Idli/handled`;
  - a draft is a proper reply in the lead's thread, and the person presses Send.
- Calendar:
  - free/busy gives the open times;
  - a booking is inserted with guests and invitations;
  - the event's id is fixed from the action's key, so a retry can never book twice.
- Sending mail is only possible in a rehearsal between the team's test accounts, for the lead's simulated replies.

**Judgement is a 9B step with a JSON schema.**
- An answer the 9B marks `unclear` goes to the person.
- Tested on fake replies: yes, no, maybe, a pick, another time, Hindi. All right, about 1 s each.
- In the end-to-end rounds it read every pick right.
- Mail dates are given in UTC, so scripts can compare them as text. A reply stamped -06:00 once looked older than
  an offer stamped -05:00.

**The routine file:**
- The Builder writes `extensions/routines/<name>.json`: steps, plus `script` steps in its own Python (JSON in,
  actions out).
- Each action has a key and is done once: `draft_email`, `book_event` (needs the person's yes), `ask_person`.
- State lives in `<team>/.idli/routines/<name>/`: done keys, what waits for the person, verdicts, the script's
  memory, settings, and one log per run.

**The person's side:** the **Runs** page (Start here, Teams, the team's card, Runs) has:
- Run now;
- what waits for them (Book it or Skip; replies to read);
- what was done;
- the last runs, step by step.

Emails wait in Gmail Drafts.

**The Builder's side:**
- `google_connect`;
- `routine_check`;
- `routine_config_set`;
- `routine_rehearse`: on the test accounts, booking without asking. Test accounts only; a real run can't skip the
  person's yes.

**Known limits:**
- A first run reads 7 days of mail from the sheet's addresses. A real first run should start "from today".
- The team's script runs as a plain process, not yet inside the Linux run wall.
- The real-account mapping (`.idli/real-accounts.json`) is not built.

## Not built yet

- The real-account step: a separate profile marked real, mapped to a role in `<team>/.idli/real-accounts.json`.
  `team_run` refuses a site tool until then.
- Signing in to sites without Google (only Google emails are checked today).

## Tested 2026-11-17/18 (laptop, as a person)

Results: [benchmarks/runs/2026-11-17-builder-journey/README.md](../benchmarks/runs/2026-11-17-builder-journey/README.md).

**What happened.** The owner's own leads request was typed into a new team's Builder, which:
- confirmed the two test profiles, after the person's yes;
- made the fake sheet, emails and busy times itself;
- learned Gmail, Calendar and Sheets;
- built two team site tools;
- rehearsed end to end, in about 38 minutes.

**Checked independently:** the call is on both test calendars (Fri 20 Nov, 2 pm, the lead's copy "Needs RSVP"),
the thread and the invitation are in the lead's inbox, and the sheet is in Drive. All seven laptop checks pass.

**Fixed on the way:** a "Leave site?" box hung every browser call. Leave-page boxes and alerts are now answered,
and question boxes are left to the person.

**Next:**
- let site tools ask the private 9B, which is what the Builder asked for, to judge replies;
- a place for daily runs and approvals, now that a new team has no left chat;
- update the "left chat" and "left and right" wording.
