# Date coarsening rules (deferred 2026-09-01, event eve)

Any date-shaped column is classed `dob` by the validator in
`app/io/engine/columns.py` (no header semantics), so operational dates -
visit dates, meeting dates - are coarsened to bare year by
`pseudonymise_frame`. Lat/lon is fine: `gps` rounds to 2 decimals (~1 km),
which still supports clusters and maps.

Decision for the event: accept it. Coarsening is one-way (no pmap entry,
nothing to rehydrate), so the model answers only at the coarseness that
left - a limitation we accept for real PII. The opt-out exists today:
clicking the column header in the review sheet keeps the column verbatim.

Later fix, discussed and parked: year-spread heuristic in `columns.py` -
dates spanning >=5 distinct years or reaching back >10 years are `dob`
(-> year); tight clusters are operational (-> keep full); headers containing
dob/birth/janm are always `dob`. Known weakness: an infant-DOB column with a
mangled header would slip through - decide the exact rules when picking this up.
