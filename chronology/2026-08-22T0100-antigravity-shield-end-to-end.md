# Antigravity with the privacy shield completed a five-turn dashboard conversation

`benchmarks/pii/shield_proxy.py` is now a working redacting reverse proxy for
Antigravity (CLI and, by the same mechanism, IDE) via `CLOUD_CODE_URL`. It
classifies every outbound part (table / data / code), redacts tables column-wise
with the validated classifier, runs an in-chat review ("I will hide these 12
columns - reply ok / also hide / don't hide") before a table first leaves, keeps
a reversible vault, rehydrates the SSE stream at event level, and blocks any
request in which a vault value survives.

Five turns on the synthetic scholarship file (dashboard, clarify, person lookup,
ranked lookup with phone, full record with Aadhaar and bank account) completed
with Antigravity's normal page quality; the page on disk holds real values and
the outbound bodies hold tokens only (0 hits for name/phone/Aadhaar). Redaction
cost 0.3-2 s per model call after the one-time 2-13 s table pass; Gemini itself
takes 2-7 s per call.

Bugs found and fixed during the run, each by the leak guard or the vault dump:
tool results arrive with role=model; `toolAction`/`toolSummary` captions were
exempt from substitution and carried rehydrated names back up; cached parts went
stale as the vault grew; substring guard matched "Atri" in "Post-Matric"; a
column kept by the user can share values with a hidden one ("Wazirganj" taluka
and village) - hidden anywhere now means hidden everywhere; header words and
kept values were being minted as names; single-word names printed by the
model's own Python ("Naam: Lalita") escaped the name-shape rule - now any
`<hidden header>: value` line is tokenised; tokens split across SSE events and
markdown-escaped tokens (`PHONE\_109`) were not rehydrated; events are CRLF
separated. Per-vault-value regex compilation made a 300-row file cost 42 s;
one compiled alternation brought it to 13 s.

Still open: Antigravity reads whatever it likes (it searched /home for the
file), so sheltered mode needs workspace confinement; names in the model's
free-form Python output that are not header-prefixed are caught only if
name-shaped; Devanagari is untested; the review is a chat message, not a UI.

Evidence: `benchmarks/runs/2026-08-22-antigravity-shield-e2e/`.
