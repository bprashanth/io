# Untested checkpoint publication resumed

Owner reaffirmed the October request to publish the experiment to origin/main after
`declaude`, update local main and create `io_silo_untested`. Repository metadata and
network access are available again. October's read-only error remains historical.

README ends with the untested end-to-end status and local/remote acceptance steps.
Ignore guards cover private backups, Cloudflare state and credentials. The existing
owner draft docs/sandbox.md is deliberately excluded. Freshly fetched origin/main
is an ancestor of the experiment tip; no forced main update is needed.

[Fresh audit](../benchmarks/runs/2026-11-06-main-handoff/audit.json): no new history
blobs over 5 MiB or private-key/provider-token pattern findings in changed files.
This is heuristic, not an exhaustive secret audit. Representative private paths
remain ignored. `git diff --check` passes. Launcher tests: 19 passed. System Python
lacks pandas; all 34 proxy tests passed in a temporary isolated venv with pandas.

Gateway service is active on loopback8789 and unauthenticated identity returns401.
This does not verify Cloudflare routing, real human authentication or model calls.
No UI/runtime changes or new human end-to-end tests are claimed. Next acceptance:
two real approved identities/laptops, both logins, CSV upload/model processing/
download, multiple conversations, reconnect/restart persistence and backup restore.

Remote V1 uses direct user ChatGPT OAuth, not a local model or OpenRouter. Each
identity owns one persistent workspace/container; multiple saved conversations
share it, with one active terminal. The remote command profile is Offline and
approval escalation is never. Local IO's separate Tools/Open/provider options
are not remote V1 switches. See app/io/remote/config.js and app/io/codex.js.

Publication sequence: commit this checkpoint, preserve the pre-rewrite tip locally,
run `declaude origin/main`, push HEAD:main without force, fetch, rebase local main
onto origin/main and create io_silo_untested from main. The final published hash
is reported in chat and can be recovered from main's history; this entry describes
the intended sequence rather than asserting success before execution.
