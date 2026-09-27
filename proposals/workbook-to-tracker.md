# Workbook to tracker: a supported local workflow

Status: proposal, requested by the owner on 2026-09-27. No implementation or architecture
choice is approved by this document. Follows the discussion recorded in
[the checkpoint](../chronology/2026-09-26T2306-dgx-checkpoint-and-workflow-direction.md).

## The problem

An NGO has a workbook with sheets for people, visits and payments. Staff want to search for
a person, see their history, record a visit and produce a monthly report. They should not
need to choose a framework, database, hosting system or synchronization strategy before
trying a useful interface.

The hypothesis is that "turn this workbook into something easier to use" is a valuable first
workflow. It is a product hypothesis, not a claim established by user research.

## Recommendation

Provide one tested local app foundation and a workbook-to-tracker recipe. Codex adapts the
screens and domain rules. io owns the guarantees around data access, persistence, validation,
backups, undo and reopening the app. A prompt recipe can guide creation but cannot enforce
those guarantees on its own.

The first experience:

1. Select and review the workbook through io's existing privacy flow.
2. Inspect sheets and propose the entities and relationships. Show uncertainty rather than
   guessing joins from names or row positions.
3. Offer a searchable register with a detail/history view and simple summary reports.
4. Preview inside io with the original workbook intact.
5. Adapt through ordinary requests: "add a follow-up date", "show overdue visits", "export
   this month". Add editing only when requested and after the data ownership is explicit.

Ask questions about the work when answers affect correctness: whether a person can have
multiple visits, which identifier links sheets, what users can change, and whether colleagues
will use the app from separate computers. Supply technical defaults without asking users to
reason about database products.

## Proposed defaults

| Need | Default |
|---|---|
| Browse, filter or chart workbook data | Read the workbook; preserve the original |
| Enter and edit records through forms | Import into a local SQLite working database, with Excel export |
| Existing local database | Work with its structure where practical; inspect before changing |
| Concurrent use from separate computers | Explicit shared-app decision and setup |

There must be one clearly identified authoritative copy. Importing Excel into SQLite does
not silently create continuous two-way synchronization. Explain: "This app saves changes
here. Export an Excel copy whenever you need one." If continuing to edit the workbook in
Excel is essential, design an explicit refresh/reimport/conflict policy instead of hiding it.

A local-only app is not implicitly a shared team service. Accounts, concurrent changes,
access control, hosting and backup ownership need a separate decision when sharing is needed.

## What belongs in the reusable foundation

- Stable record identifiers and validated relations, plus clear import errors.
- Transactional changes, backups before migrations/imports, and recoverable edits.
- Explicit workbook refresh/import/export behavior and preservation of source files.
- A durable app entry in io that reopens with its saved data and supports rebuilding screens
  without silently replacing records.
- A narrow data interface scoped to the selected workspace, with validated operations and
  authorization outside generated page code.
- Real browser checks using synthetic workbooks, including multi-sheet relationships,
  missing identifiers, duplicates and interrupted writes.

The current contained viewer is not an approved CRUD runtime. Do not give generated HTML
arbitrary filesystem access, renderer IPC privileges, or a blanket localhost/network
exception to make this work. The viewer-to-data boundary needs a separate reviewed design
and security tests; existing masking and command-network rules must remain meaningful.

## First increment and open choices

Start with one well-tested searchable workbook register and detail view. Confirm with users
whether viewing existing records or entering/updating records is the first priority; that
answer sets the first implementation's scope. Follow with the local editable tracker, rather
than immediately building a large catalogue of templates.

Still to decide: the minimum app runtime/data API; workbook formula and formatting behavior
on export; explicit refresh semantics; which edits need undo; and how apps are reopened and
maintained as the workbook structure changes. No dependency or deployment choice is made here.
