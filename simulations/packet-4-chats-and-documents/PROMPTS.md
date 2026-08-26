# packet-4: chats, text and PDF (the Ekibeki case)

Survey row 28 (Ekibeki, crafts livelihoods): "Communication getting lost in WhatsApp groups."
This packet is documents rather than spreadsheets: WhatsApp exports, a Telegram export, a
field blog, a helpline log, a PDF letter. All synthetic; the data is already in the repo -
do not copy it, open these folders directly:

- `benchmarks/t0/text-fixtures/`  (whatsapp_ekibeki.txt - 260-line field group chat,
  telegram_export.txt, field_visit_blog.txt, helpline_log.txt, annual_report_extract.txt,
  donor_thankyou.pdf)
- `benchmarks/t0/ngo-corpus/gram-sudhar/`  (a visit-log CSV plus a larger WhatsApp export -
  good for mixing tables and chat in one folder)

## Questions that were actually run (io)

1. Open text-fixtures as a sheltered dir. In the review, try the find box on the chat:
   type a village or person you can see highlighted - the counter reads like "8 hits,
   8 redacted". Type a harmless word ("signal") - "27 hits, 0 redacted" - press Redact all,
   then click one of those highlights to un-redact them again.
2. In chat: `@whatsapp_ekibeki this is a field WhatsApp group. Communication gets lost in
   here. Extract the recurring reporting patterns: what do people report, in what format,
   how often, and what would a weekly summary table look like?`
   We measured: the model, seeing only codes, extracted the five recurring message formats
   ("[Cluster] update: [X] artisans, [Y] toys done...") and proposed a weekly summary table.
   Transcript: `benchmarks/runs/2026-08-25-io-docs-v1/ekibeki_extraction.md`.
3. On gram-sudhar: ask `how many meetings were discussed in @whatsapp_field_group_export` -
   the meta line should count lines, not rows. Then try `~` in the chat box: type `~divya`
   and pick from the dropdown - the full name strikes through as you send, and the answer
   still knows who you mean.

## What to check

- Every planted name/phone in these fixtures is covered: we measured 498/498 PII mentions
  inside highlighted spans (`benchmarks/runs/2026-08-25-io-docs-v1/measure_recall.py`).
- In Antigravity with the shield: open text-fixtures as the workspace, wait out the
  blocking modal, then ask for a summary of the chat - ctrl+F a sender's name in the
  shield's "last request": zero hits.
- Over-marking is expected and honest: Hindi filler ("bhej sakta hai") sometimes gets
  highlighted; click-to-keep is the remedy. Note anything that feels annoying in practice.
