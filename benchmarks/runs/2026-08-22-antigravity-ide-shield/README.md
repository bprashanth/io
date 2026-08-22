# Privacy shield inside the real Antigravity IDE (2026-08-22)

Antigravity IDE 1.107.0 driven under Xvfb through CDP/Playwright (`ide-driver.py`),
extension `privacy-shield-0.2.0.vsix` installed from the packaged file, daemon
bundled in the extension, workspace with `test_pii_data.csv` (the user's sample),
`inventory_q1.csv` (PII under misleading headers: Item/Qty/Notes/Status) and
`field_notes.txt` (lowercase names, Hinglish, phones, email, ration card).

What had to be learned the hard way (all in the chronology entry):
- The agent chat is served by Antigravity's app-level language server. It honours
  `CLOUD_CODE_URL` from the app environment, read at launch; `jetski.cloudCodeUrl`
  alone only moves metadata calls. Routing needs: daemon listening BEFORE launch,
  env var at launch, and the setting applied right after launch.
- A dead proxy port at launch stalls the window; the daemon is therefore spawned
  detached and the setting is never left behind across sessions.
- Streamed tool-call arguments split tokens across events: per-argument tail carry
  plus an on-disk rehydration backstop for files written by the agent.
- Review decisions are keyed by column-header signature so a table re-read inside a
  page is not asked again.

Screenshots are the participant's view:
01 review prompt in chat, 02 answer with real values on screen, 03/04 misleading
headers caught by content, 05 free-text notes, 06 relaunch modal, 07 cold-start of
the packaged build. Egress checks (`/shield/last-request`) returned 0 hits for every
name, phone, email and account number at each step.
