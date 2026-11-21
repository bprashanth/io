# 2026-11-16 00:00: Start here > Teams; an Insights team that comes out as Drivey

**Asked:** the abstraction is a team, not an app. A manager makes a team by answering a few questions; for the PoC
the questions lead to an "Insights" team that is a clone of Drivey (Drivey stays as is). Idli asks, not Claude.
Minimal words; screen 1 is only a Make a team button. Assume people answer in unexpected ways (testing for someone
else, a team of one, the team starts next week). Try it, redo until it feels natural for a class.

**Built**
- `lib/teams.py`: the conversation (`route`, rebuilt from the chat's own history every turn) and the setup
  (`create`, `check`, `team_dir`, `start`). Questions: name, goal (typed), then cards for where the data lives, who
  uses it, private details and the outside query service; a plan; Set it up or Change something. Typed answers are
  read by rules first and the local 9B second (it only picks a name, a goal line or an option). Help answers, cancel,
  start over. `tests/teams_sim.py` talks it through with the real router; `tests/test_teams.py` (15 tests).
- Router (`lib/modes.py`): `teams_chat_route`. Also: a message typed while a card is open arrives from Claude Code
  as a system note ("The user sent a new message while you were working: ..."); `_events` now reads it as something
  the person said, for every Idli chat (Drivey too). Found on the laptop: before this, typing over a card re-asked it.
- Tools: `team_page` (the button, `/teams` on Drivey's page server), `team_check`, `team_create`.
- A team is `~/idli-insights/teams/<name>/` with `team.json`, Drivey's CLAUDE.md, tools and sites. Claude's masked
  copies: `~/idli-insights/claude-masked-<name>` (`home.work_dir(data_dir)`, `desktop/claude-masked.sh` picks the
  team from the folder Paseo starts it in, and labels the Privacy log with the team's name). A team set up without
  the outside service gets `no-query-service`, which turns off `can_query` for its Minis.
- Bootstrap: Start here gets a third entry, Teams; Teams and Privacy chats are labelled `idli.plain=1`.
- Paseo P20 (idli23, then idli24): team folders are Drivey projects; the heading's row reads New chat and opens the
  two halves with the team's name; Minis per team (`/api/minis-public?dir=`); pages from ports 8797-8819 trusted;
  `/teams` page; `idli.plain` chats look like Drivey's left chat.

**Tried on the laptop (test account)**: Make a team; "I'm from the IT team, just testing this for our programme
people" (got the name card); Insights; "no idea honestly, I'm not on that team" (example goal card); typed over the
card (re-asked, fixed in the router, then worked); Google Drive; "my team will use this from next week but I am just
testing it now" typed in the card's box (understood); Not sure; Yes; plan; Set it up. Insights appeared with New
chat; it opened Drivey's two halves with an empty Minis list and Claude in `claude-masked-insights`. Asked
field_vars_indicators.xlsx "how many plots are there per transect?": download, privacy card, review on Insights'
own page server (8801), Done, Switch to Claude, answered (7 transects, 37 plots). The Privacy log shows those
requests as Insights.

**Fixed after the run**: goal lead-ins ("ok so: actually it's ...") dropped; card copy; Teams and Privacy chats
get one-click cards and no tool rows (idli24). The test team was moved to `~/idli-insights/archive/` so the person
can make Insights fresh.

**Known**: the Drive download plus privacy scan of a 1,900-row workbook took about two minutes (same as Drivey).
The Teams chat keeps its history; Make a team starts over in the same chat.
