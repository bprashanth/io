# Stage ledger

Each stage below is a solidified layer of the event stack. Later stages add to
earlier ones; they never replace their evidence. A stage record states what
was decided, what the evidence is, and what was explicitly left open, so that a
later agent can extend the stack without re-deriving or silently overwriting a
prior result. The local, gitignored `checkpoint/` directory mirrors these with
machine-specific operational notes.

| Stage | Question | Outcome | Record |
|---|---|---|---|
| 1 | Can VS Code/Cline + Qwen 3.8 27B match Antigravity for NGO dashboards? | Qwen is the capable open model; Cline is not the event shell. | [stage-1](stage-1-cline-vs-antigravity.md) |
| 2 | Can a local SQL ladder (Arctic 7B → router → Qwen 27B → DuckDB) replace an agent? | Model ranking holds; router and "30/30" do not; Arctic adds nothing over a 2026 9B; schema-only frontier closes the dashboard gap. | [stage-2](stage-2-local-first-ladder.md) |
| 3 | Can stock Antigravity be used on beneficiary data without the data leaving the laptop? | Yes: the privacy-shield extension (local GLiNER + vault proxy), verified in the real IDE. | [stage-3](stage-3-privacy-shield.md) |

The final event stack is a combination: Antigravity (Part 3) with the shield
for private files; the local/DGX model tiers and DuckDB calculation (stage 2)
for the custom Part 4 build; the product requirements learned in stage 1.
