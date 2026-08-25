# Astronaut gaps accepted for the PoC

- **Compaction signal.** The log has no ground truth; a wrong number that ran cleanly (paise) is
  invisible to the compactor. Only errors, retries, scope notes and user corrections are signal.
  Later: a "that's wrong" button on every answer writing a correction entry to the log.
- **Dilution budget.** No cap on how many skills fire per question; the 9B's prompt grows with each
  hint. Misfire suite exists (`benchmarks/astronaut/`), a firing budget does not.
- **Skill precedence.** Same-name override by layer (folder > user > builtin) only; no conflict detection
  between two skills claiming the same column.
- **Auto-compaction** stub not wired (user-triggered only, as specified).
- **Template skills** are used verbatim when the question regex matches — no parameterisation.
- **Telegram shell** runs only while the laptop and the io app are open; a remote bot needs the
  kernel's tool API reachable from the server (tunnel) or the data on the server — neither for the event.
- **Astronaut harness on the laptop**: Hermes is a 3.8 GB container; the event path is the kernel +
  skills + Telegram shell without an agent loop (see chronology 2026-08-24 for the measurement).
