# 2026-08-25 03:00 - io: text/pdf/chat scanning, find-and-redact, plain-words labels, @ file mentions

Built on the minimal app (`app/io/`), same engine, same theming. Screenshots:
`benchmarks/runs/2026-08-25-io-docs-v1/`.

## Document scanner

`.txt`, `.md`, `.log` and `.pdf` (text extracted with pypdf) now load beside spreadsheets. The
detector is the stage-3 `textv2` engine unchanged: regex validators + the chat-line rule (WhatsApp
`dd/mm/yy, hh:mm - Name:` senders are marked deterministically; Telegram-style lines fall to the
same rule when they match) + GLiNER over the text and its title-cased twin + propagation of every
found name/place to all its occurrences. The review view is the document itself with every span
highlighted; clicking a highlight keeps it (and clicking a kept one hides it again), exactly like
cells in the sheet view.

## Find and redact

A find box on the document: typing shows "27 hits, 0 redacted" and a "Redact all" button; after
clicking, "27 hits, 27 redacted". The term is remembered per file (decisions store) and applied to
every occurrence; clicking any term-highlight removes the term everywhere. Verified live on the
WhatsApp export ("signal": 27/0 -> 27/27 -> removed -> 27/0; "Maval" was already 8/8 because the
village propagates from the scanner itself).

## Plain-words scanning

"hide: names, addresses, account ids" - the words go to GLiNER as zero-shot labels over the
document (threshold 0.35) and the new spans join the review with the same click-to-keep. Tested
with "money amounts, dates" on the chat export: 36 new spans. Labels are remembered per file.

## @ file mentions in chat

Typing `@` opens a file list (arrow keys + Enter, or click); the mention renders amber in the
input mirror. A mentioned question sends ONLY that file's redacted content; the answer line names
the files used. General questions still send everything (the payload-size problem for big folders
is noted and deferred - the harness discussion). Live strikethrough still applies over the whole
question including names typed around the mention.

## Verified end to end (gram-sudhar corpus)

`@whatsapp_field_group_export which villages report children attending... extract the pattern` ->
the model, seeing only tokenised chat, extracted the reporting patterns ("[count] bacche the
[centre] par", session summaries) - the Ekibeki ask from the survey ("communication getting lost
in WhatsApp groups"). Then "how many times did ~~Swati Khan~~ report from ~~Maval~~" (both struck
through as typed) -> answer came back rehydrated citing the exact chat line. 1679 spans highlighted
on the chat export review.

Recall against planted PII in fresh text fixtures (blogs, annual report extract, helpline log,
Ekibeki-style chat, Telegram export, PDF letter): see the table appended below when the fixture
run completed.
