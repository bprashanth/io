# Establish the command boundary before testing io

The first native CI experiment asked a narrower question than whether io is secure:
can the particular Codex package io ships enforce the filesystem and networking permissions
io generates? That distinction made the failures useful.

The [three runs](../chronology/2026-09-27T1044-dgx-codex-sandbox-baseline-established.md)
produced three different kinds of evidence. macOS passed on Intel and arm64 without adding
Seatbelt code to io: Codex supplies its own native backend. Linux first failed to create the
sandbox, then passed after the same narrow AppArmor setup already used on the DGX. Windows
first rejected a Unix path in io's generated configuration, then rejected restricted reads
because io selects the unelevated backend.

None of those Windows errors was an io warning standing in for a security experiment. The
harness never opened io. It invoked the bundled executable directly, with an interpreter
that first demonstrated it could read, write and connect to every synthetic target outside
the sandbox. Codex itself refused to execute the restricted-read policy.

To learn about Windows networking we therefore needed a different, labeled question. With
root read permission enabled, the unelevated backend starts. Under that diagnostic policy,
write restrictions held while parent and child Python processes connected directly to the
internet even though networking was disabled. Proxy-aware client failures would have hidden
this distinction. The diagnostic cannot count as io conformance, because it deliberately
relaxes the read boundary io needs.

An elevated-backend trial gives a plausible next direction, not a completed solution: its
Open run enforces the filesystem boundary, but its Offline run fails to create the child
process. The next investigation must resolve that execution failure and demonstrate a usable
Offline command that cannot connect. A command that cannot start is not proof of isolation.

The required gate remains red. It should become green only when the actual intended policy
allows the useful operations and refuses the forbidden ones on every target, with working
controls. After that, io's real launch path must preserve the same result. Proxy behavior,
private attachments, credential handling and generated-page isolation are later questions;
passing this small contract does not answer them.
