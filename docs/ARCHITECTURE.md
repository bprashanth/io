# io architecture

## Why io exists instead of plain Codex

The people io is for work at non-profits in India. Their spreadsheets hold beneficiaries'
names, phone numbers, villages, Aadhaar and bank details. They are not programmers, and most
have never used a terminal.

The OpenAI Codex CLI is a capable assistant for exactly the work they need: read a
spreadsheet, answer a question about it, draw a chart, clean a column. Used as it ships, it
has three problems for this audience:

1. **Everything goes to the model in the clear.** The person's question, and every file
   Codex reads to answer it, is sent to OpenAI as it is.
2. **Its commands run with the person's own access.** A command it runs can read any file the
   person can read and, depending on settings, reach the internet.
3. **It speaks to programmers.** It asks about paths, shells and permissions, and it prints
   code.

io is a small desktop app that runs the real Codex CLI inside it and fixes those three things
without changing what Codex can do on the folder the person chose.

## The pieces

```
  the person
     |
  io window (Electron)          review sheet, settings, terminal, viewer, toolbox
     |
  Codex CLI (bundled)  ---- commands ---->  the wall (Codex's sandbox, io's profile)
     |                                         reads/writes the chosen folder only
     | model traffic
     v
  io's proxy (local)   names, places, phones -> codes out; codes -> values back
     |
     v
  model provider       sees codes only
```

- **The review.** Before anything runs, io scans the chosen folder, shows the person which
  columns and values it will hide, and lets them preview exactly what will leave. What they
  approve becomes the folder's vault of codes.
- **The proxy** sits between Codex and the model provider on the person's own computer. See
  [tokenization.md](tokenization.md).
- **The wall** is Codex's own sandbox, run under a permissions profile io writes. The person
  picks how much it lets commands reach. See [sandboxing.md](sandboxing.md).
- **The model** is ChatGPT through the person's own sign-in today. An explicit OpenRouter fallback is available when
  that allowance runs out. See [model-switching.md](model-switching.md).

- **The build people get** is the thin one, scanning on the organisers' privacy server. See
  [distribution.md](distribution.md).

The detailed design and the exact privacy claim are in [io-codex.md](io-codex.md).

## How io controls Codex

io never patches Codex. It controls it through two files it owns, in a Codex home that
belongs to io alone (`~/.local/share/io/codex/home`, or on the USB stick in portable mode).
The person's own Codex setup in `~/.codex` is never read or written.

**The profile, `io.config.toml`.** Rewritten from scratch every time io launches Codex. It
points Codex's model traffic at io's proxy, switches off OpenAI-hosted plugins and telemetry,
closes the "run this outside the sandbox?" prompt, registers io's toolbox, and holds the
permissions profile that is the wall. Codex's own `config.toml` beside it is left for the
person's `/model` choice.

**The instructions, `AGENTS.md`.** Codex reads this file as standing instructions from the
person it is working for. io writes it, from `agentsMd()` in `app/io/codex.js`, and says
things like: you are talking to non-programmers; use plain words and no jargon; never ask a
technical question back; draw charts as pictures and pages as single files; codes like
`NAME_001` are ordinary labels, do not try to work out what they stand for; stay in this
folder.

Three properties of that file matter:

- **It is regenerated at every launch.** That covers a fresh start, a change of setting and a
  resumed thread. io never edits it in place, so whatever it needs to say for this launch, it
  writes, and the next launch replaces it. Nothing has to be cleaned up.
- **It travels with every request.** Codex sends its contents to the model as part of each
  turn. It passes through the proxy like everything else.
- **It is the one file in io's Codex home that commands inside the wall may read.** Everything
  else there, the sign-in token above all, is out of their reach.

Because it is rewritten per launch and read from the first turn, it is also the natural place
to hand a conversation from one model to another. See [model-switching.md](model-switching.md).

## The edges, in one place

These are the places where the protection is thinner than it looks, and where the design
work has gone. Each is covered in the linked doc.

| edge | what happens | where |
|---|---|---|
| Values the vault does not hold | amounts, dates, free-text notes go to the model as themselves | [tokenization.md](tokenization.md) |
| Pictures | the proxy cannot see inside an image, so io decides what a picture shows where it is made | [tokenization.md](tokenization.md) |
| Commands and the internet | the proxy never sees command traffic; only the wall limits it | [sandboxing.md](sandboxing.md) |
| A page Codex writes | once opened in a browser it can send anything it contains anywhere, so io shows it in a window with no network | [sandboxing.md](sandboxing.md) |
| A computer where the wall cannot run | io says so, offers a one-time setup where one exists, and otherwise runs without the wall only after saying what that costs | [sandboxing.md](sandboxing.md) |
| A conversation with an attached file | io asks whether the file is private; a private attachment makes commands offline before they can see it | [sandboxing.md](sandboxing.md) |
| Scanning on the privacy server | the text being scanned leaves the laptop, and is readable at Cloudflare's edge | [distribution.md](distribution.md) |
| Another model provider | codes still hold, but values outside the vault reach whoever runs that model | [model-switching.md](model-switching.md) |

## Where the evidence is

Every claim in these docs was measured on a laptop, on the DGX, or both. The measurements are
in `chronology/`, the argument they add up to is in
`narrative/2026-09-15-sandboxing-field-note.md`, and designs not yet built are in
`proposals/`. How agents working on io hand work to each other is in
[agent-handoff.md](agent-handoff.md).
