# Codex sandbox conformance: win32-x64

Overall: **FAIL**

**Diagnostic only: elevated. Ineligible for the io conformance gate.**

| Property | Result | Reason |
|---|---|---|
| Workspace read | PASS | Controls succeeded; restricted behavior matches contract |
| Workspace write | PASS | Controls succeeded; restricted behavior matches contract |
| Outside read blocked | PASS | Controls succeeded; restricted behavior matches contract |
| Outside write blocked | PASS | Controls succeeded; restricted behavior matches contract |
| Symlink/junction read blocked | PASS | Controls succeeded; restricted behavior matches contract |
| Symlink/junction write blocked | PASS | Controls succeeded; restricted behavior matches contract |
| Child interpreter works | PASS | Controls succeeded; restricted behavior matches contract |
| Child Outside read blocked | PASS | Controls succeeded; restricted behavior matches contract |
| Child Outside write blocked | PASS | Controls succeeded; restricted behavior matches contract |
| Child Symlink/junction read blocked | PASS | Controls succeeded; restricted behavior matches contract |
| Child Symlink/junction write blocked | PASS | Controls succeeded; restricted behavior matches contract |
| tcp:loopback blocked | VIOLATION | Offline connection reached the local receiver |
| Child tcp:loopback blocked | VIOLATION | Offline connection reached the local receiver |
| tcp:nonloopback blocked | VIOLATION | Offline connection reached the local receiver |
| Child tcp:nonloopback blocked | VIOLATION | Offline connection reached the local receiver |
| tcp:internet blocked | PASS | Controls succeeded; restricted behavior matches contract |
| Child tcp:internet blocked | PASS | Controls succeeded; restricted behavior matches contract |
