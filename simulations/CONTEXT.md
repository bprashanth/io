# Context for brainstorming (paste-ready)

We are building tooling for "Insight Out" (Sep 2-4), a hands-on AI workshop for ~30 Indian
social-sector organisations (health, education, livelihoods, environment). From their intake
survey: precious data trapped in messy Excels, WhatsApp exports, field notes and PDFs; a
recurring wish - "make me a dashboard", "who needs intervention", "flag duplicates", "map my
sites"; and real anxiety about sending beneficiary data (names, phones, Aadhaar, addresses)
to cloud AI. The goal is for them to feel the power of frontier AI on their own data without
surrendering privacy. Everything is deliberately simple - a POC, not a product.

Two artifacts exist. First, a privacy-shield plugin for Antigravity (Google's agentic IDE):
a local proxy daemon scans the workspace files at rest with an on-device NER model (GLiNER,
CPU), builds a vault of real value -> stable code (NAME_001...), deterministically swaps
values in every model-bound request, restores them in answers and files the agent writes,
and blocks any request where a protected value survives. The user experiences normal
Antigravity; Google only ever sees codes; a status page makes it auditable. Second, io, a
minimal Electron desktop app for the serious-privacy user: point at a folder, review
highlighted PII (click to keep), see exactly what will leave, chat; dashboards come back as
pages, shareable on the LAN, names rehydrated only locally.

Extension directions worth exploring: other shells over the same privacy kernel (a Telegram
bot shell exists in prototype; WhatsApp is where these orgs live); harnesses that act rather
than answer (a coding agent built a working local app from tokenised data in ~2.5 min - the
"workshop lane"); small local models (Qwen-class 9B) for fully-offline answers with receipts
vs frontier-with-redaction; local retrieval (BM25 + computed per-file summaries) for big
folders; skills/memory so the system learns each org's data quirks. Hard constraints: NGO
laptops, no GPUs, low budgets, robustness beats cleverness.
