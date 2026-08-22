# Stage 3 — Privacy shield for stock Antigravity (2026-08-21/22)

**Question.** Can participants use stock Antigravity (Part 3) on beneficiary
data without that data leaving the laptop, and without them debugging anything?

**Outcome: yes, verified in the real IDE on two machines.** Extension
`privacy-shield-0.2.3.vsix` (`extension/privacy-shield/`, daemon bundled).
A local reverse proxy replaces names, phones, Aadhaar/PAN, accounts, emails,
villages and user-chosen values with stable tokens before Antigravity's model
traffic leaves `127.0.0.1`, and restores them in the streamed answers and in
files the agent writes. The participant sees real data; Google sees tokens.

**How it routes (measured).** Antigravity's agent traffic comes from its
app-level language server. It is pointed at the proxy by `jetski.cloudCodeUrl`
written to settings.json *before* a relaunch (language servers take it as a
launch flag), with `CLOUD_CODE_URL` also set on the relaunched app. The daemon
must be listening before the app starts; it runs detached, outside the
extension host's process tree, and the relaunch helper waits for it. Enable =
one relaunch; Disable = one relaunch. Status bar: `Shield on · awaiting first
call` until a model call has actually passed through, then
`🛡️ N calls · X ms · vault M`. Internal knob; re-test on every Antigravity
build before the event.

**What the participant does.** Install `.vsix` → "Install Python environment"
(once, CPU-only, ~1.7 GB) → Enable → Relaunch. First time a table is about to
leave, the chat lists the columns to hide with the reason each was caught;
reply `ok`, `also hide X, Y`, `don't hide Z` (mixable). "Show last request that
left the laptop" is the wire view with a search box; "Show vault" lists what is
hidden; "peek mode" shows answers as the model saw them.

**Measured on 2026-08-22 (arm64 DGX) and the laptop (x64).** Scholarship CSV
(300 rows, Hinglish and mislabelled headers) → review → dashboard with correct
totals, real values on disk, 0 wire hits; follow-ups by name with phones;
fitness workbook gains (verified); WhatsApp export (12 senders, names/phones);
PDF report (coordinator, follow-up number); misleading headers caught by
content; Claude Sonnet 4.6 and Gemini 3.6/3.7 Flash both fine. Corpus
ground truth with the shield's engine: scholarship Remarks 181/182 spans,
WhatsApp names 262/291 and phones 60/60, report names 50/51 and GPS 9/9.
Per-call redaction 0.1–2 s warm; a 300-row table costs ~12 s once.

**Known limits.** Villages inside free prose (13/25 on the report) unless
they also occur in a table; tokens strip name semantics, so the model can
mislabel which hidden name is the student vs the parent; paraphrased tokens
cannot be rehydrated; first call after a daemon restart re-walks the history
(10–25 s); over-hiding of school/scheme phrases is recoverable with
`don't hide`; macOS/Windows relaunch helpers are written but untested;
Antigravity may read files outside the folder (redacted, but unconfined).

**Evidence.** `proposals/pii_antigravity.md` (as-built design),
`benchmarks/runs/2026-08-22-antigravity-ide-shield/` (first IDE run),
`benchmarks/runs/2026-08-22-antigravity-ide-shield-v2/` (0.2.3 verification),
chronology `2026-08-22T0540`, `T1230`, `T1500`, `T2130`.

**Next for this layer.** Pin the Antigravity build for the event and re-run
the smoke on it; a standalone tray app instead of an extension (owns the
daemon, launches Antigravity, one-click); ONNX model (~150 MB install);
a second unseen corpus to quote recall honestly; Windows/macOS test.
