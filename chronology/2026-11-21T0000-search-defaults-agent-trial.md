# 2026-11-21: phrase search, new defaults, an agent trial and a held-out rerun

Follows [2026-11-20T1400-scaffold-hands-on.md](2026-11-20T1400-scaffold-hands-on.md). The running list is
[todos/idli-insights/p1/scaffold_core_round1.md](../todos/idli-insights/p1/scaffold_core_round1.md).

## 1. Sync visibility (owner: "it feels like a stall")

- `sync sheets` downloaded every spreadsheet again on every sync, silently (34 to 250 s). Now unchanged sheets are
  skipped (0.1 s), and every stage announces itself with a clock time; `-vv` prints one line per sheet, mail,
  document and card; otherwise a progress line. Mail sync too.

## 2. Search, explain, judge (owner's decisions)

- Words in quotes are an exact phrase (spaces, hyphens, line breaks between; plural optional); unquoted words must
  all appear, and files with the words together rank first, by mentions, with a "how it matched" column
  ("phrase x55; p.2: ...border effects..."). "border effects": 4 documents with the phrase (wincoop.pdf 55
  mentions), 18 more with the words apart, listed last.
- `summarise --search` explains a topic from the pages that mention it most, naming the files. `judge --search`
  narrows judging. Replies after a search offer judging.
- `explain` stays the manual page. The mapper is told what search covers, through the manual (no new command).
- Defaults: Clef judges (hosted, test accounts only); the served 9B maps and words replies.
- Folds: `count` -> `list --count`; `read`/`describe` -> `get --text/--outline`; `events` -> `calendar`;
  `sync gmail|gcalendar|drive`; `--group-by`. Old forms still work; the menu shows only the new ones.
- B4/B5/B8: the reply is worded from what is shown; counts must match; no "is one of" lists for titles.

## 3. Agent trial (`benchmarks/runs/2026-11-21-agent-trial/README.md`)

22 questions in the owner's style, then 12 new ones frozen by hash before results were read. Round 3 before its
fixes: 7 right, 1 partial, 4 wrong of 12. Twenty general fixes (F1-F17, R2-R4, round-3 fixes): counts, quoting,
field meanings in the menu, own-words rule enforced in code for judge narrowing, drafts never "saved", summarise
not reworded, plural search, pasted listing rows as --reply-to, two-part questions show every short step.

## 4. Held-out rerun (`benchmarks/runs/2026-11-21-heldout-rerun/README.md`)

Same 27 frozen tasks, frozen code 9afd8e93, blind graders: the 9B 5 -> 10 correct; idli-remote 13 -> 13. After the
freeze: `--on "next month"`, `judge --since/--until/--on`, repeated `--label`. A new held-out set is needed.

## 5. dune

- `../dune` is a git repo with `.gitignore` for `*.claude.*`; `docs/cli.claude.md` holds the terms and commands
  table for the owner to copy into `docs/cli.md`. `.index.md` lists what to carry.

## 6. The owner's second session (t2): coalitions, ownership, leads (2026-11-21 afternoon)

- "creation of coalitions" unquoted ranked the NDSA fixity reports high: "of" had to appear, and words-apart
  matches were ordered newest first. Now: small words (of, the, about...) are not required, and below phrase
  matches files rank by how often each word appears, rarer words counting more (a small BM25). Coalition papers now
  follow the phrase match; `summarise --search 'coalition'` was already good (pages with most mentions).
- "owned by me": `owner = "me"` matched nothing. 'me' now means the account's address in owner, from_addr,
  organizer and to_addrs (157 files). "Who owns docs on conservation": the owner column wasn't shown and the 9B
  guessed owners from file names. Rules: a question about a field shows it (--fields); the reply states only what
  the rows show.
- "Mails from leads": the 9B searched for the word "leads"; idli-remote joined the Leads sheets (0 last week is
  right: 88profligate's mail is 16-18 Nov). The reply to the next question repeated the leads answer: wording that
  says nothing was found while rows are shown is now dropped.
- The leads workflow broke on `get sheet`'s column summary, which cut emails at 80 characters; a sheet of up to 50
  rows now shows every row in full. "The last few weeks" is 3 weeks. Views are real database views (usable inside
  SQL), and the manual proposes a view for group words (leads, funders) through the yes card. Several `--where`
  mean all of them. `ask yes` with nothing waiting says so. `-vvv` printed the whole 7,352-character prompt
  (the menu lists every folder and sheet), which looked like going through all files.
- Dev bank: `benchmarks/runs/2026-11-19-record-store/bank/tasks_owner_dev.json`, 11 tasks from the owner's
  sessions with SQL-checked expectations. Run on a clean copy of t2 (`2026-11-21-agent-trial/owner-dev/`): border
  effects, explain, coalitions, ownership, leads last week right; after fixes for placeholder REF, `end` as a field,
  `calendar` in SQL and the copied `urgent` example, the adivasi task is right too. Still weak: the 9B drops the
  person's words, carries a filter into a question that drops it ("who owns" kept owner = me), and doesn't connect
  88profligate with Asha Verma across two results.
