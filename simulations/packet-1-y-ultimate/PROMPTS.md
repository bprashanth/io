# y-ultimate: what to run and what we saw

Sports-for-development org (from the io.xlsx survey: "what is the current health of each program site? which participants, coach and site need support?"). Data: session attendance (400 rows, 6 sites), fitness assessments (180 children), donor transactions (with emails), site GPS coordinates.

## The three questions (type them exactly, one after another, in one conversation)

1. Can you make me a simple dashboard showing attendance, fitness results and donations?
2. Now show which participants, coaches and sites may need extra support to improve attendance, fitness or confidence.
3. Please add a Pune map of our sites, sized or shaded by average attendance, with a quick way to compare them.

## What we measured when we ran this (2026-08-26)

All 3 turns completed in both surfaces. io: scan 3 s, answers 23-34 s, ~706 rows sent as codes per ask, map rendered with rehydrated site names, page shared and fetched over LAN (100 KB). Antigravity+shield: same turns, zero blocks, dashboard written to disk with real values, wire clean. Screenshots: ../../benchmarks/runs/2026-08-26-io-electron-bench/ (01*, 02-y-ultimate-*) and ../../benchmarks/runs/2026-08-26-shield-robustness/.

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
- The map turn should produce a geographic view; site names are real on your screen and codes on the wire.
