# Sharing what Idli learned (dashboards and checks) between people who have the app

2026-11-12. Design context: [idli-design.md](idli-design.md). Code: `cowork/lib/share.py` (the bundle),
`cowork/lib/skills.html` + `formserver.py` (Mission control buttons), `cowork/lib/workcopy.py` (the sheet tab),
`skill_share` / `skill_import` in `cowork/sites/files/tools.py`, `/idli/share` in `dgx/muse_prefix_proxy.py`.

## What gets shared

A **skill**: what Claude left behind for one kind of file. That is the form (measures, breakdowns, filters, presets),
the checks, the spelling fixes and Claude's charts, plus the fake copy it learned from. A skill is written against
a fake copy, so it holds no rows of anyone's data. The only real words in it are labels the sharer allowed while
teaching (category values such as "Done, Follow-up, Cancelled", spelling maps). Every way below shows those words
before anything is shared or added.

A skill attaches to a file by its column headers, not its name. The receiver's Idli uses it on **their own copy of
that kind of file** (the same register template, survey or export), without teaching again.

The bundle is one format whichever way it travels: a zip with `manifest.json` (title, version, sender, tabs and
headers, counts, chart names, the real words, file hashes) and the skill folder. Installing checks the hashes, refuses
odd files, and keeps any older version in `archive/skills`.

Site plugins (code that runs unsandboxed on the receiver's machine) are deliberately not shareable this way yet.
Chart code in a skill runs in the sandbox, so it is.

## Four ways, tried

| Way | Sender does | Receiver does | Needs | Tested |
|---|---|---|---|---|
| **A. A .idli file** | Mission control → Share → "Download .idli file" | Mission control → "Add what someone else's Idli learned" → choose the file → sees what's inside → "Add it" | any way to send a file (WhatsApp, email, a USB stick) | DGX, two separate Idli homes in a headless browser: 9.6 KB households file; B added it; adding it again says "already have version 2" |
| **B. A Google Drive link** | uploads the .idli file to Drive and shares the link (as with any file) | pastes the link in Idli or Logins → `skill_import` downloads it through the app's browser → card → add | both on Google Drive | the import path reuses `file_get` (which downloads Drive files); not yet run on the laptop |
| **C. Inside the shared sheet** | nothing extra: Idli's checked copy in Drive now carries a hidden `_idli_skill` tab | opens the shared sheet in Idli; for a file it doesn't know, a card: "This file carries what a colleague's Idli learned … Add it?" → yes → ready to ask | sharing the sheet itself | DGX: A's checked copy of the programme tracker; B (no skills) got the card listing the real words (Status: Done, Follow-up, Cancelled), added it, and answered "disbursed by village" straight away. The tab is hidden and stripped when Idli reads the copy back |
| **D. A share code** | Mission control → Share → "Get a share code" → `IDLI-ZSQQ-M34P` | Mission control → types the code → "Look" → "Add it" | both reach the same Idli server (they do: it hosts the private model) | DGX: code from A's page, added on B's page, B's skills folder gained `households`. Live router serves `/idli/share` |

## Which to use

- **C is the most no-frills**: the dashboard travels with the data people already share, and the receiver gets one
  card. It only covers files shared through Idli's checked copy, and anyone with the sheet can read the hidden tab
  (the same real words the card lists).
- **D is the simplest deliberate share**: one click, then a code read out on a call or sent in a message. It relies
  on our server and stores bundles there with no expiry yet.
- **A** works with no shared service at all, the fallback for anywhere.
- **B** is A through Drive; it adds little over A except a link people are used to.

Suggested default: **C automatically** (it is already on: `IDLI_EMBED_SKILL=0` turns it off), and **D on the
Share button**, with A next to it. B stays available through `skill_import`.

## Open questions

- Versions: a received skill replaces an older one (kept in the archive). There is no merge of two people's changes
  to the same skill yet.
- Trust: anyone can add any bundle; there's no signature showing who made it. Fine within one NGO, not for a public
  library.
- Codes don't expire, and there is no way to unshare one yet.
- A library page (browse what colleagues shared) would follow naturally from D.
