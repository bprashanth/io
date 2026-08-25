# 2026-08-24 18:00 — Step 1: the minimal io, shield bridged over

Reset per the user: declutter, one piece at a time. Step 1 = what Antigravity + shield did, in io,
with a visible redaction UX and consent. No reach, no lanes. `app/io/` (the earlier `app/io-desktop`
stays untouched as the lab).

Flow, as built and screenshotted (`benchmarks/runs/2026-08-24-io-min-v1/`):

1. **Provider** (01): "io needs an AI provider." — API key or server address, memory only,
   re-asked on restart, changeable at ⚙.
2. **Home** (02): a + in the middle; the bar says "ready when you are...".
3. **Folder → the sheet** (03): every file as a spreadsheet view; columns the scanner flagged are
   highlighted with the reason under the header (names, phone numbers, Aadhaar numbers, birth
   dates…); free-text columns highlight the individual cells that contain something. Click a
   highlighted column to keep it; click a plain one to hide it. Decisions are remembered by
   header signature in `~/.config/io/decisions.json` — the shield plugin's scheme. "Looks right"
   mints the vault.
4. **Chat** (05, 06, 08): typing a coded value strikes it through live (mirror-overlay input) with
   one line: "struck-through words leave as codes". Questions are redacted, answers rehydrated.
   Every answer carries "N rows sent as codes · model · seconds". Dashboards: the model writes the
   page against `window.data`; io injects the real rows locally — the scholarship dashboard came
   back with all reference numbers correct (300/103/61/136/67.2 %) and real names on screen, 22 s.

**Engine reuse (the user's question):** the same tested code, not a rewrite — the service imports
`benchmarks/pii/{columns,detect,pseudonymize}.py` (the shield's library modules, verified in stage 3)
and runs on the installed shield extension's venv (GLiNER + CPU torch), so the scanner behaviour is
byte-identical to the plugin's. The proxy part of the shield (wire interception) isn't needed here:
io owns the traffic, so redaction is a function call, not a man-in-the-middle.

**Found again on the way:** the one-shot "model computes from full tokenised rows" page fails by
re-emitting the data and truncating (zeros everywhere); the `window.data` injection is what makes
pages correct. Text answers over full tokenised rows work.

**Egress monitor question:** with the sheet, the strikethrough, and the per-answer "N rows as
codes" line, a separate monitor panel has no job left in this app; the leak gate (block if a vault
value survives in the payload) runs on every call. Decision deferred until something needs it.
