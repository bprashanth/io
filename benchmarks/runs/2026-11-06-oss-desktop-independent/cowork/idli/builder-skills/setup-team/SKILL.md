---
name: setup-team
description: Setting up a new Idli team with the person - read their setup answers, restate the workflow as steps and the apps it touches, set up test accounts in Chrome profiles, make rehearsal data, learn each app on the test accounts and write the team's site tools with tests, rehearse end to end, and explain how it goes live. Use when the first message is a new team's setup answers.
---

# Setting up a team

The person just made a team on the Teams page. Idli asked them the fixed questions (name, goal, where the data is,
who uses it, private fields, the outside service) and sent you the answers. Those answers are the platform's
promises: you can't loosen them (for example, use the outside service when they said No).

You work only on **test accounts and fake data**. The team's real accounts are used later by Idli and the private
model on this computer, never by you. Keep every message short and plain. One question at a time.

## 0. Talk about the work first

Start with one line that shows you read their answers. Then ask about the work, not about technology:
- "What is the one task you'd most like help with?" Then: "Walk me through the last time you did it."
- Listen for the steps, the apps (Gmail, Calendar, Sheets, Drive, a portal), the files and the people.

Two to five exchanges is enough. Use their words back to them.

## 1. Restate the workflow as steps

Write it back as a short numbered list, one line per step, and name the apps it touches:

> Here is how I understand it:
> 1. A new lead arrives by email.
> 2. You check your calendar for a free slot.
> 3. You reply with two times.
> 4. When they pick one, you add it to the calendar and to the leads sheet.
>
> It touches Gmail, Calendar and Sheets. Is that right?

Fix it until they say yes. Keep a copy in `TEAM.md` (goal, the steps, the apps).

## 2. Test accounts, one Chrome profile each

Explain why in one or two lines: "I learn the apps on test accounts, never on your real one. Google won't let me
sign in inside Idli's own browser, so each test account gets its own Chrome window."

Say how many you need and why:
- **One** is usual.
- **Two** when something must happen between two people, such as an email and its reply ("one plays you, one plays a
  lead").

For each account:
1. Call `profile_new(label)` with a name the person will recognise ("Leads test me"). A Chrome window opens.
2. Tell them what the tool says: sign in there with a TEST Google account (or make a new one in that window), not
   their real one.
3. Ask: "Which email did you sign in with?"
4. Call `test_account_set(profile, email, role)` with a short role (`me`, `lead`). Idli asks the person to confirm
   in its own words. If it says the email is not signed in yet, wait a few seconds and try again, or ask them to
   check.

`profiles` shows which profiles are confirmed. Use only confirmed ones. If a profile shows an account you were not
told about, stop and ask. Never use a real account, even if the person offers.

## 3. Propose the rehearsal data

Say what fake data the rehearsal needs and offer to make it yourself in the test accounts:
- a fake sheet with made-up names and numbers;
- emails between the two test accounts ("the lead writes in, you reply");
- calendar busy blocks for the coming week.

Say which steps the person must do because a site asks a human (a captcha, a 2FA code, a consent click): "Chrome will
ask for a code on your phone. Type it there, then tell me." Then wait.

Sending email between the team's own test accounts is fine. Never send to anyone else. Never send a WhatsApp message,
from any account.

## 4. Learn each app and write the team's site tools

For each app in the steps, use it in the test profile with the browser tools (`browser_open`, `browser_read`,
`browser_click`, `browser_type`, `browser_shot`, `browser_tabs`). Prefer stable addresses (a search URL, a sheet's
export link) over long click paths.

Then write the team's own site tools, as the `build-team` skill says ("Site tools"):
- the code in `sites/<app>/` (for example `sites/gmail/find_new_leads.py`), using `chromectl`;
- pages you read, saved with `browser_read(save_as=...)` into `samples/pages/`, for its test;
- a test that runs with no browser (`chromectl.Replay`);
- a `manifest.json` entry of kind `tool` with `"profile": "<role>"`.

A new app is not a platform request. Use `platform_request` only for what only the platform can do (a change to the
app, the private model doing something new, sending a WhatsApp message).

## 5. Rehearse end to end

Run each tool on the test accounts with `rehearse(capability, instructions)`, in the order of the steps. Check the
result in the test account itself (`browser_read`). Then show a short report, one line per step:

> Rehearsal on the test accounts:
> 1. Find new lead emails: pass (found 2 of 2)
> 2. Free slots next week: pass
> 3. Draft the reply: pass (draft saved, not sent)
> 4. Add to the sheet: fail (the sheet's columns moved). Fixing it now.

Fix what failed and rehearse again. `team_check` must pass, then `team_save` with a one-line summary.

## 6. Say how it will go live

In three or four plain lines:
- The real account is signed in to a separate Chrome profile that only Idli uses. You never open it.
- The first real runs are "draft and show me": Idli prepares the email or the calendar entry and the person checks
  it before anything is sent or saved.
- The private model on this computer reads the real emails and sheets. You designed those steps with fake data, so
  nothing real comes to you.
- Connecting the real account is a later step in Idli. Until then the team runs on the test accounts only.

Write the steps, the test accounts' roles (not their passwords), what's built and what's waiting in `TEAM.md`.

## Teams that are about files, not apps

If the work is about files (photos, voice notes, videos, spreadsheets), skip steps 2 and 3: build readers and tools
on fake samples as the `build-team` skill says, and tell the person how to try it ("Pick a video with @ on the left
and ask: cut the silences").
