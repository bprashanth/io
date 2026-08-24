# io (minimal)

Point io at a folder. It shows what will leave as codes; you correct it by clicking. Then talk.

- Start: `cd app/io && npm install && npm start` (needs Node 18+; Python comes from the installed
  privacy-shield extension's venv, which carries the tested scanner — GLiNER, CPU-only).
  Headless: run `service.py 8801` with that venv and open `http://127.0.0.1:8801/`.
- Provider: an OpenRouter API key, or any OpenAI-compatible server address. Kept in memory;
  asked again on restart. Model defaults to `google/gemini-3.7-flash`; change it in settings (⚙).
- The sheet view highlights what the scanner flagged, with the reason under each header.
  Click a column to change it. Decisions are remembered by header signature
  (`~/.config/io/decisions.json`), the vault per folder (`vault-…-local-only.json`), exactly
  like the shield plugin.
- Questions and answers pass through the same vault both ways. A value you type that is coded
  strikes through as you type. Every answer says how many rows left as codes.
- Pages/dashboards: the model writes the page against `window.data`; io pours the real rows in
  locally, so figures are computed in your browser over the true data.

Engine: `benchmarks/pii/{columns,detect,pseudonymize}.py` — the privacy-shield modules, unchanged.
