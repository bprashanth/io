# The file form, end to end (2026-11-08, laptop Paseo driven from the DGX)

The single-file flow now has three parts, each with a fixed job:

| Part | Job | Never does |
|---|---|---|
| **Teach** (Claude, Teach workspace) | Once per file layout: describes every tab (what a row is, columns, checks, clean-ups), the file's words (measures, business rules such as "paid out = Approved + Paid"), and how tabs connect. Writes `file-skills/<id>/skill.json` and tests it on a junk-data mock. | See real values |
| **The form** (code: `lib/formkit.py`, `lib/formserver.py`) | A page per file in a Paseo tab: a tab per sheet; dropdowns for what to count, how to break it down, which rows, which dates; the checks' problems; the contract test's verdict. Turns a form state (a *spec*) into one checked DuckDB query. Reads the user's date words ("last month", "this FY", "08/26 to 10/26"). | Guess |
| **Idli** (Muse 30B or the 9B) | Finds the file, talks, offers teaching, and fills the same form from a typed question; relays the answer, which the form tab also shows. | Write SQL or numbers (raw SQL tools are disallowed for co-work) |

Before every query a **contract test** checks the file is still the layout Idli was taught: a new category value or
column is reported and the answer still runs; a used column gone, a tab gone or dates no longer parsing stops and
asks for re-teaching. Tested on six kinds of edited copies (`lib/test_formkit.py`).

## What a user did (30B unless noted; answers checked against pandas)

| Step | Typed | What happened | Result |
|---|---|---|---|
| 1 | "open the form for https://docs.google.com/spreadsheets/d/…" | `file_get` asked the browser for the real .xlsx, `file_open` recognised the volunteer register, ran checks, opened the form tab | ✅ 11 problems listed (mobiles, emails, a "TBD" date, "pending" stipend) |
| 2 | "how many volunteers have joined since july and how much stipend have we paid them? split by district" | form spec, answer relayed | ✅ 25 / ₹32,100 (Google's quick export had given ₹24,600) |
| 3 | "who hasn't been paid yet?" | listed the 9 with stipend 0, offered the blank reading | ✅ reasonable; missed "pending" (Ravi Pawar) |
| 4 | "how many people joined last month?" | `period: last_month` | ✅ 3 |
| 5 | "which of the september joiners are from pune?" | | ✅ Rekha Patil, Kavya Shaikh |
| 6 | "i've also put the field programme tracker in the folder… how much each district disbursed last quarter" | unknown 3-tab file → teach offer → labels to share (Status, District) → Teach chat asked about tabs, links, which district, which visits count, first names → skill v1 → Idli continued by itself | ✅ Pune ₹2,68,750, Satara ₹1,55,750, Kolhapur ₹1,33,000, Sangli ₹1,04,000 |
| 7 | "which officer gave out the most money in september?" / "any follow-up visits pending in wai?" | form, no teaching | ✅ Kavita More ₹74,750 / ✅ 4 |
| 8 | "meena and meena kulkarni are the same person, she should be one line" | the form couldn't merge them → re-teach → Claude added the Officers tab's name as an "Officer" breakdown (data only, no code) → v2 | ✅ Meena Kulkarni ₹49,000, one line |
| 9B | same link, then "joined since july… by district", "who joined last month?" | form opened; first answer exact; for the second the listing only gave a count, so the 9B escaped to raw SQL | ✅ answers; fixed: listings now name the rows, raw SQL tools disallowed |

## Downloads, honestly

Paseo's browser downloads fine: the request ends in the system "Save" dialog (its title is the long Google
download URL). In these runs the laptop screen was locked and the DGX was driving through a tunnel, so nobody
could click it, and that, not Paseo, is why early downloads "failed". For the rest of the session the browser
was switched to save without asking (a DevTools setting, the same effect as the Paseo patch below), then switched
back. On a normal desktop: `file_get` triggers the export, brings the dialog to the front, the person clicks
Save (any folder; it also looks in the folders the dialog recently saved to), and Idli copies the file into the
workspace. `desktop/paseo-browser-downloads.patch` (Paseo 0.15.2, tested with vitest) makes it silent: a
`will-download` handler saves into `PASEO_BROWSER_DOWNLOAD_DIR` or Downloads, never overwriting. It is a
convenience, not a blocker.

Side effect to know about: during the silent-download test the export replaced `~/Downloads/volunteer_register.xlsx`
on the laptop with a fresh export of the same sheet (the owner's copy in `~/idli-insights/testdata` is untouched).
Four Save dialogs from the locked-screen attempts were left open; they need Cancel.

## Found and fixed along the way
- Google's quick export blanks text in number columns; the quick-export warning now goes into what Idli says.
- Mocks gave a first name and the full name unrelated fakes; people's names now become `PersonN SurnameM`, a bare
  first name `PersonN`, across tabs. The question sent to Teach uses the same fakes ("Person6 and Person6 Surname6").
- Lookups: `"match": "first_name"` (written by the Teach chat, reviewed, kept); lookup misses are reported as problems.
- Row listings now include the rows; contact columns (phone, email) are search-only, never a breakdown.
