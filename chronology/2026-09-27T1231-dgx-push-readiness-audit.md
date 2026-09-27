# Push hygiene and laptop launch audit — DGX, 2026-09-27

Fetched origin/main and inspected the incoming range through c8a63ca: nine commits,
275 changed files, including earlier local features and native sandbox work, not
only the remote experiment. Origin/main is an ancestor. There is no master branch;
main is the repository's default branch. No merge or push to main was performed.

Measured incoming Git objects (including intermediate versions): 215 unique blobs,
1,549,572 bytes total; largest 94,284 bytes (ui/index.html). No oversized incoming
artifacts. A wider current-tree scan covered 8,240 distinct blobs / 168,033,152 bytes.
The largest existing tracked file is 12,488,388 bytes, an old benchmark record already
on main. Large historical benchmark evidence was not removed or history-rewritten.

Scanned provider/GitHub token patterns, JWTs, private-key headers, credential-value
fields, and exact locally known OpenRouter/remote-session secrets without printing
values. Incoming history has zero matches. The current-tree scan matches only the
existing auth-fixture.json: its README documents fake credentials; the JWT header
uses alg:none and account/refresh fields contain fixture markers. No live credential
was found. This is a pattern/exact-value audit, not a mathematical proof that every
possible secret format is absent. The laptop capability remains outside Git with
mode0600; screenshots, Python environments, Codex bundles, payloads and dependencies
are ignored.

Found and fixed ignore gaps: portable io-data, named remote connection files,
.io-remote directories, auth.json and openrouter-key.json now have guards. Raw proxy
capture directories default to ignored, including the two pre-existing untracked
before/after drive directories. Previously tracked, reviewed evidence remains tracked.
Added a Docker build-context allowlist so unrelated local data/dependencies are not
sent to the builder. The actual remote Docker image builds successfully with it.
Verified representative ignore paths with git check-ignore. No application behaviour
changed, so the previously passing application/CI suites were not rerun for ignore
rules. docs/sandbox.md is pre-existing untracked prose and was left untouched.

Push hygiene is clean for the reviewed branch; this is not a blanket production or
merge-readiness claim. The inherited native Windows sandbox required job deliberately
fails its contract, and successful live OAuth/model interaction and two-machine GUI
use remain pending. The remote-specific CI has five passing jobs. Do not silently
change the native security suite to green to make a merge look ready.

The existing laptop worker was checked healthy, signed out, sandbox=true, Codex
0.154.0. It expires at 16:10 IST today. Copy its private connection file over SSH,
forward DGX loopback8787 over Tailscale100.82.28.38, then launch run.sh with
IO_REMOTE_CONNECTION. Plain run.sh selects local mode. A new device code is generated
when Sign in is clicked; earlier chat codes are expired.
