# Teach Idli a file: human-style runs (2026-11-08, laptop Paseo driven from the DGX)

Idli never computes numbers. A spreadsheet is recognised by its headers. A known file runs its **file skill**:
checks, a "- checked" copy with formulas, and taught DuckDB questions. An unknown file, or a new kind of question,
goes to **Teach**: Idli builds a mock with junk values and a hidden `_idli_teach` watermark, scrubs the question,
shows what will be sent, and after a yes opens a Claude chat in the Teach workspace. Claude confirms the columns,
checks and reading of the question, writes `file-skills/<id>/skill.json` (data and SQL, no code), tests it on the
mock, and writes `done.json`. A watcher then tells the Idli chat to continue.

Code:
- `cowork/lib/filekit.py`
- `cowork/sites/files/tools.py`
- `cowork/.claude/skills/teach-file/SKILL.md`
- `cowork/idli/CLAUDE.md`

Skills taught in these runs: `cowork/file-skills/{tech_reimbursement_form,volunteer_register,households}`.

Questions were typed as a user would; ground truth comes from pandas on the source files.

| # | Model | Ask | Path | Result |
|---|---|---|---|---|
| 1 | Muse 30B | "how much did we spend on tech reimbursements between 26 aug and 26 oct?" | unknown → asked dates and statuses → teach (Status/Category labels shared, names fake) → auto-continue | ✅ ₹43,020, 12 claims (Approved+Paid) |
| 2 | Muse 30B | "who has been claiming the most for hardware this year?" | known file, new question → teach v2 (Claude asked which statuses count) | ✅ Anaya Rao ₹24,970, full ranking exact |
| 3 | Muse 30B | volunteers since July per district + stipend (messy file) | unknown → teach (district names kept fake at the user's request) → checks: 5 bad mobiles, 4 bad emails, 1 bad date → "carry on" | ✅ counts 25 (8/8/5/4); ❌ stipend ₹24,600 vs ₹32,100 (see gap 1), now caveated |
| 4 | Muse 30B | "how many volunteers joined in september, by district?" | known file, taught question, new dates, no teach | ✅ 7 (2/2/2/1) |
| 5 | Muse 30B | stipend since July | known file | caveat about hidden cells relayed ✅ |
| A | 9B (OpenRouter) | "how many volunteers joined in august, by district?" | known file (after fixing checked-copy matching) | ✅ 4 (2/1/1) + caveat |
| B | 9B | "how much did we actually pay out or approve on tech reimbursements in september?" | known file, taught question | ✅ ₹32,700, 7 claims |
| C | 9B | "which ward has the highest debt? the household data is in drive" | unknown → teach (wards anonymous) → auto-continue | ✅ Yerawada ₹4,90,000, full ranking exact |

The 9B was wrong on the vague date question before file skills, because it compared date strings. With skills it gets
the numbers right, because the numbers come from SQL that Claude wrote and tested.

## Found and fixed during the runs
- **Privacy:** the first Teach chat started in the *private* folder. An agent-scoped `paseo run` ignored `--cwd`.
  Its only command was rejected at the permission prompt, so nothing was read.
  `teach_send` now picks the Teach workspace explicitly, runs the CLI without the agent's identity, verifies the
  new chat's folder, and stops and archives it otherwise.
- **Scrubbing:** labels the user agreed to share were scrubbed from the question; they no longer are.
- **Confirmation:** Claude once skipped the confirmation round; the skill now requires it.
- **Mock quality:** the mock invented future dates and the wrong kind of spelling variants. Fake values now stay in the
  real range and copy the real casing.
- **Matching:** a title row merged into a header broke matching, and so did checked copies with `Check:` columns.
  Matching now tolerates both, and checked copies are hidden from `sheet_list`.
- **Runtime change:** Claude added a generic `not_future` rule to the runtime. It was reviewed and adopted, and the
  skill now says such changes must be generic and called out.

## Open
1. **Google's sheet export hides text in number columns** ("Rs. 300", "pending" come back blank). There is no browser
   route around it: Paseo drops downloads, and docs.google.com blocks in-page fetches. Idli now warns, and the caveat
   travels into every answer that uses the column. The real fix is a Drive download, through a Paseo change or the
   Drive API in a server-side plugin.
2. **Stale local copies:** a chat may reuse a sheet copy saved by an earlier chat (scenario B).
3. **Teach chats prompt for Bash** in some modes. They now start in `auto`.
4. **Model polish:** question cards (AskUserQuestion) are fine in the app but can't be read from the CLI, so remote
   driving reads them from the transcript. The 9B once echoed a tool instruction verbatim; tool output now separates
   `say_to_user` from `then`.
