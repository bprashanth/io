# Sharing Minis between people who have Idli

2026-11-12, decided 2026-11-13. Design context: [docs/idli-design.md](../docs/idli-design.md).

**Decision: one way, the share code.** On the Minis page each workflow has a **Share** button that shows a code
(`IDLI-W5AM-HPA6`). The other person types it next to **Add a Mini**, sees one line saying what it is, and says
yes or no. Nothing else is on the page. Anyone who has a code knows what to do with it, and the same code works for
any kind of workflow (file forms today, site plugins later).

The other three ways below were built and tested, then parked. A file download is an extra step for no gain, and a
workflow hidden inside someone's spreadsheet could look shady.

## What a Mini is

A **Mini** is what Claude left behind for one kind of file (internally a "file skill"): the form (measures,
breakdowns, filters, presets), the checks, spelling fixes, Claude's chart code, and the fake copy it learned from.
It was written against a fake copy, so it holds no rows of anyone's data. The only real words in it are labels the
sharer allowed while teaching (category values such as "Done, Follow-up, Cancelled", spelling maps).

A Mini is not tied to one file. It attaches to any file whose tabs and column headers match it. The person who adds it
uses it on **whatever file of that kind they open**: their own copy of the register template, or the same Drive
sheet if the sharer shared that too.

## How the code works (as built)

| Step | What happens | Code |
|---|---|---|
| Share | The sender's Idli zips the Mini (`manifest.json`: title, version, tabs, counts, real words, file hashes; plus the skill folder) and posts it to the Idli server. The server stores it and returns a code. | `lib/share.py` `pack_bytes`; `formserver.py` `/api/skills/code`; `dgx/muse_prefix_proxy.py` `/idli/share` (`~/idli-shares/<code>`) |
| Add | The receiver's Idli fetches the bundle by code, checks it (hashes match, only expected files, ids agree) and shows one line: "Households: 6 measures, 12 checks, 0 charts, for files with tabs Households." | `/api/skills/preview`, `share.inspect`, `share.short` |
| Yes | It is installed in their skills folder; an older copy is moved to `archive/skills`; `shared_from.json` records where it came from. | `/api/skills/install`, `share.install` |
| In chat | "share households" → `skill_share` gives the code; pasting a code → `skill_import` → the same yes/no card. | `sites/files/tools.py` |

The code reaches the same server that runs the private model, so both people need only what Idli already needs.

Tested 2026-11-13 on the DGX: two separate Idli homes, the Minis page in a headless browser. A's Share showed
`IDLI-W5AM-HPA6`; B typed a wrong code ("No Mini with that code."), then the right one, saw the one-line description,
said Yes, and Households appeared in B's list. Through `skill_import` the same code gave the same card and install.
Earlier (2026-11-12) a code made on the laptop round-tripped through silo.

## Not yet decided: keeping a Mini fresh

Two separate things change over time.

**1. The data.** A Mini doesn't store data or results. Every question and every dashboard view runs the form on the
file Idli has open, at that moment. The file is a snapshot. `file_get` downloads it from Drive when its link is pasted.
If the sheet changes in Drive, nothing reruns until it is fetched again. Options:
- (a) As today: fetch again when the person pastes the link or says "refresh".
- (b) **Check on open (recommended).** When a chat opens a known file, or the dashboard tab gets focus, ask Drive
  for the file's modified time (one cheap request through the app's browser). If it changed, re-download and the
  charts redraw (the form cache is already keyed by the file's modified time).
- (c) Poll every N minutes while the dashboard is open. That is live, but it costs Drive requests and may surprise
  people.

**2. The workflow.** Today a code is a frozen copy of one version. If the sender teaches more (a new measure, a new
chart), receivers don't get it unless they are sent a new code. Options:
- (a) As today: share again to get a new code.
- (b) **The code follows the Mini (recommended).** A Mini gets one code for life. When its owner's Idli saves a new
  version after teaching, it re-publishes under the same code. A receiver's Idli checks that code when it opens a
  file of that kind (or loads the Minis page). If there is a newer version, it shows one card: "Households has an
  update: adds Households below poverty line. Update?" On yes the old version goes to the archive, as now.
- (c) Auto-update with no card. Simpler, but a chart someone relies on could change under them.
- Edits on both sides: if the receiver also taught their copy (a local version above the shared one), don't
  overwrite it. Say there is an update and offer it as a replacement; there is no merge. It is a fork, like a
  copied spreadsheet.
- Server side, (b) needs the owner to be able to update a code but no one else. Give the sender a private
  update token at share time, kept in the Mini's `shared_to.json`. Expiry and "stop sharing" follow from the same
  record.

## The ways tried and parked

| Way | How it worked | Tested | Why parked |
|---|---|---|---|
| **A .idli file** | Download the bundle; the other person picks the file | DGX, two Idli homes: 9.6 KB households bundle installed; adding again said "already have version 2" | An extra step (save, send, find, pick) for nothing the code doesn't do |
| **A Drive link** | Upload the .idli file to Drive; paste the link into Idli, which downloads it through the app's browser | built on `file_get`; not run on the laptop | A plus Drive |
| **Inside the shared sheet** | Idli's checked copy carried the Mini in a hidden `_idli_skill` tab; opening that sheet offered it | DGX: B got the card, added it, answered at once | A hidden payload in someone's spreadsheet can look shady, and anyone with the sheet can read the tab. Now off unless `IDLI_EMBED_SKILL=1` |

The bundle format, `share.inspect` and `share.install` are shared by all of them, so any of these could come back
without new plumbing. The UI and tools now offer only the code.

## Open questions

- Trust: anyone with a code can add it, and nothing shows who really made it. That is fine within one NGO, not for a
  public library.
- Codes don't expire, and nothing can unshare one yet (see the update token above).
- A library page (browse what colleagues shared) would follow naturally from codes.
