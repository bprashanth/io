# 0.3.0: discovery at rest — the span model never sees traffic again

Decision (user, after the 404 postmortem): the week's bug parade — footer
fragments as addresses, label words as people, path segments as places, and
finally a junk vault entry rewriting the model id — shared one root: running
ML discovery on text streaming through the proxy, where scaffolding and data
are indistinguishable. Architecture change, converging fully on io's contract:

- Scan at rest: the daemon takes `--scan <workspace folder>` (the extension
  passes it), walks csv/xlsx/txt/md/log/pdf (recursive, skip .git/node_modules
  etc., 300-file/8MB caps), and mints the vault from files alone using the
  same scanner io uses (classify_columns + pseudonymise_frame + text engine;
  pdf via pdftotext). A watcher rescans changed/new files (~5s; errored files
  wait until they change). openpyxl added to requirements for xlsx.
- Deterministic in flight: with `privacyShield.discovery: "files"` (default)
  the request path runs no ML at all — known-value replacement, partial-name
  matching, validators, digit runs, the deterministic name heuristics. The
  legacy behaviour survives as discovery: "requests".
- Fail-closed scan gate: model calls arriving mid-scan are held up to 45s and
  then answered in-chat ("still scanning your folder, n/m files — nothing was
  sent"); the status bar shows "Scanning your files… n/m · <file>" from the
  daemon's scan state. A query can never leave with a partially built vault.

Standalone verification on the shield-dash corpus: 5 files scanned to a
60-entry vault (all names/phones/aadhaar/emails from csv+xlsx+pdf, zero junk);
probe question naming file people fully redacted with the model id intact; a
csv dropped into the folder was learned within ~10s and a question naming the
new person (including the bare first name) left with 0 real values.
