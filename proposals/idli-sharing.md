# Sharing Minis between people who have Idli

2026-11-12, decided 2026-11-13. Design context: [docs/idli-design.md](../docs/idli-design.md).

## Share vs clone

- **Share** (shipped): a Mini is the dashboard for **one Google Drive file**. Sharing it gives the other person the
  same dashboard on the **same file**. Their Idli opens that file with their own Google account. If they can't open
  it in Drive, the Mini says so and stops.
- **Clone** (later, [todos P3](../todos/idli-insights/p3/clone_mini.md)): the workflow without the file, for someone's
  own file of the same kind. Different code.

The one way to share is a **code**. On the Minis page each row has **Share**, which shows a code
(`IDLI-E2HW-2DD4`). The other person types it next to **Add a Mini**, sees one line ("Households: the Google Drive
file "Household survey 2025" (6 measures, 12 checks, 0 charts).") and says Yes or No. Anyone who has a code knows
what to do with it.

## How it works (as built)

| Step | What happens | Code |
|---|---|---|
| Use | When a file opened from a Drive link gets its dashboard, Idli records that Drive file on the Mini (`sources.json` in the skill folder; not shared, not in git). The Mini's title on the Minis page becomes a link. | `formserver.Files.meta`, `share.remember_source` |
| Share | The Mini (form, checks, charts, the fake copy) plus the Drive file's id, link and title go to the Idli server, which returns a code. A Mini never opened from Drive can't be shared: "Open the file in Idli from its Drive link first." | `share.pack_bytes(with_file=True)`, `/api/skills/code`, `/idli/share` on the router |
| Add | The receiver's Idli fetches the code, checks the bundle (hashes, expected files only), shows one line, and on Yes installs it with the file recorded. | `/api/skills/preview`, `/install`, `share.install` |
| Open | Clicking the Mini fetches the Drive file **every time**, then runs the dashboard on it. No access: "You don't have access to "Household survey 2025" in Google Drive. Ask whoever shared this Mini to share the file with you", with a link to the file. | `/api/minis/open`, `lib/drivefetch.py`, `form.html?mini=` |
| In chat | "share households" gives the code (`skill_share`); pasting a code shows the same Yes/No card (`skill_import`). | `sites/files/tools.py` |

**Fetching as the person.** `drivefetch` runs `fetch(export URL)` inside a Google tab of the app's browser, so it
carries the person's own sign-in, with no download box. If no Google tab is open, it reads the browser session's
Google cookies through any of the app's tabs and makes the same request. Both use DevTools, which is on in our
dev builds (as the quiet downloads already are). A shipping build needs a small Paseo patch for it.

Tested 2026-11-13 on the DGX:
- Two Idli homes, each with a fake Drive standing for what that person's Google account can open.
- A's Share on a Mini never opened from Drive gave the "open it first" message.
- On Households it gave a code.
- B added it and opened it before having access, and got the no-access page.
- Given access, B saw the dashboard.
- After the sheet was edited (31 rows to 14), a reload showed the new numbers.
- The in-tab fetch ran in real Chromium through DevTools. It followed a redirect to the xlsx (byte-identical), and
  refused a sign-in page and a 403.
- Not yet run against real Google on the laptop, including the cookie fallback.

## Refresh: every time the Mini loads

Each open (clicking the Mini, or reloading its tab) fetches the file. If the bytes are unchanged, the form's cached
results are reused (the cache is keyed by the file's modified time, which stays put). So the cost of always fetching is the
export request itself:
- A small sheet exports in about 1 to 3 seconds; that guess still needs measuring on the laptop.
- Sheets with many tabs or tens of thousands of rows take longer.

The header shows "fetched in N s", so we'll see real numbers.

**Push notifications from Drive** exist (Drive API `files.watch` / `changes.watch`), but not for us yet:
- They need a Drive API OAuth token. Idli uses the browser's sign-in, not the API.
- They need a public HTTPS address for Google to call. silo could host it, and would then have to tell the
  person's app.
- Watch channels expire and must be renewed.

That makes sense once Idli has a proper Google sign-in, and only for dashboards left open. For "fresh when I open
it", fetching on open is simpler and always right. A cheaper "has it changed?" check also needs the API (the file's
`modifiedTime`), so it comes with the same sign-in.

## Not decided: when the sharer changes the workflow

Today a code is a frozen copy of one version of the Mini. The data is always fresh, because it's fetched from Drive,
but a new measure or chart the sharer adds doesn't reach receivers without a new code. Proposed:
- **One code per Mini, for life.** The sharer's Idli re-publishes under the same code when it saves a new version.
  The receiver's Idli checks the code when the Mini opens. If there's a newer version, it shows one card: "Households
  has an update: adds Households below poverty line. Update?" The old version goes to the archive.
- Only the sharer can update a code: a private update token kept on their machine. The same token gives "stop
  sharing" and expiry.
- If the receiver also taught their copy, it's a fork: offer the update as a replacement, never merge.

## Ways tried and parked

| Way | How it worked | Why parked |
|---|---|---|
| **A .idli file** | Download the bundle; the other person picks the file | An extra step (save, send, find, pick) for nothing the code doesn't do |
| **A Drive link to the .idli file** | Upload it to Drive; paste the link into Idli | A plus Drive |
| **Inside the shared sheet** | Idli's checked copy carried the workflow in a hidden `_idli_skill` tab | A hidden payload in someone's spreadsheet can look shady. Off unless `IDLI_EMBED_SKILL=1` |

All three were tested on the DGX on 2026-11-12. They share the bundle format and `share.inspect` / `install` with the code.

## Open questions

- Trust: anyone with a code can add it, and nothing shows who really made it. Fine within one NGO.
- Codes don't expire and can't be withdrawn yet (see the update token).
- Several files in one Mini: later. Several tabs in one file already work.
