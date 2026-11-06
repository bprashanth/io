# Requested untested main checkpoint and follow-on branch

Owner explicitly requested: append untested acceptance steps to README, audit large/sensitive
files, commit, run the shell `declaude` helper, publish to origin/main, then fetch/rebase local
main and create `io_silo_untested` from main.

Prepared: README now labels this as an untested end-to-end release checkpoint while retaining
the distinction from passing automated tests. It lists local per-machine conformance and
real two-user remote laptop acceptance, plus persistence/restoration tests and deployment limits.
Additional ignore guards cover private backup exports, local Cloudflare credentials, standard
private SSH key names, certificate bundles and SQLite journals.

[Audit](../benchmarks/runs/2026-10-11-main-handoff/audit.json) compares against the locally stored
origin/main (not newly fetched): no new history blob over5MiB, no private-key/provider-key/JWT
pattern findings in changed file contents. Credential files, dependencies, Codex binaries,
screenshots, release archives and gateway state pass representative ignore checks. This is a
heuristic audit, not a guarantee against every possible secret. No user credentials were read.
Existing untracked owner draft docs/sandbox.md was excluded and remains untouched.

Inspected `bash -ic 'type declaude'`: it is a function that rewrites commit messages with
`git filter-branch` to remove Claude attribution trailers. It defaults to the current upstream,
which would miss previously pushed experiment commits; invoke explicitly as `declaude origin/main`
after fetching main and committing this checkpoint. Preserve the old branch tip for recovery.
No force push to main is authorized or necessary; stop and reconcile a non-fast-forward result.

Execution limitation: this session again has read-only .git, restricted network and no elevation.
README/ignore/evidence files can be prepared, but publication and branch creation are not yet
completed. The October11 earlier push authorization remains valid; the current restriction is
execution access, not missing user permission. Do not report main updated or the new branch
created without verifying those operations.

No application code changed and no new runtime/UI tests were run for this README-only checkpoint.
The most recent completed automated evidence is in the preceding October11 sandbox/CI entries.
Human end-to-end acceptance remains outstanding as stated in README.

Attempted staging of only README, .gitignore and this checkpoint's chronology/benchmark files.
Git failed with `Unable to create .git/index.lock: Read-only file system` (exit 128).
Consequently no commit, declaude rewrite, push, main rebase or branch creation was performed.
`git diff --check` passed. Continue the requested Git sequence from a session with writable
repository metadata and origin connectivity; user authorization is already explicit.
