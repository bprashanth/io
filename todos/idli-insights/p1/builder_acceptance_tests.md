# The Builder's exit test: the failing request becomes the person's test

Owner idea, 2026-11-16, agreed as a p1 todo. Context: [MODEL_TYPES](../../../narrative/MODEL_TYPES.md). On the
laptop the Builder made a photo reader that passed its own fake-sample test, but read the owner's real table image
badly. Nothing asked the person "is this good enough?".

## The flow

1. **Ask for the exit test first.** The Builder gets the failing request, for example "what does this table
   indicate? @finance_caste_table.png". Before building, it asks one plain question with a suggestion: "When is
   this good enough? Suggested: the table's rows and columns match the picture." The answer goes into the
   manifest as the capability's acceptance check: the question shown to the person, plus checks code can run
   (minimum rows, columns, average confidence).
2. **Build and test on fake samples,** as today (`team_check`).
3. **Try it on the real file, on this computer.** A new Builder tool, `team_try`, runs the capability on the file
   from the failing request. The person sees the result in the left pane beside the original (the picture and
   the table side by side): "Is this right?" Yes / No, with a box for what's wrong.
4. **The Builder never sees the result.** It gets only:
   - yes or no;
   - the person's note, masked;
   - plain numbers: rows, columns, average confidence, empty cells.
5. **On No, take the next option on the capability menu,** and say so: "Tesseract read 12 rows at confidence 31.
   Try RapidOCR next?" The order is local, then a better local tool, then the private model, then outside (only
   after unmasking, with a yes).
6. **On Yes, keep it as an acceptance test.** It stays in the team's private folder (for example
   `.idli/acceptance/`), not in `extensions/` git, because it comes from a real file. It holds the file's
   fingerprint, the person's yes, and the checks. If a later version changes what that file produces, Idli asks
   the person again before using the change.

## Pieces to build

- A side-by-side review card (built on the privacy review page): the original file next to the reader's tables.
- `team_try` in the Builder's tools. It returns only yes/no, the masked note and the numbers.
- An acceptance store, rerun by `team_check`. A changed result means asking the person again, not failing
  silently.
- Manifest fields: `accept.ask` (the question) and `accept.checks`.
- Readers declare which menu option they use, so the next option can be suggested.

## Evidence for the menu order (images)

See `benchmarks/runs/2026-11-16-image-reading/REPORT.md`. On the owner's real table screenshots:
- Tesseract: 0 to 6% of cells right;
- RapidOCR: 91 to 100%;
- the 9B with its vision projector: 96 to 100%, in 6 to 8 s;
- Muse at low reasoning effort: 82 to 100%.
