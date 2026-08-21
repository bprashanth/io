# Custom Idli app for insight out 

## IO Event plan

This is the message sent out to the event participants 

```
Agenda
There are four parts to the day of. 

Part 1: Where are we with AI?
Casual conversations around where AI is today, what excites you, what worries you, and what it could mean for the work we do.

Part 2: Talking to AI
We all use AI for answers. In this session, we’ll explore how to talk to AI better and get more useful responses for our own work.

Part 3: Insight Out
You bring the data, you handle the keyboard. We’ll show you how AI can help you turn your data into charts and dashboards, and make your insights easier to understand and use.

Part 4: Outside In
Mainstream AI wasn’t built for the social sector, and we want to recognise that. For this section, we’ve cooked up some slightly wild, definitely unpolished experiments to try with you. While the first three sections are interactive demos, this one is about participatory creation.
```

So the antigravity integration mentioned in [pii_antigravity](pii_antigravity.md) is for Part 3. We will use that as a bridge into Part 4. 
Part 4 itself needs a custom build.

## Custom build

1. Antigravity at full power on non-sensitive work. Run their actual non-beneficiary problems: the proposal bank, the reconciliation task, cleaning a messy sheet. This shows mainstream AI's ceiling and covers the open-ended half of their wishes without you building anything.
    - then show them the antigravit privacy plugin
2. Part 4 = same conversation, flip the switch. Identical terse-question -> dashboard interaction, but now with beneficiary-shaped data, and.. an egress monitor on screen: a small panel showing what actually left the laptop (schema: yes; column names: yes; rows: 0/pii 0 or whatever the case may be - not sure about the exact nature of this or whether it adds value, just an idea of the kind of thing we'd want to showcase). That single widget answers "where is the data centre" by showing the wire.
3. Per-file marking, not per-session. On ingest, a PII flagger spots name/phone/age columns and asks "mask these?" — a file marked sheltered forces the local path for anything touching it, while the same session can do open-mode work on other files. Ekibeki needs both in one afternoon. - not sure what exactly this translates to or if we shoudl just keep it as a SHELTERED mode vs per file? 
4. Receipts for the accuracy fear. Every chart gets a flip side: the SQL that produced it + row counts. You already save query.sql per panel in the harness — just expose it as "how was this computed." Directly answers the misinterpretation concern, costs nothing.
5. This is probably the most important one - a review filter for privacy. "looks like this file has pii" or in sheltered mode for every file show a picker saying "auto redacted, piont and click at more redcations / columns". 

These are just some ideas of what the custom build can showcase. 

## Part 4 proposal (appended 2026-08-21 after the sheltered-mode measurements)

Evidence: `docs/sheltered-mode-feasibility-2026-08-21.md`,
`docs/foundation-reverification-2026-08-21.md`,
`chronology/2026-08-21T2345-antigravity-proxy-interception-probe.md`.

### What Part 4 is

The same "terse question -> dashboard" conversation as Part 3, on
beneficiary-shaped data, inside our own small app instead of Antigravity. The
point is not a better dashboard; it is that the participant can *see* what
left the laptop and choose who answers.

### Building blocks that already exist and measured well

| Block | Measured | Where |
|---|---|---|
| Column-level PII finder: rules + 181 MB GLiNER, CPU only | 33/33 private columns on four synthetic NGO tables, 1 false alarm, 3-8 s/file | `benchmarks/pii/columns.py` |
| Free-text redactor (chat exports, reports) | 93-100 % of private spans; over-redacts | `benchmarks/pii/detect.py` (`textv2`) |
| Trusted-server redactor (Qwen 3.5 27B) for text the laptop can't do | 100 %/100 %, ~2 min per 15 KB | same, `llm:` engine |
| Reversible token vault (`NAME_146`, `PLACE_040`), follow-up resolution, "which Santosh?" | 4-turn demo, no leak | `benchmarks/pii/pseudonymize.py`, `sheltered_query_demo.py` |
| Remote model writes SQL over tokens; DuckDB runs it locally | Qwen 3.5 27B no-think: 29/30 on the realistic holdout, ~3 s/query | `benchmarks/scripts/run_v2_query_gate.py --prompt-style shell` |
| Remote model writes a blind HTML template from schema (+ optional tokenised 20-row sample); laptop injects rows | Gemini 3.7 Flash: Antigravity-class page, all figures correct, ~$0.02, 0 rows sent | `benchmarks/pii/remote_dashboard.py` |

### The app, screen by screen

1. **Point at a folder.** Only files in it are readable. Each file gets a
   badge: *open* or *sheltered*. Sheltered is the default when the PII finder
   flags anything.
2. **Review sheet** (first time a file is seen, keyed by file hash). The sheet
   is shown with flagged columns tinted and the reason beside each ("12-digit
   unique numbers", "names under header `col_17`"). Tick/untick. Two buttons:
   *Looks right* and *Just do it* (skips review from now on). For text files: a
   side-by-side redacted preview; files too long to glance at are refused in
   sheltered mode or handed to the trusted 27B with explicit consent.
3. **Ask.** Plain question box plus a model picker: **low** (9B, local or
   DGX) / **medium** (Qwen 27B on the DGX) / **high** (frontier via
   OpenRouter). The question itself is redacted through the vault before it
   leaves; ambiguous names trigger a "which one?" prompt.
4. **Egress monitor** (always visible, the centrepiece). A small panel with
   the last request that left the laptop: model, bytes, and a checklist —
   column names: yes; row count: 0 / 20 sample (tokenised) / all; real
   names/phones/IDs: 0 (guard asserted). The guard is the leak assertion that
   already runs on every outbound payload.
5. **Dashboard** rendered locally from the template; every panel has a flip
   side showing the SQL that produced it and the row count ("how was this
   computed"). Download gives the real, rehydrated table.
6. **Follow-ups** keep the vault; the dashboard updates in place.

### What it deliberately does not do

- No open-ended coding agent. The model returns SQL or a page template; the
  laptop computes. This is why the numbers are right and why nothing leaks.
- No k-anonymity. Direct identifiers are hidden; age + village + school can
  still identify a child. Say so on the screen.
- No Devanagari/transliteration matching yet.

### Order of work

1. Second unseen PII corpus; re-measure without touching rules.
2. Serve a 9B and a 27B on the DGX; time the low/medium tiers.
3. Wire the existing scripts into one local service with the six screens
   above (Python + a local web page is enough for the event).
4. Rehearse with 20 concurrent sessions against the DGX.
