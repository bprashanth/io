# Hive mind: ten laptops, ten 9Bs, one answer

## Context

Insight Out (Sep 2-4): ~30 social-sector orgs bring their real data - Excels, WhatsApp
exports, field notes - and use AI on it without surrendering privacy. What exists today
(the io desktop app): point it at a folder, an on-device scanner replaces personal data
with stable codes (NAME_001...), the user reviews and approves what leaves, asks plain
questions, and every question fans out blind to three models (laptop 9B, mid 27B,
frontier) over the same coded payload; the user votes for the best answer without
knowing which model wrote it, and votes land on a room board with a why.

## What the blind test already taught us

- Language work (explain, rewrite): the 9B ties or beats the big models.
- Data interpretation: the 9B invents numbers ("Khed, 3909" for a sum that is Shirur
  2,866) and once said 0 students were enrolled in a file with 320 rows.
- Precise aggregation: all three tiers failed the same wide-format sum.
- Big contexts hurt the small model most: attention, not window, is its limit. Give a
  9B 50k tokens of rows and it grabs the wrong cells; give it one file and one narrow
  task and it is respectable.

## The idea

The event room has ~10 capable laptops, each able to run one 9B locally. Treat them as
one machine:

- Participants' (coded) data folders are shared across the LAN - every laptop can read
  every folder's tokenised copy. Real values never leave any laptop's vault.
- A question like "which sites need intervention and why" is decomposed into narrow,
  file-scoped chunks: "sum attendance per site in file A", "list children below fitness
  threshold in file B", "extract complaints from chat C". Chunks are farmed in parallel
  to the 9Bs, one focused chunk of data and one focused unit of compute each - then the
  partial results are combined into the final answer.
- Two planner options: (a) a frontier model plans - it sees only the redacted question
  and the folder manifest (file names, columns, row counts), never data rows; only the
  local 9Bs touch the coded data. (b) best case, a 9B itself plans - fully local, and
  the experiment is whether planning survives at 9B scale.
- "Build me a dashboard" farms differently: chunks compute per-file aggregates (JSON),
  a single assembly step (frontier or the best local answer) turns merged aggregates
  into one page. The laptop that asked renders and rehydrates.

## The question to settle

Is this "90B" - ten focused 9Bs plus a planner - as good as or better than one 27B on
the same tasks? The blind-test machinery answers it directly: add "hive" as a fourth
anonymous card and let the room vote. The bet: a 9B is made smarter two ways at once -
a deterministic pipeline around it, and a narrow slice of data with dedicated compute
inside it. Map-reduce for attention, not for disk.

Open questions: chunk failure and retry (a 9B chunk can still invent - do chunks come
back with receipts, e.g. row counts the merger can check?); LAN scheduling (a dumb
queue is probably enough for 10 nodes); latency (parallel chunks may beat one 27B's
single long call); and whether the planner's decomposition is itself the hard 20%.
