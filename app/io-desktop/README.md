# io desktop (T0 prototype)

A small desktop app for the "Laptop" reach tier of `proposals/pii_idli.md`:
point it at a folder of CSV / Excel files, ask questions, or ask for a
dashboard / report. The model only ever sees **column names and a list of
category values**; every number on screen is the result of a DuckDB query
that ran on your machine. Pages are drawn by a deterministic renderer from a
*plan* the model returns (panels + SQL), never from model-written HTML.

```
Electron window  ──►  server/io_service.py (127.0.0.1, picks a free port ≥ 8791)
                         │  DuckDB over the folder's files (dates auto-typed,
                         │  spelling-normalised join columns computed locally)
                         │  Ask lane:  question → SQL → run → table / auto chart
                         │  Build lane: request → plan JSON → run each panel → page
                         └─► model: local llama.cpp / Ollama URL   or   OpenRouter + key
```

## Install on a laptop

Needs Python 3.10+ and Node 18+.

```
cd app/io-desktop
./install.sh          # Windows: powershell -ExecutionPolicy Bypass -File install.ps1
npm start
```

`install.sh` creates `.venv` with duckdb, pandas, openpyxl, sqlglot (no torch,
no model weights) and installs Electron. No service runs when the app is
closed; the Python process is a child of the window.

## Configure the model

Click **Settings** in the sidebar.

- **OpenRouter**: paste a key, model defaults to `qwen/qwen3.5-9b` (the
  model chosen in `benchmarks/runs/2026-08-22-t0-*`). The key is saved to
  `~/.config/io-desktop/config.json` with mode 600; it is never written into
  the repo.
- **Local**: any OpenAI-compatible server. For the same model on CPU:
  `llama-server -m Qwen3.5-9B-Q4_K_M.gguf -c 6144 -b 256 -ub 256 --jinja --reasoning-budget 0 -fa on --cache-type-k q8_0 --cache-type-v q8_0`
  (5.2 GB resident; ~17 tokens/s on 8 CPU threads; first answer ~30 s,
  follow-ups ~15 s thanks to prefix caching). Under an 8 GB cap the 8192
  context was OOM-killed; 6144 survives.

Headless use without Electron: `python3 server/io_service.py 8791` and open
`http://127.0.0.1:8791/` in a browser.

## Three lanes

- **Ask** — question → one SQL query → table / auto chart, receipted.
- **Build** (say *dashboard* / *report*) — the model returns a plan of panels;
  every figure is a query result; narrative numbers are receipts.
- **Page** (say *app* / *form* / *website* / *PWA*) — the model writes the
  page itself; rows never go to it. If the request points at loaded data the
  laptop pours the rows in as `window.data` (snake_case keys) when the page
  opens. The page is syntax-checked before it is shown, runtime errors are
  reported back for one repair, and a page that shows none of your real
  values is called out as made up. "Download the page" saves the file.

## While you wait

The answer card lists what the app is doing (reading files, asking the
model, running queries, checking, rendering, repairing) with elapsed seconds.
A small model takes 2–40 s hosted and longer on a laptop CPU; the steps are
real, not decoration.

## Live

Save a file in the folder and the app reloads it: pages re-run their
receipts on the next view ("data as of …"), the last answers recompute, no
model call. Edit a value in the sheet, watch the ranking reorder.

## What the sidebar tells a participant

- **Files**: what was loaded, rows × columns; the spelling-normalised columns
  ("School (as in lpf_outreach)") are computed locally when two files name the
  same things differently.
- **Reach dial**: only *Laptop* is live in this prototype.
- **Egress this session**: calls, bytes, rows sent (always 0). Every answer
  shows "sent: column names only · rows: 0".
- Answers carry a receipt ("How this was computed") with the exact SQL and a
  CSV download of the real rows.

## Guard rails that are code, not model behaviour

- SQL is parsed with sqlglot; only a single read-only SELECT/WITH runs.
- Narrative numbers must be `{{receipt}}` placeholders; any digit the model
  typed itself is removed from the page and counted ("numeric-literal lint").
- KPI panels that return several rows are shown as tables; lines over raw
  numeric pairs become scatter plots; >20 bars are cut with a note; long
  labels switch to horizontal bars; percentage-looking columns outside 0–100
  get a visible "check this" flag.
- Follow-ups carry the last four turns, but a question that clearly points at
  other files starts a new topic (otherwise the 9B joins the wrong files).

## Known limits of the 9B at this tier (measured, see chronology 2026-08-23)

- Sign conventions ("endline minus baseline", "fall as a positive number") and
  aggregation level ("average of monthly rates") must be said explicitly.
- It reaches for a second file only when the question mentions it.
- When a request names something the data does not have (a "disbursed
  amount" with no amount column) it may compute a proxy under that title —
  open the receipt.
- Dashboards come out complete and clean; prose in reports is generic.

## Astronaut mode (Settings → Astronaut)

io does not self-learn; it asks permission to remember. With astronaut on:

- **Propose skills from my usage** — with your consent, a remote model (the trusted 27B or a
  frontier model) reads this folder's interaction log (questions, queries, errors — never rows)
  and proposes skills as cards. Edit, approve or discard; approved skills apply from the next
  question. Cards that contain data values are blocked.
- **Add a skill** — a guided form: a hint about a table, a rule for a kind of question, a mapping
  for differently-named columns across files, or a correction to how a file is read (dates
  month-first, header on row N). Preview shows where it would fire.
- **See why** — click any file: header row found, blocks merged, dates typed and which way,
  numbers parsed from text, ids kept as text, skills fired. "This was read wrong — correct it"
  opens the wizard on that file.
- **Telegram** — paste a bot token from @BotFather; the bot runs from this laptop while the app
  is open. `/reach` changes who answers; every reply says what left the laptop (column names only,
  rows 0). `/why`, `/skills`, `/propose`, `/approve N`.

Skills are JSON files: built-in (`skills/builtin/`), yours (`~/.config/io-desktop/skills/`), and
per folder (`<folder>/.io/skills/`).
