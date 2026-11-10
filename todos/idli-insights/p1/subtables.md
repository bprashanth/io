# Read every table on a tab (subtables and info blocks)

Owner's decision, 2026-11-10: Idli must not ignore subtables. Many NGO sheets have more than one table on a tab:
- a key/value info block above the main table (the germination template: nursery name, ecoregion, contact person);
- two tables side by side;
- sections stacked under each other with their own headers.

## How it works today (`lib/filekit.py`, `build_tables`)
- Each tab gets one header row and one table.
- Sections stacked under each other with the same header are handled: the repeated headers are skipped.
- Anything else is ignored. E6 showed the germination file's contact block was never checked.
- The fake copy (`mock_column`) also loses spacer and notes rows and merged headers, so Claude can't see the
  structure either (E1).

So Claude does not pick these up automatically yet: the engine can't express them.

## What to build
1. **Teaching:** the skill describes every table on a tab as its own table: its cell range or anchor text, its
   header, its kind (records, key/value block, lookup). A key/value block becomes one record with named fields
   (nursery name, contact email) that checks and the form can use.
2. **The engine:** reads each declared table, and gives each one its own form tab, checks and dashboard section.
   A key/value block shows as a small "About this file" panel.
3. **The fake copy:** keeps the layout (spacer rows, notes rows, merged headers, instruction rows), so Claude sees
   the real structure (the E1 fixes behind `IDLI_MOCK_V2=1` are the start).
4. **Not confusing the 9B:** the form lists tables by plain names ("Nursery details", "Species"). The dial-setting
   call picks a table first, then the dials.
5. **When the structure itself is the problem**, for example a table that can't be told apart from the one next
   to it: Claude suggests a simpler layout while teaching, and the working copy carries one comment saying how to
   restructure it for next time. This fits the clean/standardise step: it's a suggestion, never an automatic
   change.

## How to test
Add to E6 and E2: a planted file with an info block plus two side-by-side tables. Score whether each table is
found, checked, and answerable in the form, and whether the 9B's question steps on it stay at the E7 level.
