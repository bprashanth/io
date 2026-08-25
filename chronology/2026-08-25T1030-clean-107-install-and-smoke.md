# Clean 1.107 install from the apt channel, 0.2.5: bare first names in questions were leaking

Wiped the old 1.104 apt install on the x86 laptop and reinstalled from
Google's channel: purge → fixed the malformed sources line (flat-repo form
404s; the correct entry is `.../antigravity-auto-updater-dev/
antigravity-debian main`, key at the standard Artifact Registry
`doc/repo-signing-key.gpg`, same fingerprint as the shipped keyring) →
`apt install antigravity=1.23.2-1776332190` → `apt-mark hold`.
`antigravity --version` now prints 1.107.0. Re-checked the channel: nothing
newer than 1.23.2 has landed since Aug 22. README Quick start rewritten with
the verified apt flow plus a corrected tarball fallback (the tarball root is
`Antigravity/` itself — the old instruction moved only the ELF; symlink
`/opt/antigravity/bin/antigravity` into PATH).

Extension flow on the clean build, as a participant: trust dialog → Enable →
relaunch. The 1.7 GB Python env now lives in globalStorage (0.2.4 change) and
verifiably survives extension updates — two update cycles kept it. Smoke on
`tests/test_pii_data.{csv,xlsx}` (adversarial headers: emails under
Comm_Route, phones under Loc_Pin, PANs under Tax_Code): review caught every
column by validator, dashboard built and rendered with real values locally,
0 wire hits for every value, follow-ups clean on Gemini 3.6 Flash and Claude
Sonnet 4.6 — including the agent grepping the real-valued dashboard.html on
disk (known values re-tokenised outbound, 0 hits).

One real leak found: a typed follow-up "give me Priya's email" sent the bare
first name — only full values were in the vault and the span model misses
short possessives. 0.2.5 wires the io app's partial-name pass into the proxy:
a capitalised fragment matching exactly one known NAME/PLACE value gets that
token (linkage kept); matching several gets its own token (privacy first —
the model then asks for the full name instead of guessing; full-name
questions answer perfectly). The pass only considers clean name-shaped vault
values so GLiNER span-noise ("Row 5: ['…'") cannot poison it.

Noted for demos: aggregations over hidden values are impossible by design
(domain counts on hidden emails come back token-based — keep the column with
"don't hide" if that analysis matters), and the vault accumulates across
sessions (run "Privacy Shield: Forget this session's vault" between
participants). Evidence: `debug/20260825T0950-v107-clean-install-smoke/`
(local).
