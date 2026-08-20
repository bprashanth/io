# District Immunisation by Year

A single-page website built from `district_immunisation.csv`.

## Run

Option 1 — just open it (data is embedded as a fallback, so it still works offline):

```
open index.html        # or double-click the file
```

Option 2 — serve the folder so the page loads the CSV live (recommended):

```
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Features

- **Fixed year** — shows 2023 only (change the `ONLY_YEAR` constant in the script to switch years).
- **District comparison** — horizontal bar chart of the fully-immunised share of children due, top district highlighted.
- **Details table** — rank, children due, fully immunised, and rate per district.
- **Summary stats** — district count, totals, overall rate, top performer.
- **Download** — a "Download CSV" button next to the Details table exports the shown table as `district_immunisation_2023.csv`.
- **Source** — shown in the footer, taken from the `source` column of the CSV.

No external libraries or CDNs — the page is fully self-contained.
