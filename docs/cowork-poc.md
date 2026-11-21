# Co-work POC: start here

**Status (2026-11-07):** a working proof of concept on the owner's laptop. It is driven from the DGX over a tunnel.
The owner tests it by hand next and designs the next experiments. **Agents: verify, and fix what the owner
asks. Don't start new experiments on your own.**

## What changed (newest first): DGX agent, read this after every `git pull`

Either agent adds an entry here for every change that needs something done on the other machine. The mechanism, and what the owner starts on the laptop, are in [laptop-dgx-sync.md](laptop-dgx-sync.md).

- **2026-11-13, DGX: share = the same Drive file; a Mini fetches its file on every open.** A Mini records the
  Drive file it was opened from (`sources.json`); Share sends the workflow plus that file's id, and the receiver's
  Idli opens the same file with their own Google account (`lib/drivefetch.py`: `fetch()` inside a Google tab via
  DevTools, else the browser session's cookies). Clicking a Mini fetches the file fresh and runs the dashboard;
  without access it says so. Clone (workflow without the file) is [todos P3](../todos/idli-insights/p3/clone_mini.md).
  DGX: two homes with fake Drives (no access, then access, then an edited sheet shows new numbers); the in-tab fetch
  in real Chromium. Laptop with real Drive: the in-tab fetch fails (cross-origin export redirect), so the cookie route
  is the only one; Share then open 1.0 s fetch / 1.5 s to the dashboard; a second empty Idli home on the laptop added
  the code and opened the same file; the DGX added it via silo (no Google there, so "sign in first"); a file the
  account can't open shows the no-access page. Not tested: two different Google accounts.
- **2026-11-13, DGX: Minis, shared by code only.** Mission control is now **Minis** ("Here is a list of workflows
  Idli has learned to analyse"): each row is a title with Share (shows the code) and Delete; the top has "Add a Mini
  [code] Add" with a one-line description and Yes/No. File download, Drive link and the hidden sheet tab are gone
  from the UI and tools (the sheet tab is off unless `IDLI_EMBED_SKILL=1`); the four ways and the open sync
  questions (refreshing the file; a code that follows the Mini's versions) are in
  [proposals/idli-sharing.md](../proposals/idli-sharing.md). DGX: two Idli homes, share, wrong code, add, chat tools.
- **2026-11-12 (late night), DGX + laptop: design narrative; sharing what Idli learned, four ways.**
  - **Design:** [idli-design.md](idli-design.md): a teacher model (Claude) learns from stand-ins and leaves
    scaffolding (forms, checks, charts, site tools) that a private worker model drives; the app makes the teaching
    loop easy and keeps the scaffold. History declauded (166 commits; backup branch
    `backup/oss-desktop-eval-pre-declaude-20261112`); not pushed.
  - **Sharing** ([idli-sharing.md](../proposals/idli-sharing.md)): one bundle (`lib/share.py`: the skill, a manifest listing
    the real words inside, hashes) and four ways: a .idli file (Mission control Share / Add), a Drive link
    (`skill_import`), a hidden `_idli_skill` tab in the checked copy (a colleague who opens the shared sheet gets a
    card), and a share code from the Idli server (`/idli/share` on the router). DGX: two Idli homes, A shared and
    B added by file, by code and from the sheet, then answered straight away. Laptop: code round trip through silo.
  - **Incident:** resetting the laptop to the rewritten history overwrote the households skill the owner had just
    taught (git-tracked fixture files; the warning lines were missed). Rebuilt from the Claude Code transcript
    (v2, 7 measures, its tests pass); the overwritten copy is in `archive/skills`. The extra "Greet and confirm
    availability" workspace is not archived yet (the owner's teaching chat was using it).
- **2026-11-12 (night), laptop: Vega-Lite charts and the Idli | Claude split, verified in the app.**
  - **Charts** (`lib/vlchart.py`): code picks the chart from the answer's shape (bars; one panel per figure; a time
    line; a heatmap for two breakdowns; a point map when rows have latitude/longitude, rows at one place merged into a
    counted bubble). The chat gets an SVG made offline (vl-convert); the dashboard draws the same spec with vendored
    vega (no eval) and drills on click (the value becomes a filter, the breakdown moves on). Idli's CLAUDE.md sends
    maps and drill-downs to the form. Claude's own charts (chart_request) are still matplotlib.
  - **Laptop, Muse, households (test account):** figures by ward as panels (18 s) → "break Yerawada Ward down by
    household head" (17 s) → map sized by debt (16 s) → "ask Claude: a scatter ..." → Claude opened on the right in
    Idli's workspace (provider idli-teach), green border → Claude drew it on fake data, "Yes, back to Idli" → border
    moved left, Idli drew it from the real file.
  - **Found and fixed after the run (not yet re-seen in the app):** the left pane showed an old tab when Claude opened
    (teach_send now puts Idli's chat in front, then focuses Claude); map points at the same rounded location hid
    each other (merged). Dashboard drill tested on the DGX only.
  - **Install:** `/opt/Paseo/resources/app-dist` → `~/idli-insights/paseo/app-dist` (P13/P14 build); `config/ui.json`
    split true. Don't take Paseo's 0.15.4 update until the patches are rebuilt on it.
- **2026-11-12 (evening), DGX + laptop: Muse and Claude only; simpler layout; readable answers and charts.**
  - **Owner, after testing the three modes on the laptop:** Steam's answers were unreadable and it didn't converse;
    the 9B described a chart it hadn't drawn (the quick chart drew only the first figure: one bar). Muse only.
    The menu lists Idli 30B alone; the router still serves `idli-9b` / `idli-steam` for experiments; the 9B is
    stopped (`dgx/idli-9b.sh up` to bring it back).
  - **Answers:** more than 2 figures read "4 figures by Ward", one line per figure; ratios, months, shares and
    scores never get Rs. **Charts:** several figures draw one panel each; a single row draws none. Idli's
    instructions now send "show that as a chart" to the form's chart, Claude only for shares, side-by-side
    filters, maps and computed trends.
  - **form_explain** (new tool): "how is X worked out?" answered from the skill in code. Muse had sent that
    question to Claude, whose card then said "I haven't seen households before" for a known file; that wording is
    fixed too.
  - **Fake copy:** places that read like names (wards such as "Yerawada Ward") are no longer faked as people
    ("Person27 Surname32" confused Claude). teach_file returns `question_for_claude` (names replaced).
  - **Layout:** Start here holds the Start here chat, a Mission control tab (what Idli has learned) and one Drive
    tab; the old Mission control heading is deleted. Heading order still needs a drag (Paseo patch P2).
  - **The terminal in the Claude workspace was the DGX agent's** (for `git pull`); Idli never opens one.
  - **Verified on the DGX** (real Claude Code + Muse, household survey): figures by ward → panels chart (8 s) →
    form_explain → share question → Claude card ("can't do this yet") → Not now sends nothing.
  - **Laptop:** on `69eb3b49`+bootstrap (menu, layout, form_explain); the last commit (`b16323b9`, the chart rule
    in Idli's CLAUDE.md) needs `git pull` + bootstrap. A terminal tab in Start here may be stuck closing.
  - **Split panel** (Idli left, Claude right): `todos/idli-insights/p1/split_panel.md`.
- **2026-11-12 (afternoon), DGX: form engine reads two model slips the way they were meant** (all modes).
  - **Date words:** "this year" came back as `{"period": "year"}`, in `filters` or in `date`; the form refused it,
    so the question errored and the follow-up had nothing to refer to. `formkit.period` now takes "year", "this
    year", "FY" and the like, and other words go through `parse_when`. A date range written as a filter is read
    as the spec's date.
  - **"Not everything but one":** "which are still pending" came back as Status not Approved, Paid, Rejected
    (Codex's "Ward D alone" miss is the same slip). When 2 or more known values are excluded and one is left, the
    spec becomes that value: the answer says "Status is Pending" and leaves out blank or new statuses.
  - Both in `formkit.normalize_spec` (run before the query and its description). Quick clarify set, today's
    prompt on the 9B: 23/32 (was 22); the reimbursement conversation now answers both steps.
  - **Quick clarify experiment** (`benchmarks/runs/2026-11-12-clarify-quick/REPORT.md`): nobody over-asks; today,
    vague words and names not in the file go to Claude; Muse with clarify/absent replies and code value hints gets
    29/32 (asks about "poor", says "IAF funder" isn't there), the 9B 24/32. Not in the product yet.
- **2026-11-12 (morning), DGX: Idli's model switch: Muse, 9B, Steam powered** (commit `3cc04497`; laptop not yet
  pulled, tunnel down). The owner asked for the code/cards result behind a switch in Idli's model menu.
  - **How:** Paseo's Idli provider lists three models; the id goes to the DGX router behind silo
    (`dgx/muse_prefix_proxy.py`, port 8185), which picks the backend. Logic in `cowork/lib/modes.py`.
    - **Idli 30B (Muse)** `muse-glimmer-30b`, the default: today's product, unchanged (file_ask keeps spec-only).
    - **Idli 9B** `idli-9b`: the E7 winner. The 9B (container `idli-9b`, `dgx/idli-9b.sh`, 2 slots of 32k) runs the
      chat on a lean prompt (`idli/CLAUDE-9b.md`, the 12 Idli tools), file_ask takes the person's words and a second
      9B call sets the form's dials (the split, now in `sites/files/tools.py`), and the eval's guards (show a tool's
      card, no made-up numbers, no own cards) run in the router. New: teach_send only right after "Yes, send and
      switch" (the 9B sent once after "Not now" in testing).
    - **Steam powered** `idli-steam`: code runs the chat (no model): tool cards are shown as they are, each answer
      maps to the next tool, typed text goes to file_ask with the person's words (one 9B call for the dials), and
      answers are shown as code rendered them.
  - **Codex's fixes:** typed units (`answer_text` uses the measure's format: a count never gets Rs, percent gets
    %); tests in `lib/test_formkit.py`. The numeric-literal fix is for the Clef adapter only; nothing to port.
  - **Tested on the DGX** through real Claude Code (the 9B benchmark's `cc_convo.py`, fake Drive, planted-mess tree
    file): open → upload card → Continue → question → chart → "share" question → Claude card → Not now, in all
    three modes. Per step: Steam 2-6 s, 9B 16-40 s, Muse 11-30 s. Muse behaves as before; the 9B repeats E7's
    weak spots (redraws an existing chart through Claude). 16k slots overflowed on the 4th question (16,421
    tokens), hence 32k.
  - **Known gaps:** spare "New chat"s open on the default model (switch from the menu); Steam has no clarifying
    questions (Codex: F's one miss was a scope choice); Steam's own "teach the new layout" card is new wording.
  - **Pre-existing, not from this change:** `run_tests.py files` fails "teaching request sends fake values only"
    (last green 11-08).
- **2026-11-12 (morning), DGX: round 2 evals on today's flow (E2b, E3b, E4, E5) and the Codex code/cards experiment**
  (branch `exp/evals-1111` at `0b395e5a`, local only; `benchmarks/runs/2026-11-10-idli-pipeline-eval/REPORT.md`,
  "Round 2"; Codex: branch `exp/clef-form`, `benchmarks/runs/2026-11-11-clef-form/REPORT.md`).
  - **E3b (trip to Claude through the upload/Continue cards):** the cards add no failures. Muse on the checked
    copy got 9/9 right; 36/45 overall vs 21/27 for E3 on the same corrected answers. 39/40 trips came back,
    about half a minute and $0.15 each. All 40 trips were charts (`chart_request`), never new measures.
  - **E3b misses, all on the 9B:** 3 wrong bounces (the split called form questions unsupported); on village-chart
    the 9B offered Claude a turn late after `file_ask(chart=true)` said the form can't draw it.
  - **E2b (`IDLI_MOCK_V2`):** overall gain is noise (90/78/85% vs 88/85%). Duplicate IDs 33→78% but end-before-start
    100→33%. Ship only with the date-order fix.
  - **E4:** from `exp/answer-mock`: 9B rewording drops a number in 13/53 turns; code rendering keeps 74/74.
  - **E5 (10 charts, fake → real):** 10/10 ran on real data, 0 broke only on real data, 0 dropped rows on their own.
  - **Codex (code/cards):** 6 card journeys run with 0 model calls. Replacing the form planner fails (A 12/20 vs
    new 9B prompt 4/20, Clef 9/20); keeping the planner but moving coordination and wording into code (F) gets
    19/20 vs A 20/20 with a third of the calls and ~5 s instead of ~25 s. Found a units bug: `answer_text` prints
    a count as "Rs16".
  - **Not done:** nothing merged into `oss-desktop-eval`; nothing pushed.
- **2026-11-11 (night), DGX: cards back at every step into analysis; "Continue" re-reads the copy from Drive**
  (commits `05ea479d`, `dd54e801`; laptop pulled). This replaces the two entries below: no copy is made without
  asking.
  - **Owner:** a card is deterministic and less messy than asking for free text ("fixed"). Always ask at a decision
    point:
    1. **Upload.** `file_open`, when the file has problems and no checked copy for this skill version (new or
       re-taught): "The checks found N problems in K kinds... Upload a checked copy to your Drive so you can fix
       them?" → "Yes, upload a checked copy (Recommended)" / "No, analyse the original".
    2. **Continue.** `working_copy` then returns its own card: "I've uploaded "<name>" to your Drive, next to the
       original... Fix what you think matters there. Continue with analysis?" → "Continue with analysis" / "Not
       yet". The same card comes back when the copy already exists.
    3. **On Continue:** `working_copy_ready` downloads the copy from Drive again, so the person's corrections are
       read. It now says what was fixed and what's new ("you fixed 1 problem; 1 new one appeared (Density row 3,
       ...)"): a fix can create a problem on another tab, which totals alone hide.
  - **A file with a copy:** "Use the checked copy (Recommended)" (read again from Drive) / "Use the original".
  - **Re-taught since the copy** (copies record `skill_version`): Idli says the checks changed and offers a fresh
    upload.
  - **Charts:** they don't upload. Rows with problems are drawn as they are, and Idli points at the copy if there
    is one (the 51392d9d/dabfad55 no-drop rule stays).
  - **`idli/CLAUDE.md`:** the clean steps describe the two cards.
  - **Verified in the app (laptop, 2026-11-11 22:54-23:00, cestrum original by link, reloaded chat; the laptop's
    Google account is a test account):**
    - Upload card → yes → "field_vars_indicators - Idli working copy 11 Nov 2257" in Drive (red cells, comments,
      tab counts, Idli checks tab) → Continue card.
    - I typed a species code into D5 in the Drive copy, and its red cleared.
    - Continue → re-downloaded: D5 = 'cesaur' in the downloaded copy.
    - The total stayed 195: the D5 fix removed one problem but added a Density count mismatch for that plot. That's
      why the message now lists both. (D5 is left filled in that test copy.)
    - Screenshots: Drive tabs over DevTools with node (`Page.captureScreenshot`; key events for typing). App
      clicks are in CSS pixels: half the screenshot's pixels.
- **2026-11-11 (late afternoon), DGX: [superseded the same night: cards are back] the checked copy is made after every teach, without asking** (commit
  `8a117e7f`; laptop pulled).
  - **Owner:** whenever Claude teaches a file (new or re-taught), Idli makes the checked copy in Drive (red cells,
    a comment per kind of problem) and gives the link. No "Mark them in Drive?" card any more.
  - **How:** `file_open` makes it when the file has problems, came from a Drive link (`file_get` recorded its id)
    and has no copy for the current skill version. Copies now record `skill_version`, so a re-teach makes a fresh
    copy. Idli says: "The checks found N problems in K kinds. I've marked them in a copy next to the original
    (<link>, open in a tab) ... Fix what you think matters and say "fixed", or carry on with the original."
  - **Cards:**
    - Clean goal: "I've fixed it, go on" / "Analyse the original now".
    - Analyse goal: the usual start card; "fixed" → `working_copy_ready`.
  - **Charts** (entry below) reuse this copy; they make one only if none exists, e.g. a file taught before this
    change.
  - **Verified on the DGX** with the Drive upload stubbed: first open makes the copy; reopening doesn't; a new
    skill version makes a fresh one; a chart reuses it. The formkit tests pass.
  - **Verified in the app (laptop, 2026-11-11 22:48), with the cestrum original opened by its link in a reloaded
    "New chat":**
    - **First try:** the file still had its 9 Nov copy on record, so Idli offered "Use the checked copy / Use the
      original" and made no second copy. That's right.
    - **Second try:** the copy record was set aside (backup
      `drive/field_vars_indicators.xlsx.source.json.bak-2026-11-11` on the laptop). Idli made "field_vars_indicators
      - Idli working copy 11 Nov 2248" next to the original, opened it in a tab, gave the link with the new wording,
      then showed the start card.
    - **In the copy:** red cells; a comment on the first cell of each kind ("'neosco' appears 75 times but isn't
      in the Read me tab ... Same problem in 74 more cells"); counts on the tab names (8, 1, 4); and an "Idli
      checks" tab listing all 12 kinds with links.
    - Drive now holds both the 9 Nov and 11 Nov copies.
    - **Tooling:** screenshots of Drive tabs come from DevTools (`Page.captureScreenshot` over the tab's
      websocket, in node). `drive.py shot` only sees the app window, whose clicks are in CSS pixels (half the
      screenshot's).
- **2026-11-11 (afternoon), DGX: [the upload part superseded the same night] charts never drop rows; messy rows go to the checked copy** (commits `51392d9d`,
  then `dabfad55`, which replaces its card).
  - **Why:** in E3, Claude's chart code removed rows with a repeated ID before counting, without telling anyone.
  - **Owner's decision:** code never drops or merges rows. No card either. Idli draws the chart from the rows as
    they are and sends the person to the checked copy:
    - If rows the chart reads have open problems (the tabs its code reads, the columns it mentions, plus
      whole-row problems), `chart_show` makes the checked copy if there isn't one (`working_copy`: red cells, a
      comment per kind of problem, next to the original in Drive), or opens the existing one.
    - Idli then says: "N rows this chart uses have problems (e.g. Status 'cancel'); they're drawn as they are.
      They're marked in your checked copy: <link>. Fix what you think matters and say "fixed" to redraw, or just
      carry on."
    - "fixed" → `working_copy_ready` → the chart again on the copy.
    - The person scans the colours and comments and decides what's worth fixing.
  - **Rule change:** the checked copy used to be made only after a yes on a card. It's now also made without asking
    when a chart uses rows with problems. It's still the only write: a new file, the original untouched.
  - **Merging values:** no special-casing. "cancel" vs "Cancelled", or "12 cm" in a number column, are flagged by
    the checks (already: the status rule and the number rule), not read quietly. The teach-file skill now says
    chart code must not drop rows (`drop_duplicates`, outliers) or merge values.
  - **Correction to the E3 report:** chart code already reads exactly what the form reads (`chartkit.tables()`
    calls `formkit.build`). The split spellings are in the form too; they're flagged problems, which the person
    now sees in the checked copy.
  - **Verified on the DGX:** field-visits fixture with Claude's E3 status chart.
    - With no Drive source, the chart draws and Idli says the 3 rows and that it couldn't make the copy.
    - With an existing copy, the chart draws and Idli gives the link.
    - The formkit and fixkit tests pass.
    - **Not yet seen in the app:** the laptop pulled `51392d9d` only; making the Drive copy from a chart needs a
      file with problems and a chart Claude wrote.
  - **Owner decisions (2026-11-11):**
    1. Charts use the form's reading: already true.
    2. No silent drops: the checked copy, as above.
    3. Hold `IDLI_MOCK_V2` for one more E2 run.
    4. "Measures": undecided. A measure is a named calculation in the file's form ("Number of visits", "Total amount
       (Rs)") that the 9B picks to answer in words. In E3 every new question went to Claude as a chart (the chat
       model chose `chart_request` over `teach_file`); the alternative is Claude adding a measure such as "Share
       of visits cancelled".
  - **Next:** [todo](../todos/idli-insights/p1/chart_code_reading.md). Rerunning E3 waits for the owner.
- **2026-11-11, DGX: E1-E3 results** ([report](https://github.com/bprashanth/io/blob/idli-pipeline-eval/benchmarks/runs/2026-11-10-idli-pipeline-eval/REPORT.md),
  branch `idli-pipeline-eval` at `4dbc4c22`).
  - **E1 (fake copy):** keeps 43 of 62 kinds of planted mistake; 47 with Codex's fixes behind `IDLI_MOCK_V2=1`
    (off). Still lost: spacer and notes rows, merged headers, info blocks; "12-Mar-22" dates and start-before-end
    order (p2 todo).
  - **E2 (teaching from the fake copy vs the real file):** 88%/85% of mistakes found from today's fake copy, 90%
    from the fixed one (but 35 false alarms vs 20), 81% from the real file. Noise-level: better fake data is not
    the next investment.
  - **E3 (the trip to Claude and back, 9B x2 and Muse):**
    - The trip works: 0 wrong bounces in 27 chats; sent 23/24, back 22/23; about a minute and $0.15 a trip.
    - Every share question went as a chart, never as a form gap.
    - Claude's chart code gave exactly right numbers on the real file in 12 of 24 trips, the same for both chat
      models. It split readable spellings ("cancel"/"Cancelled") and dropped repeated-ID rows without being
      asked (p1 todo `chart_code_reading.md`).
    - 6 of the 9 expected answers had to be corrected first (Codex's `refcheck.md`).
  - **Harness bugs fixed:** the E3 runner wrote nothing because `idli.setup()` changes into a temp folder; a
    stalled Claude API call waited 30 min (headless teaching now caps calls at 5 min).
- **2026-11-10 (late night), DGX: owner's decisions after E6/E7.**
  - Readable-but-inconsistent values are flagged only when they would confuse the 9B; a strict mode comes later
    (p3).
  - Template instruction rows stay unchanged in the fake copy.
  - Every table on a tab must be read, subtables and info blocks included. This is new work (p1). Where a layout
    would confuse the 9B, Claude suggests a simpler one.
  - Soft phases ship.
  - The handoff page gained a guide for running experiments in parallel: worktree plus branch per experiment, an
    own benchmark folder, product changes behind a switch, merge into `oss-desktop-eval`, then one PR to `main`.
- **2026-11-10 (late night), DGX: E6 and E7 results** ([report](https://github.com/bprashanth/io/blob/idli-pipeline-eval/benchmarks/runs/2026-11-10-idli-pipeline-eval/REPORT.md),
  branch `idli-pipeline-eval`).
  - **E6 (cleaning on files with planted mess):** Claude learned each file from its fake copy, with no person in
    the loop and Haiku as the owner. Its checks found 73% and 71% of 161 planted mistakes in two runs, with 20 and
    17 false alarms in 3,378 rows, and skipped 38 of 42 layout rows.
    - **Misses:** values the reader quietly fixes (units, casing, "n/a"); checks Claude didn't write (counts across
      tabs, totals, duplicate IDs); and the fake copy turning a template's instruction rows into junk.
  - **E7 (local 9B with the split, 12 tools):** soft phases scored 86% on held3, the same as Muse, and 78% vs 85%
    on question steps, at about twice Muse's speed. Hard phases (only the current step's tools) scored 79%: a wrong
    guess between clean and analyse loses the question. Claude Code does re-read a changed tool list mid-chat.
  - **The capacity todo** moved to p2 (test the 9B only).
  - **Owner decisions pending:** mark or quietly read units, casing and "n/a"; keep instruction rows in the fake
    copy; read info blocks above a table; ship soft phases.
- **2026-11-10 (night), DGX: no index, no file search; each chat gets only the tools it needs.** Handoff page:
  [idli-handoff.md](idli-handoff.md).
  - **Idli** asks for the file's link instead of searching Drive.
  - **Start here** has its own folder (`~/idli-insights/setup`) and heading. It only checks sign-ins (Google
    through the Drive tab, Claude through `claude auth status`, Muse through `/v1/models`) with a new
    `setup_check` tool.
  - **Mission control** holds only What Idli has learned (`idli/LEARNED.md`).
  - **Tool lists:** a per-folder `cowork.tools` file, written by the bootstrap, keeps each chat's tools to its
    job. Idli has 12 (it had 34), Start here 1, Mission control 3.
  - **Migration:** the bootstrap archives the old Start here workspace.
  - **Verified on the DGX:** the tool lists, the Claude and Muse checks, and the formkit and fixkit tests.
  - **Laptop:** run `git pull dgx oss-desktop-eval`, then the bootstrap.
  - **Known gap:** a working copy now lands in My Drive (the folder came from the index).
- **2026-11-10 (evening), DGX: one file at a time; an eval of the whole pipeline is planned.** The owner
  dropped the upfront Drive index from the journey. Idli works from one link or upload at a time, and each learned
  file leaves a context card. Those cards become the index and, later, a graph like idlisseus's site-pack graph
  ([todo](../todos/idli-insights/p1/file_by_file_index.md)). Todos are now sorted into `todos/idli-insights/p1..p3`.
  The 9B benchmark (branch `idli-9b-bench`) found that a separate call to set the form's dials, inside
  `file_ask`, makes a 9B nearly as good as Muse on fresh chats (9B alone 79-81% vs Muse 83%). It tested only
  forms that already existed. The new [pipeline eval plan](../benchmarks/runs/2026-11-10-idli-pipeline-eval/PLAN.md)
  tests the rest on planted-mess files: the cleaning output (E6), fewer tools by phase (E7, 29 → about 9), how
  realistic the fake copy is (E1), teaching from the fake copy judged on the real file (E2), the bounce to Claude
  and back (E3), the wording of answers (E4), and charts (E5). Not started: waiting for the owner's go.
- **2026-11-10, DGX: Muse through Cloudflare (silo.idli.cc).** The owner put Muse behind Cloudflare Access at
  `silo.idli.cc` (tunnel → DGX 8185, the prefix proxy → Muse) with a service token. `lib/muse.py` gives the URL and
  the two Access headers from `~/idli-insights/config/muse-access.json`; `desktop/muse-connect.py <token file>`
  checks the token and points the Idli 30B provider at silo through `ANTHROPIC_CUSTOM_HEADERS` (Claude Code sends
  them on every call). End to end on the laptop with nothing listening on 8181: start card, Analyse, "the cestrum
  field vars file" (16 s, two matches), the original (54 s with the download), checked copy (48 s), "how many
  cestrum trees, what share" (17 s: 317, 17.34%), chart of share by transect (12 s, bars in the chat). On the DGX
  the only client of 8185 during the run was `cloudflared`. Running chats keep the settings they started with:
  the bootstrap's spare was replaced and Start here reloaded. Copying the token needs the laptop's ssh to the DGX,
  which Tailscale gates with a browser check.
- **2026-11-09 (late night), DGX: "What Idli has learned" is a page again.** The owner preferred the list page to
  a chat table. Mission control now has two workspaces: Start here (setup chat) and What Idli has learned (the
  `/skills` page in a browser tab, plus a small chat that only points at it). The page says "Here is a list of files
  Idli has learned to analyze", refreshes itself every 5 s, and has Delete under each entry (P11 crops the right
  edge). The form server keeps its token across restarts and the bootstrap starts it, so the tab's link stays good.
  Found: Paseo's `browser_list_tabs` lists only the tabs of the workspace on screen, so each bootstrap rerun opened
  Drive and the page again; the bootstrap now remembers what it opened (`~/idli-insights/config/bootstrap-tabs.json`).
- **2026-11-09 (night), DGX: owner's feedback on the journey.**
  - **No waiting for "hi":** Idli always keeps one chat named "New chat" open on the start card (made by the
    bootstrap, then by `ensure_spare` in `sites/files/tools.py`). Using it renames it ("Clean: <file>",
    "Analyse: <file>", "Find: …") and opens the next one in the background (one spare at most, one start per 2 min).
  - **Mission control:** the first heading is now Mission control, with the workspace Start here holding two
    chats: "Start here" (setup, indexing) and "What Idli has learned" (tools `skills_list`, `skill_delete` with a
    confirm card). Bootstrap renames the heading and creates both chats.
  - **Teach card:** the Labels question has "None (Recommended)" (typing in Other is for a different answer);
    the fake copy opens in a `fake-copy.localhost` tab ("Fake copy for Claude: <file>") so the person sees exactly
    what Claude gets.
  - **A leak found and closed:** the households mock kept the real coordinate range, so Claude worked out the survey
    was around Pune. Coordinates (columns named lat/lon/…) are now faked around (0, 0) with the same spread, postal
    codes are random; IDs (PAN, receipt numbers, plot codes) keep their shape and fixed prefixes so checks can be
    written. The teach skill tells Claude never to put real-world places or extents in chart code.
  - **Teach skill:** step 0 discusses what they want to find out (the poverty-trap kind of brainstorm); clean-ups are
    phrased as how Idli reads the real file (Claude never tidies the fake copy); a question typed into Other is
    answered before the card is asked again.
  - Laptop: `file-skills/households` holds the owner's re-teach (uncommitted, kept across pulls with a stash).
- **2026-11-09 (evening), DGX: one journey, scoped.** Field note:
  [narrative/2026-11-09-one-journey-field-note.md](../narrative/2026-11-09-one-journey-field-note.md); test steps:
  [cowork-manual-test.md](cowork-manual-test.md) section "The Idli journey".
  - **Start:** an Idli chat opens with a card, *Clean up a file* / *Analyse a file* (tool `start`); a first
    message that already says what it wants skips it. `file_get`/`file_open` take `goal` and show the matching card.
  - **Clean:** unknown file -> teach card -> Claude (one step at a time, cards) -> back -> "Mark them in Drive"
    -> working copy next to the original (live red cells, one comment per kind of problem) -> "I'm ready" ->
    `working_copy_ready` re-checks the copy and moves on to analysis. Analysing a file with a working copy offers
    "Use the checked copy (Recommended)"; one without says it hasn't been cleaned.
  - **Analyse:** questions go to `file_ask` (multi-turn); a graph is `file_ask` with `chart` (one breakdown: bars;
    two: a grid), drawn from the form's answer into the chat and the dashboard. Anything the form can't draw, or
    "suggest analyses", goes to `chart_request`: a fake copy to Claude, who agrees the chart on cards, writes
    `file-skills/<id>/charts/<chart>.py`, renders it on the fake data in its chat, and hands back; Idli runs it on
    the real data (`chart_show`) inside a bubblewrap wall (no network, read-only, home hidden, `lib/chartkit.py`).
  - **Dashboard:** problems collapsed to one line with **View problems in Drive** (the working copy) and Details;
    the freed space has a live bar chart of the current answer and a gallery of the file's charts.
  - **Skills page** (`/skills`, tool `show_skills`): what Idli has learned, one per file, with Delete (moved to
    `~/idli-insights/archive/skills`). The cestrum skill was removed this way to retest teaching from scratch.
  - **Engine (from Claude's teaching session):** `row_checks` (taught SQL conditions across columns and tabs),
    lookup `accept` patterns for a team's own codes, `"case": "lower"`; small whole-number columns (transect,
    plot) are breakdowns.
  - **Removed from Idli:** the `sheets` site (free SQL, its own charts), which Muse used to make up a chart
    query that failed. `cowork.sites` in the Idli folder is now `google` + `files` (bootstrap rewrites it).
  - **Laptop:** `matplotlib` in the cowork venv; `bwrap` needed (present on Ubuntu/Pop). `__pycache__` is no longer
    tracked (it blocked pulls).
- **2026-11-08 (late), DGX: first-run experience (OOBE) played as a new user.** Field note:
  [narrative/2026-11-08-oobe-field-note.md](../narrative/2026-11-08-oobe-field-note.md); runs and numbers:
  `benchmarks/runs/2026-11-08-oobe/` (`oobe_test.py`, `results.jsonl`, `search_eval.py`, `search_chat_test.py`).
  - **Layout:** headings Start here / Idli / Claude, laid out by `desktop/idli-bootstrap.py` (run by
    `desktop/idli-launch.sh`, the "Idli" app-menu entry). Start here chat opens on low thinking.
  - **Start here:** greeting, "yes" (any go-ahead) starts the index, progress in a `drive-index.localhost` tab,
    finish with next steps in the chat (the indexer's "Drive index: done" note prompts it if the model stopped).
    30B: greeting ~10 s, acts ~5 s, index 182 files in 5.5 min; 9B: same, waits silently and writes the finish.
  - **Search:** vector index 23/25 first-place vs 22/25 for today's lexical+summaries; not adopted yet. Summaries
    now carry everyday words. 30B chat search 34-80 s (reasoning tokens at ~30 tok/s), 9B 7 s.
  - **Fixed:** double `.xlsx` on downloaded Excel names; Idli no longer downloads when only asked to find.
  - **Laptop:** `fastembed` added to the cowork venv (eval only).
- **2026-11-08 (night), owner + DGX: finding files in Drive.** The owner's live run took ~5 min of substring
  searching before Idli asked anything. Now:
  - **Drive index** (`lib/driveindex.py`, tools `drive_index` / `drive_index_status` / `drive_find`), built by Idli
    on the laptop after the user says yes. It walks My Drive and Shared with me (10 levels, loop-safe, big folders
    scrolled to the end) with 5 tabs, reads the first rows of Sheets/Excel and the opening of Docs, and Muse
    writes a one-line summary per file, 4 at a time. Photos and videos: name, folder, date only. Stored in
    `~/idli-insights/config/drive-index.duckdb`. Real Drive (182 files, 19 folders): ~3.5 min.
  - **drive_find**: index search in ~0.3 s (names, folders, contents, modified dates, date words such as "in
    December"). With no clear match, one quick Drive full-text search on the rarest word, then ask the user.
    "bikapathymund cestrum datasheet": "no file mentions 'bikapathymund'; 'cestrum' is in field_vars_indicators.xlsx".
  - **Sidebar, top to bottom**: "Start here" (its own folder `~/idli-insights/start-here`, instructions from
    `idli/START-HERE.md`: greeting, sign-in, Drive index; tabs: the chat, Drive, Gmail), "Idli insights" (the
    private folder, where the work happens), "Teacher - Claude" (the Teach folder). Order set by dragging in the
    app. `setup-laptop.py` doesn't create the start-here folder yet.
  - **Providers** relabelled: "Idli - 30B (private, on Muse)", "Idli - 9B (OpenRouter, not private)",
    "Teach - Claude (fake data and test accounts only)" (backup `~/.paseo/config.json.bak-20261108-labels`).
  - **Workspaces** renamed "Idli - private" and "Teach - Claude"; old chats and two extra workspaces archived;
    leftovers from the form runs moved to `~/idli-insights/archive/cowork-real-20261108/`.
  - **Open**: photo location (EXIF) isn't visible in Drive's list; needs the details panel or the Drive API.
    Paseo always defaults new Claude-based chats to Auto mode, which blocks Idli's tools; pick Bypass.
- **2026-11-08 (evening), DGX: the file form is built and run end to end.** Details and results:
  [JOURNEY.md](../benchmarks/runs/2026-11-08-form-fill-eval/JOURNEY.md) and the model comparison in
  [README.md](../benchmarks/runs/2026-11-08-form-fill-eval/README.md).
  - **Code:** `lib/formkit.py` (form per tab, spec to SQL, lookups across tabs, contract test, date words),
    `lib/formserver.py` + `lib/form.html` (the page, 127.0.0.1 only, token per start), files site tools
    `file_get` / `file_open` / `file_ask` / `teach_file` / `teach_send` (file_check and file_answer are gone),
    teach-file skill writes the form format; `idli/CLAUDE.md` rewritten.
  - **Skills:** existing three gained labels, measures and rules; `field_programme_tracker` (3 tabs) taught v1 and
    re-taught v2 by the laptop's Teach chat.
  - **Laptop actions (done by the DGX):** `git pull`; `idli/CLAUDE.md` copied to `~/idli-insights/cowork-real/`;
    `~/.paseo/config.json` co-work providers also disallow `mcp__cowork__sheet_query` and `sheet_profile`
    (backup `config.json.bak-20261108-forms`). Paseo's download behaviour was set to "save without asking" over
    DevTools for testing and set back to default.
  - **Owner:** four stale Save dialogs on the laptop need Cancel. `~/Downloads/volunteer_register.xlsx` was
    replaced by a fresh export of the same sheet during the test.
  - **Moving code:** the laptop's `ssh` to the DGX hangs (Tailscale check?), so code moved through GitHub
    (declaude, force-with-lease) and laptop files came back as base64 through a Paseo terminal.
- **2026-11-08 (later), owner + DGX: downloads work, and the file flow becomes a form.**
  - **Correction:** Paseo's browser *does* download. Opening `…/spreadsheets/d/<id>/export?format=xlsx` shows a red
    `GUEST_VIEW_MANAGER_CALL … ERR_FAILED (-2)` line (cosmetic: the page load is cancelled because the response is a
    file), then the system "Save as" dialog. The owner saved the volunteer register to `~/idli-insights/testdata` on the
    laptop and it is intact (`Rs. 300` present). Paseo 0.15.2 has no `will-download` handler, so Electron falls back to
    the dialog. Idli can't click a system dialog, so automatic downloads still need a small Paseo change (save into the
    workspace folder, no dialog). Plugins can't do it: they run in the daemon and app UI, not the browser session.
  - **Decision (owner):** for single-file work, the model's role shrinks. Teach describes a file once (measures,
    groupings, date columns, business rules, checks, every tab). Idli then opens a **form** for that file: dropdowns
    tailored to its data, the schema problems, and the answer, all computed by code. The model finds files, talks, and
    fills the form from a typed question; it never writes SQL or numbers. A **contract test** runs before every query,
    and a changed schema asks for re-teaching. The entry point is "open the form for <link>". Next: compare a plain form,
    a classifier with a date parser, and 4B/9B/30B models on filling the form from vague questions.
- **2026-11-08, DGX: teach Idli a file.** New `files` site (file_open, file_check, file_answer, teach_file, teach_send),
  `lib/filekit.py`, the `teach-file` Claude skill, `idli/CLAUDE.md` (copied into `~/idli-insights/cowork-real/CLAUDE.md`), and
  `cowork.sites` gains `files`. Three file skills taught in human-style runs; results in
  [TEACH-FILE.md](../benchmarks/runs/2026-11-07-cowork-event-eval/TEACH-FILE.md).
  - **Laptop action:** `git pull` (done by the DGX). If you rebuild the laptop, `setup-laptop.py` now writes both.
  - **Open:** Google's sheet export blanks text in number columns; Idli warns but a real Drive download is still needed.
- **2026-11-07 20:xx, DGX: Muse latency fixes.** Claude Code's "hi" in a new chat re-read 18.6k tokens cold (~28-41 s).
  - **Muse** now runs with `--cache-ram 32768` (same flags otherwise; restarted with silo's `tg-bridge/serve_muse.sh`).
  - **Prefix proxy** `dgx/muse_prefix_proxy.py` on DGX `127.0.0.1:8185` (user service `muse-prefix-proxy`). It rewrites
    Claude Code's mid-conversation `system` message to user text, so Muse's template stops printing every tool twice.
    Prompt 18.6k -> 10.7k tokens; a new folder re-reads ~2.2k ("hi" ~4-6 s instead of ~28 s).
  - **T4GC Claude settings** add `autoMemoryEnabled: false`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` (the per-folder memory path
    sat before the tools and broke the cache for every new folder) and `CLAUDE_CODE_MAX_CONTEXT_TOKENS=65536` (Muse's slot size;
    Claude Code assumed 200k).
  - **Laptop action:** `git pull`; merge the three keys from `laptop/claude-t4gc-settings.json` into
    `~/idli-insights/config/claude-t4gc/settings.json`; `laptop-up.sh stop && laptop-up.sh` (its `-L 8181` now targets DGX 8185).
    Done by the DGX through a laptop terminal on 2026-11-07 (settings backed up as `settings.json.bak-20261107`).
  - **Co-work tool list trimmed** (`desktop/setup-laptop.py`, and merged into the laptop's `~/.paseo/config.json`):
    unused Claude Code built-ins (Workflow, Cron*, plan mode, worktrees, SendMessage, ...) are disallowed, and so is
    `gmail_draft_reply`, because co-work is read-only (find, suggest, download). Co-work prompt 17,180 -> 3,859 tokens;
    measured co-work "hi": cold prefill 4.3 s, warm ~6 s end to end including agent start.
- **2026-11-07 20:xx, DGX: `~/idli-insights` bootstrapped.** Moved the DGX's old `cowork/accounts.local.json` to `~/idli-insights/config/accounts.json` (chmod 600), so no `scp` was needed. If the laptop's copy has changed since, `scp` it over. Added [laptop-dgx-sync.md](laptop-dgx-sync.md). `lib/accounts.py` now resolves the new path. `check-from-dgx.sh`: ALL CHECKS PASSED (google 8/8, sheets 5/5) once the tunnel was back. The laptop had no workspace on the repo's `cowork/` folder, so the DGX created one ("DIY (cowork)") and started a one-line DIY chat in it.

- **2026-11-07 19:50, `~/idli-insights` and Paseo only.**
  - **What moved:**
    - Everything outside the repo now lives in `~/idli-insights` (layout in
      [driving-desktop.md](driving-desktop.md#idli-insights)).
    - The test-account file moved from `cowork/accounts.local.json` to `~/idli-insights/config/accounts.json`.
      `lib/accounts.py` still falls back to the old path.
    - The co-work workspace is now `~/idli-insights/cowork-real`.
    - The DIY sandbox blocks the private folders there.
    - T3 and AionUi are no longer maintained.
  - **DGX action:** do "Bootstrap the DGX" in driving-desktop.md. That means creating
    `~/idli-insights/config/accounts.json` (the owner copies it from the laptop) and deleting the old
    `cowork/accounts.local.json`. Then rerun `desktop/check-from-dgx.sh`.
  - **Also recorded:** Muse first-turn latency (cowork/README.md, "Findings"): about 16k prompt tokens (co-work)
    or 34k (full Claude Code) are re-read when the prompt cache is cold.
- **2026-11-07 18:xx, single DGX checkout.** The DGX agent moved to `~/src/github.com/bprashanth/io` (`7a8a140`).

## The idea in one paragraph

Idli is a Drive assistant for NGO staff. It uses Claude and a private model together to ask better questions of
their own data and to manage the data-entry work around it. Claude, working only on a copy with fake values,
establishes each file's structure, cleaning and validation rules (a "skill"). The private model runs those rules
on the real file and flags issues as comments in a working copy in the person's Drive, where they fix them. Once
the file is clean (or they choose to go ahead), Idli builds a **form** over it, so a small private model (Muse, or
a 9B) can hold a conversation about the data and answer from the form, never from its own arithmetic. The aim is
not a dashboard but discovering questions through conversation; the form is the scaffolding that keeps the
answers true. Charts follow the same pattern: question -> fake data -> Claude writes and agrees the chart code ->
Idli runs it on the real data locally. Everyone starts in **Start here** (index the Drive, re-index any time),
then works in **Idli**, one file at a time.

The earlier framing (DIY site plugins for websites, gap reports) still exists in the code but is not the focus.

## Read in this order

1. [cowork/README.md](../benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/README.md): layout, wiring, results table, findings, caveats.
2. [docs/driving-desktop.md](driving-desktop.md): how the DGX drives the laptop's Paseo (tunnel, CLI, DevTools, moving code), and how to recreate everything.
3. [docs/cowork-manual-test.md](cowork-manual-test.md): the owner's hand-test steps. Bugs they find come from here.
4. Chronology, oldest first:
   - [16:15 desktop UX + first Gmail/Drive tools](../chronology/2026-11-07T1615-laptop-desktop-ux-and-cowork.md)
   - [17:50 POC + gap loop + 9B](../chronology/2026-11-07T1750-laptop-cowork-diy-poc.md)
   - [18:30 handoff](../chronology/2026-11-07T1830-laptop-cowork-handoff-to-dgx.md)
5. Background, only if needed:
   - [field note](../narrative/2026-11-07-cowork-ui-as-api-field-note.md)
   - [laptop app guide](oss-desktop-laptop-testing.md)
   - [handing work between agents](agent-handoff.md), [laptop ↔ DGX sync](laptop-dgx-sync.md)

## Verify before anything else (DGX agent)

The owner starts the tunnel on the laptop (`desktop/laptop-up.sh`). Then, on the DGX:
```sh
cd ~/src/github.com/bprashanth/io && git pull
cd benchmarks/runs/2026-11-06-oss-desktop-independent/cowork
desktop/check-from-dgx.sh
```
Expect `ALL CHECKS PASSED`. Report each FAIL line to the owner with what you think the cause is. Then show
you control the app:
1. Run one co-work question on Muse with `paseo-remote.sh run` (an example is in driving-desktop.md).
2. Read its answer with `logs`.
3. Open its workspace and screenshot it with `drive.py`.
4. If the answer mentions a dashboard, click its **Open** button and screenshot the dashboard tab.

## What is verified (single runs, laptop, 2026-11-07)

- **Site tests:** `google` 8/8, `sheets` 5/5 against the test account and mock workbook. From the DGX, check them through the tunnel.
- **Muse 30B on co-work:**
  - Excel question: partly right, it mis-merged spelling variants.
  - Google Sheet question: right.
  - Gmail and Docs tasks: right in the earlier prototype.
- **The full gap loop, once:** Muse's `report_gap` → scrubbed → DIY (Claude Opus) built `gsheet_read` in 13 minutes → Muse correct in a new chat.
- **Dashboard Open button:** shows under the reply and opens the rendered page in a workspace-browser tab.
- **Qwen3.5-9B, via OpenRouter** (test data left the machine, by the owner's choice): Sheet ✅, Doc ✅ mostly, Excel half, AWS email ❌.
- **The DGX drives the laptop:** the CLI (`ls`, `provider ls`, terminal), DevTools screenshot and tabs list were all checked by hand before this handoff. `check-from-dgx.sh` passed on the DGX at handoff, after the agent-reload and workspace-focus fixes.

## Known bugs and rough edges (candidates when the owner asks for a fix)

| # | Bug | Where |
|---|---|---|
| 1 | The dashboard **Open** button opens a new workspace-browser tab but doesn't bring it to the front | `dashboard-links/server/open.ts` (uses daemon `browser_new_tab`; timeline rows get no `navigation.openBrowser`) |
| 2 | Each co-work run in a new workspace leaves Gmail/Drive tabs behind, so tabs pile up | `lib/browser.tab_for` |
| 3 | New browser tabs only open in the workspace the app is **showing**; elsewhere `browser_new_tab` times out ("open the browser pane"). Found at handoff. Workaround: `drive.py goto <wks>` first. A real fix might have the plugin or tools ask the app to show the workspace | `lib/browser.tab_for`, `dashboard-links` |
| 3b | The browser tools refuse closed (idle) caller agents with "Parent agent … not found". Workaround: `paseo agent reload <id>` | `run_tests.py`, `lib/browser.py` |
| 4 | Test runs rewrite `sites/*/site.json` (`last_test`), which dirties git | `run_tests.py` |
| 5 | Claude Code's Linux sandbox blocks 127.0.0.1:6767, so DIY ran outside the sandbox | `cowork/.claude/settings.json` |
| 6 | `report_gap` text written by the model can include personal names; the user must scrub it | `cowork_mcp.py` |
| 7 | `gsheet_read` can blank out a stray text cell in a mostly numeric column (gviz) | `sites/google/tools.py` |
| 8 | The bar-chart CSS was changed for narrow windows; the change hasn't been looked at | `sites/sheets/tools.py` `t_sheet_chart` |
| 9 | In a narrow Paseo window a browser tab can get a viewport wider than the visible pane (1280 px shown in 630), so the right edge of the dashboard and the skills page's Delete buttons are cut off. Widening the window helps | Paseo (patch P11) |
| 10 | Working copies pile up in Drive (one per "Mark them"); the index only knows the ones built before the last re-index, so `drive_find` can offer an old copy | `sites/files/tools.py` `t_working_copy`, `lib/driveindex.py` |
| 11 | A chat keeps the tool code it started with; after a `git pull` on the laptop, start a new Idli chat | `cowork_mcp.py` (one process per chat) |
| 12 | Muse often stops after writing text when a `then` asks for a card afterwards; cards that must happen go first, with the text inside the card | Idli tools' `then` strings |
| 13 | The form server restarts on the next Idli tool call; an open dashboard tab from before shows "connection refused" until then | `sites/files/tools.py` `_server` |

## Rules carried over from the owner

- Co-work never sends email and never edits documents. It drafts and suggests only. Don't add tools that send,
  delete, submit, pay or publish.
- No custom agent instructions (AGENTS.md and the like) as a workaround for UX gaps. Fix it in a plugin.
- DIY uses only test accounts and mock data, and works only in the cowork folder.
- The laptop has no disk space for models. Serve models on the DGX.
- Commits are `declaude`d before they go to GitHub. Pushing is the owner's call.
- Write a chronology entry before you stop (see agent-handoff.md).

### 2026-11-09, DGX: cards before switching views

When Idli wants the person somewhere else, it asks first with a yes/no card, and switches only on yes. Two places:
after "yes, index my Drive" ("Switch to the progress tab to watch it?"), and when teaching starts ("Opening Claude to
teach this file. Switch there now?"), with Claude asking "Go back to Idli?" when teaching is done. Switching to a
chat in another workspace uses Paseo's own deep link (`paseo://h/<server>/agent/<id>`, handed to the running app by
launching it again), so it works in a normal install. Browser tabs have no deep link, so the progress tab is
clicked through the DevTools port for now (dev only; Paseo patch P7). Measured on the 30B: card 23 s after
"rebuild index", yes brought the progress tab forward, and the chat carried on waiting for the index. The teaching
round trip is wired but not yet run end to end.

### 2026-11-09, DGX: fewer rounds between finding and analysing

- Found a file: the open-it card now carries a picture of its first rows (an SVG drawn from the index, kept in the
  private workspace folder). Muse reliably calls a card but often stops after writing a line before one, so the
  picture goes inside the card. "Yes" opens the file read-only in a tab here (`file_peek`).
- "Help me analyse X": no Save box (dev builds set each browser tab's download behaviour over DevTools; shipping
  needs patch P1), then for a file Idli hasn't been taught, one card instead of four rounds: send a copy with fake
  values to Claude and switch there, plus which label columns may go as they are. Measured on Muse: find to card
  20 s; analyse to the teach card 42 s (search, download, open, fake copy).
- Bugs found on the way: the find tool still said "download spreadsheets" (overrode the peek card); index reads
  with parameters failed silently (no previews); a short word covering the start of a longer one scored as a near
  match ("field" for "fieldvars"). Search check after the fixes: 23 of 25 right first with today's index, same as
  the vector index.

### 2026-11-09, DGX: from problems to fixes; gaps go to Claude and back

- A question the dashboard can't answer (here: sheet row numbers) now goes to Claude with a card, not a paste-in
  gap report: Idli sends the fake copy plus what was missing, switches to Claude, Claude extends the skill (one
  card: "add row numbers"), and on "back to Idli" the watcher outside Claude's sandbox switches the app and Idli
  reruns the question. Ran end to end on Muse + Claude.
- Problems became fixes. Each problem has its real cell (blank rows and columns count, as in the sheet), and
  either a suggested fix (approx 12 -> 12, "pending" -> blank, a date in another format, a code one typo away
  from the list) or a note saying what a person must check. Accept/reject per fix in the dashboard; "Save fix
  list" writes the list and a fixed copy of the original with each changed cell commented. The checked copy has
  a comment on every problem cell. Nothing is written to the person's Drive.
- Layout: rows that repeat the headings are skipped (49 in the cestrum file, which had 439 problems; now 196),
  sub-headings and totals rows are suggested skips, and Claude sees them in the fake copy and discusses them in
  teach mode (skip, or a cleaner layout for their next version; their choice). A code missing from the list that
  recurs (UKS1, Fern) gets "add it to the list if your team uses it" rather than a typo guess.
- Not done: links straight to a cell in Google (needs each tab's id; clicking tabs to read them was unreliable),
  and comments on the live Google Sheet (a write; the person's call).
- Working copy in Drive (2026-11-09). After file_get the card offers "Mark them in a Drive copy". On yes, Idli builds a copy of the original with live red highlights (conditional formatting from the same checks, so a cell clears when fixed), one comment per kind of problem on its first cell (Google imports them as real comments, counted on each tab), grey skipped rows and an "Idli checks" tab, then drops it onto the original's Drive folder in a tab (DevTools drag-drop; Paseo patch P9) and opens it. The cestrum file: 196 problems -> 15 kinds, 17 comments. "I'm ready" downloads the copy, drops the checks tab, re-checks and answers from the copy (317 Cestrum trees, 48 s). The only Drive write, a new file, after a yes.
- Muse latency: the minute+ was mostly reasoning over two contradictions in Idli's instructions (link vs drive_find; "say say_to_user" vs "write nothing before the card"), 1,285 tokens in one step. Fixed, and file_get now opens the form itself (one turn fewer): link -> card 44 s, steps think 160-560 tokens. What's left: re-prefills and tool time (optimizations 7, 8).
