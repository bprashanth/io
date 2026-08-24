# 2026-08-26 01:00 - io: doc preview + honest meta + ~name~ lookup + share links; shield 0.2.4 lifecycle; payload ROI; workshop probe

Checkpoint tag to revert to if this batch is disliked: `checkpoint-doc-scanner-v1`.

## io fixes (all verified in the running app, screenshots in benchmarks/runs/2026-08-26-io-fixes-v1/)

1. **Docs in Preview.** "This is what leaves" now shows documents too: the full tokenised
   text with every code boxed (01-doc-preview.png), same semantics as the xlsx grid.
2. **"0 rows sent as codes" was a counter bug, not a redaction hole.** The doc payload was
   always tokenised and leak-gated (verified: 29k chars of codes for the WhatsApp export).
   The meta line now counts documents: "320 rows + 560 lines sent as codes, model, 9.8s".
3. **~name~ closes the partial-name loop.** Typing `~divya` pops a dropdown of vault matches
   ("Divya Thorat  name"); picking inserts the full value, the strikethrough takes it, and the
   question leaves as NAME_xxx. Multiple matches force a choice; a closed `~divya~` with one
   match auto-resolves. Verified end to end: "what can you tell me about ~divya" -> full
   summary of her 31 visits and WhatsApp activity (02/03/04 screenshots).
4. **Share on your network.** Each built page gets "share on your network": a second listener
   on 0.0.0.0 serves ONLY explicitly shared pages (the main API stays loopback); the link is
   copied to the clipboard. A phone on the same wifi renders the dashboard with real names,
   rehydrated locally before sharing (06-shared-page-lan.png). This is the io answer to "how
   do I share this dashboard like a link" - no GitHub Pages, no upload.

## Shield 0.2.4 (extension/privacy-shield, vsix built)

Fresh-laptop e2e on a cloned profile with an empty extensions dir, AG 1.107.0 on Xvfb, driven
over CDP (screenshots in benchmarks/runs/2026-08-26-ag-plugin-e2e/). What the run caught:

- **Restricted Mode silence.** A fresh folder opens untrusted; pre-0.2.4 the shield simply
  never activated - no status item, no protection, no warning. 0.2.4 declares
  untrustedWorkspaces support: a shield that only runs a local daemon must not go silent.
- **Foreign-daemon adoption.** With a daemon from ANOTHER profile alive on 8765, the fresh
  install showed "Shield on" without spawning anything - adopted someone else's daemon and
  vault. 0.2.4: status.json reports its `server` dir; the extension only adopts its own.
- **Uninstall leak.** The daemon (deliberately spawned outside the process tree) outlives
  uninstall, and settings keep routing AG at it. 0.2.4 ships a vscode:uninstall hook that
  quits this install's daemon(s) and removes jetski.cloudCodeUrl when it points at them.
- The one-time install actually costs ~500 MB download / 1.7 GB disk (message said 200 MB);
  copy fixed. Install UX is good: terminal run ending in "privacy shield environment ready".
- **Updates wiped the environment.** Upgrading 0.2.3 -> 0.2.4 made the IDE delete the old
  versioned extension folder - and the 1.7 GB venv and model cache inside it, forcing a full
  reinstall on every update. 0.2.4 moves the env to globalStorage (survives updates); the
  legacy in-extension venv is still honoured, and uninstall removes the env (vault kept).
- **Catch-and-replace verified in the real Agent flow** (0.2.3 daemon, fresh profile): asked
  the Agent for a dashboard from the PII csv; the in-chat consent fired ("ask before a table
  first leaves"), the model's turn carries the shield annotation ("shield: ... 486 ms
  redaction, vault 13"), the status bar reads "5 calls - 487 ms - vault 13", and the audit:
  dash.html on disk has 114 real-name occurrences (rehydrated locally) while the wire view of
  what left has 10 distinct codes and zero real names.
- `TROUBLESHOOTING.md`: status bar states, the status page as a token audit
  (calls, bytes_out, tokens_est_out, blocked, vault_entries, `server` identity), both logs,
  and the failure table for demo-day diagnosis.

## Payload ROI (the size-limit decision)

Corpus: a generated 120-file, 18.5 MB NGO shared drive (60 visit CSVs, 24 attendance CSVs,
12 WhatsApp exports, 12 narrative reports, donor CRM, grant letters; seeded, gold answers
recomputed independently) and 12 questions in three kinds: single-file, cross-file
aggregate, needle-in-many-files. Gemini 3.7 Flash, redacted payloads and questions,
answers rehydrated then graded. Script + raw answers: `benchmarks/runs/2026-08-26-payload-roi/`.

| condition | correct | avg payload |
|---|---|---|
| today's io (all files, 150 KB cap) | 0/12 | 147 KB |
| option 1: naive caps (5 files, 1 MB each) | 0/12 | 34 KB |
| option 2: BM25 top chunks (60 KB) | 5/12 | 61 KB |
| BM25 chunks + local manifest | **7/12** | 73 KB |
| whole-file selection + manifest | 5/12 | 105 KB |

Readings:
- The complaint is real: on a big folder today's io sends truncated fragments and the model
  answers "file not provided". Naive caps pick the wrong files and also score zero. Both out.
- Retrieval is the answer, but the two variants are complementary: chunks find needles,
  whole files count correctly (the chunk run answered "24" where the whole file says 43).
- The **local manifest** (per-file row counts and numeric sums, computed on the laptop) is
  what rescues aggregates - it costs nothing and lifted BM25 from 5 to 7.
- What stays unsolved by any payload strategy: needles across 60 files and folder-wide
  computations - those are local-compute questions (the ask lane / the deferred harness
  discussion), not context questions.
- Cost is a non-issue at this size: every condition lands under a cent per question on
  flash; the ROI is quality, not dollars.

Recommendation for io: BM25 selection over the redacted corpus with (a) whole-file
promotion when a file is named or one file dominates the scores, (b) the local manifest
always included, (c) the existing @ mention as the explicit override, and (d) a visible
"searched N files, sent M" line so the user knows what the model saw. Caps only as an
outer safety bound, not as the selection mechanism.

## Workshop probe (actions on the laptop)

codex CLI + frontier over a tokenised workspace built and verified a working dashboard app in
2m38s / 37k tokens with zero real values anywhere; the server must be owned by io (it died
with the harness). Full analysis and proposed lane shape:
`backlog/2026-08-26-actions-lane-workshop.md`.
