# foundation-without: what to run and what we saw

Urban graduation-model org (survey row: "where are the 30 households positioned in order of their vulnerability level?"). Data: 30 households (income, debts, vulnerability score, GPS), 150 caseworker visit notes (free text, some contain phone numbers - the scanner must catch these inside prose), milestones.

## The three questions (type them exactly, one after another, in one conversation)

1. Please make me a dashboard of household progress, visits, money pressures and milestones.
2. Rank households by vulnerability and clearly show who seems to have slipped since recent visits or missed milestones.
3. Add a map of households colored by vulnerability, with household details and recent visit notes when I select one.

## What we measured when we ran this (2026-08-26)

All 3 turns completed in both surfaces. io: scan 15 s (free-text notes cost GLiNER time), answers 22-37 s, 255 rows as codes, map colored by vulnerability, share fetched (49 KB). Shield leg: clean wire, no blocks.

## What to check, each time

- **In Antigravity without the shield**: pick a name/phone from the data, ask a question that
  uses it, and know that everything left as-is. (Do this first so the contrast lands.)
- **In Antigravity with the shield on**: after the answer, open the shield menu -> status
  page. `calls` moved, `vault_entries` matches roughly the people in your files. Open
  "last request" and ctrl+F a real name and a real phone from the data: **zero hits** is a
  pass; codes like NAME_012 are what you should see instead. The file the agent wrote on
  disk should have the real values.
- **In io**: the review sheet shows the same columns highlighted; Preview shows the exact
  tokenised payload; after asking, the meta line under the answer says how many rows left
  as codes; built pages get "share on your network" - open the link from your phone.
- The visit notes are the interesting redaction case: phones inside free text, Hinglish. In io, click a highlighted note cell to see exactly what was found.
