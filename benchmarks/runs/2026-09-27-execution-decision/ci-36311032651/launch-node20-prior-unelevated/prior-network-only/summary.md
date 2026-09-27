# Codex sandbox conformance: win32-x64

Overall: **FAIL**

**Diagnostic only: unelevated-network. Ineligible for the io conformance gate.**

| Property | Result | Reason |
|---|---|---|
| Workspace read | PASS | Controls succeeded; restricted behavior matches contract |
| Workspace write | PASS | Controls succeeded; restricted behavior matches contract |
| Outside read blocked | VIOLATION | Offline sandbox allowed a forbidden operation |
| Outside write blocked | PASS | Controls succeeded; restricted behavior matches contract |
| Symlink/junction read blocked | VIOLATION | Offline sandbox allowed a forbidden operation |
| Symlink/junction write blocked | PASS | Controls succeeded; restricted behavior matches contract |
| Child interpreter works | PASS | Controls succeeded; restricted behavior matches contract |
| Child Outside read blocked | VIOLATION | Offline sandbox allowed a forbidden operation |
| Child Outside write blocked | PASS | Controls succeeded; restricted behavior matches contract |
| Child Symlink/junction read blocked | VIOLATION | Offline sandbox allowed a forbidden operation |
| Child Symlink/junction write blocked | PASS | Controls succeeded; restricted behavior matches contract |
| tcp:loopback blocked | VIOLATION | Offline connection reached the local receiver |
| Child tcp:loopback blocked | VIOLATION | Offline connection reached the local receiver |
| tcp:nonloopback blocked | VIOLATION | Offline connection reached the local receiver |
| Child tcp:nonloopback blocked | VIOLATION | Offline connection reached the local receiver |
| tcp:internet blocked | VIOLATION | Offline sandbox allowed a forbidden operation |
| Child tcp:internet blocked | VIOLATION | Offline sandbox allowed a forbidden operation |
