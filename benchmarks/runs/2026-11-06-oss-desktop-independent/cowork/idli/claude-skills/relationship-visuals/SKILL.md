---
name: relationship-visuals
description: Choose varied, readable relationship charts when comparing or linking NGO spreadsheets, groups, households, loans, visits, and trainings. Prepare a CSV and Vega-Lite spec for Idli after chart consent.
---

# Relationship visuals for masked Claude

Use this when a question links entities, events, or measures across sheets. Choose the
chart from the question, not from the first numeric column. A chart should convey one
message; split unrelated messages into separate answers.

## Work within the masked workflow

Follow `CLAUDE.md`: offer the proposed chart in one short sentence and wait for the
person's consent before computing its CSV or calling `idli_show`. An explicit request
to draw a chart is consent for that chart. Do not show unsolicited charts.

Names and places may be stable codes such as `PLACE_003` and `VALUE_012`. Preserve
them exactly, including in joins and labels; never infer or substitute real names.
Read `drive/` without modifying it. Save computed scripts, CSVs, and specs in this
work folder. Use neutral column names; codes belong in cell values.

Before joining, identify each sheet's row grain and primary/foreign keys. Check key
uniqueness, missing keys, unmatched rows, and join cardinality (pandas `validate=`).
Aggregate each one-to-many fact sheet separately before combining measures: joining
raw repayments to raw visits multiplies both counts. Report source files, sheets,
columns, rows read, and rows omitted for blanks or unmatched keys.

Clean observed whitespace/case/date/rupee variations explicitly; preserve the raw
inputs. Do not normalize opaque codes or invent missing values. Blank paid amounts
are unknown, not zero. For repayment share, use sum of known paid amounts divided by
sum of their corresponding dues; report excluded installments. For attendance, use
the known count divided by eligible members, distinguishing a missed session (zero)
from an unknown count (blank). Missing future cohort periods are absent, not zero.
State comparison windows, units, and denominators. A change after an event shows
sequence/association; it cannot establish that the event caused the change.

## Pick a visual deliberately

Track the last chart family shown in this conversation. **Never use the same chart
type twice in a row unless the person asks for it.** A different colour, orientation,
or mark inside the same composition does not make a new family. If the best choice
repeats, choose a suitable alternative below or offer a table/text answer. Resetting
the CSV does not reset the previous chart choice.

| Question shape | Chart family and template | Required CSV fields | Useful alternative |
| --- | --- | --- | --- |
| Which entities connect across two categories; where are the concentrations? | [Join matrix](.claude/skills/relationship-visuals/templates/matrix.vl.json) | `ward`, `officer`, `households` | Layered bars for fewer categories |
| Who has the most linked entities, compared with a reference? | [Ranked dots with links to a reference](.claude/skills/relationship-visuals/templates/ranked-dot.vl.json) | `officer`, `households`, `capacity`, `visited`, `unvisited` | Matrix by ward and officer |
| Does a relationship evolve differently for each group? | [Small multiples](.claude/skills/relationship-visuals/templates/small-multiples.vl.json) | `group`, `month`, `repayment_rate` | Slope for two specified windows |
| Which events precede/follow an outcome for one entity? | [Event strip](.claude/skills/relationship-visuals/templates/event-strip.vl.json) | `date`, `lane`, `outcome`, `details` | Small multiples for several entities |
| Which groups changed between two windows? | [Before/after slope](.claude/skills/relationship-visuals/templates/slope.vl.json) | `group`, `period`, `repayment_rate` | Ranked change dots |
| How do members connect two sets (e.g. groups and wards)? | [Bipartite-like layered bars](.claude/skills/relationship-visuals/templates/layered-bars.vl.json) | `group`, `ward`, `households` | Join matrix for many categories |
| Do entry cohorts retain participation at the same elapsed stage? | [Cohort table](.claude/skills/relationship-visuals/templates/cohort-table.vl.json) | `cohort`, `elapsed_quarter`, `attendance_label`, `observed_sessions`, `planned_sessions` | Small multiples of elapsed time |

These seven templates are executable Vega-Lite v5 JSON, with no data or transforms.
All joins, ordering variables, cohorts, windows, and labels are computed in Python.
Read only the chosen template, rename its fields or prepare the specified CSV
columns, and replace its title with the single finding being shown. Choose the
family by its composition: small multiples and slope charts both contain lines but
answer different temporal questions. Layered bars show membership counts by both
sets; they do not draw individual network edges or imply geographical distance.

## Make it readable

- Label axes in plain words and include units: “Households assigned”, “Amount repaid
  as share of amount due”, “Training entry quarter”. Keep internal IDs in tooltips
  when useful; use the stable display codes as entity labels in masked sessions.
- Use explicit `nominal`, `ordinal`, `quantitative`, or `temporal` field types: Idli
  reads CSV values as strings. Write ISO `YYYY-MM-DD` dates and finite numbers.
  Fractions run from 0 to 1; percent axes use `.0%`, not an additional factor of 100.
- Keep counts on a zero baseline, before/after groups on a shared scale, dates in
  time order, and ranked dots sorted by count. Explain any reference line/capacity
  as a stated assumption rather than a measured policy.
- Keep category counts small enough to read; explicitly disclose any top-N filter.
  Use text counts in a matrix, tooltips on dots, consistent scales in facets, and
  a sequential palette for magnitude. Do not rely on colour alone for event types.
  A cohort table's blank cell means unobserved; label its denominators in the answer.

## Render locally, then show

The installed templates live in `.claude/skills/relationship-visuals/templates/`.
Build a CSV with a self-contained pandas script, then load the chosen JSON. Templates
omit `data`; **pass the spec without `data` to `idli_show`**, which loads `data_csv`
locally. Do not add remote URLs, inline private data, external images, JavaScript,
network layouts, or Vega-only transforms. There is no need for a `lookup`, `pivot`,
`window`, `fold`, or custom transform: prepare the final rows in Python instead.

For an offline preview, mirror Idli's string-valued CSV loading and inject values
only into a temporary copy of the spec (not the object passed to the tool):

```python
import copy, csv, json
from pathlib import Path
import vl_convert as vlc

spec = json.loads(Path('.claude/skills/relationship-visuals/templates/matrix.vl.json').read_text())
spec['title'] = 'Household connections by ward and officer'
with open('relationships.csv', newline='') as handle:
    rows = list(csv.DictReader(handle))
preview = copy.deepcopy(spec)
preview['data'] = {'values': rows}
Path('relationships.svg').write_text(vlc.vegalite_to_svg(json.dumps(preview)))
Path('relationships.vl.json').write_text(json.dumps(spec, indent=2))
```

Inspect the preview for clipped labels, empty marks, and misleading scales. If it
fails, correct the CSV/field mapping and rerender; do not claim a chart was shown.
Then invoke the MCP tool using the loaded **object**, not a JSON string:

```text
idli_show(title="Household connections by ward and officer",
          vega_lite=spec, data_csv="relationships.csv")
```

State the finding and its missing-data limits briefly, and remember the shown chart
family for the next question. For a saved Mini, follow `CLAUDE.md`'s separate checking
and saving workflow; this skill does not authorize saving a Mini.
