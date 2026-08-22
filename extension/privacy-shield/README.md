# Privacy Shield for Antigravity

Hides names, phones, Aadhaar/PAN, bank accounts, emails, villages and other personal
values on this laptop before Antigravity sends anything to the model, and puts the real
values back in the answers and the files it writes.

## Install (once)
1. Install the `.vsix`: Extensions view → `…` → *Install from VSIX…* (or drag it onto the window).
2. Command palette → **Privacy Shield: Install Python environment** (needs Python 3.10+ and
   internet once; ~1.7 GB on disk, CPU only, no GPU needed).
3. Command palette → **Privacy Shield: Enable**, .

The status bar shows `🛡️ N calls · X ms · vault M`. Click it to toggle. Disable + restart
returns Antigravity to normal.

## While using it
- The first time a table is about to leave the laptop, a message appears in the chat
  listing the columns that will be hidden. Reply `ok`, `also hide X, Y` or `don't hide Z`.
- **Privacy Shield: Show last request that left the laptop** opens the wire view with a
  search box — type your own name, expect 0 hits.
- **Toggle peek mode** shows answers exactly as the model produced them (tokens instead of
  names) so you can see the model never had the real values.
- **Forget this session's vault** clears the token map.

## Limits
Antigravity may read files outside the folder you point it at; the shield redacts whatever
it reads but does not confine it. Values printed by the model's own scripts are caught
when they are name-shaped or follow a hidden column header. Non-Latin scripts are untested.
