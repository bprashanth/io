# Dashboard smoke test: two leaks found and closed, review grammar extended, verdict "demo-grade yes, pin and re-verify"

Smoke-tested the real participant flow on Antigravity 1.107.0 (the current
apt-latest, i.e. what a Linux downloader gets today): csv + txt + csv with
misleading headers + xlsx with nested tables/merged titles + pdf; "build a
dashboard.html", follow-up questions, both model families (Claude Sonnet 4.6,
Gemini 3.6 Flash — Gemini works now that sign-in state is fresh; the earlier
"no valid model" was stale user status). Full evidence and screenshots in
`debug/20260822T1040-…/`; design record updated in
`proposals/pii_antigravity.md`.

Passed: dashboard built and rendered with real values on disk while the wire
had 0 hits for every name/phone/email/PAN/aadhaar/ration number; follow-ups
naming real people redacted outbound and rehydrated in answers on both model
families; misleading headers caught by content; review flow honoured
`ok, don't hide scheme, also hide status and Ujjwala` exactly (column keeps,
column adds, and content values in one reply).

Found and fixed (0.2.2):
- Kept columns leaked validator-class PII: nested-xlsx `Unnamed:` headers made
  the review keep the email column and two emails hit the wire. Kept columns
  now still get hard validators (email/PAN/aadhaar/IFSC/UPI/phone/voter/
  vehicle).
- GLiNER missed a prose name next to tokenised identifiers ("Surveyor: Anita
  Kulkarni (EMAIL_004, PHONE_019)"): deterministic contact-line heuristic.
- Review-reply parser was single-directive; now clause-aware, and `also hide`
  accepts arbitrary values (minted as CUSTOM_ tokens, hidden everywhere).
- split_table false-positived on comma-rich instruction prose (header cells
  must now look like column names); reviews are skipped when nothing would be
  hidden or the table is already tokenised; a pending review re-asks on
  non-answers (fail-closed).
- Egress firewall false-positive on quoted/lower-cased token echoes
  ('email_002'); token-shaped vault values exempt from mint and blocker.
- Routing: normal quits used to clear jetski.cloudCodeUrl, so a plain reopen
  ran unshielded until the next endpoint push (the new "awaiting first call"
  status caught this live). The setting now survives every quit while
  enabled; a dead daemon at launch costs a transient loginError that
  self-heals (measured), and activation clears the setting if the daemon
  cannot start (deliberate fail-open, visible in the status bar).
- UX: clicking the shield opens an Enable/Disable picker (disable = two
  deliberate steps); status bar distinguishes "on · awaiting first call" from
  verified-active.

Open/accepted: internal-knob dependency (re-run smoke on every new build; the
knob moved once already between 1.104 and 1.107), pinned upstream host, small
residual GLiNER miss rate on odd prose names, paraphrased tokens cannot
rehydrate, review repetition when scripts keep changing output formats,
first-call-after-restart redaction costs seconds (cold cache), macOS/Windows
untested. This laptop's flaky run_command ("failed to check terminal shell
support") and broken browser-driver download are environmental (present with
shield off) — do not misattribute at the event.
