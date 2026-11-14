---
name: newsroom-charts
description: Show a clear finding from NGO spreadsheets with annotated newsroom charts or local India maps through idli_show.
---

Offer a chart in one short sentence. Wait for the person to agree. Compute its rows into a local CSV with a checked script. Call `idli_show(title, vega_lite, data_csv, sources, script)` with the source paths and script. Work with the stable codes. Local charts show real labels without a reveal.

Use a headline that states the finding. Keep a short subtitle with the unit. Put the source, exclusions and any uncertainty in `description`. Keep words plain. No arrow characters or middle dots. Split a long headline into two short lines. All templates fit a 360 px pane in light and dark themes.

Label groups directly. Avoid a legend. Use one muted blue highlight with the other groups grey. Use light value gridlines only. Include zero for bars. Keep scales shared across small multiples. Describe an association without claiming it caused a change. State the interval meaning on ranged dots. For a heat table use readable numbers in the cells. Check that a finding still holds after excluding blanks.

Read one template that fits the question. Replace fields, headline, subtitle and description with the actual finding. The template has no private data. Use the CSV field names exactly.

| Template | When to use it |
| --- | --- |
| [sorted-bars](.claude/skills/newsroom-charts/templates/sorted-bars.vl.json) | Rank a few groups. Direct counts and one highlighted group. |
| [comparison-dots](.claude/skills/newsroom-charts/templates/comparison-dots.vl.json) | Compare group values without the visual weight of bars. |
| [annotated-outlier](.claude/skills/newsroom-charts/templates/annotated-outlier.vl.json) | Point out one unusual value with a short annotation. |
| [slope](.claude/skills/newsroom-charts/templates/slope.vl.json) | Compare the same groups at two dates. Label the final point. |
| [small-multiples](.claude/skills/newsroom-charts/templates/small-multiples.vl.json) | Compare trends across groups on the same scale. |
| [ranged-dots](.claude/skills/newsroom-charts/templates/ranged-dots.vl.json) | Show an estimate and its range. Say what the range means. |
| [heat-table](.claude/skills/newsroom-charts/templates/heat-table.vl.json) | Compare groups across a small set of periods. |
| [gps-points](.claude/skills/newsroom-charts/templates/gps-points.vl.json) | Show rows with numeric lat and lon. The local server fits an India state basemap to the points. In usermeta.idli_map set label to a group column (one label per group) and color to the column that colours the points. |
| [district-map](.claude/skills/newsroom-charts/templates/district-map.vl.json) | Compare district totals. Combine rows to one per district first. |

Maps use `usermeta.idli_map` as in the templates. GPS maps name `lat` and `lon` fields. District maps name `field` and numeric `value`. Add `state` to distinguish duplicate district names. The server checks coordinates and matches names locally. Case, spacing, a district suffix and common spelling variants are handled. Ambiguous names remain unmatched. Check `description` for unmatched districts and tell the person which data was left out. If no names match, fix the input instead of drawing an empty map.

Bundled boundaries are `/geo/india-states.topo.json` (object `states`) and `/geo/india-districts.topo.json` (object `districts`). They are simplified historic DataMeet boundaries. Attribute DataMeet in the description. State boundaries use CC BY 4.0. District boundaries use CC BY 2.5 India. They may differ from today's districts. The server resolves geometry locally. Do not use remote tiles or boundary URLs. Never reveal or search a GPS code to draw a map. If map validation fails, follow its error message and use a table while correcting it.

Every point and district supports the same source popover and Copy to Claude menu as bars. Pin keeps the chart for a Mini.
