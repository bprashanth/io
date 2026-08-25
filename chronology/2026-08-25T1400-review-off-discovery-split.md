# Review off by default; discovery scoped to files and typed questions (0.2.7)

Decision (user): the in-chat review is the plugin's most complex and most
bug-prone surface and interrupts the flow; drop it from the default path and
let the vault/wire views be the after-the-fact review. The upfront per-folder
review remains io's differentiator. `privacyShield.review` now defaults to
"off" (the chat machinery stays behind the setting).

Discovery/replacement split, converging the plugin on io's contract: GLiNER
minting now runs only on functionResponse content (file reads, script output)
and on the typed question inside <USER_REQUEST> (scanned with the full engine
— previously the question text classified as "code" and got regex-only, so a
brand-new typed name was missed; unit-tested). Summaries, user_information,
metadata and model echoes are replacement-only: known values still hidden
everywhere, nothing ever minted from scaffolding. Plus mint guards: generic
label words AND phrases ("Village", "Child name", "Child ID" — word-level
check), our own footer fragments ("629 ms redaction" had been minted as an
ADDRESS from a summary echo), and token echoes are never mintable; the footer
is stripped wherever it appears, not just at end-of-text.

Verified live on the corpus workspace (Gemini 3.5 Flash, silent flow, zero
interruptions): "build a dashboard.html to help understand child fitness
scores" → columns.json read mints nothing (previously the source of
village/Taluka/District/City junk), xlsx analysis mints 60 clean entries
(villages, schools, coach names), dashboard written and rendered with real
values locally, 0 wire hits for every ground-truth name/phone from
child_fitness_scores.cells.json, 0 blocked, no junk vault entries. The two
token-looking strings in the HTML are the model's own template placeholders
(NAME_000/PHONE_000 — not vault tokens).

Also fixed: the "Install now" flow never passed the globalStorage target to
install.sh/ps1, so fresh envs landed back in the versioned extension folder
and would die on update — exactly what the 0.2.4 change was for.

## Addendum (same day, 0.2.8): the 404 was the shield rewriting the model id

User hit `HTTP 404 Requested entity was not found` on every send. Chain, fully
traced: Antigravity wraps its context-compaction summary in the same
`<USER_REQUEST>` tags as typed questions → the full-engine question scan ran
GLiNER over a machine summary full of file paths → minted "gemini",
"antigravity", "desinotorious" as places → the 0.2.4-era last-line-of-defence
pass (which substitutes known values over the WHOLE serialized body) rewrote
the top-level model field to `PLACE_055-3.5-flash-low` and the userAgent to
`PLACE_056` → Google 404s on the nonexistent model. Reproduced against the
live daemon with a crafted probe; unit repro missed it because the full-body
pass lives in the request handler, not in redact_request.

Fixes in 0.2.8: the full-body pass restores model/userAgent/project/requestId
after substitution (a junk vault entry can never again corrupt routing
fields); USER_REQUEST spans over 1500 chars are treated as compaction
summaries (replacement-only, no discovery); product/platform words (gemini,
antigravity, google, claude, vscode, python, …) are never mintable as
names/places; incoming model id now logged per request for diagnosis.
Poisoned vault entries removed surgically. Verified: crafted probe and a
fresh conversation both leave with the clean model id; shielded analysis of
the fitness xlsx proceeds normally (the model computing with NAME_ tokens and
correcting its own KeyError is the shield working, not a bug).
