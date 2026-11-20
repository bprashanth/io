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
