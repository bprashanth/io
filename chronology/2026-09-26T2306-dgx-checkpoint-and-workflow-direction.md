# DGX checkpoint and next workflow discussion

Checkpoint requested by the owner after the six-feature implementation.
Current branch: `io_codex_3`. Implementation commit: `755d7f7`,
"Protect private attachments, add OpenRouter fallback, and make thin setup server-first".
Not pushed. Full measured results and limitations are in
[the implementation entry](2026-09-26T2220-dgx-six-feature-implementation.md).

Recorded verification remains 77 passing tests, real Electron/Playwright drives with live
OpenRouter, actual Linux wall/control probes, and a packaged Linux arm64 smoke. The final
224 MiB thin tar archive passed gzip integrity verification and is located at
`~/.local/share/io-builds/2026-09-26/io-linux-arm64-thin.tar.gz`. No tests were rerun for this
documentation checkpoint. Preexisting untracked September 14 evidence and `docs/sandbox.md`
remain untouched.

## Next discussion, not an implementation decision

The owner wants NGO users to build their own useful tools without having to choose technical
architecture for common cases. The example is a local web interface over a multi-sheet Excel
workbook or local SQL data, displayed inside io. They asked whether to leave the workflow to
Codex or supply something canned. No new app workflow has been authorized for implementation
yet; this turn is a brief design discussion.

Initial recommendation: provide a tested local app foundation and a small set of workflow
recipes, with Codex adapting screens and domain rules. Start with "turn this workbook into a
tracker": inspect sheets, show proposed relationships, make a searchable list and detail
view, then add controlled editing if requested. Ask about the work (what is tracked, what
changes, who uses it), not database/framework choices.

Proposed defaults to discuss: keep read-only Excel views backed by the workbook; for an
editable tracker use a local SQLite working store with explicit Excel import/export and a
clear statement that the original workbook is not continuously synchronized. Do not create
two silent sources of truth. A team using separate computers is a separate product boundary
that requires an explicit shared-service decision, not an invisible extension of a local app.

The reusable foundation would own storage, backup/undo, validation, restart/reopen and the
viewer/data access boundary. A prompt recipe alone cannot enforce these properties. These
are proposals; this checkpoint adds no dependency, server, write API or privacy exception.
