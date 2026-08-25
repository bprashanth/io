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

## Recall against planted PII (fresh fixtures, `benchmarks/t0/text-fixtures/`)

Nine generated fixtures (blog, annual report extract, helpline log, 260-line Ekibeki-style
WhatsApp chat, Telegram export, PDF letter, three mixed spreadsheets) with a gold file of every
planted value and its occurrence count (`gold.json`, generator seeded and byte-reproducible).
Mention-level measurement (`benchmarks/runs/2026-08-25-io-docs-v1/measure_recall.py`): every
occurrence of every planted value must fall inside a highlighted span.

| file | class | mentions | covered |
|---|---|---|---|
| annual_report_extract.txt | person / email / pan | 11 / 2 / 1 | all |
| donor_thankyou.pdf | person / email / phone | 7 / 1 / 1 | all (the phone was split across a line break by PDF extraction and still caught: the span is `+91\n62115 63890`) |
| field_visit_blog.txt | person / phone / email / aadhaar / account / ifsc | 17 / 3 / 2 / 1 / 1 / 1 | all |
| helpline_log.txt | person / phone | 40 / 21 | all |
| telegram_export.txt | person / phone | 93 / 13 | all (the `[dd.mm.yy hh:mm] Name:` sender format is caught without a second chat-line rule) |
| whatsapp_ekibeki.txt | person / phone | 265 / 18 | all |

**498/498 mentions covered.** The cost is over-marking: the Telegram export shows 194 spans for
about 106 planted mentions - the title-cased GLiNER pass flags some Hindi phrases ("bhej sakta
hai") as entities. Click-to-keep is the remedy and the trade is the right one for a shield.

## Mixed spreadsheets (the header trap)

`mixed_headers.csv` disguises Aadhaar numbers as "Item Code", emails as "Batch" and names inside
"QC Notes". The rule ladder hid all three from the values, not the headers: "why: account
numbers", "why: emails", "why: in some cells" (per-cell shading on exactly the 15 cells carrying
names). `sports_day.xlsx` shades Participant, Guardian Mobile and the Remarks cells that carry a
substitute contact, leaving clean Remarks cells alone - the column-vs-cell rule as specced. One
over-caution: "House" (Green/Red House values) is flagged as villages; a header click keeps it.

## Ekibeki extraction on the fixture chat

`@whatsapp_ekibeki ... extract the recurring reporting patterns` on the 260-line generated chat:
the model (restricted by the mention to that one file, seeing only tokens) returned the five
message-format templates (`[Cluster] update: [X] artisans, [Y] toys done, [Z] pending orders`,
payment receipts, order confirmations, exhibition dates, contact shares - the last with
[NAME]/[PHONE] placeholders because those values were codes), per-cluster production and payment
summaries, and a proposed weekly summary table. Transcript:
`benchmarks/runs/2026-08-25-io-docs-v1/ekibeki_extraction.md`.

## Modal fix found by the run

Docs-only folders could not be opened from the UI at all: the scan modal counted only
spreadsheets, showed "excel / csv (none here)" and OK was dead (API tests had bypassed it). The
modal rows are now live: "whatsapp / text (5 files, scanned on this laptop)", "pdf (1 file...)",
each dimmed only when absent. pypdf added to install.sh/install.ps1. Screenshots 09-14.
