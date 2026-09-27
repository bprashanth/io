# Sandbox conformance matrix

Root: `/home/runner/work/io/io/sandbox-artifacts`
Output: `/home/runner/work/io/io/sandbox-matrix`
Overall: **FAIL**

Required targets: `linux-x64`, `darwin-x64`, `darwin-arm64`, `win32-x64`

| Target | State | Source |
|---|---|---|
| linux-x64 | PASS | /home/runner/work/io/io/sandbox-artifacts/sandbox-linux-x64/results.json |
| darwin-x64 | PASS | /home/runner/work/io/io/sandbox-artifacts/sandbox-darwin-x64/results.json |
| darwin-arm64 | PASS | /home/runner/work/io/io/sandbox-artifacts/sandbox-darwin-arm64/results.json |
| win32-x64 | FAIL | /home/runner/work/io/io/sandbox-artifacts/sandbox-win32-x64/results.json |

| Property ID | Name | linux-x64 | darwin-x64 | darwin-arm64 | win32-x64 |
|---|---|---|---|---|---|
| workspace_read | Workspace read | PASS | PASS | PASS | EXECUTION ERROR |
| workspace_write | Workspace write | PASS | PASS | PASS | EXECUTION ERROR |
| outside_read | Outside read blocked | PASS | PASS | PASS | EXECUTION ERROR |
| outside_write | Outside write blocked | PASS | PASS | PASS | EXECUTION ERROR |
| link_read | Symlink/junction read blocked | PASS | PASS | PASS | EXECUTION ERROR |
| link_write | Symlink/junction write blocked | PASS | PASS | PASS | EXECUTION ERROR |
| child_execution | Child interpreter works | PASS | PASS | PASS | EXECUTION ERROR |
| child:outside_read | Child Outside read blocked | PASS | PASS | PASS | EXECUTION ERROR |
| child:outside_write | Child Outside write blocked | PASS | PASS | PASS | EXECUTION ERROR |
| child:link_read | Child Symlink/junction read blocked | PASS | PASS | PASS | EXECUTION ERROR |
| child:link_write | Child Symlink/junction write blocked | PASS | PASS | PASS | EXECUTION ERROR |
| tcp:loopback | TCP loopback | PASS | PASS | PASS | EXECUTION ERROR |
| child:tcp:loopback | Child tcp:loopback blocked | PASS | PASS | PASS | EXECUTION ERROR |
| tcp:nonloopback | TCP nonloopback | PASS | PASS | PASS | EXECUTION ERROR |
| child:tcp:nonloopback | Child tcp:nonloopback blocked | PASS | PASS | PASS | EXECUTION ERROR |
| tcp:internet | TCP internet | PASS | PASS | PASS | EXECUTION ERROR |
| child:tcp:internet | Child tcp:internet blocked | PASS | PASS | PASS | EXECUTION ERROR |
