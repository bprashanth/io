# io — custom app for Insight Out

## Event plan

Message sent to participants:

```
Agenda
There are four parts to the day of.

Part 1: Where are we with AI?
Casual conversations around where AI is today, what excites you, what worries
you, and what it could mean for the work we do.

Part 2: Talking to AI
We all use AI for answers. In this session, we'll explore how to talk to AI
better and get more useful responses for our own work.

Part 3: Insight Out
You bring the data, you handle the keyboard. We'll show you how AI can help
you turn your data into charts and dashboards, and make your insights easier
to understand and use.

Part 4: Outside In
Mainstream AI wasn't built for the social sector, and we want to recognise
that. For this section, we've cooked up some slightly wild, definitely
unpolished experiments to try with you. While the first three sections are
interactive demos, this one is about participatory creation.
```

Part 3 runs Antigravity at full power on non-sensitive work (proposal bank,
reconciliation, cleaning a messy sheet), then reveals the privacy plugin
([pii_antigravity](pii_antigravity.md)) as the bridge: "you just watched a
frontier agent work — here is what it saw." Part 4 is the same terse-question
→ dashboard conversation on beneficiary-shaped data, inside **io**, our own
app, where the participant can *see* what left the laptop and *choose* who
answers.

## The product in one breath

Private by default. Auditable on demand. Power by consent. Numbers come from
execution, never from imagination. Creativity is outsourced; custody never is.

## Design: two axes, not one mode

The earlier open-ended questions ("sheltered per file or per session?",
"insights flow vs generic app building?", "art mode vs correctness mode?")
resolve into two independent axes.

### Axis 1 — Reach (a consent dial: who is allowed to help)

Set per session, overridable per file. Framed as what you *gain*, not what
you fear — "allow escalations for better art."

| Reach | Who sees anything | What leaves the laptop | What you get |
|---|---|---|---|
| **T0: Laptop** | SLM on laptop (for event it will be openrouter) | nothing | correct tables, patterns, joins, basic charts |
| **T1: T4GC** | Qwen 27B on the t4gc DGX (for event it will be openrouter) | schema + tokens | better query understanding, decent dashboards; data stays in sector custody |
| **T2: Frontier** | Gemini/etc. via OpenRouter | schema + tokens + ≤20 tokenised sample rows | the pretty stuff — Antigravity-class pages |

T0 honesty rule: at T0 the local model writes **SQL only**. Charting is
deterministic auto-viz (time×numeric → line, categorical×numeric → bar,
Observable-Plot-style defaults). We do not ask a 9B to design dashboards;
we ask it to do the one thing small models do reliably. If the user wants
better art, the dial — not the model — is the upgrade path.

*Measured 2026-08-23 (stage 4):* T0 = **Qwen 3.5 9B** for both lanes. In the
Build lane the 9B does not write pages; it returns a *plan* (panels with SQL
and a narrative of `{{receipt}}` placeholders) and the laptop renders it —
83/89 panels executable on a 12-request gate, best of every laptop-sized
model, 0 typed numbers. Ask: suite 25/30, holdout 23/30, anchor 16/30; the
laptop compensates deterministically (typed dates, spelling-normalised join
columns, topic-switch rule, chart guards, 0–100 plausibility flag). What it
cannot do without the dial: unstated sign/unit conventions, aggregation
level, reaching for a file the question does not name. Evidence and tables:
`docs/stages/stage-4-t0-model-and-io-desktop.md`. Shim: `app/io-desktop/`.

### Axis 2 — Lane (routed by intent, not toggled)

- **Ask lane** — question → SQL → DuckDB runs locally → dashboard/table.
  Deterministic, receipted, the Part 4 default.
- **Build lane** — "build me an app for this" → goes to the tier the dial
  allows. The model never gets rows in its prompt; it gets a **contract**:
  data will be available at runtime via `window.data` / duckdb-wasm over
  these columns. The laptop pours real data in when the page runs.

Both lanes obey the same dial and the same guard. This is how generic app
building escapes the "DuckDB shackle" without escaping the privacy model:
**DuckDB is not the product, it is the data plane.** A bird-photo app and a
child-fitness dashboard are the same architecture — frontier writes arbitrary
pages, the laptop remains the only place data lives.

## Sheltered by default, review is lazy

Point io at a folder. Everything in it is **sheltered by definition** — OPEN
is the explicit opt-out per file ("this file's rows may leave"), used rarely.
The PII scan (3–8 s/file, CPU) runs in the background and badges files; the
**review sheet appears only when a query first touches a file**, not as an
upfront interrogation:

- flagged columns tinted, reason beside each ("12-digit unique numbers",
  "names under header `col_17`"); tick/untick; *Looks right* / *Just do it*
  (skips review from then on). Remembered by file hash.
- text files: side-by-side redacted preview on first touch; too long to
  glance at → refused in sheltered mode, or handed to the trusted 27B with
  explicit consent.

The real cost of sheltering everything is small and known: the first-touch
scan, and the remote model losing semantic hooks (it can't reason
"PLACE_040 is coastal" the way it could with "Ratnagiri"). All heavy compute
on real values is local anyway. The default state *is* the privacy claim.

## Receipts: the model never says a number

Protocol rule, not a feature: models emit SQL (or page templates), never
numeric claims. Every figure on screen exists because the laptop executed a
query.

- io keeps a manifest: `panel_id → {sql, rowcount, result_hash, tier,
  timestamp}`. Generated templates must tag elements `data-receipt="q7"` —
  that is the entire indexing scheme.
- Default screen stays clean. One gesture (audit view / ⓘ) overlays each
  panel with its query and offers **re-run & diff** — recompute now, flag
  drift.
- **Numeric-literal lint** (the BS detector): scan generated output for
  numbers that don't trace to a query result. A hardcoded figure = the model
  made it up = auto-flag and regenerate. Turns "is the 9B lying" from a
  suspicion into a lint error.
- Provenance attaches to *numbers*, not pixels. Prose, layout, and Build-lane
  art carry no receipts — that is the honest resolution of "art vs society":
  it's per-figure, not per-mode.

## Egress monitor (the centrepiece)

Always-visible panel, adapted from the shield plugin's existing view — the
interceptor becomes a shared library with two frontends (Antigravity plugin,
io native), same code, same egress log. Per outbound request: tier, bytes,
and a checklist — column names: yes; rows: 0 / 20 sample (tokenised) / all;
real names/phones/IDs: 0 (guard asserted). Guard hit = blocked call = red
state, friendly message. Readable from a projector at the back of the room.

## The app, screen by screen

1. **Point at a folder.** Only files in it are readable. Background scan
   badges each file *sheltered* (default) or lets the user flip one to
   *open*.
2. **Ask box + the dial.** Plain question box; reach dial low/medium/high
   (T0/T1/T2). Questions are redacted through the vault before leaving;
   ambiguous names trigger "which Santosh?" locally.
3. **Review sheet** — appears lazily, first time a query touches a file
   (as above).
4. **Egress monitor** — always visible (as above).
5. **Dashboard / table**, rendered locally. Ask lane: receipted panels,
   audit view, re-run & diff. Download yields the real, rehydrated table.
   Live pages embed duckdb-wasm where the demo calls for it, so an edit to
   the underlying sheet re-ranks the visual with no remote call.
6. **Follow-ups** keep the vault; the dashboard updates in place. "I don't
   understand, you figure it out" = escalate one tier (within the dial's
   permission) + replan; breakage unsurfaced.

## Anchor demos (synthetic mirrors only — never rehearse on real data)

1. **Sportathon** (child fitness, multi-location): the flagship sheltered
   run — minors' PII, egress monitor showing rows: 0, T2 dashboard.
2. **Foundation Without** (30-household vulnerability ranking): the live
   one — duckdb-wasm page; edit a value in the sheet, watch the ranking
   reorder locally. Rudra's ask, verbatim.
3. **Lila Poonawalla** (cross-file applicant reconciliation): the
   correctness one — fuzzy name-matching runs *locally* on real strings
   (DuckDB `jaro_winkler`); the model only writes the matching strategy over
   schema + tokens. Output is a discrepancy table + counts, not charts.
   Note for the room: tokenisation would break fuzzy matching if it ran
   remotely (Shamik/Shameek → different tokens) — it works *because* the
   architecture keeps matching local.

## Building blocks that already exist and measured well

| Block | Measured | Where |
|---|---|---|
| Column-level PII finder: rules + 181 MB GLiNER, CPU only | 33/33 private columns on four synthetic NGO tables, 1 false alarm, 3–8 s/file | `benchmarks/pii/columns.py` |
| Free-text redactor (chat exports, reports) | 93–100 % of private spans; over-redacts | `benchmarks/pii/detect.py` (`textv2`) |
| Trusted-server redactor (Qwen 3.5 27B) for text the laptop can't do | 100 %/100 %, ~2 min per 15 KB | same, `llm:` engine |
| Reversible token vault (`NAME_146`, `PLACE_040`), follow-up resolution, "which Santosh?" | 4-turn demo, no leak | `benchmarks/pii/pseudonymize.py`, `sheltered_query_demo.py` |
| Remote model writes SQL over tokens; DuckDB runs it locally | Qwen 3.5 27B no-think: 29/30 on the realistic holdout, ~3 s/query | `benchmarks/scripts/run_v2_query_gate.py --prompt-style shell` |
| Remote model writes a blind HTML template from schema (+ optional tokenised 20-row sample); laptop injects rows | Gemini 3.7 Flash: Antigravity-class page, all figures correct, ~$0.02, 0 rows sent | `benchmarks/pii/remote_dashboard.py` |

## What it deliberately does not do

- No open-ended coding agent in the Ask lane. The model returns SQL or a
  template; the laptop computes. This is why the numbers are right and why
  nothing leaks. (The Build lane exists, but it is data-blind by contract.)
- No k-anonymity. Direct identifiers are hidden; age + village + school can
  still identify a child. Say so on screen — "redacted on your machine",
  never "anonymised".
- No Devanagari/transliteration matching yet.
- T0 does not pretend: no LLM-designed dashboards from a 9B, no over-claiming
  local capability. Basic and correct beats pretty and wrong.

## Order of work

1. ~~Pick the SLM (9b, sql model.. whatever) - must work well for ask lane and decently (even if its determistic) for the build lane; time the T0/T1 tiers.~~ **Done 2026-08-23:** Qwen 3.5 9B (T0), Qwen 3.5 27B (T1); T0 timings ~2 s hosted, ~30 s first / ~15 s follow-up on an 8 GB-class CPU; see stage 4.
   1b. Test `app/io-desktop` on the laptop (install.sh, key or local llama.cpp); decide whether T0 at the event is the hosted 9B or Qwen 3.6 35B-A3B under a different tier name.
2. ~~Extract the shield interceptor into the shared library; wire the
   Antigravity plugin and io to it.~~ **Done differently 2026-08-24:** the vault
   (classifier + pseudonym map + consistency pass + leak gate) is `app/io-desktop/server/shelter.py`,
   feeding the io **open lane** — Antigravity-free building with the shield built in; verified
   against the stage-3 reference numbers (`chronology/2026-08-24T1200-…`). The Antigravity plugin
   keeps its own copy for now (backlog: one shared egress chokepoint).
3. Build io as one local service with the six screens (Python + local web
   page is enough for the event): dial, lazy review, vault, guard, monitor.
4. Receipts manifest + audit view + numeric-literal lint; T0 deterministic
   auto-viz.
5. Build-lane contract (`window.data` / duckdb-wasm injection) + the three
   synthetic mirrors; FW demo on duckdb-wasm.
6. Rehearse with 20 concurrent sessions against the DGX; low-RAM timing
   under a hard 8 GB cap.

