# DGX: handoff verification before feature work

The checkout is `io_codex_3`, at `4ad4fed` ("Merge pull request #19 from
bprashanth/io_codex_2"), identical to fetched `origin/main`. `git pull --ff-only`
fetched but could not merge because this branch has no upstream. No branch switch
was needed. Existing untracked files and benchmark directories were left alone.

Baseline: 18 launcher tests and 31 proxy tests passed. The launcher's live wall test
was skipped, however: its fixture lives under `/tmp`, which io explicitly grants.
It therefore read the supposedly forbidden file. Another test passed a directory
string to `sandboxCheck`, whose interface now requires an options object, and
misreported the already-installed AppArmor grant as absent.

Direct `sandboxCheck` with the bundled binary, checkout Python runtime and io's
actual data directory returned `{ok:true, checked:true, platform:"linux"}`.
The launcher fixtures now live under a temporary directory in the user's home,
outside the granted temp tree; the control deliberately keeps its secret in temp.
The status test now passes the real options object on every platform.

Not tested at this checkpoint: requested features, macOS or Windows, real ChatGPT
quota exhaustion, and a clean thin installation. These require subsequent drives.
The owner's current request authorizes the six implementation requests and their
documented design decisions. Lower-model Cursor CLI agents handle routine UI and
bootstrap edits; privacy controls and integration remain with the primary agent.
