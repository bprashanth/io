# Handoff for Codex: Idli experiments (2026-11-11)

You are running experiments on **Idli**, a Drive helper for people at NGOs. It helps them clean a spreadsheet and
ask questions of it, while their data stays on their machine. This page is everything you need to start. Read it
whole before touching anything.

## 1. What Idli is (2 minutes)
- **One file at a time.** The person pastes a Google Sheets link.
- **Learning:** Claude learns the file from a **fake copy** (same shape, fake values; `lib/filekit.py`). It writes
  a "skill" for it: checks, clean-ups, and a **form** (measures, breakdowns and filters the private model can ask
  for).
- **Checks** run locally on the real file.
- **The private model** answers questions only by filling the form (`file_ask`); code computes every number. Two
  models:
  - the **local 9B** (Qwen3.5-9B; the free tier, and the subject of the evals);
  - **Muse 30B** (the baseline).
- **The bounce:** when the form can't answer or draw something, Idli sends Claude a fresh fake copy plus the
  question. Claude extends the form or writes chart code, and Idli runs it on the real data in a sandbox.
- **Cards:** clickable questions in the chat. Every decision point is a card.

**Full background**, only if you need it: `docs/idli-handoff.md`, and the chronology `docs/cowork-poc.md`
("What changed", newest first).

## 2. What changed today (2026-11-11): your experiments must use this
These are on branch `oss-desktop-eval`, up to commit `6b545170`. The chronology entries are dated 2026-11-11.
1. **Upload card.** `file_open` on a file with problems and no checked copy (for its skill version):
   "Upload a checked copy to your Drive so you can fix them?" → "Yes, upload a checked copy (Recommended)" /
   "No, analyse the original".
2. **Continue card.** After the upload, `working_copy` returns "…Fix what you think matters there. Continue with
   analysis?" → "Continue with analysis" / "Not yet". On Continue, `working_copy_ready` downloads the copy from
   Drive again (the person's fixes). It reports what was fixed and what's new.
3. **A file that already has a copy:** "Use the checked copy (Recommended)" / "Use the original".
4. **Charts never drop or merge rows.** Chart code may not `drop_duplicates`, remove outliers or merge spellings
   (teach-file skill). Rows with problems are drawn as they are, and `chart_show` points at the checked copy.
5. **The owner's decisions:**
   - flag messy values (e.g. "cancel" vs "Cancelled", "12 cm") through the checks; don't special-case them;
   - hold `IDLI_MOCK_V2` (the fixed fake copy) for one more E2 run;
   - "measures vs charts" is still open.

**Consequence for the harnesses:** the 9B harness's fake Drive (`benchmarks/runs/2026-11-10-idli-9b/harness/idli.py`,
`_drive()`) writes a `.source.json` with an id. So **the upload card will now appear** at the start of scripted
chats on files with problems. Existing scenarios don't expect it. Handle it in the harness (section 5, E3 step 2),
not by editing the product.

## 3. Rules (non-negotiable)
- **Never touch `~/.codex`.** Never print, copy or commit credentials:
  - `~/.config/idlisseus/*.json` (OpenRouter key, silo token);
  - `~/idli-insights/config/*`.
- **Synthetic data only.** The planted-mess fixtures are in
  `benchmarks/runs/2026-11-10-idli-pipeline-eval/fixtures/`. Don't use the owner's real files. Claude only ever sees
  fake copies; keep it that way.
- **One worktree and branch per experiment,** your own benchmark folder, no edits to shared code:
  ```sh
  cd ~/src/github.com/bprashanth/io
  git worktree add ../io-<name> -b exp/<name> oss-desktop-eval
  cd ../io-<name>
  ```
  - Results go only in `benchmarks/runs/2026-11-12-<name>/` (PLAN.md, scripts, results, REPORT.md).
  - Reuse other harnesses by importing or copying them; don't edit them in place.
  - Product code (`benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/{lib,sites,idli}`) changes only
    behind an env switch that's off by default, in its own small commit.
  - Don't edit `docs/`, `todos/` or `narrative/`. Put the chronology line and todo changes under "For the
    integrator" at the end of your REPORT.md.
- **Machine:**
  - Use `IDLI_HOME`/`COWORK_DATA_DIR` folders inside your benchmark dir, never `~/idli-insights`.
  - **GPU:** follow `benchmarks/runs/GPU_COORDINATION.md`. The local 9B starts with
    `benchmarks/runs/2026-11-10-idli-pipeline-eval/harness/serve9b.sh up` (port 8291; it refuses below 40 GB
    free). Stop it when you're done (`serve9b.sh down`).
  - **Muse** (container `idli-muse`) is shared: you're a client only. Never stop or restart it. Run its chats one at
    a time.
  - No `pkill -f`: scan `/proc` instead. Pick unused ports. Name containers `exp-<name>-*`.
  - Don't drive the owner's laptop.
- **Long runs:** `nohup <script> > <log> 2>&1 &`, then check the log with short commands. Commit often.
- **Don't push.** The integrating agent pushes after `declaude`.
- **Benchmarks:** no per-question hacks to raise a score; fix the flow. Fresh chats (held3) are the judge.
- **Write the report plainly,** with tables, surprises, what wasn't measured, cost and time, and decisions for
  the owner.

## 4. Where things are
- **The product:** `benchmarks/runs/2026-11-06-oss-desktop-independent/cowork/`.
  - Tools: `sites/files/tools.py` (`file_get`, `file_open`, `file_ask`, `chart_request`, `chart_show`,
    `teach_file`, `teach_send`, `working_copy`, `working_copy_ready`, …).
  - Libraries: `lib/` (`filekit`, `formkit`, `chartkit`, `workcopy`).
  - Idli's instructions: `idli/CLAUDE.md`. The teach skill: `.claude/skills/teach-file/SKILL.md`.
  - Tests: `PYTHONPATH=. .venv/bin/python lib/test_formkit.py` (and `test_fixkit.py`).
- **The pipeline eval** (E1-E3 done; read its REPORT.md first): branch `idli-pipeline-eval`, folder
  `benchmarks/runs/2026-11-10-idli-pipeline-eval/` (call it E/). Its worktree is
  `.claude/worktrees/agent-aaf212a4b5f290bbe`.
  - `E/PLAN.md`: every planned eval.
  - `E/REPORT.md`: E6, E7, E1, E2 and E3 results, and the open decisions.
  - Teaching headless: `E/harness/teach_run.py` (Claude Code with the teach-file skill; Haiku answers the cards
    from `fixtures/<stem>.doc.md`).
  - E3: `E/harness/e3_bounce.py` (one chat), `e3_all.sh` (batch), `e3_rescore.py` (strict scoring: reruns chart
    code on the real fixture), `e3_refcheck.py`.
    - The corrected expected answers are in `E/results/e3/refcheck.md`: 6 of 9 original refs were wrong.
    - Chats: `E/scenarios/e3.json`.
  - E7 chat runner: `E/harness/e7_*`, variant `E/variants/e7-soft12` (12 tools, soft phases).
- **The 9B chat harness:** `benchmarks/runs/2026-11-10-idli-9b/harness/{convo.py,idli.py,run.py,score.py}`.
  - **Gotcha:** `idli.setup()` does `os.chdir` into a temp home, so pass absolute paths for outputs.
  - `teach_run.py` caps each Claude API call at 5 minutes (`API_TIMEOUT_MS=300000`).
- **The baseline numbers to beat** (`E/REPORT.md`):
  - E7 soft phases on held3: 9B 86%, Muse 86%.
  - E3, the trip to Claude and back: sent 23/24, back 22/23, 0 wrong bounces, about a minute and $0.15 a trip. But
    only 12/24 trips gave exactly right numbers on the real file.

## 5. Experiments to run (in this order; each its own worktree/branch/folder)

### E3b: rerun E3 on today's product (first)
**Question:** with the no-drop rule, the cards and the corrected refs, how many trips give exactly right numbers?
1. Merge `idli-pipeline-eval` into your branch, or copy E/'s harness and scenarios into your folder.
2. **Make the harness handle today's cards.** The scripted user answers:
   - the upload card with **"No, analyse the original"** in run A;
   - with **"Yes, upload a checked copy"** in run B: stub `working_copy` as the harness stubs Drive. "Upload" means
     writing the checked copy into the fake Drive; then answer **"Continue with analysis"**.
   - Implement both answers in `convo.py`'s scripted-card path, or in your copy of it, not as per-scenario steps.
3. Score with `e3_rescore.py` against the **corrected refs** (`E/results/e3/refcheck.md`).
   - Accept ≥ or > for "clear 70%".
   - Count "readable value split into its own bar" separately, as E3 did.
   - Count **rows dropped by chart code**: it should now be 0.
4. Runs: 9 chats × (9B ×2, Muse ×1) for A; 9B ×1 for B.
5. Report:
   - **Main table:** routed, sent, Claude finished, came back, exactly right, split values, rows dropped, minutes
     and $ per trip.
   - **Then A vs B,** and the comparison with E3's table.
   - **Note the measures-vs-charts behaviour:** how often the 9B chose `chart_request` vs `teach_file` for a
     number question. That's input for the owner's open decision.

### E2b: one more E2 run on the fixed fake copy (`IDLI_MOCK_V2=1`) (second)
**Question:** does the fixed fake copy keep its gain (90% found) without doubling false alarms (35 vs 20)?
- Rerun E2's teaching on the 5 fixtures with `IDLI_MOCK_V2=1`, twice. Score as `E/results/e2-logs/table.txt` does.
- Report per file, with the tax file separately (14 of the 35 false alarms were there).
- **Recommend:** ship `IDLI_MOCK_V2`, or not.

### E4: wording the answer (third; see `E/PLAN.md` E4)
**Question:** does the 9B's rewording lose or invent numbers?
- Use oracle dials, so only the wording varies, and compare:
  - (A) the code template shown as is, plus at most one line from the model;
  - (B) today's rewording;
  - (C) a friendlier code template.
- Score: numbers lost, numbers invented, a UX grade.
- **Note:** `../io-answer-mock` (branch `exp/answer-mock`) has already benchmarked "trusted answer rendering".
  Read its report first and build on it rather than repeat it.

### E5: charts from fake to real (optional; E3b covers much of it)
- Only if E3b leaves chart failures that aren't about messy rows.
- Run 10 chart requests on the fixtures: Claude writes the code on the fake copy, and it runs on the real data.
- Score: runs; shows what was asked; every number traces to the data.

## 6. When you finish each experiment
- **`REPORT.md` in your folder, ending with:**
  - "For the integrator": one chronology line, plus new or changed todos;
  - "For the owner to decide".
- **Commit on your branch** with a clear message. Don't push.
- **Stop the 9B server.** Leave Muse running.
- **Tell the owner** the branch, the last commit and the one-paragraph result.
